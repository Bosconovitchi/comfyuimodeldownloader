# ComfyUI-Model-Downloader

**ComfyUI のテンプレートやワークフローで不足しているモデルを、ワンクリック・全速でダウンロード — キュー管理、ファイル単位の操作、整合性検証付き。**

純粋な ComfyUI プラグインです。スタンドアロンサーバーも追加のデーモンも必要ありません。バックエンドは ComfyUI サーバープロセス内で動作し、UI は ComfyUI ページ内で動作します。ComfyUI を閉じればすべてが停止します（`aria2c --stop-with-process` によりダウンロードも停止します）。

> English | [简体中文](README.zh-CN.md) | **日本語** | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | **한국어** | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | **Tiếng Việt** | **ไทย** | [Bahasa Indonesia](docs/README.id.md)

## このプラグインが存在する理由

ComfyUI 組み込みのテンプレートダウンローダーはモデルを**シングルスレッド**でダウンロードします。また、一部の地域では `huggingface.co` に到達できない、または大幅に速度制限されるため、組み込みの「Download」ボタンは失敗するか極端に遅くなります。このプラグインは以下のことを行います。

- 現在開いているテンプレート/ワークフローについて、**どのモデルが不足しているか**を検出します（組み込みの不足モデルパネルと同じメタデータを使用します）。
- 高速な Hugging Face ミラーである **hf-mirror.com** を自動的に経由し、**aria2c、ファイルあたり 16 接続、3 ファイル並列**でダウンロードします。通常、帯域幅を使い切る速度が出ます。
- 中断されたダウンロードを再開し、**ファイルの整合性を検証**し（Hugging Face 公式の LFS レコードに対するサイズ + SHA256）、完全な**ダウンロードマネージャーパネル**を提供します。再試行、キャンセル、全停止、キューの並べ替え、ファイルの削除、フォルダーで表示が可能です。

## 仕組み

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

- **ライフサイクル連動**: すべてが ComfyUI 内部で動作します。ComfyUI を停止すると → ルートが消え、実行中のすべての `aria2c` が自ら終了します（`--stop-with-process=<server pid>`）。フロントエンドも、ページが非表示の間はポーリングを一時停止し、アンロード時に後片付けを行います。
- **ダウンロードは手動のみ**: テンプレートを切り替えても、不足モデル数の表示が更新されるだけです。ボタンをクリックするまで何もダウンロードされません（ダウンロード実行中にボタンを再度クリックすると、新しいテンプレートの不足モデルがキューに追加されます）。

## 機能

| 機能 | 説明 |
|---|---|
| 自動検出 | テンプレートを開くと → フローティングボタンに不足モデルの数が表示されます。テンプレートを切り替えると → カウントが自動更新されます。 |
| 高速ダウンロード | aria2c、ファイルあたり 16 接続、3 ファイル並列。Hugging Face の URL には `hf-mirror.com` ミラーを自動使用します。 |
| キュー管理 | ダウンロード中にモデルを追加、項目の上下移動、個別キャンセル、全停止ができます。 |
| 整合性検証 | 各チェック時: ファイルの欠落、`.aria2` の残存（未完了 → 自動再開）、サイズ不一致、SHA256 不一致（HF の LFS レコードと比較）。各ダウンロード後: SHA256 の再検証。検証済みファイルはセッションごとにキャッシュされる（mtime + サイズ）ため、テンプレートを切り替えるたびに大きなファイルを再ハッシュすることはありません。 |
| ファイル単位の操作 | 再試行、キャンセル、⏫/⏬ で並べ替え、ディスクからファイルを削除（確認あり）、Windows エクスプローラーで表示。 |
| 再開 | 中断されたダウンロードは `.aria2` 制御ファイルを保持します。もう一度ダウンロードをクリックすると、最初からやり直すのではなく再開します。 |

## 要件

- **ComfyUI**（カスタムノード対応の最近のバージョン。ComfyUI 0.3.x + Comfy Desktop 1.x でテスト済み）
- ComfyUI を起動する環境の `PATH` 上に **aria2c** があること
- `requests` Python パッケージ（標準的な ComfyUI インストールには既に含まれています）
- Windows / Linux 対応（「フォルダーで表示」ボタンは Windows 専用です。Linux では代替動作に自動的に切り替わります）

### aria2 のインストール

