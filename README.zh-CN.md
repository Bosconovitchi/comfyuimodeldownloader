# ComfyUI-Model-Downloader

**一键满速下载 ComfyUI 模板/工作流缺失的模型 —— 带下载队列管理、逐文件操作和完整性校验。**

纯 ComfyUI 插件，无独立服务、无额外守护进程：后端运行在 ComfyUI 服务器进程内，前端运行在 ComfyUI 页面内。关闭 ComfyUI 即全部停止（下载也会停，靠 `aria2c --stop-with-process` 守护）。

> [English](README.md) | 简体中文 | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## 为什么需要这个插件

ComfyUI 自带的模板下载是**单线程**的，而且在部分网络环境下 `huggingface.co` 直连不通或被严重限速，内置的"下载"按钮经常失败或龟速。本插件：

- 自动检测当前打开的模板/工作流**缺哪些模型**（使用与内置缺失面板相同的元数据来源）。
- 用 **aria2c 下载，每文件 16 连接、3 文件并行**，Hugging Face 链接**自动走 hf-mirror.com 镜像**——通常能跑满带宽。
- 断点续传、**完整性校验**（大小 + SHA256，对照 Hugging Face 官方 LFS 记录），并提供一个完整的**下载管理面板**：重试、取消、全部停止、调整排队、删除文件、在文件夹中查看。

## 工作原理

```
┌──────────────────────── ComfyUI ────────────────────────┐
│  前端 (web/index.js)                                    │
│  • 每 2 秒扫描图节点 properties.models 元数据            │
│  • 浮动按钮: "⬇ 下载缺失模型 (N)"                        │
│  • 下载管理面板 (进度/速度/操作)                         │
│          │ REST (同源)                                  │
│  后端 (__init__.py, 进程内路由)                         │
│  • /comfy_fetch/check   – 存在性 + 完整性检查           │
│  • /comfy_fetch/download– 队列, aria2c ×16, 3 并行      │
│  • retry/cancel/stop/reorder/delete/reveal              │
└─────────────────────────────────────────────────────────┘
```

- **生命周期绑定**：一切都跑在 ComfyUI 内部。关闭 ComfyUI → 路由消失，所有运行中的 `aria2c` 自动终止（`--stop-with-process=<服务器 pid>`）。前端在页面隐藏时暂停轮询，页面卸载时清理。
- **下载纯手动触发**：切换模板只刷新缺失数量，不点按钮绝不下载（下载进行中再点按钮 = 把新模板的缺失模型加入队列）。

## 功能

| 功能 | 说明 |
|---|---|
| 自动检测 | 打开模板 → 浮动按钮显示缺失数量；切换模板 → 数量自动更新 |
| 高速下载 | aria2c，每文件 16 连接，3 文件并行，HF 链接自动换 hf-mirror.com 镜像 |
| 队列管理 | 下载中可追加任务、⏫⏬ 调整排队、取消单个、停止全部 |
| 完整性校验 | 每次检查：文件缺失 / `.aria2` 残留（未下完 → 自动续传）/ 大小不符 / SHA256 不符（对照 HF LFS 记录）；每次下载完成后再次 SHA256 校验；已校验文件按 (修改时间+大小) 会话缓存，切模板不重复哈希大文件 |
| 逐文件操作 | 重试、取消、⏫/⏬ 排序、删除磁盘文件（带确认）、资源管理器定位（Windows） |
| 断点续传 | 中断的下载保留 `.aria2` 控制文件，再次点击下载自动续传而非重头下 |

## 环境要求

- **ComfyUI**（任意支持自定义节点的新版本；已在 ComfyUI 0.3.x + Comfy Desktop 1.x 实测）
- **aria2c** 在 ComfyUI 启动环境的 `PATH` 中
- Python 包 `requests`（标准 ComfyUI 环境自带）
- 支持 Windows / Linux（"在文件夹中查看"仅 Windows；Linux 优雅降级）

### 安装 aria2

- **Windows**：从 <https://github.com/aria2/aria2/releases> 下载 ZIP（如 `aria2-1.37.0-win-64bit-build1.zip`），解压，把含 `aria2c.exe` 的目录加入用户 `PATH`。
- **Linux**：`sudo apt install aria2` / `sudo dnf install aria2`；macOS：`brew install aria2`。
- 验证：终端运行 `aria2c --version`。

## 安装本插件

### 方式一 — ComfyUI Manager

1. ComfyUI → **Manager** → **Custom Nodes Manager**
2. 搜索 `ComfyUI-Model-Downloader` 并安装
3. 重启 ComfyUI

