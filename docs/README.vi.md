# ComfyUI-Model-Downloader

**Tải xuống với tốc độ tối đa chỉ bằng một cú nhấp chuột các mô hình còn thiếu cho mẫu (template) và quy trình (workflow) ComfyUI — kèm quản lý hàng đợi, thao tác theo từng tệp và xác minh tính toàn vẹn.**

Một plugin ComfyUI thuần túy. Không cần máy chủ riêng, không cần daemon phụ: phần backend chạy bên trong tiến trình máy chủ ComfyUI và phần UI chạy bên trong trang ComfyUI. Đóng ComfyUI là mọi thứ dừng lại (kể cả các lượt tải xuống, nhờ `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | **日本語** | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | **한국어** | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | **Tiếng Việt** | **ไทย** | [Bahasa Indonesia](docs/README.id.md)

## Vì sao plugin này tồn tại

Trình tải mẫu tích hợp sẵn của ComfyUI tải mô hình **đơn luồng**, và ở một số khu vực `huggingface.co` không truy cập được hoặc bị giới hạn tốc độ nặng, khiến nút "Download" tích hợp sẵn thất bại hoặc chậm như rùa. Plugin này:

- Phát hiện **những mô hình nào còn thiếu** cho mẫu/quy trình đang mở (dùng cùng metadata với bảng mô hình còn thiếu tích hợp sẵn).
- Tải chúng bằng **aria2c, 16 kết nối mỗi tệp, 3 tệp song song**, tự động đi qua **hf-mirror.com** (một mirror Hugging Face tốc độ cao) — thường tận dụng tối đa băng thông của bạn.
- Tiếp tục các lượt tải bị gián đoạn, **xác minh tính toàn vẹn của tệp** (kích thước + SHA256 đối chiếu với bản ghi LFS chính thức của Hugging Face), và cung cấp **bảng quản lý tải xuống** đầy đủ: thử lại, hủy, dừng tất cả, sắp xếp lại hàng đợi, xóa tệp, hiện trong thư mục.

## Cách hoạt động

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

- **Gắn với vòng đời**: mọi thứ chạy bên trong ComfyUI. Dừng ComfyUI → các route biến mất và mọi `aria2c` đang chạy tự kết thúc (`--stop-with-process=<server pid>`). Frontend cũng tạm dừng việc quét khi trang bị ẩn và dọn dẹp khi trang được gỡ bỏ (unload).
- **Chỉ tải thủ công**: việc chuyển mẫu chỉ làm mới số lượng mô hình còn thiếu. Không có gì được tải cho đến khi bạn nhấp nút (hoặc nhấp lại nút trong lúc đang tải, để thêm các mô hình còn thiếu của mẫu mới vào hàng đợi).

## Tính năng

| Tính năng | Mô tả |
|---|---|
| Tự động phát hiện | Mở một mẫu → nút nổi hiển thị số mô hình còn thiếu. Chuyển mẫu → số đếm tự cập nhật. |
| Tải nhanh | aria2c, 16 kết nối/tệp, 3 tệp song song, tự động dùng mirror `hf-mirror.com` cho URL Hugging Face. |
| Quản lý hàng đợi | Thêm mô hình giữa chừng khi đang tải, di chuyển mục lên/xuống, hủy từng mục, dừng tất cả. |
| Xác minh tính toàn vẹn | Mỗi lần kiểm tra: tệp thiếu, tệp `.aria2` còn sót (chưa hoàn tất → tự nối lại), sai kích thước, sai SHA256 (so với bản ghi LFS của HF). Sau mỗi lượt tải: xác minh lại SHA256. Các tệp đã xác minh được lưu đệm theo phiên (mtime+kích thước) nên tệp lớn không bị băm lại mỗi lần chuyển mẫu. |
| Thao tác từng tệp | Thử lại, hủy, sắp xếp lại ⏫/⏬, xóa tệp khỏi đĩa (có xác nhận), hiện trong Windows Explorer. |
| Tải tiếp | Các lượt tải bị gián đoạn giữ lại tệp điều khiển `.aria2`; nhấp tải lại sẽ tiếp tục thay vì làm lại từ đầu. |

## Yêu cầu

- **ComfyUI** (bất kỳ phiên bản gần đây nào có hỗ trợ custom node; đã kiểm thử trên ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** nằm trong `PATH` của môi trường khởi động ComfyUI
- Gói Python `requests` (đã có sẵn trong các bản cài ComfyUI chuẩn)
- Hỗ trợ Windows / Linux (nút "hiện trong thư mục" chỉ có trên Windows; Linux tự chuyển sang cách khác một cách nhẹ nhàng)

### Cài đặt aria2

- **Windows**: tải ZIP từ <https://github.com/aria2/aria2/releases> (ví dụ `aria2-1.37.0-win-64bit-build1.zip`), giải nén, rồi thêm thư mục chứa `aria2c.exe` vào `PATH` của người dùng.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Kiểm tra: mở terminal và chạy `aria2c --version`.

## Cài đặt

### Cách 1 — ComfyUI Manager

1. Mở ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Tìm `ComfyUI-Model-Downloader` rồi cài đặt.
3. Khởi động lại ComfyUI.

### Cách 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Ứng dụng desktop (Comfy Desktop)**: thư mục `custom_nodes` nằm bên trong thư mục cài đặt, ví dụ `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (đường dẫn thay đổi tùy bố cục). Nếu không chắc, hãy xem mục "Import times for custom nodes" trong nhật ký máy chủ để biết thư mục nào thực sự được quét.

## Cách sử dụng

1. **Khởi động lại ComfyUI** sau khi cài đặt (plugin sẽ không có UI nếu máy chủ chưa tải lại nó).
2. Mở **mẫu** bất kỳ (hoặc bất kỳ quy trình nào có nút nhúng metadata `properties.models` — các mẫu chính thức đều có).
3. Đợi ~2 giây. Một nút nổi xuất hiện ở **góc dưới bên phải**:
   - `⬇ Download missing models (N)` — N mô hình bị thiếu/hỏng. **Nhấp vào nó** để bắt đầu tải.
4. **Bảng quản lý tải xuống** tự mở, hiển thị mọi tệp: biểu tượng trạng thái, thanh tiến trình, phần trăm, tốc độ trực tiếp, thư mục đích, thông báo lỗi.
5. Trong khi tải, bạn có thể:
   - Chuyển mẫu → nút hiển thị `Downloading x/y · Pending N (click to enqueue)`. **Không có gì tự tải xuống**; hãy nhấp nút để thêm mô hình còn thiếu của mẫu mới vào hàng đợi.
   - Trong bảng: sắp xếp lại các mục trong hàng đợi bằng ⏫/⏬, **Hủy** từng mục, **Dừng tất cả**, **Thử lại** các mục thất bại, **Xóa tệp**, **Hiện trong thư mục**.
6. Khi mọi thứ xong, bảng giữ lại kết quả cuối cùng (✅/⚠️) cho đến khi bạn đóng bằng ✕.

### Nút hiển thị gì

| Tình huống | Chữ trên nút | Hành động khi nhấp |
|---|---|---|
| Không có lượt tải nào đang chạy, có mô hình thiếu | `⬇ Download missing models (N)` | Bắt đầu tải |
| Đang tải, không có mục thiếu mới | `Downloading x/y · file 45%` | Mở bảng |
| Đang tải, mẫu mới có mô hình thiếu | `Downloading x/y · Pending N (click to enqueue)` | Thêm chúng vào hàng đợi |
| Đã xong hết, một số thất bại | `⚠ x ok / y failed (click to retry)` | Thử lại các mục thất bại |
| Không thiếu gì | (ẩn) | — |

## Logic tải xuống & tính toàn vẹn

Với mỗi mô hình, plugin kiểm tra (theo thứ tự):

1. Tệp không tồn tại hoặc ≤ 1 MB → **thiếu** → tải xuống.
2. Tồn tại `<file>.aria2` → **chưa hoàn tất** → aria2c nối lại.
3. Kích thước ≠ bản ghi LFS của Hugging Face → **hỏng** → xóa và tải lại.
4. SHA256 ≠ bản ghi LFS của Hugging Face → **hỏng** → xóa và tải lại (chỉ xác minh một lần mỗi phiên cho mỗi tệp, trừ khi tệp thay đổi).
5. Sau mỗi lượt tải hoàn tất, SHA256 được kiểm tra lại; nếu sai lệch thì mục đó bị đánh dấu thất bại.

Kích thước/hàm băm kỳ vọng lấy từ `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` và được lưu đệm theo URL. Các URL không phải Hugging Face (ví dụ Civitai) chỉ kiểm tra sự tồn tại + `.aria2` + kích thước.

## Kho lưu trữ bị kiểm soát (mô hình yêu cầu giấy phép)

Một số mô hình (ví dụ LTX-2.5, Gemma) bị **kiểm soát truy cập (gated)** trên Hugging Face — bạn phải chấp nhận giấy phép / yêu cầu quyền truy cập trước khi tải xuống. Plugin phát hiện điều này và báo lỗi bằng một thông báo rõ ràng thay vì lỗi khó hiểu.

1. Mở trang mô hình trên huggingface.co (ví dụ https://huggingface.co/Lightricks/LTX-2.5), đăng nhập, rồi chấp nhận điều khoản / yêu cầu quyền truy cập.
2. Tạo access token chỉ đọc: https://huggingface.co/settings/tokens → New token → loại **Read**.
3. Đặt nó làm biến môi trường cho ComfyUI rồi khởi động lại:
   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (thêm vào script khởi động ComfyUI)
4. Khởi động lại ComfyUI và thử lại — các lượt tải khi đó sẽ kèm `Authorization: Bearer <token>`, và metadata toàn vẹn (kích thước/SHA256) cũng được tải về cùng token.

## Cấu hình

Mọi giá trị có thể chỉnh đều là hằng số ở đầu `__init__.py`:

| Hằng số | Mặc định | Ý nghĩa |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Số tệp tải song song |
| cờ aria2 | `-x16 -s16 -k1M` | 16 kết nối/tệp, khối 1 MB |
| `HF_MIRROR` | `https://hf-mirror.com` | Mirror dùng cho URL `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | Tệp nhỏ hơn mức này được coi là thiếu |
| `ARIA2_FALLBACKS` | đường dẫn cục bộ | Vị trí tuyệt đối của aria2c sẽ thử nếu không có trong PATH |

## Xử lý sự cố

| Triệu chứng | Cách khắc phục |
|---|---|
| Không thấy nút nổi nào cả | Khởi động lại hoàn toàn ComfyUI (trên desktop: khay hệ thống → thoát). Kiểm tra nhật ký máy chủ xem có `Import times for custom nodes: … ComfyUI-Model-Downloader` không. Trong trang, làm mới cứng (Ctrl+R). Kiểm tra sức khỏe: mở `http://127.0.0.1:8188/comfy_fetch/ping` → sẽ trả về `{"ok": true}`. |
| Nút không hiện gì sau khi mở mẫu | Các nút của quy trình phải nhúng metadata `properties.models` (mẫu chính thức có). Với quy trình tự tạo không có metadata, plugin không có gì để kiểm tra — hãy thêm mô hình theo cách thủ công. |
| Tải xuống thất bại ngay lập tức | Không tìm thấy `aria2c` → cài aria2 và đảm bảo nó nằm trong PATH mà ComfyUI khởi động cùng (cần khởi động lại). |
| Rất chậm | Mạng của bạn cũng không tới được `hf-mirror.com`; hãy thử dùng proxy. |
| Số đếm có vẻ cũ sau khi chuyển mẫu | Đợi ~2 giây cho chu kỳ quét; nếu vẫn còn, làm mới cứng (Ctrl+R). |
| Thao tác trong bảng không có tác dụng | Tệp có thể đã bị xóa mất (xóa) hoặc không còn trong hàng đợi (sắp xếp lại); hãy kiểm tra biểu tượng trạng thái trong bảng. |

## Tham chiếu API (cho nhà phát triển)

Mọi endpoint đều do chính máy chủ ComfyUI phục vụ (không cần thêm cổng):

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

`reason` trên các mục bị thiếu: `missing` | `incomplete` (tự nối lại) | `size` | `hash`.

## Giấy phép

MIT © 2026 Bosconovitchi
