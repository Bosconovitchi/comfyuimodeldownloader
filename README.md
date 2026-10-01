# ComfyUI-Model-Downloader

**One-click, full-speed download of missing models for ComfyUI templates and workflows — with queue management, per-file actions, and integrity verification.**

A pure ComfyUI plugin. No standalone server, no extra daemons: the backend lives inside the ComfyUI server process and the UI lives inside the ComfyUI page. Close ComfyUI and everything stops (downloads included, via `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Why this plugin exists

ComfyUI's built-in template downloader downloads models **single-threaded**, and in some regions `huggingface.co` is unreachable or severely throttled, so the built-in "Download" button fails or crawls. This plugin:

- Detects **which models are missing** for the currently open template/workflow (same metadata the built-in missing-models panel uses).
- Downloads them with **aria2c, 16 connections per file, 3 files in parallel**, through **hf-mirror.com** automatically (a fast Hugging Face mirror) — typically saturating your bandwidth.
- Resumes interrupted downloads, **verifies file integrity** (size + SHA256 against Hugging Face's official LFS records), and gives you a full **download manager panel**: retry, cancel, stop all, reorder queue, delete the file, reveal in folder.

## How it works

```
┌──────────────────────── ComfyUI ────────────────────────┐
│  Frontend (web/index.js)                                │
│  • scans the graph every 2s for node properties.models  │
│  • floating button: "⬇ Download N missing models"       │
│  • download manager panel (progress/speed/actions)      │
│          │ REST (same-origin)                           │
│  Backend (__init__.py, in-process routes)               │
│  • /comfy_fetch/check   – existence + integrity check   │
│  • /comfy_fetch/download– queue, aria2c ×16, 3 parallel │
│  • retry/cancel/stop/reorder/delete/reveal              │
└─────────────────────────────────────────────────────────┘
```

- **Lifecycle binding**: everything runs inside ComfyUI. Stop ComfyUI → the routes disappear and every running `aria2c` terminates itself (`--stop-with-process=<server pid>`). The frontend also pauses polling while the page is hidden and cleans up on unload.
- **Downloads are manual-only**: switching templates only refreshes the missing-model count. Nothing downloads until you click the button (or click the button again while a download runs, to enqueue the new template's missing models).

## Features

| Feature | Description |
|---|---|
| Auto detection | Opens a template → the floating button shows how many models are missing. Switch templates → the count updates automatically. |
| Fast downloads | aria2c, 16 connections/file, 3 parallel files, automatic `hf-mirror.com` mirror for Hugging Face URLs. |
| Queue management | Enqueue more models mid-download, move items up/down, cancel single items, stop everything. |
| Integrity verification | On every check: missing file, leftover `.aria2` (incomplete → auto-resume), size mismatch, SHA256 mismatch (vs HF LFS records). After each download: SHA256 re-verification. Verified files are cached per session (mtime+size) so big files are not re-hashed on every template switch. |
| Per-file actions | Retry, cancel, ⏫/⏬ reorder, delete file from disk (with confirmation), reveal in Windows Explorer. |
| Resume | Interrupted downloads keep their `.aria2` control file; clicking download again resumes instead of restarting. |

## Requirements

- **ComfyUI** (any recent version with custom-node support; tested on ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** on the `PATH` of the environment that starts ComfyUI
- `requests` Python package (already present in standard ComfyUI installs)
- Windows / Linux supported (the "reveal in folder" button is Windows-only; Linux falls back gracefully)

### Installing aria2

- **Windows**: download the ZIP from <https://github.com/aria2/aria2/releases> (e.g. `aria2-1.37.0-win-64bit-build1.zip`), extract, and add the folder containing `aria2c.exe` to your user `PATH`.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Verify: open a terminal and run `aria2c --version`.

## Installation

### Method 1 — ComfyUI Manager

1. Open ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Search `ComfyUI-Model-Downloader` and install.
3. Restart ComfyUI.

### Method 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Desktop app (Comfy Desktop)**: the `custom_nodes` folder is inside the installation, e.g. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (path varies by layout). If in doubt, check the server log's "Import times for custom nodes" section to see which directory is actually scanned.

## Usage

1. **Restart ComfyUI** after installation (the plugin has no UI if the server hasn't reloaded it).
2. Open any **template** (or any workflow whose nodes embed `properties.models` metadata — official templates do).
3. Wait ~2 seconds. A floating button appears at the **bottom-right**:
   - `⬇ Download missing models (N)` — N models are missing/broken. **Click it** to start downloading.
4. The **download manager panel** opens automatically, showing every file: status icon, progress bar, percentage, live speed, target folder, error messages.
5. While downloading you can:
   - Switch templates → the button shows `Downloading x/y · Pending N (click to enqueue)`. **Nothing auto-downloads**; click the button to add the new template's missing models to the queue.
   - In the panel: ⏫/⏬ reorder queued items, **Cancel** a single item, **Stop all**, **Retry** failed items, **Delete file**, **Reveal in folder**.
6. When everything finishes, the panel keeps the final results (✅/⚠️) until you close it with ✕.

### What the button shows

| Situation | Button text | Click action |
|---|---|---|
| No download running, models missing | `⬇ Download missing models (N)` | Start downloading |
| Download running, no new missing | `Downloading x/y · file 45%` | Open the panel |
| Download running, new template missing models | `Downloading x/y · Pending N (click to enqueue)` | Enqueue them |
| All finished, some failed | `⚠ x ok / y failed (click to retry)` | Retry failures |
| Nothing missing | (hidden) | — |

## Download logic & integrity

For each model the plugin checks (in order):

1. File absent or ≤ 1 MB → **missing** → download.
2. `<file>.aria2` exists → **incomplete** → aria2c resumes it.
3. Size ≠ Hugging Face LFS record → **corrupted** → delete & re-download.
4. SHA256 ≠ Hugging Face LFS record → **corrupted** → delete & re-download (only verified once per session per file unless the file changes).
5. After every completed download the SHA256 is re-checked; a mismatch marks the item as failed.

Expected sizes/hashes come from `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` and are cached per URL. Non-Hugging-Face URLs (e.g. Civitai) fall back to existence + `.aria2` + size checks only.

## Gated repositories (license-required models)

Some models (e.g. LTX-2.5, Gemma) are **gated** on Hugging Face — you must accept the license / request access before downloading. The plugin detects this and fails with a clear message instead of a cryptic error.

1. Open the model page on huggingface.co (e.g. <https://huggingface.co/Lightricks/LTX-2.5>), sign in, and accept the terms / request access.
2. Create a read-only access token: <https://huggingface.co/settings/tokens> → New token → type **Read**.
3. Set it as an environment variable for ComfyUI and restart:

   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (add to your ComfyUI start script)

4. Restart ComfyUI and retry — downloads then carry `Authorization: Bearer <token>`, and integrity metadata (size/SHA256) is fetched with the token too.

## Configuration

All tunables are constants at the top of `__init__.py`:

| Constant | Default | Meaning |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Parallel files |
| aria2 flags | `-x16 -s16 -k1M` | 16 connections/file, 1 MB chunks |
| `HF_MIRROR` | `https://hf-mirror.com` | Mirror used for `huggingface.co` URLs |
| `MIN_FILE_SIZE` | `1_000_000` | Files smaller than this count as missing |
| `ARIA2_FALLBACKS` | local paths | Absolute aria2c locations tried if not on PATH |

## Troubleshooting

| Symptom | Fix |
|---|---|
| No floating button at all | Restart ComfyUI completely (tray → quit on desktop). Check the server log for `Import times for custom nodes: … ComfyUI-Model-Downloader`. In the page, hard-refresh (Ctrl+R). Health check: open `http://127.0.0.1:8188/comfy_fetch/ping` → should return `{"ok": true}`. |
| Button shows nothing after opening a template | The workflow's nodes must embed `properties.models` metadata (official templates do). For hand-made workflows without metadata, the plugin has nothing to check — add the models manually. |
| Download fails immediately | `aria2c` not found → install aria2 and make sure it's on the PATH ComfyUI starts with (restart required). |
| Very slow | Your network can't reach `hf-mirror.com` either; try a proxy. |
| Count looks stale after switching templates | Wait ~2s for the poll cycle; hard-refresh (Ctrl+R) if it persists. |
| Panel action does nothing | The file may already be gone (delete) or not in the queue (reorder); check the panel status icons. |

## API reference (for developers)

All endpoints are served by the ComfyUI server itself (no extra port):

```
GET  /comfy_fetch/ping                       → {"ok": true}
GET  /comfy_fetch/status                     → {"running", "items", "queue"}
POST /comfy_fetch/check   {models:[...]}     → {"missing":[{url,name,directory,reason}]}
POST /comfy_fetch/download {models:[...]}    → {"started":true,"count":N}  (idempotent-ish, dedupes)
POST /comfy_fetch/retry  {name,directory}    → re-queue a failed/cancelled item
POST /comfy_fetch/cancel {name,directory}    → cancel one item (kills its aria2c)
POST /comfy_fetch/stop   {}                  → stop everything
POST /comfy_fetch/reorder {name,directory,direction:"up"|"down"}
POST /comfy_fetch/delete {name,directory}    → delete the model file from disk
POST /comfy_fetch/reveal {name,directory}    → open Explorer at the file (Windows)
```

`reason` on missing items: `missing` | `incomplete` (auto-resume) | `size` | `hash`.

## License

MIT © 2026 Bosconovitchi
