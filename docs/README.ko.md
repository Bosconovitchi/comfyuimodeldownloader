# ComfyUI-Model-Downloader

**ComfyUI 템플릿과 워크플로우에 누락된 모델을 원클릭으로 최고 속도 다운로드 — 큐 관리, 파일별 작업, 무결성 검증 지원.**

순수 ComfyUI 플러그인입니다. 독립 서버도, 추가 데몬도 없습니다. 백엔드는 ComfyUI 서버 프로세스 안에서, UI는 ComfyUI 페이지 안에서 동작합니다. ComfyUI를 닫으면 모든 것이 중지됩니다(`aria2c --stop-with-process`에 따라 다운로드 포함).

> English | [简体中文](README.zh-CN.md) | **日本語** | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | **한국어** | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | **Tiếng Việt** | **ไทย** | [Bahasa Indonesia](docs/README.id.md)

## 이 플러그인이 필요한 이유

ComfyUI 내장 템플릿 다운로더는 모델을 **단일 스레드**로 내려받습니다. 게다가 일부 지역에서는 `huggingface.co`에 접속할 수 없거나 심하게 제한되어 내장 "Download" 버튼이 실패하거나 거북이처럼 느려집니다. 이 플러그인은 다음과 같은 일을 합니다.

- 현재 열린 템플릿/워크플로우에 **어떤 모델이 누락되었는지** 감지합니다(내장 누락 모델 패널이 사용하는 것과 동일한 메타데이터 사용).
- 빠른 Hugging Face 미러인 **hf-mirror.com**을 자동으로 경유해 **aria2c, 파일당 16개 연결, 파일 3개 병렬**로 다운로드합니다. 보통 대역폭을 꽉 채우는 속도가 나옵니다.
- 중단된 다운로드를 이어받고, **파일 무결성을 검증**하며(Hugging Face 공식 LFS 레코드 대비 크기 + SHA256), 완전한 **다운로드 관리자 패널**을 제공합니다. 재시도, 취소, 전체 중지, 큐 순서 변경, 파일 삭제, 폴더에서 보기가 가능합니다.

## 작동 방식

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

- **수명주기 결합**: 모든 것이 ComfyUI 안에서 실행됩니다. ComfyUI를 중지하면 → 라우트가 사라지고 실행 중인 모든 `aria2c`가 스스로 종료됩니다(`--stop-with-process=<server pid>`). 프런트엔드도 페이지가 숨겨져 있는 동안 폴링을 일시 중지하고, 언로드 시 정리 작업을 수행합니다.
- **다운로드는 수동 전용**: 템플릿을 전환해도 누락 모델 개수만 갱신됩니다. 버튼을 클릭하기 전에는 아무것도 다운로드되지 않습니다(다운로드 실행 중에 버튼을 다시 클릭하면 새 템플릿의 누락 모델이 큐에 추가됩니다).

## 기능

| 기능 | 설명 |
|---|---|
| 자동 감지 | 템플릿을 열면 → 플로팅 버튼에 누락된 모델 수가 표시됩니다. 템플릿을 전환하면 → 개수가 자동으로 갱신됩니다. |
| 빠른 다운로드 | aria2c, 파일당 16개 연결, 파일 3개 병렬, Hugging Face URL에 `hf-mirror.com` 미러 자동 사용. |
| 큐 관리 | 다운로드 중 모델 추가, 항목 위/아래 이동, 개별 항목 취소, 전체 중지. |
| 무결성 검증 | 매 확인 시: 파일 누락, 잔여 `.aria2`(미완료 → 자동 재개), 크기 불일치, SHA256 불일치(HF LFS 레코드 대비). 다운로드 후마다: SHA256 재검증. 검증된 파일은 세션별로 캐시되므로(mtime+크기) 템플릿을 전환할 때마다 큰 파일을 다시 해시하지 않습니다. |
| 파일별 작업 | 재시도, 취소, ⏫/⏬ 순서 변경, 디스크에서 파일 삭제(확인 필요), Windows 탐색기에서 보기. |
| 이어받기 | 중단된 다운로드는 `.aria2` 제어 파일을 유지합니다. 다운로드를 다시 클릭하면 처음부터 다시 시작하지 않고 이어받습니다. |

## 요구 사항

- **ComfyUI**(커스텀 노드를 지원하는 최신 버전. ComfyUI 0.3.x + Comfy Desktop 1.x에서 테스트됨)
- ComfyUI를 시작하는 환경의 `PATH`에 **aria2c**가 있을 것
- `requests` Python 패키지(표준 ComfyUI 설치에는 이미 포함되어 있음)
- Windows / Linux 지원("폴더에서 보기" 버튼은 Windows 전용. Linux에서는 자동으로 대체 동작을 사용함)

### aria2 설치

- **Windows**: <https://github.com/aria2/aria2/releases>에서 ZIP(예: `aria2-1.37.0-win-64bit-build1.zip`)을 다운로드해 압축을 풀고, `aria2c.exe`가 들어 있는 폴더를 사용자 `PATH`에 추가합니다.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2`(macOS).
- 확인: 터미널을 열고 `aria2c --version`을 실행합니다.

## 설치

### 방법 1 — ComfyUI Manager

1. ComfyUI 열기 → **Manager** → **Custom Nodes Manager**.
2. `ComfyUI-Model-Downloader` 검색 후 설치.
3. ComfyUI 재시작.

### 방법 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **데스크톱 앱(Comfy Desktop)**: `custom_nodes` 폴더는 설치 폴더 내부에 있습니다(예: `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes`, 경로는 레이아웃에 따라 다름). 확실하지 않다면 서버 로그의 "Import times for custom nodes" 섹션을 확인해 실제로 스캔되는 디렉터리를 파악하세요.

