# ComfyUI-Model-Downloader

**Unduhan sekali klik dengan kecepatan penuh untuk model yang hilang pada template dan workflow ComfyUI — dengan manajemen antrean, aksi per file, dan verifikasi integritas.**

Plugin ComfyUI murni. Tanpa server mandiri, tanpa daemon tambahan: backend berada di dalam proses server ComfyUI dan UI berada di dalam halaman ComfyUI. Tutup ComfyUI dan semuanya berhenti (termasuk unduhan, melalui `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | **Português** | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | **العربية** | **हिन्दी** | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | **Bahasa Indonesia**

## Mengapa plugin ini ada

Pengunduh template bawaan ComfyUI mengunduh model secara **single-threaded**, dan di beberapa wilayah `huggingface.co` tidak dapat dijangkau atau dibatasi dengan sangat ketat, sehingga tombol "Download" bawaan gagal atau merayap. Plugin ini:

- Mendeteksi **model mana yang hilang** untuk template/workflow yang sedang terbuka (metadata yang sama dengan yang digunakan panel model-hilang bawaan).
- Mengunduhnya dengan **aria2c, 16 koneksi per file, 3 file paralel**, melalui **hf-mirror.com** secara otomatis (mirror Hugging Face yang cepat) — biasanya memenuhi bandwidth Anda.
- Melanjutkan unduhan yang terputus, **memverifikasi integritas file** (ukuran + SHA256 terhadap catatan LFS resmi Hugging Face), dan memberi Anda **panel pengelola unduhan** lengkap: coba lagi, batalkan, hentikan semua, susun ulang antrean, hapus file, tampilkan di folder.

## Cara kerjanya

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

- **Ikatan siklus hidup**: semuanya berjalan di dalam ComfyUI. Hentikan ComfyUI → rute-rute hilang dan setiap `aria2c` yang berjalan mengakhiri dirinya sendiri (`--stop-with-process=<pid server>`). Frontend juga menjeda polling saat halaman tersembunyi dan membersihkan diri saat unload.
- **Unduhan hanya manual**: mengganti template hanya menyegarkan hitungan model yang hilang. Tidak ada yang diunduh sampai Anda mengeklik tombolnya (atau mengeklik tombolnya lagi saat unduhan berjalan, untuk mengantrekan model yang hilang dari template baru).

## Fitur

| Fitur | Deskripsi |
|---|---|
| Deteksi otomatis | Buka template → tombol mengambang menunjukkan berapa banyak model yang hilang. Ganti template → hitungan diperbarui secara otomatis. |
| Unduhan cepat | aria2c, 16 koneksi/file, 3 file paralel, mirror `hf-mirror.com` otomatis untuk URL Hugging Face. |
| Manajemen antrean | Antrekan lebih banyak model di tengah unduhan, pindahkan item naik/turun, batalkan satu item, hentikan semuanya. |
| Verifikasi integritas | Pada setiap pemeriksaan: file hilang, sisa `.aria2` (tidak lengkap → resume otomatis), ukuran tidak cocok, SHA256 tidak cocok (vs catatan LFS HF). Setelah setiap unduhan: verifikasi ulang SHA256. File yang terverifikasi di-cache per sesi (mtime+ukuran) sehingga file besar tidak di-hash ulang setiap ganti template. |
| Aksi per file | Coba lagi, batalkan, susun ulang ⏫/⏬, hapus file dari disk (dengan konfirmasi), tampilkan di Windows Explorer. |
| Resume | Unduhan yang terputus menyimpan file kontrol `.aria2`; mengeklik unduh lagi akan melanjutkan alih-alih memulai ulang. |

## Persyaratan

- **ComfyUI** (versi terbaru apa pun dengan dukungan custom node; diuji pada ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** pada `PATH` lingkungan yang menjalankan ComfyUI
- Paket Python `requests` (sudah ada di instalasi ComfyUI standar)
- Windows / Linux didukung (tombol "tampilkan di folder" khusus Windows; Linux menurun dengan anggun)

### Memasang aria2

- **Windows**: unduh ZIP dari <https://github.com/aria2/aria2/releases> (mis. `aria2-1.37.0-win-64bit-build1.zip`), ekstrak, dan tambahkan folder yang berisi `aria2c.exe` ke `PATH` pengguna Anda.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Verifikasi: buka terminal dan jalankan `aria2c --version`.

## Instalasi

### Metode 1 — ComfyUI Manager

1. Buka ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Cari `ComfyUI-Model-Downloader` lalu pasang.
3. Mulai ulang ComfyUI.

### Metode 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Aplikasi desktop (Comfy Desktop)**: folder `custom_nodes` berada di dalam instalasi, mis. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (jalurnya bervariasi menurut tata letak). Jika ragu, periksa bagian "Import times for custom nodes" pada log server untuk melihat direktori mana yang benar-benar dipindai.

## Penggunaan

1. **Mulai ulang ComfyUI** setelah instalasi (plugin tidak memiliki UI jika server belum memuat ulangnya).
2. Buka **template** apa pun (atau workflow apa pun yang nodenya menyematkan metadata `properties.models` — template resmi melakukannya).
3. Tunggu ~2 detik. Sebuah tombol mengambang muncul di **kanan bawah**:
   - `⬇ Download missing models (N)` — N model hilang/rusak. **Klik tombolnya** untuk mulai mengunduh.
4. **Panel pengelola unduhan** terbuka otomatis, menampilkan setiap file: ikon status, bilah kemajuan, persentase, kecepatan langsung, folder tujuan, pesan kesalahan.
5. Saat mengunduh, Anda dapat:
   - Mengganti template → tombol menampilkan `Downloading x/y · Pending N (click to enqueue)`. **Tidak ada yang diunduh otomatis**; klik tombolnya untuk menambahkan model yang hilang dari template baru ke antrean.
   - Di panel: susun ulang item antrean ⏫/⏬, **Batalkan** satu item, **Hentikan semua**, **Coba lagi** item yang gagal, **Hapus file**, **Tampilkan di folder**.
6. Saat semuanya selesai, panel menyimpan hasil akhir (✅/⚠️) sampai Anda menutupnya dengan ✕.

### Yang ditampilkan tombol

| Situasi | Teks tombol | Aksi klik |
|---|---|---|
| Tidak ada unduhan berjalan, model hilang | `⬇ Download missing models (N)` | Mulai mengunduh |
| Unduhan berjalan, tidak ada yang baru hilang | `Downloading x/y · file 45%` | Buka panel |
| Unduhan berjalan, model template baru hilang | `Downloading x/y · Pending N (click to enqueue)` | Antrekan mereka |
| Semua selesai, sebagian gagal | `⚠ x ok / y failed (click to retry)` | Coba lagi yang gagal |
| Tidak ada yang hilang | (tersembunyi) | — |

## Logika unduhan & integritas

Untuk setiap model, plugin memeriksa (secara berurutan):

1. File tidak ada atau ≤ 1 MB → **hilang** → unduh.
2. `<file>.aria2` ada → **tidak lengkap** → aria2c melanjutkannya.
3. Ukuran ≠ catatan LFS Hugging Face → **rusak** → hapus & unduh ulang.
4. SHA256 ≠ catatan LFS Hugging Face → **rusak** → hapus & unduh ulang (hanya diverifikasi sekali per sesi per file kecuali file berubah).
5. Setelah setiap unduhan selesai, SHA256 diperiksa ulang; ketidakcocokan menandai item sebagai gagal.

Ukuran/hash yang diharapkan berasal dari `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` dan di-cache per URL. URL non-Hugging-Face (mis. Civitai) hanya mengandalkan pemeriksaan keberadaan + `.aria2` + ukuran.

## Konfigurasi

Semua pengaturan adalah konstanta di bagian atas `__init__.py`:

| Konstanta | Default | Arti |
|---|---|---|
| `MAX_CONCURRENT` | `3` | File paralel |
| flag aria2 | `-x16 -s16 -k1M` | 16 koneksi/file, potongan 1 MB |
| `HF_MIRROR` | `https://hf-mirror.com` | Mirror yang digunakan untuk URL `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | File yang lebih kecil dari ini dianggap hilang |
| `ARIA2_FALLBACKS` | jalur lokal | Lokasi aria2c absolut yang dicoba jika tidak ada di PATH |

## Pemecahan masalah

| Gejala | Perbaikan |
|---|---|
| Tidak ada tombol mengambang sama sekali | Mulai ulang ComfyUI sepenuhnya (baki → keluar di desktop). Periksa log server untuk `Import times for custom nodes: … ComfyUI-Model-Downloader`. Di halaman, muat ulang paksa (Ctrl+R). Pemeriksaan kesehatan: buka `http://127.0.0.1:8188/comfy_fetch/ping` → harus mengembalikan `{"ok": true}`. |
| Tombol tidak menampilkan apa pun setelah membuka template | Node workflow harus menyematkan metadata `properties.models` (template resmi melakukannya). Untuk workflow buatan tangan tanpa metadata, plugin tidak memiliki apa pun untuk diperiksa — tambahkan model secara manual. |
| Unduhan langsung gagal | `aria2c` tidak ditemukan → pasang aria2 dan pastikan ia ada di PATH yang digunakan ComfyUI saat memulai (perlu mulai ulang). |
| Sangat lambat | Jaringan Anda juga tidak dapat mencapai `hf-mirror.com`; coba proxy. |
| Hitungan tampak basi setelah mengganti template | Tunggu ~2 detik untuk siklus polling; muat ulang paksa (Ctrl+R) jika masih berlanjut. |
| Aksi panel tidak melakukan apa pun | File mungkin sudah hilang (hapus) atau tidak ada di antrean (susun ulang); periksa ikon status panel. |

## Referensi API (untuk pengembang)

Semua endpoint dilayani oleh server ComfyUI sendiri (tanpa port tambahan):

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

`reason` pada item yang hilang: `missing` | `incomplete` (resume otomatis) | `size` | `hash`.

## Lisensi

MIT © 2026 Bosconovitchi
