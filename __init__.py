"""ComfyUI-Model-Downloader — 一键满速下载 ComfyUI 模板/工作流缺失模型.

纯 ComfyUI 插件, 无独立服务:
  - 后端随 ComfyUI 服务器进程运行, 随其退出而终止 (aria2 子进程带
    --stop-with-process 守护, ComfyUI 关闭时自动停止下载)
  - 前端以扩展 JS 形式运行在 ComfyUI 页面内, 页面关闭即卸载

后端接口:
  GET  /comfy_fetch/template_models/{id}  解析蓝图 id -> 模型清单
  GET  /comfy_fetch/status | /comfy_fetch/ping
  POST /comfy_fetch/check    {"models":[{"url","name","directory"}]} -> {"missing":[...]}
  POST /comfy_fetch/download {"models":[...]}  (支持运行中追加, 按 name+directory 去重)
  POST /comfy_fetch/retry | /cancel | /stop | /reorder | /delete | /reveal

前端 web/index.js: 浮动按钮 + 下载管理面板, 扫描工作流节点 properties.models,
检测缺失 (含完整性校验: .aria2 续传检测 / 大小 / SHA256), aria2c 并行下载.
"""
import asyncio
import glob
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import urllib.parse

from aiohttp import web

import folder_paths
import requests
from server import PromptServer

LOGGER = logging.getLogger("ComfyUI-Model-Downloader")

WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

HF_DIRECT = "https://huggingface.co"
HF_MIRROR = "https://hf-mirror.com"
MIN_FILE_SIZE = 1_000_000
MAX_CONCURRENT = 3
ARIA2_FALLBACKS = [r"C:\Users\x8987\AppData\Local\aria2\aria2c.exe"]

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLUEPRINTS_DIR = os.path.join(_BASE_DIR, "blueprints")

_STATE = {"running": False, "items": [], "queue": [], "procs": {}}


# ---------- 诊断: 请求日志中间件 + 心跳 ----------

def _install_request_logging():
    try:
        app = PromptServer.instance.app
        if app is not None:

            @web.middleware
            async def _log_bfp(request, handler):
                p = request.path
                interesting = p.startswith(("/extensions", "/comfy_fetch", "/global_subgraphs"))
                if interesting:
                    LOGGER.info("[BFP] %s %s", request.method, p)
                try:
                    resp = await handler(request)
                except Exception:
                    LOGGER.exception("[BFP] handler error %s", p)
                    raise
                if interesting:
                    LOGGER.info("[BFP] <- %s %s -> %s", request.method, p, resp.status)
                return resp

            app.middlewares.append(_log_bfp)
            LOGGER.info("[BFP] request logging middleware installed")
    except Exception:
        LOGGER.exception("[BFP] failed to install middleware")


_install_request_logging()


def _aria2c():
    p = shutil.which("aria2c")
    if p:
        return p
    for cand in ARIA2_FALLBACKS:
        if os.path.exists(cand):
            return cand
    return None


def _safe_name(name):
    n = os.path.basename(str(name or "").replace("\\", "/")).strip()
    if n in ("", ".", "..") or ".." in n:
        return None
    return n


def _safe_dir(directory):
    d = str(directory or "").strip().replace("\\", "/").strip("/")
    if not d:
        d = "checkpoints"
    parts = [p for p in d.split("/") if p]
    if not parts or any(not re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts):
        return None
    return "/".join(parts)


def _roots_for(directory):
    try:
        roots = folder_paths.get_folder_paths(directory)
        if roots:
            return [r for r in roots if r]
    except Exception:
        pass
    return [os.path.join(folder_paths.models_dir, directory)]


def _target_root(directory):
    roots = _roots_for(directory)
    for r in roots:
        if "ComfyUI-Shared" in r.replace("\\", "/"):
            return r
    return roots[0]


def _exists(name, roots):
    for r in roots:
        p = os.path.join(r, name)
        try:
            if os.path.exists(p) and os.path.getsize(p) > MIN_FILE_SIZE:
                return True
        except OSError:
            continue
    return False


def _mirror(url):
    if url.startswith(HF_DIRECT):
        return url.replace(HF_DIRECT, HF_MIRROR, 1)
    return url