## 사용법

1. 설치 후 **ComfyUI를 재시작**합니다(서버가 다시 로드하지 않으면 플러그인 UI가 없습니다).
2. 아무 **템플릿**(또는 노드에 `properties.models` 메타데이터가 포함된 워크플로우 — 공식 템플릿이 이에 해당)을 엽니다.
3. 약 2초 기다리면 **오른쪽 아래**에 플로팅 버튼이 나타납니다.
   - `⬇ Download missing models (N)` — N개 모델이 누락/손상되었습니다. **클릭하면** 다운로드가 시작됩니다.
4. **다운로드 관리자 패널**이 자동으로 열려 모든 파일을 표시합니다. 상태 아이콘, 진행률 막대, 백분율, 실시간 속도, 대상 폴더, 오류 메시지.
5. 다운로드 중에 할 수 있는 일:
   - 템플릿을 전환하면 → 버튼에 `Downloading x/y · Pending N (click to enqueue)`가 표시됩니다. **자동으로 다운로드되는 것은 없습니다**. 버튼을 클릭해야 새 템플릿의 누락 모델이 큐에 추가됩니다.
   - 패널에서: ⏫/⏬로 대기 항목 순서 변경, 개별 항목 **취소**, **전체 중지**, 실패 항목 **재시도**, **파일 삭제**, **폴더에서 보기**.
6. 모두 끝나면 패널은 ✕로 닫을 때까지 최종 결과(✅/⚠️)를 유지합니다.

### 버튼에 표시되는 내용

| 상황 | 버튼 텍스트 | 클릭 동작 |
|---|---|---|
| 실행 중인 다운로드 없음, 모델 누락 | `⬇ Download missing models (N)` | 다운로드 시작 |
| 다운로드 실행 중, 새 누락 없음 | `Downloading x/y · file 45%` | 패널 열기 |
| 다운로드 실행 중, 새 템플릿에 누락 모델 있음 | `Downloading x/y · Pending N (click to enqueue)` | 큐에 추가 |
| 모두 완료, 일부 실패 | `⚠ x ok / y failed (click to retry)` | 실패 항목 재시도 |
| 누락 없음 | (숨김) | — |

## 다운로드 로직 및 무결성

플러그인은 각 모델에 대해 (순서대로) 확인합니다.

1. 파일 없음 또는 1 MB 이하 → **누락** → 다운로드.
2. `<file>.aria2` 존재 → **미완료** → aria2c가 이어받기.
3. 크기 ≠ Hugging Face LFS 레코드 → **손상** → 삭제 후 재다운로드.
4. SHA256 ≠ Hugging Face LFS 레코드 → **손상** → 삭제 후 재다운로드(파일이 변경되지 않는 한 세션당 파일당 한 번만 검증).
5. 완료된 다운로드마다 SHA256을 재확인하며, 불일치하면 해당 항목을 실패로 표시합니다.

예상 크기/해시는 `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true`에서 가져오며 URL별로 캐시됩니다. Hugging Face가 아닌 URL(예: Civitai)은 존재 확인 + `.aria2` + 크기 확인만으로 대체됩니다.

## 설정

조정 가능한 값은 모두 `__init__.py` 상단의 상수입니다.

| 상수 | 기본값 | 의미 |
|---|---|---|
| `MAX_CONCURRENT` | `3` | 병렬 파일 수 |
| aria2 플래그 | `-x16 -s16 -k1M` | 파일당 16개 연결, 1 MB 청크 |
| `HF_MIRROR` | `https://hf-mirror.com` | `huggingface.co` URL에 사용할 미러 |
| `MIN_FILE_SIZE` | `1_000_000` | 이보다 작은 파일은 누락으로 간주 |
| `ARIA2_FALLBACKS` | 로컬 경로 | PATH에 없을 때 시도할 aria2c 절대 경로 |

## 문제 해결

| 증상 | 해결책 |
|---|---|
| 플로팅 버튼이 아예 보이지 않음 | ComfyUI를 완전히 재시작합니다(데스크톱: 트레이 → 종료). 서버 로그에서 `Import times for custom nodes: … ComfyUI-Model-Downloader`를 확인합니다. 페이지에서 하드 새로고침(Ctrl+R). 상태 확인: `http://127.0.0.1:8188/comfy_fetch/ping`을 열면 `{"ok": true}`가 반환되어야 합니다. |
| 템플릿을 열어도 버튼에 아무것도 표시되지 않음 | 워크플로우 노드에 `properties.models` 메타데이터가 포함되어 있어야 합니다(공식 템플릿은 포함). 메타데이터가 없는 수제 워크플로우는 플러그인이 확인할 대상이 없습니다 — 모델을 수동으로 추가하세요. |
| 다운로드가 즉시 실패 | `aria2c`를 찾을 수 없음 → aria2를 설치하고 ComfyUI를 시작할 때 쓰는 PATH에 있는지 확인하세요(재시작 필요). |
| 매우 느림 | 네트워크가 `hf-mirror.com`에도 접속할 수 없습니다. 프록시를 사용해 보세요. |
| 템플릿 전환 후 개수가 오래된 값처럼 보임 | 폴링 주기까지 약 2초 기다립니다. 계속되면 하드 새로고침(Ctrl+R). |
| 패널 동작이 아무 효과 없음 | 파일이 이미 사라졌거나(삭제) 큐에 없을 수 있습니다(순서 변경). 패널의 상태 아이콘을 확인하세요. |

## API 참조(개발자용)

모든 엔드포인트는 ComfyUI 서버 자체가 제공합니다(추가 포트 불필요).

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

누락 항목의 `reason`: `missing` | `incomplete`(자동 재개) | `size` | `hash`.

## 라이선스

MIT © 2026 Bosconovitchi
