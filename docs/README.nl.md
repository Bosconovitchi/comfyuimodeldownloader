# ComfyUI-Model-Downloader

**Ontbrekende modellen voor ComfyUI-sjablonen en -workflows met één klik op volle snelheid downloaden — met wachtrijbeheer, acties per bestand en integriteitscontrole.**

Een pure ComfyUI-plugin. Geen losse server, geen extra daemons: de backend draait binnen het ComfyUI-serverproces en de UI binnen de ComfyUI-pagina. Sluit ComfyUI en alles stopt (inclusief downloads, dankzij `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | **Русский** | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | **Türkçe** | **Nederlands** | **Polski** | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Waarom deze plugin bestaat

De ingebouwde sjabloondownloader van ComfyUI downloadt modellen **single-threaded**, en in sommige regio's is `huggingface.co` onbereikbaar of zwaar afgeknepen, waardoor de ingebouwde "Download"-knop faalt of kruipt. Deze plugin:

- Detecteert **welke modellen ontbreken** voor het momenteel geopende sjabloon/workflow (dezelfde metadata die het ingebouwde paneel voor ontbrekende modellen gebruikt).
- Downloadt ze met **aria2c, 16 verbindingen per bestand, 3 bestanden parallel**, automatisch via **hf-mirror.com** (een snelle Hugging Face-mirror) — doorgaans wordt je bandbreedte volledig benut.
- Hervat onderbroken downloads, **verifieert de bestandsintegriteit** (grootte + SHA256 tegen de officiële LFS-records van Hugging Face) en geeft je een volledig **downloadmanager-paneel**: opnieuw proberen, annuleren, alles stoppen, wachtrij herschikken, bestand verwijderen, tonen in map.

## Hoe het werkt

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

- **Levenscycluskoppeling**: alles draait binnen ComfyUI. Stop ComfyUI → de routes verdwijnen en elke draaiende `aria2c` beëindigt zichzelf (`--stop-with-process=<server pid>`). De frontend pauzeert ook het pollen terwijl de pagina verborgen is en ruimt op bij het verlaten.
- **Downloads zijn uitsluitend handmatig**: van sjabloon wisselen vernieuwt alleen het aantal ontbrekende modellen. Er wordt niets gedownload totdat je op de knop klikt (of opnieuw klikt terwijl een download loopt, om de ontbrekende modellen van het nieuwe sjabloon in de wachtrij te zetten).

## Functies

| Functie | Beschrijving |
|---|---|
| Automatische detectie | Open een sjabloon → de zwevende knop toont hoeveel modellen ontbreken. Wissel van sjabloon → de teller werkt automatisch bij. |
| Snelle downloads | aria2c, 16 verbindingen/bestand, 3 parallelle bestanden, automatische `hf-mirror.com`-mirror voor Hugging Face-URL's. |
| Wachtrijbeheer | Voeg tijdens het downloaden modellen toe, verplaats items omhoog/omlaag, annuleer losse items, stop alles. |
| Integriteitsverificatie | Bij elke controle: ontbrekend bestand, achtergebleven `.aria2` (onvolledig → automatisch hervatten), grootteafwijking, SHA256-afwijking (t.o.v. HF LFS-records). Na elke download: SHA256-herverificatie. Geverifieerde bestanden worden per sessie gecachet (mtime+grootte), zodat grote bestanden niet bij elke sjabloonwissel opnieuw worden gehasht. |
| Acties per bestand | Opnieuw proberen, annuleren, ⏫/⏬ herschikken, bestand van schijf verwijderen (met bevestiging), tonen in Windows Verkenner. |
| Hervatten | Onderbroken downloads behouden hun `.aria2`-controlebestand; opnieuw op downloaden klikken hervat in plaats van opnieuw te beginnen. |

## Vereisten

- **ComfyUI** (elke recente versie met ondersteuning voor custom nodes; getest op ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** in de `PATH` van de omgeving die ComfyUI start
- het Python-pakket `requests` (al aanwezig in standaard ComfyUI-installaties)
- Windows / Linux ondersteund (de knop "tonen in map" werkt alleen op Windows; op Linux wordt netjes teruggevallen)

### aria2 installeren

- **Windows**: download de ZIP van <https://github.com/aria2/aria2/releases> (bijv. `aria2-1.37.0-win-64bit-build1.zip`), pak uit en voeg de map met `aria2c.exe` toe aan je gebruikers-`PATH`.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Controleer: open een terminal en voer `aria2c --version` uit.

## Installatie

### Methode 1 — ComfyUI Manager

1. Open ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Zoek `ComfyUI-Model-Downloader` en installeer.
3. Herstart ComfyUI.

### Methode 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Desktop-app (Comfy Desktop)**: de map `custom_nodes` bevindt zich binnen de installatie, bijv. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (het pad varieert per indeling). Kijk bij twijfel in de serverlog bij "Import times for custom nodes" om te zien welke map daadwerkelijk wordt gescand.

## Gebruik

1. **Herstart ComfyUI** na de installatie (de plugin heeft geen UI zolang de server hem niet opnieuw heeft geladen).
2. Open een willekeurig **sjabloon** (of een workflow waarvan de nodes `properties.models`-metadata bevatten — officiële sjablonen doen dat).
3. Wacht ~2 seconden. **Rechtsonder** verschijnt een zwevende knop:
   - `⬇ Download missing models (N)` — N modellen ontbreken/zijn kapot. **Klik erop** om het downloaden te starten.
4. Het **downloadmanager-paneel** opent automatisch en toont elk bestand: statuspictogram, voortgangsbalk, percentage, live snelheid, doelmap, foutmeldingen.
5. Tijdens het downloaden kun je:
   - Van sjabloon wisselen → de knop toont `Downloading x/y · Pending N (click to enqueue)`. **Er wordt niets automatisch gedownload**; klik op de knop om de ontbrekende modellen van het nieuwe sjabloon aan de wachtrij toe te voegen.
   - In het paneel: items in de wachtrij ⏫/⏬ herschikken, een los item **Annuleren**, **Alles stoppen**, mislukte items **Opnieuw proberen**, **Bestand verwijderen**, **Tonen in map**.
6. Als alles klaar is, bewaart het paneel de eindresultaten (✅/⚠️) totdat je het sluit met ✕.

### Wat de knop toont

| Situatie | Knoptekst | Klikactie |
|---|---|---|
| Geen download bezig, modellen ontbreken | `⬇ Download missing models (N)` | Downloaden starten |
| Download bezig, geen nieuwe ontbrekende | `Downloading x/y · file 45%` | Paneel openen |
| Download bezig, nieuw sjabloon mist modellen | `Downloading x/y · Pending N (click to enqueue)` | In wachtrij zetten |
| Alles klaar, sommige mislukt | `⚠ x ok / y failed (click to retry)` | Mislukte opnieuw proberen |
| Niets ontbreekt | (verborgen) | — |

## Downloadlogica en integriteit

Voor elk model controleert de plugin (in volgorde):

1. Bestand afwezig of ≤ 1 MB → **ontbreekt** → downloaden.
2. `<file>.aria2` bestaat → **onvolledig** → aria2c hervat het.
3. Grootte ≠ Hugging Face LFS-record → **beschadigd** → verwijderen en opnieuw downloaden.
4. SHA256 ≠ Hugging Face LFS-record → **beschadigd** → verwijderen en opnieuw downloaden (per sessie per bestand slechts één keer geverifieerd, tenzij het bestand verandert).
5. Na elke voltooide download wordt de SHA256 opnieuw gecontroleerd; een afwijking markeert het item als mislukt.

Verwachte groottes/hashes komen van `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` en worden per URL gecachet. Niet-Hugging-Face-URL's (bijv. Civitai) vallen terug op alleen bestaan + `.aria2` + groottecontroles.

## Gated-repositories (modellen waarvoor een licentie vereist is)

Sommige modellen (bijv. LTX-2.5, Gemma) zijn **gated** op Hugging Face — je moet de licentie accepteren / toegang aanvragen voordat je kunt downloaden. De plugin detecteert dit en faalt met een duidelijke melding in plaats van een cryptische fout.

1. Open de modelpagina op huggingface.co (bijv. https://huggingface.co/Lightricks/LTX-2.5), log in en accepteer de voorwaarden / vraag toegang aan.
2. Maak een alleen-lezen-toegangstoken aan: https://huggingface.co/settings/tokens → New token → type **Read**.
3. Stel deze in als omgevingsvariabele voor ComfyUI en herstart:
   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (voeg toe aan je ComfyUI-startscript)
4. Herstart ComfyUI en probeer opnieuw — downloads dragen dan `Authorization: Bearer <token>`, en integriteitsmetadata (grootte/SHA256) wordt ook met het token opgehaald.

## Configuratie

Alle instelbare waarden zijn constanten bovenaan in `__init__.py`:

| Constante | Standaard | Betekenis |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Parallelle bestanden |
| aria2-vlaggen | `-x16 -s16 -k1M` | 16 verbindingen/bestand, 1 MB-chunks |
| `HF_MIRROR` | `https://hf-mirror.com` | Mirror gebruikt voor `huggingface.co`-URL's |
| `MIN_FILE_SIZE` | `1_000_000` | Bestanden kleiner dan dit tellen als ontbrekend |
| `ARIA2_FALLBACKS` | lokale paden | Absolute aria2c-locaties die worden geprobeerd als hij niet in PATH staat |

## Problemen oplossen

| Symptoom | Oplossing |
|---|---|
| Helemaal geen zwevende knop | Herstart ComfyUI volledig (op desktop: systeemvak → afsluiten). Controleer in de serverlog op `Import times for custom nodes: … ComfyUI-Model-Downloader`. Doe op de pagina een harde refresh (Ctrl+R). Gezondheidscheck: open `http://127.0.0.1:8188/comfy_fetch/ping` → zou `{"ok": true}` moeten retourneren. |
| Knop toont niets na het openen van een sjabloon | De nodes van de workflow moeten `properties.models`-metadata bevatten (officiële sjablonen doen dat). Bij handgemaakte workflows zonder metadata heeft de plugin niets te controleren — voeg de modellen handmatig toe. |
| Download mislukt onmiddellijk | `aria2c` niet gevonden → installeer aria2 en zorg dat hij in de PATH staat waarmee ComfyUI start (herstart vereist). |
| Erg traag | Je netwerk kan `hf-mirror.com` ook niet bereiken; probeer een proxy. |
| Teller lijkt verouderd na wisselen van sjabloon | Wacht ~2 s op de pollcyclus; als het aanhoudt: harde refresh (Ctrl+R). |
| Paneelactie doet niets | Het bestand is mogelijk al verdwenen (verwijderen) of staat niet in de wachtrij (herschikken); controleer de statuspictogrammen in het paneel. |

## API-referentie (voor ontwikkelaars)

Alle endpoints worden door de ComfyUI-server zelf geserveerd (geen extra poort):

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

`reason` bij ontbrekende items: `missing` | `incomplete` (automatisch hervatten) | `size` | `hash`.

## Licentie

MIT © 2026 Bosconovitchi