def _normalize_models(models):
    """过滤/清洗请求里的模型列表, 返回合法项."""
    items = []
    for m in models or []:
        url = str(m.get("url") or "")
        if not url.startswith(("http://", "https://")):
            continue
        name = _safe_name(m.get("name"))
        if not name:
            name = _safe_name(urllib.parse.urlparse(url).path)
        directory = _safe_dir(m.get("directory"))
        if not name or not directory:
            continue
        item = {"url": url, "name": name, "directory": directory}
        reason = str(m.get("reason") or "")
        if reason in _REASON_OK:
            item["reason"] = reason
        items.append(item)
    return items


# ---------- 蓝图解析 (与核心 subgraph_manager 的 id 算法一致) ----------

def _blueprint_entries():
    out = {}
    for f in glob.glob(os.path.join(BLUEPRINTS_DIR, "*.json")):
        file = f.replace("\\", "/")
        eid = hashlib.sha256(f"templates{file}".encode()).hexdigest()
        out[eid] = f
    return out


def _extract_models_from_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return []
    seen = {}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "models" and isinstance(v, list):
                    for m in v:
                        if isinstance(m, dict) and m.get("url"):
                            seen[(m.get("name"), m.get("url"))] = {
                                "url": m["url"],
                                "name": m.get("name") or "",
                                "directory": m.get("directory") or "",
                            }
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d)
    return list(seen.values())


# ---------- 下载执行 (并行) ----------

def _find_item(name, directory):
    for it in _STATE["items"]:
        if it["name"] == name and it["directory"] == directory:
            return it
    return None


# ---------- 完整性校验 ----------

_EXPECTED_CACHE = {}   # url -> {"size": int|None, "sha256": str|None}
_VERIFIED = {}         # path -> (mtime_ns, size, ok)
_REASON_OK = {"missing", "incomplete", "size", "hash"}
HF_TOKEN = os.environ.get("HF_TOKEN") or None
HASH_SKIP_LIMIT = 2 * 1024**3   # 检查时超过 2GB 的文件跳过全量哈希 (下载完成时已校验过)
_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_cache.json")


def _load_cache():
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        for k, v in (raw.get("verified") or {}).items():
            if isinstance(v, list) and len(v) == 3:
                _VERIFIED[k] = (int(v[0]), int(v[1]), bool(v[2]))
        for k, v in (raw.get("expected") or {}).items():
            if isinstance(v, dict):
                _EXPECTED_CACHE[k] = v
    except Exception:
        pass


def _save_cache():
    try:
        tmp = _CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"verified": _VERIFIED, "expected": _EXPECTED_CACHE}, f)
        os.replace(tmp, _CACHE_PATH)
    except Exception:
        pass


_load_cache()


def _parse_hf(url):
    """解析 HF 直链 -> (owner, repo, rev, path). 非 HF 返回 None."""
    m = re.match(
        r"https?://(?:www\.)?(?:huggingface\.co|hf-mirror\.com)/"
        r"([^/]+)/([^/]+)/resolve/([^/]+)/(.+)", url)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


def _fetch_expected_sync(url):
    """从 HF API 获取文件预期大小和 SHA256 (LFS oid)."""
    hf = _parse_hf(url)
    if not hf:
        return {}
    owner, repo, rev, path = hf
    try:
        api = f"https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true"
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        r = requests.get(api, timeout=20, headers=headers)
        if r.status_code in (401, 403):
            code = r.headers.get("X-Error-Code") or ""
            msg = r.headers.get("X-Error-Message") or ""
            if code == "GatedRepo":
                return {"gated": True, "error": msg}
        r.raise_for_status()
        for entry in r.json():
            if entry.get("type") == "file" and entry.get("path") == path:
                lfs = entry.get("lfs") or {}
                out = {"size": entry.get("size")}
                if lfs.get("oid"):
                    out["sha256"] = lfs["oid"]
                return out
    except Exception as e:
        LOGGER.warning("[BFP] 获取预期元数据失败 %s: %s", url, e)
    return {}


def _gated_error_sync(url):
    """探测 403 是否因受限仓库(Gated)引起, 返回用户可读原因或 None."""
    try:
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"
        r = requests.head(url, timeout=15, headers=headers, allow_redirects=False)
        if r.status_code in (401, 403):
            code = r.headers.get("X-Error-Code") or ""
            if code == "GatedRepo":
                return ("受限仓库 (Gated): 该模型需先在 huggingface.co 上接受许可/申请访问, "
                        "并设置 HF_TOKEN 环境变量后重启 ComfyUI")
            return f"HTTP {r.status_code} (X-Error-Code: {code or '未知'})"
    except Exception:
        pass
    return None


