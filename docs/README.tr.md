# ComfyUI-Model-Downloader

**ComfyUI şablonları ve iş akışları için eksik modelleri tek tıkla tam hızda indirme — kuyruk yönetimi, dosya bazında işlemler ve bütünlük doğrulamasıyla.**

Saf bir ComfyUI eklentisi. Ayrı bir sunucu yok, ekstra daemon yok: arka uç ComfyUI sunucu sürecinin içinde, arayüz de ComfyUI sayfasının içinde çalışır. ComfyUI'ı kapatın, her şey durur (indirmeler dahil, `aria2c --stop-with-process` sayesinde).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | **Русский** | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | **Türkçe** | **Nederlands** | **Polski** | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Bu eklenti neden var

ComfyUI'ın yerleşik şablon indiricisi modelleri **tek iş parçacıklı** indirir ve bazı bölgelerde `huggingface.co` erişilemez ya da ciddi şekilde kısıtlanmıştır; bu yüzden yerleşik "Download" düğmesi başarısız olur ya da sürünür. Bu eklenti:

- Açık olan şablon/iş akışı için **hangi modellerin eksik olduğunu** tespit eder (yerleşik eksik-modeller panelinin kullandığı meta verilerin aynısı).
- Bunları **aria2c ile, dosya başına 16 bağlantı, 3 dosya paralel** olarak, otomatik şekilde **hf-mirror.com** üzerinden (hızlı bir Hugging Face aynası) indirir — genellikle bant genişliğinizi doyurur.
- Yarım kalan indirmeleri devam ettirir, **dosya bütünlüğünü doğrular** (Hugging Face'in resmi LFS kayıtlarına göre boyut + SHA256) ve eksiksiz bir **indirme yöneticisi paneli** sunar: yeniden dene, iptal et, hepsini durdur, kuyruğu yeniden sırala, dosyayı sil, klasörde göster.

## Nasıl çalışır

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

- **Yaşam döngüsü bağı**: her şey ComfyUI'ın içinde çalışır. ComfyUI'ı durdurun → yollar kaybolur ve çalışan her `aria2c` kendini sonlandırır (`--stop-with-process=<server pid>`). Ön uç ayrıca sayfa gizliyken yoklamayı duraklatır ve sayfa kapanınca temizlik yapar.
- **İndirmeler yalnızca manueldir**: şablon değiştirmek yalnızca eksik model sayısını yeniler. Düğmeye tıklayana kadar hiçbir şey indirilmez (ya da indirme sürerken yeni şablonun eksik modellerini kuyruğa eklemek için düğmeye tekrar tıklayana kadar).

## Özellikler

| Özellik | Açıklama |
|---|---|
| Otomatik algılama | Bir şablon açın → yüzen düğme kaç modelin eksik olduğunu gösterir. Şablon değiştirin → sayaç otomatik güncellenir. |
| Hızlı indirme | aria2c, dosya başına 16 bağlantı, 3 paralel dosya, Hugging Face URL'leri için otomatik `hf-mirror.com` aynası. |
| Kuyruk yönetimi | İndirme sürerken kuyruğa model ekleyin, öğeleri yukarı/aşağı taşıyın, tek tek iptal edin, her şeyi durdurun. |
| Bütünlük doğrulaması | Her kontrolde: eksik dosya, kalan `.aria2` (tamamlanmamış → otomatik devam), boyut uyuşmazlığı, SHA256 uyuşmazlığı (HF LFS kayıtlarına göre). Her indirmeden sonra: SHA256 yeniden doğrulaması. Doğrulanan dosyalar oturum başına önbelleğe alınır (mtime+boyut), böylece büyük dosyalar her şablon değişiminde yeniden hash'lenmez. |
| Dosya bazında işlemler | Yeniden dene, iptal et, ⏫/⏬ sırala, dosyayı diskten sil (onayla), Windows Gezgini'nde göster. |
| Devam ettirme | Kesintiye uğrayan indirmeler `.aria2` kontrol dosyalarını korur; tekrar indirmeye tıklamak yeniden başlatmak yerine devam ettirir. |

## Gereksinimler

- **ComfyUI** (özel düğüm destekli güncel herhangi bir sürüm; ComfyUI 0.3.x + Comfy Desktop 1.x üzerinde test edildi)
- ComfyUI'ı başlatan ortamın `PATH` değerinde **aria2c**
- Python paketi `requests` (standart ComfyUI kurulumlarında zaten mevcuttur)
- Windows / Linux desteklenir ("klasörde göster" düğmesi yalnızca Windows'ta çalışır; Linux'ta zarifçe devre dışı kalır)

### aria2 kurulumu

- **Windows**: ZIP dosyasını <https://github.com/aria2/aria2/releases> adresinden indirin (örn. `aria2-1.37.0-win-64bit-build1.zip`), çıkarın ve `aria2c.exe` içeren klasörü kullanıcı `PATH` değerinize ekleyin.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Doğrulama: bir terminal açın ve `aria2c --version` çalıştırın.

## Kurulum

### Yöntem 1 — ComfyUI Manager

1. ComfyUI'ı açın → **Manager** → **Custom Nodes Manager**.
2. `ComfyUI-Model-Downloader` arayın ve kurun.
3. ComfyUI'ı yeniden başlatın.

### Yöntem 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Masaüstü uygulaması (Comfy Desktop)**: `custom_nodes` klasörü kurulumun içindedir, örn. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (yol yerleşime göre değişir). Emin değilseniz, hangi dizinin gerçekten tarandığını görmek için sunucu günlüğündeki "Import times for custom nodes" bölümüne bakın.

## Kullanım

1. Kurulumdan sonra **ComfyUI'ı yeniden başlatın** (sunucu yeniden yüklemediği sürece eklentinin arayüzü olmaz).
2. Herhangi bir **şablonu** açın (veya düğümleri `properties.models` meta verisi içeren herhangi bir iş akışını — resmi şablonlar içerir).
3. ~2 saniye bekleyin. **Sağ altta** yüzen bir düğme belirir:
   - `⬇ Download missing models (N)` — N model eksik/bozuk. İndirmeyi başlatmak için **tıklayın**.
4. **İndirme yöneticisi paneli** otomatik açılır ve her dosyayı gösterir: durum simgesi, ilerleme çubuğu, yüzde, canlı hız, hedef klasör, hata mesajları.
5. İndirme sürerken şunları yapabilirsiniz:
   - Şablon değiştirin → düğme `Downloading x/y · Pending N (click to enqueue)` gösterir. **Hiçbir şey otomatik indirilmez**; yeni şablonun eksik modellerini kuyruğa eklemek için düğmeye tıklayın.
   - Panelde: kuyruktaki öğeleri ⏫/⏬ sıralayın, tek bir öğeyi **İptal et**, **Hepsini durdur**, başarısız öğeleri **Yeniden dene**, **Dosyayı sil**, **Klasörde göster**.
6. Her şey bittiğinde panel, ✕ ile kapatana kadar son sonuçları (✅/⚠️) tutar.

### Düğme ne gösterir

| Durum | Düğme metni | Tıklama eylemi |
|---|---|---|
| İndirme yok, eksik modeller var | `⬇ Download missing models (N)` | İndirmeyi başlat |
| İndirme sürüyor, yeni eksik yok | `Downloading x/y · file 45%` | Paneli aç |
| İndirme sürüyor, yeni şablonda eksik modeller var | `Downloading x/y · Pending N (click to enqueue)` | Kuyruğa ekle |
| Hepsi bitti, bazıları başarısız | `⚠ x ok / y failed (click to retry)` | Başarısızları yeniden dene |
| Eksik yok | (gizli) | — |

## İndirme mantığı ve bütünlük

Eklenti her model için (sırayla) şunları kontrol eder:

1. Dosya yok ya da ≤ 1 MB → **eksik** → indir.
2. `<file>.aria2` mevcut → **tamamlanmamış** → aria2c devam ettirir.
3. Boyut ≠ Hugging Face LFS kaydı → **bozuk** → sil ve yeniden indir.
4. SHA256 ≠ Hugging Face LFS kaydı → **bozuk** → sil ve yeniden indir (dosya değişmediği sürece oturum başına dosya başına yalnızca bir kez doğrulanır).
5. Tamamlanan her indirmeden sonra SHA256 yeniden kontrol edilir; uyuşmazlık öğeyi başarısız olarak işaretler.

Beklenen boyutlar/hash'ler `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` adresinden gelir ve URL başına önbelleğe alınır. Hugging Face dışı URL'ler (örn. Civitai) yalnızca varlık + `.aria2` + boyut kontrollerine düşer.

## Korumalı depolar (lisans gerektiren modeller)

Bazı modeller (örn. LTX-2.5, Gemma) Hugging Face'te **korumalı** (gated) durumdadır — indirmeden önce lisansı kabul etmeniz / erişim talep etmeniz gerekir. Eklenti bunu algılar ve anlaşılmaz bir hata yerine açık bir mesajla başarısız olur.

1. huggingface.co üzerindeki model sayfasını açın (örn. https://huggingface.co/Lightricks/LTX-2.5), oturum açın ve koşulları kabul edin / erişim talep edin.
2. Salt okunur bir erişim anahtarı (token) oluşturun: https://huggingface.co/settings/tokens → New token → türü **Read**.
3. Bunu ComfyUI için bir ortam değişkeni olarak ayarlayın ve yeniden başlatın:
   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (ComfyUI başlangıç betiğine ekleyin)
4. ComfyUI'ı yeniden başlatın ve tekrar deneyin — indirmeler artık `Authorization: Bearer <token>` başlığını taşır ve bütünlük meta verileri (boyut/SHA256) de bu token ile alınır.

## Yapılandırma

Tüm ayarlanabilir değerler `__init__.py` dosyasının başındaki sabitlerdir:

| Sabit | Varsayılan | Anlamı |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Paralel dosyalar |
| aria2 bayrakları | `-x16 -s16 -k1M` | Dosya başına 16 bağlantı, 1 MB parçalar |
| `HF_MIRROR` | `https://hf-mirror.com` | `huggingface.co` URL'leri için kullanılan ayna |
| `MIN_FILE_SIZE` | `1_000_000` | Bundan küçük dosyalar eksik sayılır |
| `ARIA2_FALLBACKS` | yerel yollar | PATH'te yoksa denen mutlak aria2c konumları |

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| Yüzen düğme hiç görünmüyor | ComfyUI'ı tamamen yeniden başlatın (masaüstünde: tepsi → kapat). Sunucu günlüğünde `Import times for custom nodes: … ComfyUI-Model-Downloader` kaydını kontrol edin. Sayfada sert yenileme yapın (Ctrl+R). Sağlık kontrolü: `http://127.0.0.1:8188/comfy_fetch/ping` adresini açın → `{"ok": true}` dönmelidir. |
| Şablon açıldıktan sonra düğme hiçbir şey göstermiyor | İş akışının düğümleri `properties.models` meta verisi içermelidir (resmi şablonlar içerir). Meta verisi olmayan elle yapılmış iş akışları için eklentinin kontrol edeceği bir şey yoktur — modelleri elle ekleyin. |
| İndirme hemen başarısız oluyor | `aria2c` bulunamadı → aria2'yi kurun ve ComfyUI'ın başladığı PATH'te olduğundan emin olun (yeniden başlatma gerekir). |
| Çok yavaş | Ağınız `hf-mirror.com` adresine de ulaşamıyor; bir proxy deneyin. |
| Şablon değiştirdikten sonra sayaç güncel görünmüyor | Yoklama döngüsü için ~2 sn bekleyin; devam ederse sert yenileme yapın (Ctrl+R). |
| Panel eylemi hiçbir şey yapmıyor | Dosya zaten silinmiş (silme) ya da kuyrukta değil (yeniden sıralama) olabilir; paneldeki durum simgelerini kontrol edin. |

## API referansı (geliştiriciler için)

Tüm uç noktalar ComfyUI sunucusunun kendisi tarafından sunulur (ekstra port yok):

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

Eksik öğelerde `reason`: `missing` | `incomplete` (otomatik devam) | `size` | `hash`.

## Lisans

MIT © 2026 Bosconovitchi