- **Windows**: <https://github.com/aria2/aria2/releases> から ZIP（例: `aria2-1.37.0-win-64bit-build1.zip`）をダウンロードして展開し、`aria2c.exe` が含まれるフォルダーをユーザーの `PATH` に追加します。
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2`（macOS）。
- 確認: ターミナルを開いて `aria2c --version` を実行します。

## インストール

### 方法 1 — ComfyUI Manager

1. ComfyUI を開き → **Manager** → **Custom Nodes Manager** へ進みます。
2. `ComfyUI-Model-Downloader` を検索してインストールします。
3. ComfyUI を再起動します。

### 方法 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **デスクトップアプリ（Comfy Desktop）**: `custom_nodes` フォルダーはインストール先の内部にあります。例: `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes`（パスはレイアウトによって異なります）。不明な場合は、サーバーログの「Import times for custom nodes」セクションを確認すると、実際にスキャンされているディレクトリが分かります。

## 使い方

1. インストール後に **ComfyUI を再起動**します（サーバーがリロードしていないと、プラグインの UI は表示されません）。
2. 任意の**テンプレート**（またはノードに `properties.models` メタデータが埋め込まれたワークフロー。公式テンプレートはこれに該当します）を開きます。
3. 約 2 秒待つと、**右下**にフローティングボタンが表示されます。
   - `⬇ Download missing models (N)` — N 個のモデルが不足/破損しています。**クリックすると**ダウンロードが始まります。
4. **ダウンロードマネージャーパネル**が自動で開き、すべてのファイルを表示します。状態アイコン、プログレスバー、パーセンテージ、リアルタイム速度、保存先フォルダー、エラーメッセージ。
5. ダウンロード中にできること:
   - テンプレートを切り替えると → ボタンに `Downloading x/y · Pending N (click to enqueue)` と表示されます。**自動では何もダウンロードされません**。ボタンをクリックすると、新しいテンプレートの不足モデルがキューに追加されます。
   - パネル内: ⏫/⏬ でキュー内の項目を並べ替え、個別項目の**キャンセル**、**全停止**、失敗した項目の**再試行**、**ファイルの削除**、**フォルダーで表示**ができます。
6. すべて完了すると、パネルは ✕ で閉じるまで最終結果（✅/⚠️）を表示し続けます。

### ボタンの表示内容

| 状況 | ボタンのテキスト | クリック時の動作 |
|---|---|---|
| ダウンロード実行中でなく、モデルが不足 | `⬇ Download missing models (N)` | ダウンロードを開始 |
| ダウンロード実行中、新たな不足なし | `Downloading x/y · file 45%` | パネルを開く |
| ダウンロード実行中、新しいテンプレートに不足モデルあり | `Downloading x/y · Pending N (click to enqueue)` | キューに追加 |
| すべて完了、一部失敗 | `⚠ x ok / y failed (click to retry)` | 失敗を再試行 |
| 不足なし | （非表示） | — |

## ダウンロードのロジックと整合性

プラグインは各モデルについて（順番に）チェックします。

1. ファイルが存在しない、または 1 MB 以下 → **不足** → ダウンロード。
2. `<file>.aria2` が存在する → **未完了** → aria2c が再開します。
3. サイズ ≠ Hugging Face の LFS レコード → **破損** → 削除して再ダウンロード。
4. SHA256 ≠ Hugging Face の LFS レコード → **破損** → 削除して再ダウンロード（ファイルが変更されない限り、セッションごとにファイルごと 1 回だけ検証されます）。
5. 完了したダウンロードごとに SHA256 が再チェックされ、不一致の場合はその項目が失敗としてマークされます。

期待されるサイズ/ハッシュは `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` から取得され、URL ごとにキャッシュされます。Hugging Face 以外の URL（Civitai など）では、存在確認 + `.aria2` + サイズのチェックのみにフォールバックします。

## 設定

調整可能な値はすべて `__init__.py` の先頭にある定数です。

| 定数 | デフォルト | 意味 |
|---|---|---|
| `MAX_CONCURRENT` | `3` | 並列ファイル数 |
| aria2 フラグ | `-x16 -s16 -k1M` | ファイルあたり 16 接続、1 MB チャンク |
| `HF_MIRROR` | `https://hf-mirror.com` | `huggingface.co` の URL に使用するミラー |
| `MIN_FILE_SIZE` | `1_000_000` | これより小さいファイルは不足とみなす |
| `ARIA2_FALLBACKS` | ローカルパス | PATH にない場合に試す aria2c の絶対パス |

## トラブルシューティング

| 症状 | 対処法 |
|---|---|
| フローティングボタンがまったく表示されない | ComfyUI を完全に再起動します（デスクトップではトレイ → 終了）。サーバーログで `Import times for custom nodes: … ComfyUI-Model-Downloader` を確認します。ページではハードリフレッシュ（Ctrl+R）を行います。ヘルスチェック: `http://127.0.0.1:8188/comfy_fetch/ping` を開くと、`{"ok": true}` が返るはずです。 |
| テンプレートを開いてもボタンに何も表示されない | ワークフローのノードに `properties.models` メタデータが埋め込まれている必要があります（公式テンプレートは対応しています）。メタデータのない手作りのワークフローでは、プラグインがチェックする対象がありません — モデルを手動で追加してください。 |
| ダウンロードがすぐに失敗する | `aria2c` が見つかりません → aria2 をインストールし、ComfyUI を起動する際の PATH に含まれていることを確認してください（再起動が必要です）。 |
| 非常に遅い | ネットワークから `hf-mirror.com` にも到達できていません。プロキシを試してください。 |
| テンプレート切り替え後にカウントが古いまま | ポーリングサイクルまで約 2 秒待ちます。それでも続く場合はハードリフレッシュ（Ctrl+R）してください。 |
| パネルの操作で何も起こらない | ファイルが既に存在しない（削除済み）、またはキューにない（並べ替え）可能性があります。パネルの状態アイコンを確認してください。 |

## API リファレンス（開発者向け）

すべてのエンドポイントは ComfyUI サーバー自身が提供します（追加ポートは不要です）。

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

不足項目の `reason`: `missing` | `incomplete`（自動再開） | `size` | `hash`。

## ライセンス

MIT © 2026 Bosconovitchi
