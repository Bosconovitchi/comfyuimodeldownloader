/**
 * ComfyUI-Blueprint-Fetcher 前端
 * - 浮动按钮: 显示当前模板缺失模型数, 一键下载
 * - 下载管理面板: 实时查看每个文件的下载状态/进度/速度
 * - 模板加载检测: 包装 window.api.fetchApi (前端 api 客户端自有 HTTP 层,
 *   不经过 window.fetch) 捕获 /global_subgraphs/<id> 请求 -> 后端解析模板模型清单
 *   兜底: 轮询扫描图节点 properties.models (含子图内部节点)
 */
(function () {
  "use strict";
  if (window.__blueprintFetcherInjected) return;
  window.__blueprintFetcherInjected = true;

  // 心跳: 固定打给 python 服务器 (跨域也会到达并被日志记录)
  function ping(tag) {
    try {
      const origin = encodeURIComponent(window.location.href);
      fetch("http://127.0.0.1:8188/comfy_fetch/ping?v=" + tag + "&ver=7&origin=" + origin).catch(() => {});
    } catch (e) { /* 静默 */ }
  }
  ping("start");

  let btn = null;
  let panel = null;
  let pollTimer = null;
  let statusTimer = null;
  let lastGraphRef = null;
  let lastModelKey = null;
  let currentMissing = [];
  let lastStatus = null;
  let apiHooked = false;
  let checkSeq = 0; // 检查请求序号, 丢弃过期响应

  function apiUrl(path) {
    return window.location.origin + path;
  }

  async function jfetch(path, opts) {
    const r = await fetch(apiUrl(path), opts);
    return r.json();
  }

  // ---------- 模型收集 ----------

  // 图节点扫描 (含子图内部节点), properties.models 与前端缺失检测同源
  function collectModelsFromGraph() {
    const seen = new Map();
    const g = window.app && window.app.graph;
    if (!g) return [];

    const walkNodes = (nodes) => {
      for (const n of nodes || []) {
        const props = (n && n.properties) || {};
        const arr = Array.isArray(props.models) ? props.models : [];
        for (const m of arr) {
          if (m && typeof m.url === "string" && /^https?:\/\//.test(m.url)) {
            const key = m.url + "|" + (m.name || "");
            if (!seen.has(key)) {
              seen.set(key, { url: m.url, name: m.name || "", directory: m.directory || "" });
            }
          }
        }
        // 子图内部节点
        if (n && n.subgraph && n.subgraph._nodes) {
          walkNodes(n.subgraph._nodes);
        }
      }
    };
    walkNodes(g._nodes);
    return Array.from(seen.values());
  }

  async function checkAndUpdateUI(models) {
    if (!models || !models.length) return;
    const seq = ++checkSeq;
    try {
      const res = await jfetch("/comfy_fetch/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models }),
      });
      if (seq !== checkSeq) return; // 已有更新的检查, 丢弃过期响应
      currentMissing = res.missing || [];
      renderButton();
    } catch (e) { /* 静默 */ }
  }

  // 模板加载/切换: 后端直接解析蓝图模型清单
  async function onTemplateFetched(tid) {
    try {
      const res = await jfetch("/comfy_fetch/template_models/" + encodeURIComponent(tid));
      if (res && Array.isArray(res.models) && res.models.length) {
        await checkAndUpdateUI(res.models);
      }
    } catch (e) { /* 静默 */ }
  }

  // 关键钩子: api 客户端用自有 HTTP 层, 必须包装 fetchApi 本身
  // 该版本前端可能不暴露 window.api, 多候选对象逐一尝试
  function apiCandidates() {
    const out = [];
    const cands = [
      window.api,
      window.app && window.app.api,
      window.app && window.app.apiClient,
    ];
    for (const o of cands) {
      if (o && typeof o === "object" && !out.includes(o)) out.push(o);
    }
    return out;
  }

  function hookApiClient() {
    if (apiHooked) return;
    for (const api of apiCandidates()) {
      if (typeof api.fetchApi === "function") {
        apiHooked = true;
        const orig = api.fetchApi.bind(api);
        api.fetchApi = function (path, options) {
          try {
            const p = String(path || "");
            const m = p.match(/global_subgraphs\/([A-Za-z0-9]+)/);
            if (m) {
              const tid = m[1];
              setTimeout(() => onTemplateFetched(tid), 600);
              setTimeout(() => onTemplateFetched(tid), 2000);
            }
          } catch (e) { /* 静默 */ }
          return orig(path, options);
        };
        return;
      }
    }
  }

  // 次级钩子: 万一有代码走 window.fetch
  function hookWindowFetch() {
    if (window.__bpfetchHooked) return;
    window.__bpfetchHooked = true;
    const orig = window.fetch ? window.fetch.bind(window) : null;
    if (!orig) return;
    window.fetch = function (...args) {
      try {
        const u = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url);
        if (typeof u === "string") {
          const m = u.match(/global_subgraphs\/([A-Za-z0-9]+)/);
          if (m) {
            const tid = m[1];
            setTimeout(() => onTemplateFetched(tid), 600);
            setTimeout(() => onTemplateFetched(tid), 2000);
          }
        }
      } catch (e) { /* 静默 */ }
      return orig.apply(window, args);
    };
  }

  // ---------- UI: 浮动按钮 ----------

  function ensureButton() {
    if (btn) return btn;
    btn = document.createElement("div");
    btn.style.cssText = [
      "position:fixed", "right:16px", "bottom:16px", "z-index:99999",
      "background:#1e1e30", "color:#d8d8ff", "border:1px solid #4a4a7a",
      "border-radius:10px", "padding:10px 14px", "font-size:13px",
      "font-family:system-ui,sans-serif", "cursor:pointer",
      "box-shadow:0 4px 16px rgba(0,0,0,.55)", "display:none",
      "user-select:none", "max-width:340px", "overflow:hidden",
      "text-overflow:ellipsis", "white-space:nowrap",
    ].join(";");
    document.body.appendChild(btn);
    return btn;
  }

  function renderButton() {
    const b = ensureButton();
    const st = lastStatus;
    if (st && st.running) {
      const items = st.items || [];
      const done = items.filter((i) => i.status === "done").length;
      const queued = st.queue || 0;
      const cur = items.find((i) => i.status === "downloading");
      let label = "下载中 " + done + "/" + items.length;
      if (queued) label += " · 队列 +" + queued;
      if (cur) label += " · " + cur.name + " " + (cur.progress || 0) + "%";
      if (currentMissing.length) {
        label += " · 待下载 " + currentMissing.length + " (点击加入队列)";
        b.onclick = enqueueMissing;
      } else {
        b.onclick = showPanel;
      }
      b.innerHTML = label;
      b.style.display = "block";
      return;
    }
    if (currentMissing.length) {
      b.innerHTML = "⬇ 下载缺失模型 (" + currentMissing.length + ")";
      b.style.display = "block";
      b.onclick = startDownload;
      return;
    }
    b.style.display = "none";
    b.onclick = null;
  }

  // ---------- UI: 下载管理面板 ----------

  function ensurePanel() {
    if (panel) return panel;
    panel = document.createElement("div");
    panel.style.cssText = [
      "position:fixed", "right:16px", "bottom:64px", "z-index:99998",
      "width:360px", "max-height:420px", "overflow-y:auto",
      "background:#141428", "color:#d8d8ff", "border:1px solid #4a4a7a",
      "border-radius:12px", "font-family:system-ui,sans-serif",
      "box-shadow:0 8px 32px rgba(0,0,0,.7)", "display:none",
      "padding:0", "font-size:12px",
    ].join(";");
    document.body.appendChild(panel);
    return panel;
  }

  function statusIcon(it) {
    if (it.status === "done") return "✅";
    if (it.status === "error") return "⚠️";
    if (it.status === "downloading") return "⬇️";
    if (it.status === "cancelled") return "⏹";
    return "⏳"; // queued
  }

  // 行内操作按钮: 事件委托
  window.__bpAct = async function (act, name, directory, direction) {
    if (act === "delete" && !window.confirm("确定删除模型文件 " + name + " ?\n(从磁盘永久删除)")) return;
    try {
      const body = { name, directory };
      if (act === "reorder") body.direction = direction;
      await jfetch("/comfy_fetch/" + act, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } catch (e) { /* 静默 */ }
    // 立即刷新面板与按钮
    try {
      const s = await jfetch("/comfy_fetch/status");
      lastStatus = s;
      if (panel && panel.style.display !== "none") renderPanel(s.items || []);
      renderButton();
    } catch (e) { /* 静默 */ }
  };

  function actionBtn(act, label, title, name, directory, direction) {
    const n = encodeURIComponent(name || "");
    const d = encodeURIComponent(directory || "");
    return '<button data-bp-act="' + act + '" data-name="' + n + '" data-dir="' + d + '"'
      + (direction ? ' data-dir2="' + direction + '"' : "")
      + ' style="cursor:pointer;background:#2a2a4a;color:#c8c8e8;border:1px solid #3a3a6a;'
      + 'border-radius:5px;padding:1px 6px;font-size:11px;margin-left:4px" title="' + title + '">' + label + "</button>";
  }

  function renderPanel(items) {
    const p = ensurePanel();
    const done = items.filter((i) => i.status === "done").length;
    const err = items.filter((i) => i.status === "error").length;
    const running = items.some((i) => i.status === "downloading" || i.status === "queued");
    let html = '<div style="padding:10px 12px;border-bottom:1px solid #33335a;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;background:#141428;">'
      + '<b>下载管理</b><span style="color:#9a9ac0">' + done + "/" + items.length
      + (err ? " (失败 " + err + ")" : "")
      + (running ? " · 下载中" : "") + "</span>"
      + '<span style="margin-left:auto;display:flex;align-items:center;gap:6px">'
      + (running ? '<button id="bpFetchStop" style="cursor:pointer;background:#5a2a2a;color:#f0c0c0;border:1px solid #7a3a3a;border-radius:5px;padding:2px 8px;font-size:11px">⏹ 停止全部</button>' : "")
      + '<span id="bpFetchClose" style="cursor:pointer;color:#9a9ac0;margin-left:4px">✕</span></span></div>';
    for (const it of items) {
      const pct = it.progress || 0;
      const barW = it.status === "done" ? 100 : pct;
      const speed = it.speed ? " · " + it.speed : "";
      let acts = "";
      if (it.status === "queued") {
        acts += actionBtn("reorder", "⏫", "上移", it.name, it.directory, "up")
          + actionBtn("reorder", "⏬", "下移", it.name, it.directory, "down")
          + actionBtn("cancel", "取消", "取消此下载", it.name, it.directory);
      } else if (it.status === "downloading") {
        acts += actionBtn("cancel", "取消", "取消此下载", it.name, it.directory);
      } else if (it.status === "error" || it.status === "cancelled") {
        acts += actionBtn("retry", "重试", "重新下载", it.name, it.directory)
          + actionBtn("delete", "删除文件", "删除已下载的源文件", it.name, it.directory);
      } else if (it.status === "done") {
        acts += actionBtn("reveal", "打开位置", "在文件夹中查看", it.name, it.directory)
          + actionBtn("delete", "删除文件", "删除已下载的源文件", it.name, it.directory);
      }
      html += '<div style="padding:8px 12px;border-bottom:1px solid #22223c">'
        + '<div style="display:flex;justify-content:space-between;gap:8px">'
        + '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + statusIcon(it) + " " + it.name + "</span>"
        + '<span style="color:#9a9ac0;white-space:nowrap">'
        + (it.status === "downloading" ? pct + "%" + speed : (it.status === "error" ? "失败" : it.status === "queued" ? "排队" : ""))
        + "</span></div>"
        + '<div style="margin-top:4px;display:flex;justify-content:space-between;align-items:center;gap:8px">'
        + '<span style="color:#7a7ab0;font-size:11px">目录: ' + it.directory
        + (it.error ? " · " + it.error : "") + "</span>"
        + '<span style="white-space:nowrap">' + acts + "</span></div>"
        + '<div style="margin-top:4px;height:4px;background:#2a2a4a;border-radius:2px">'
        + '<div style="height:4px;width:' + barW + '%;background:'
        + (it.status === "error" ? "#c05a5a" : it.status === "done" ? "#58b368" : "#5a7ac0")
        + ';border-radius:2px"></div></div></div>';
    }
    p.innerHTML = html;
    // 事件委托
    p.querySelectorAll("[data-bp-act]").forEach((el) => {
      el.onclick = () => {
        const act = el.getAttribute("data-bp-act");
        const name = decodeURIComponent(el.getAttribute("data-name"));
        const dir = decodeURIComponent(el.getAttribute("data-dir"));
        const dir2 = el.getAttribute("data-dir2") || null;
        window.__bpAct(act, name, dir, dir2);
      };
    });
    const closeEl = document.getElementById("bpFetchClose");
    if (closeEl) closeEl.onclick = () => { p.style.display = "none"; };
    const stopEl = document.getElementById("bpFetchStop");
    if (stopEl) stopEl.onclick = () => window.__bpAct("stop", "", "", null);
  }

  function showPanel() {
    const p = ensurePanel();
    const st = lastStatus;
    if (st && st.items && st.items.length) {
      renderPanel(st.items);
      p.style.display = "block";
    }
  }

  // ---------- 下载流程 ----------

  async function startDownload() {
    if (!currentMissing.length) return;
    try {
      const res = await jfetch("/comfy_fetch/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: currentMissing }),
      });
      if (res.error) {
        const b = ensureButton();
        b.innerHTML = "⚠ " + res.error;
        b.style.display = "block";
        return;
      }
      showPanel();
      watchStatus();
    } catch (e) {
      const b = ensureButton();
      b.innerHTML = "⚠ 请求失败, 重试";
      b.style.display = "block";
    }
  }

  // 下载进行中点击按钮: 把当前缺失模型手动加入队列
  async function enqueueMissing() {
    if (!currentMissing.length) return;
    try {
      const res = await jfetch("/comfy_fetch/download", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: currentMissing }),
      });
      if (res.error) {
        const b = ensureButton();
        b.innerHTML = "⚠ " + res.error;
        return;
      }
      currentMissing = []; // 已入队, 清空待下载标记
      showPanel();
      watchStatus();
    } catch (e) {
      const b = ensureButton();
      b.innerHTML = "⚠ 请求失败, 重试";
      b.style.display = "block";
    }
  }

  async function watchStatus() {
    if (statusTimer) clearInterval(statusTimer);
    statusTimer = setInterval(async () => {
      try {
        const s = await jfetch("/comfy_fetch/status");
        lastStatus = s;
        const items = s.items || [];
        if (panel && panel.style.display !== "none" && items.length) {
          renderPanel(items);
        }
        renderButton();
        if (!s.running) {
          clearInterval(statusTimer);
          statusTimer = null;
          if (items.length) {
            const done = items.filter((i) => i.status === "done").length;
            const err = items.filter((i) => i.status === "error").length;
            if (panel && panel.style.display !== "none") {
              renderPanel(items); // 最终状态留在面板里供查看
            }
            if (!err && done === items.length) {
              await refreshCombos();
              ensureButton().title = "模型已就位。如列表未刷新请按 Ctrl+R";
            } else if (err) {
              const b = ensureButton();
              b.innerHTML = "⚠ " + done + " 成功 / " + err + " 失败 (点击重试)";
              b.style.display = "block";
              b.onclick = startDownload;
            }
            // 下载完成后立刻重新检查一次
            setTimeout(() => { checkAndUpdateUI(collectModelsFromGraph()); }, 1500);
          }
        }
      } catch (e) { /* 静默 */ }
    }, 1000);
  }

  async function refreshCombos() {
    try {
      const app = window.app;
      if (app && typeof app.refreshComboInNodes === "function") {
        app.refreshComboInNodes();
        return;
      }
    } catch (e) { /* ignore */ }
    try {
      const api = window.api;
      if (api && typeof api.refreshComboInNodes === "function") {
        api.refreshComboInNodes();
      }
    } catch (e) { /* ignore */ }
  }

  // ---------- 主循环: 轮询图变化 (兜底) ----------

  async function poll() {
    try {
      hookApiClient(); // window.api 可能晚于 app 出现
      if (!window.app) return;
      const g = window.app.graph;
      if (g && g !== lastGraphRef) {
        lastGraphRef = g;
        lastModelKey = null;
      }
      const models = collectModelsFromGraph();
      if (models.length) {
        const key = JSON.stringify(models.map((m) => m.url));
        if (key !== lastModelKey) {
          lastModelKey = key;
          checkAndUpdateUI(models);
        }
      }
      renderButton();
    } catch (e) { /* 静默 */ }
  }

  // ---------- 启动 ----------

  hookWindowFetch();

  let tries = 0;
  const readyTimer = setInterval(() => {
    tries++;
    hookApiClient(); // 每次 tick 都尝试 (api 可能晚出现)
    if (window.app && window.app.graph) {
      clearInterval(readyTimer);
      ping("ready");
      pollTimer = setInterval(poll, 2000);
      poll();
    } else if (tries > 240) {
      clearInterval(readyTimer); // 120 秒后放弃
    }
  }, 500);

  // 页面隐藏(最小化/切走)时暂停轮询, 恢复时立即检查一次
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      if (pollTimer) clearInterval(pollTimer);
    } else {
      if (!pollTimer && window.app && window.app.graph) {
        pollTimer = setInterval(poll, 2000);
        lastModelKey = null;
        poll();
      }
    }
  });

  window.addEventListener("beforeunload", () => {
    if (pollTimer) clearInterval(pollTimer);
    if (statusTimer) clearInterval(statusTimer);
    if (btn && btn.parentNode) btn.parentNode.removeChild(btn);
    if (panel && panel.parentNode) panel.parentNode.removeChild(panel);
    btn = null;
    panel = null;
  });
})();