def _expected(url):
    if url not in _EXPECTED_CACHE:
        _EXPECTED_CACHE[url] = _fetch_expected_sync(url)
        if _EXPECTED_CACHE[url]:
            _save_cache()
    return _EXPECTED_CACHE[url]


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _check_integrity(path, expected):
    """返回 (ok, reason). reason: missing/incomplete/size/hash."""
    if not os.path.exists(path):
        return False, "missing"
    try:
        size = os.path.getsize(path)
    except OSError:
        return False, "missing"
    if size <= MIN_FILE_SIZE:
        return False, "missing"
    if os.path.exists(path + ".aria2"):
        return False, "incomplete"   # 未下载完, aria2 可续传
    exp_size = expected.get("size")
    exp_hash = expected.get("sha256")
    if exp_size and size != exp_size:
        return False, "size"
    if exp_hash:
        try:
            st = os.stat(path)
            cache = _VERIFIED.get(path)
            if cache and cache[0] == st.st_mtime_ns and cache[1] == size:
                return cache[2], ""
            if size > HASH_SKIP_LIMIT:
                # 超大文件: 检查时跳过全量哈希 (下载完成时已做 SHA256 校验), 只验大小
                return True, ""
            ok = _file_sha256(path) == exp_hash
            _VERIFIED[path] = (st.st_mtime_ns, size, ok)
            _save_cache()
            if not ok:
                return False, "hash"
        except OSError:
            return False, "missing"
    return True, ""


def _do_check_sync(models):
    """同步版检查 (在 to_thread 中运行, 避免阻塞事件循环)."""
    missing = []
    for m in models:
        roots = _roots_for(m["directory"])
        found = None
        for r in roots:
            p = os.path.join(r, m["name"])
            if os.path.exists(p):
                found = p
                break
        if found is None:
            missing.append(dict(m, reason="missing"))
            continue
        expected = _expected(m["url"])
        ok, reason = _check_integrity(found, expected)
        if not ok:
            missing.append(dict(m, reason=reason))
    return missing


async def _download_one(aria, it, root_override=None):
    it["status"] = "downloading"
    it["progress"] = 0
    it.pop("speed", None)
    root = root_override or _target_root(it["directory"])
    os.makedirs(root, exist_ok=True)
    target = os.path.join(root, it["name"])
    try:
        if os.path.exists(target) and os.path.getsize(target) > MIN_FILE_SIZE:
            reason = it.get("reason")
            if reason in ("size", "hash"):
                # 损坏文件: 删除后全新下载
                try:
                    os.remove(target)
                except OSError:
                    pass
                try:
                    os.remove(target + ".aria2")
                except OSError:
                    pass
            else:
                # 已存在且无损坏标记: 跳过 (incomplete 的 .aria2 由 aria2 自动续传)
                it["status"] = "done"
                it["progress"] = 100
                return
    except OSError:
        pass

    url = _mirror(it["url"])
    exp = await asyncio.to_thread(_expected, url)
    if exp.get("gated") and not HF_TOKEN:
        it["status"] = "error"
        it["error"] = "受限仓库 (Gated): 需在 huggingface.co 申请访问并设置 HF_TOKEN 后重启 ComfyUI"
        return
    if not HF_TOKEN:
        pre = await asyncio.to_thread(_gated_error_sync, url)
        if pre and "Gated" in pre:
            # 下载前快速探测: 受限仓库直接失败, 给出明确指引
            it["status"] = "error"
            it["error"] = pre
            return
    args = [
        aria, "-x16", "-s16", "-k1M",
        "--file-allocation=none",
        "--auto-file-renaming=false",
        "--allow-overwrite=false",
        # 生命周期绑定: ComfyUI 进程退出时 aria2 自动停止
        f"--stop-with-process={os.getpid()}",
        "--max-tries=5", "--retry-wait=5",
        "--connect-timeout=30", "--timeout=60",
    ]
    if HF_TOKEN:
        args.append(f"--header=Authorization: Bearer {HF_TOKEN}")
    args += ["-d", root, "-o", it["name"], url]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _STATE["procs"][it["name"]] = proc
    try:
        buf = b""
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            lines = buf.replace(b"\r", b"\n").split(b"\n")
            buf = lines.pop()
            for line in lines:
                m = re.search(rb"\((\d+)%\)", line)
                if m:
                    it["progress"] = int(m.group(1))
                s = re.search(rb"DL:([0-9.]+)([KMG]?)(i?B)", line)
                if s:
                    it["speed"] = s.group(1).decode() + s.group(2).decode().lower() + "B/s"
        rc = await proc.wait()
    finally:
        _STATE["procs"].pop(it["name"], None)
    if it["status"] != "downloading":
        return  # 已被取消/停止, 不再覆盖状态
    try:
        if rc == 0 and os.path.exists(target) and os.path.getsize(target) > MIN_FILE_SIZE:
            exp = await asyncio.to_thread(_expected, url)
            exp_hash = exp.get("sha256")
            if exp_hash:
                ok = (await asyncio.to_thread(_file_sha256, target)) == exp_hash
                if not ok:
                    it["status"] = "error"
                    it["error"] = "SHA256 校验失败, 文件损坏"
                    return
                _VERIFIED.pop(target, None)
            it["status"] = "done"
            it["progress"] = 100
        else:
            it["status"] = "error"
            reason = await asyncio.to_thread(_gated_error_sync, url)
            it["error"] = reason or f"aria2 退出码 {rc}"
    except OSError:
        it["status"] = "error"
        it["error"] = "下载完成但文件校验失败"