### 方式二 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# 重启 ComfyUI
```

> **桌面版（Comfy Desktop）**：`custom_nodes` 在安装目录内部，例如 `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<实例>\ComfyUI\custom_nodes`（视安装布局而定）。不确定时看服务器日志里的 "Import times for custom nodes" 段落，确认实际扫描的目录。

## 使用步骤

1. 安装后**完全重启 ComfyUI**（不重启服务器不会加载插件）。
2. 打开任意**模板**（或任意节点带 `properties.models` 元数据的工作流，官方模板都有）。
3. 等约 2 秒，**右下角**出现浮动按钮：
   - `⬇ 下载缺失模型 (N)` —— 有 N 个模型缺失/损坏。**点击**开始下载。
4. **下载管理面板**自动弹出，显示每个文件：状态图标、进度条、百分比、实时速度、目标目录、错误信息。
5. 下载中可以：
   - 切换模板 → 按钮显示 `下载中 x/y · 待下载 N (点击加入队列)`。**不会自动下载**，点击按钮才把新模板的缺失模型加入队列。
   - 面板内：⏫/⏬ 调整排队顺序、**取消**单个、**停止全部**、失败项**重试**、**删除文件**、**打开位置**。
6. 全部结束后面板保留最终结果（✅/⚠️），点 ✕ 关闭。

### 按钮状态一览

| 场景 | 按钮显示 | 点击效果 |
|---|---|---|
| 无下载，有缺失 | `⬇ 下载缺失模型 (N)` | 开始下载 |
| 下载中，无新缺失 | `下载中 x/y · 文件名 45%` | 打开面板 |
| 下载中，新模板有缺失 | `下载中 x/y · 待下载 N (点击加入队列)` | 加入队列 |
| 结束但有失败 | `⚠ x 成功 / y 失败 (点击重试)` | 重试失败项 |
| 无缺失 | （隐藏） | — |

## 下载逻辑与完整性

对每个模型按顺序检查：

1. 文件不存在或 ≤ 1MB → **缺失** → 下载。
2. 存在 `<文件>.aria2` → **未下完** → aria2c 自动续传。
3. 大小 ≠ HF LFS 记录 → **损坏** → 删除重建。
4. SHA256 ≠ HF LFS 记录 → **损坏** → 删除重建（每会话每文件只哈希一次，文件变化才会重算）。
5. 每次下载完成后再次 SHA256 校验，不符标记失败。

预期大小/哈希来自 `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true`，按 URL 缓存。非 Hugging Face 链接（如 Civitai）只做存在性 + `.aria2` + 大小检查。

## 配置

所有可调项都在 `__init__.py` 顶部的常量里：

| 常量 | 默认值 | 含义 |
|---|---|---|
| `MAX_CONCURRENT` | `3` | 并行文件数 |
| aria2 参数 | `-x16 -s16 -k1M` | 每文件 16 连接、1MB 分块 |
| `HF_MIRROR` | `https://hf-mirror.com` | huggingface.co 链接使用的镜像 |
| `MIN_FILE_SIZE` | `1_000_000` | 小于此大小的文件视为缺失 |
| `ARIA2_FALLBACKS` | 本地路径 | PATH 找不到时依次尝试的 aria2c 绝对路径 |

## 常见问题

| 症状 | 解决办法 |
|---|---|
| 完全没有浮动按钮 | 完全重启 ComfyUI（桌面版托盘退出）。检查服务器日志 "Import times for custom nodes: … ComfyUI-Model-Downloader"。页面硬刷新（Ctrl+R）。健康检查：浏览器打开 `http://127.0.0.1:8188/comfy_fetch/ping` → 应返回 `{"ok": true}` |
| 打开模板后按钮不出现 | 工作流节点必须带 `properties.models` 元数据（官方模板都有）。手写工作流没有元数据时插件无从检测，手动处理 |
| 下载立即失败 | `aria2c` 找不到 → 安装 aria2 并确保它在 ComfyUI 启动环境的 PATH 中（需重启） |
| 速度很慢 | 你的网络连 hf-mirror.com 也不畅；尝试代理 |
| 切换模板后数字没变 | 等约 2 秒轮询周期；仍不行就 Ctrl+R 硬刷新 |
| 面板操作没反应 | 文件可能已被删除（删除）或不在队列（排序）；看面板状态图标确认 |

## API 参考（开发者）

所有接口由 ComfyUI 服务器自身提供（无额外端口）：

```
GET  /comfy_fetch/ping                       → {"ok": true}
GET  /comfy_fetch/status                     → {"running", "items", "queue"}
POST /comfy_fetch/check   {models:[...]}     → {"missing":[{url,name,directory,reason}]}
POST /comfy_fetch/download {models:[...]}    → {"started":true,"count":N}  (去重追加)
POST /comfy_fetch/retry  {name,directory}    → 失败/取消项重新入队
POST /comfy_fetch/cancel {name,directory}    → 取消单个 (杀掉其 aria2c)
POST /comfy_fetch/stop   {}                  → 全部停止
POST /comfy_fetch/reorder {name,directory,direction:"up"|"down"}
POST /comfy_fetch/delete {name,directory}    → 从磁盘删除模型文件
POST /comfy_fetch/reveal {name,directory}    → 资源管理器定位文件 (Windows)
```

缺失项的 `reason`：`missing`（缺失）| `incomplete`（未下完，自动续传）| `size` | `hash`。

## 许可证

MIT © 2026 Bosconovitchi
