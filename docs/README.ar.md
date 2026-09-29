# ComfyUI-Model-Downloader

**تنزيل بضغطة واحدة وبأقصى سرعة للنماذج الناقصة في قوالب وسير عمل ComfyUI — مع إدارة قائمة الانتظار، وإجراءات لكل ملف، والتحقق من سلامة الملفات.**

إضافة ComfyUI خالصة. لا خادم مستقل ولا عمليات خلفية إضافية: تعمل الواجهة الخلفية داخل عملية خادم ComfyUI وتعيش الواجهة داخل صفحة ComfyUI. أغلق ComfyUI فيتوقف كل شيء (بما في ذلك التنزيلات، عبر `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | **Português** | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | **العربية** | **हिन्दी** | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | **Bahasa Indonesia**

## لماذا وُجدت هذه الإضافة

يقوم منزّل القوالب المدمج في ComfyUI بتنزيل النماذج **بخيط واحد**، وفي بعض المناطق يتعذر الوصول إلى `huggingface.co` أو يكون مقيّدًا بشدة، فيفشل زر "Download" المدمج أو يزحف. هذه الإضافة:

- تكتشف **النماذج الناقصة** للقالب/سير العمل المفتوح حاليًا (نفس البيانات الوصفية التي يستخدمها لوح النماذج الناقصة المدمج).
- تنزّلها باستخدام **aria2c، 16 اتصالًا لكل ملف، و3 ملفات بالتوازي**، عبر **hf-mirror.com** تلقائيًا (مرآة Hugging Face سريعة) — وعادةً ما تشبع عرض النطاق الترددي لديك.
- تستأنف التنزيلات المتقطعة، و**تتحقق من سلامة الملفات** (الحجم + SHA256 مقابل سجلات LFS الرسمية لـ Hugging Face)، وتمنحك **لوحة مدير تنزيلات** كاملة: إعادة المحاولة، الإلغاء، إيقاف الكل، إعادة ترتيب قائمة الانتظار، حذف الملف، الإظهار في المجلد.

## كيف تعمل

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

- **ارتباط دورة الحياة**: كل شيء يعمل داخل ComfyUI. أوقف ComfyUI → تختفي المسارات وينهي كل `aria2c` قيد التشغيل نفسه (`--stop-with-process=<معرّف عملية الخادم>`). كما تُوقِف الواجهة الأمامية الاستقصاء أثناء إخفاء الصفحة وتنظّف عند التفريغ.
- **التنزيلات يدوية فقط**: تبديل القوالب يحدّث فقط عدد النماذج الناقصة. لا يُنزَّل شيء حتى تنقر الزر (أو تنقر الزر مرة أخرى أثناء تنزيل جارٍ لإضافة النماذج الناقصة من القالب الجديد إلى قائمة الانتظار).

## الميزات

| الميزة | الوصف |
|---|---|
| الاكتشاف التلقائي | افتح قالبًا → يعرض الزر العائم عدد النماذج الناقصة. بدّل القالب → يتحدّث العدد تلقائيًا. |
| تنزيل سريع | aria2c، 16 اتصالًا/ملفًا، 3 ملفات بالتوازي، مرآة `hf-mirror.com` تلقائية لعناوين Hugging Face. |
| إدارة قائمة الانتظار | أضف مزيدًا من النماذج أثناء التنزيل، حرّك العناصر لأعلى/لأسفل، ألغِ عناصر مفردة، أوقف كل شيء. |
| التحقق من السلامة | عند كل فحص: ملف ناقص، بقايا `.aria2` (غير مكتمل → استئناف تلقائي)، عدم تطابق الحجم، عدم تطابق SHA256 (مقابل سجلات HF LFS). بعد كل تنزيل: إعادة التحقق من SHA256. تُخزَّن الملفات المتحقق منها مؤقتًا لكل جلسة (mtime+الحجم) حتى لا تُعاد تجزئة الملفات الكبيرة عند كل تبديل قالب. |
| إجراءات لكل ملف | إعادة المحاولة، الإلغاء، إعادة الترتيب ⏫/⏬، حذف الملف من القرص (مع تأكيد)، الإظهار في مستكشف ويندوز. |
| الاستئناف | تحتفظ التنزيلات المتقطعة بملف التحكم `.aria2` الخاص بها؛ النقر على التنزيل مرة أخرى يستأنف بدلًا من إعادة البدء. |

## المتطلبات

- **ComfyUI** (أي إصدار حديث يدعم العقد المخصصة؛ مُختبَر على ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** في `PATH` البيئة التي تُشغّل ComfyUI
- حزمة Python `requests` (موجودة مسبقًا في تثبيتات ComfyUI القياسية)
- يدعم Windows / Linux (زر "الإظهار في المجلد" خاص بـ Windows فقط؛ ويتدهور Linux بلطف)

### تثبيت aria2

- **Windows**: نزّل ملف ZIP من <https://github.com/aria2/aria2/releases> (مثلًا `aria2-1.37.0-win-64bit-build1.zip`)، فك الضغط، وأضف المجلد الذي يحتوي على `aria2c.exe` إلى `PATH` المستخدم لديك.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (نظام macOS).
- تحقّق: افتح طرفية وشغّل `aria2c --version`.

## التثبيت

### الطريقة 1 — مدير ComfyUI

1. افتح ComfyUI → **Manager** → **Custom Nodes Manager**.
2. ابحث عن `ComfyUI-Model-Downloader` وثبّته.
3. أعد تشغيل ComfyUI.

### الطريقة 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **تطبيق سطح المكتب (Comfy Desktop)**: مجلد `custom_nodes` موجود داخل التثبيت، مثلًا `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (يختلف المسار حسب التخطيط). عند الشك، راجع قسم "Import times for custom nodes" في سجل الخادم لمعرفة الدليل الذي يُفحص فعليًا.

## الاستخدام

1. **أعد تشغيل ComfyUI** بعد التثبيت (لا تظهر واجهة للإضافة إذا لم يُعد الخادم تحميلها).
2. افتح أي **قالب** (أو أي سير عمل تُضمّن عقده بيانات `properties.models` — القوالب الرسمية تفعل ذلك).
3. انتظر ~ثانيتين. يظهر زر عائم في **أسفل اليمين**:
   - `⬇ Download missing models (N)` — هناك N نموذجًا ناقصًا/تالفًا. **انقر عليه** لبدء التنزيل.
4. تُفتح **لوحة مدير التنزيلات** تلقائيًا وتعرض كل ملف: أيقونة الحالة، شريط التقدم، النسبة المئوية، السرعة اللحظية، مجلد الوجهة، رسائل الخطأ.
5. أثناء التنزيل يمكنك:
   - تبديل القوالب → يعرض الزر `Downloading x/y · Pending N (click to enqueue)`. **لا يُنزَّل شيء تلقائيًا**؛ انقر الزر لإضافة النماذج الناقصة من القالب الجديد إلى قائمة الانتظار.
   - في اللوحة: أعد ترتيب العناصر المنتظرة ⏫/⏬، **إلغاء** عنصر واحد، **إيقاف الكل**، **إعادة المحاولة** للعناصر الفاشلة، **حذف الملف**، **الإظهار في المجلد**.
6. عند اكتمال كل شيء، تحتفظ اللوحة بالنتائج النهائية (✅/⚠️) حتى تغلقها بـ ✕.

### ما يعرضه الزر

| الحالة | نص الزر | إجراء النقر |
|---|---|---|
| لا تنزيل جارٍ، نماذج ناقصة | `⬇ Download missing models (N)` | بدء التنزيل |
| تنزيل جارٍ، لا نواقص جديدة | `Downloading x/y · file 45%` | فتح اللوحة |
| تنزيل جارٍ، نماذج القالب الجديد ناقصة | `Downloading x/y · Pending N (click to enqueue)` | إضافتها إلى قائمة الانتظار |
| اكتمل كل شيء، بعضها فشل | `⚠ x ok / y failed (click to retry)` | إعادة محاولة الفاشل |
| لا شيء ناقص | (مخفي) | — |

## منطق التنزيل والسلامة

لكل نموذج تتحقق الإضافة (بالترتيب):

1. الملف غائب أو ≤ 1 ميجابايت → **ناقص** → تنزيل.
2. يوجد `<file>.aria2` → **غير مكتمل** → يستأنفه aria2c.
3. الحجم ≠ سجل Hugging Face LFS → **تالف** → حذف وإعادة التنزيل.
4. SHA256 ≠ سجل Hugging Face LFS → **تالف** → حذف وإعادة التنزيل (يُتحقق منه مرة واحدة فقط لكل جلسة لكل ملف ما لم يتغير الملف).
5. بعد كل تنزيل مكتمل يُعاد فحص SHA256؛ وأي عدم تطابق يعلّم العنصر كفاشل.

تأتي الأحجام/التجزئات المتوقعة من `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` وتُخزَّن مؤقتًا لكل عنوان URL. تعتمد العناوين خارج Hugging Face (مثل Civitai) على فحوصات الوجود + `.aria2` + الحجم فقط.

## الإعداد

جميع القيم القابلة للضبط هي ثوابت في أعلى `__init__.py`:

| الثابت | الافتراضي | المعنى |
|---|---|---|
| `MAX_CONCURRENT` | `3` | الملفات المتوازية |
| أعلام aria2 | `-x16 -s16 -k1M` | 16 اتصالًا/ملفًا، مقاطع بحجم 1 ميجابايت |
| `HF_MIRROR` | `https://hf-mirror.com` | المرآة المستخدمة لعناوين `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | الملفات الأصغر من هذا تُعدّ ناقصة |
| `ARIA2_FALLBACKS` | مسارات محلية | مواقع aria2c المطلقة التي تُجرَّب إذا لم يكن في PATH |

## استكشاف الأخطاء وإصلاحها

| العَرَض | الحل |
|---|---|
| لا يظهر زر عائم إطلاقًا | أعد تشغيل ComfyUI بالكامل (من الدرج → إنهاء في سطح المكتب). ابحث في سجل الخادم عن `Import times for custom nodes: … ComfyUI-Model-Downloader`. في الصفحة، حدّث بقوة (Ctrl+R). فحص السلامة: افتح `http://127.0.0.1:8188/comfy_fetch/ping` → يجب أن يُرجع `{"ok": true}`. |
| لا يعرض الزر شيئًا بعد فتح قالب | يجب أن تُضمّن عقد سير العمل بيانات `properties.models` (القوالب الرسمية تفعل ذلك). بالنسبة لسير العمل المصنوع يدويًا بدون بيانات وصفية، لا تملك الإضافة ما تفحصه — أضف النماذج يدويًا. |
| يفشل التنزيل فورًا | لم يُعثر على `aria2c` → ثبّت aria2 وتأكد من وجوده في PATH الذي يبدأ به ComfyUI (يلزم إعادة التشغيل). |
| بطيء جدًا | شبكتك لا تصل إلى `hf-mirror.com` أيضًا؛ جرّب وكيلًا. |
| يبدو العدد قديمًا بعد تبديل القوالب | انتظر ~ثانيتين لدورة الاستقصاء؛ حدّث بقوة (Ctrl+R) إذا استمر الأمر. |
| إجراء اللوحة لا يفعل شيئًا | قد يكون الملف قد حُذف بالفعل (حذف) أو ليس في قائمة الانتظار (إعادة الترتيب)؛ تحقق من أيقونات الحالة في اللوحة. |

## مرجع واجهة برمجة التطبيقات (للمطورين)

تخدم جميع نقاط النهاية من خادم ComfyUI نفسه (بدون منفذ إضافي):

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

`reason` في العناصر الناقصة: `missing` | `incomplete` (استئناف تلقائي) | `size` | `hash`.

## الترخيص

MIT © 2026 Bosconovitchi