async def _run_loop():
    """队列式下载: 持续消费 _STATE['queue'], 运行中可追加任务."""
    aria = _aria2c()
    try:
        if not aria:
            for it in _STATE["items"]:
                if it["status"] not in ("done", "error"):
                    it["status"] = "error"
                    it["error"] = "aria2c 未找到"
            return
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def worker(it):
            if not _STATE["running"]:
                it["status"] = "cancelled"
                return
            async with sem:
                if not _STATE["running"]:
                    it["status"] = "cancelled"
                    return
                await _download_one(aria, it)

        while _STATE["running"] and _STATE["queue"]:
            batch = []
            while _STATE["queue"] and len(batch) < MAX_CONCURRENT:
                batch.append(_STATE["queue"].pop(0))
            await asyncio.gather(*(worker(it) for it in batch))
    except Exception as e:
        LOGGER.exception("download loop failed")
        for it in _STATE["items"]:
            if it["status"] not in ("done", "error", "cancelled"):
                it["status"] = "error"
                it["error"] = repr(e)
    finally:
        _STATE["running"] = False


# ---- HTTP 路由 ----

try:
    _ROUTES = PromptServer.instance.routes
except Exception:
    _ROUTES = None

if _ROUTES is not None:

    @_ROUTES.get("/comfy_fetch/ping")
    async def comfy_fetch_ping(request):
        LOGGER.info("[BFP] ping from frontend: %s", request.rel_url.query_string)
        resp = web.json_response({"ok": True})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    @_ROUTES.get("/comfy_fetch/template_models/{tid}")
    async def comfy_fetch_template_models(request):
        tid = request.match_info.get("tid", "")
        entry = _blueprint_entries().get(tid)
        if not entry:
            return web.json_response({"error": "unknown template id"}, status=404)
        return web.json_response({
            "name": os.path.splitext(os.path.basename(entry))[0],
            "models": _extract_models_from_file(entry),
        })

    @_ROUTES.post("/comfy_fetch/check")
    async def comfy_fetch_check(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        models = _normalize_models(body.get("models"))
        # 完整性校验含哈希计算, 放到线程避免阻塞事件循环
        missing = await asyncio.to_thread(_do_check_sync, models)
        return web.json_response({"missing": missing})

    @_ROUTES.post("/comfy_fetch/download")
    async def comfy_fetch_download(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        items = _normalize_models(body.get("models"))
        if not items:
            return web.json_response({"error": "没有有效的模型"}, status=400)
        # 去重: 已在处理/队列中的同名同目录任务跳过
        existing = {(it["name"], it["directory"]) for it in _STATE["items"]}
        existing |= {(it["name"], it["directory"]) for it in _STATE["queue"]}
        new_items = [it for it in items if (it["name"], it["directory"]) not in existing]
        if not new_items:
            return web.json_response({"started": True, "count": 0, "note": "全部已在队列"})
        for it in new_items:
            it["status"] = "queued"
            it["progress"] = 0
        if _STATE["running"]:
            # 运行中: 追加到队列
            _STATE["items"].extend(new_items)
            _STATE["queue"].extend(new_items)
            LOGGER.info("[BFP] 追加 %d 个任务, 队列剩余 %d", len(new_items), len(_STATE["queue"]))
            return web.json_response({"started": True, "count": len(new_items), "queued": len(_STATE["queue"])})
        _STATE["running"] = True
        _STATE["items"] = new_items
        _STATE["queue"] = list(new_items)
        asyncio.ensure_future(_run_loop())
        return web.json_response({"started": True, "count": len(new_items)})

    @_ROUTES.get("/comfy_fetch/status")
    async def comfy_fetch_status(request):
        return web.json_response({
            "running": _STATE["running"],
            "items": _STATE["items"],
            "queue": len(_STATE["queue"]),
        })

    @_ROUTES.post("/comfy_fetch/retry")
    async def comfy_fetch_retry(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = _safe_name(body.get("name"))
        directory = _safe_dir(body.get("directory"))
        it = _find_item(name, directory) if name and directory else None
        if it is None:
            return web.json_response({"ok": False, "error": "任务不存在"}, status=404)
        it["status"] = "queued"
        it["progress"] = 0
        it.pop("error", None)
        it.pop("speed", None)
        _STATE["queue"].append(it)
        if not _STATE["running"]:
            _STATE["running"] = True
            asyncio.ensure_future(_run_loop())
        return web.json_response({"ok": True})

    @_ROUTES.post("/comfy_fetch/cancel")
    async def comfy_fetch_cancel(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = _safe_name(body.get("name"))
        directory = _safe_dir(body.get("directory"))
        it = _find_item(name, directory) if name and directory else None
        if it is None:
            return web.json_response({"ok": False, "error": "任务不存在"}, status=404)
        if it in _STATE["queue"]:
            _STATE["queue"].remove(it)
        proc = _STATE["procs"].get(it["name"])
        it["status"] = "cancelled"
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass
        return web.json_response({"ok": True})

    @_ROUTES.post("/comfy_fetch/stop")
    async def comfy_fetch_stop(request):
        for it in list(_STATE["queue"]):
            it["status"] = "cancelled"
        _STATE["queue"].clear()
        for name, proc in list(_STATE["procs"].items()):
            for x in _STATE["items"]:
                if x["name"] == name and x["status"] == "downloading":
                    x["status"] = "cancelled"
            try:
                proc.kill()
            except Exception:
                pass
        _STATE["running"] = False
        return web.json_response({"ok": True})

    @_ROUTES.post("/comfy_fetch/reorder")
    async def comfy_fetch_reorder(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = _safe_name(body.get("name"))
        directory = _safe_dir(body.get("directory"))
        direction = str(body.get("direction") or "")
        q = _STATE["queue"]
        idx = next((i for i, it in enumerate(q)
                    if it["name"] == name and it["directory"] == directory), None)
        if idx is None:
            return web.json_response({"ok": False, "note": "不在排队队列中"})
        j = idx - 1 if direction == "up" else idx + 1
        if 0 <= j < len(q):
            q[idx], q[j] = q[j], q[idx]
        return web.json_response({"ok": True, "queue": [it["name"] for it in q]})

    @_ROUTES.post("/comfy_fetch/delete")
    async def comfy_fetch_delete(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = _safe_name(body.get("name"))
        directory = _safe_dir(body.get("directory"))
        if not name or not directory:
            return web.json_response({"ok": False, "error": "参数无效"}, status=400)
        it = _find_item(name, directory)
        if it is not None and it in _STATE["queue"]:
            _STATE["queue"].remove(it)
        if it is not None and it["status"] == "downloading":
            it["status"] = "cancelled"
            proc = _STATE["procs"].get(it["name"])
            if proc is not None:
                try:
                    proc.kill()
                except Exception:
                    pass
        for root in _roots_for(directory):
            p = os.path.join(root, name)
            if os.path.exists(p):
                try:
                    os.remove(p)
                    return web.json_response({"ok": True, "path": p})
                except OSError as e:
                    return web.json_response({"ok": False, "error": str(e)})
        return web.json_response({"ok": False, "error": "文件不存在"})

    @_ROUTES.post("/comfy_fetch/reveal")
    async def comfy_fetch_reveal(request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        name = _safe_name(body.get("name"))
        directory = _safe_dir(body.get("directory"))
        if not name or not directory:
            return web.json_response({"ok": False, "error": "参数无效"}, status=400)
        for root in _roots_for(directory):
            p = os.path.join(root, name)
            if os.path.exists(p):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(p)])
                return web.json_response({"ok": True, "path": p})
        return web.json_response({"ok": False, "error": "文件不存在"})
