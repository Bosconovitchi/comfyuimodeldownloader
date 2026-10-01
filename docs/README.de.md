# ComfyUI-Model-Downloader

**Ein-Klick-Download fehlender Modelle für ComfyUI-Vorlagen und -Workflows mit voller Geschwindigkeit — mit Warteschlangenverwaltung, Aktionen pro Datei und Integritätsprüfung.**

Ein reines ComfyUI-Plugin. Kein eigenständiger Server, keine zusätzlichen Daemons: Das Backend läuft im ComfyUI-Serverprozess und die Oberfläche in der ComfyUI-Seite. Schließen Sie ComfyUI und alles stoppt (Downloads eingeschlossen, über `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | **Français** | **Deutsch** | [Русский](docs/README.ru.md) | **Español** | [Português](docs/README.pt-BR.md) | **Italiano** | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Warum es dieses Plugin gibt

Der eingebaute Vorlagen-Downloader von ComfyUI lädt Modelle **single-threaded** herunter, und in manchen Regionen ist `huggingface.co` nicht erreichbar oder stark gedrosselt, sodass der eingebaute „Download“-Button scheitert oder kriecht. Dieses Plugin:

- Erkennt, **welche Modelle fehlen** für die aktuell geöffnete Vorlage/den aktuell geöffneten Workflow (dieselben Metadaten, die auch das eingebaute Panel für fehlende Modelle verwendet).
- Lädt sie mit **aria2c, 16 Verbindungen pro Datei, 3 Dateien parallel** herunter, automatisch über **hf-mirror.com** (einen schnellen Hugging-Face-Spiegel) — und sättigt damit in der Regel Ihre Bandbreite.
- Setzt unterbrochene Downloads fort, **prüft die Dateiintegrität** (Größe + SHA256 gegen die offiziellen LFS-Einträge von Hugging Face) und bietet ein vollständiges **Download-Manager-Panel**: erneut versuchen, abbrechen, alles stoppen, Warteschlange neu ordnen, Datei löschen, im Ordner anzeigen.

## So funktioniert es

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

- **Lebenszyklus-Bindung**: Alles läuft innerhalb von ComfyUI. Stoppen Sie ComfyUI → die Routen verschwinden und jeder laufende `aria2c` beendet sich selbst (`--stop-with-process=<server pid>`). Das Frontend pausiert außerdem das Polling, solange die Seite ausgeblendet ist, und räumt beim Entladen auf.
- **Downloads nur manuell**: Der Wechsel der Vorlage aktualisiert nur die Anzahl der fehlenden Modelle. Es wird nichts heruntergeladen, bis Sie auf den Button klicken (oder während eines laufenden Downloads erneut klicken, um die fehlenden Modelle der neuen Vorlage einzureihen).

## Funktionen

| Funktion | Beschreibung |
|---|---|
| Automatische Erkennung | Vorlage öffnen → der schwebende Button zeigt, wie viele Modelle fehlen. Vorlage wechseln → die Anzahl wird automatisch aktualisiert. |
| Schnelle Downloads | aria2c, 16 Verbindungen/Datei, 3 parallele Dateien, automatischer `hf-mirror.com`-Spiegel für Hugging-Face-URLs. |
| Warteschlangenverwaltung | Weitere Modelle während des Downloads einreihen, Einträge nach oben/unten verschieben, einzelne Einträge abbrechen, alles stoppen. |
| Integritätsprüfung | Bei jeder Prüfung: fehlende Datei, übrig gebliebene `.aria2` (unvollständig → automatische Fortsetzung), Größenabweichung, SHA256-Abweichung (gegen HF-LFS-Einträge). Nach jedem Download: erneute SHA256-Prüfung. Geprüfte Dateien werden pro Sitzung gecacht (mtime+Größe), damit große Dateien nicht bei jedem Vorlagenwechsel neu gehasht werden. |
| Aktionen pro Datei | Erneut versuchen, abbrechen, ⏫/⏬ neu ordnen, Datei von der Festplatte löschen (mit Bestätigung), im Windows-Explorer anzeigen. |
| Fortsetzen | Unterbrochene Downloads behalten ihre `.aria2`-Steuerdatei; ein erneuter Klick auf „Herunterladen“ setzt fort statt neu zu starten. |

## Voraussetzungen

- **ComfyUI** (jede neuere Version mit Custom-Node-Unterstützung; getestet mit ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** im `PATH` der Umgebung, die ComfyUI startet
- Python-Paket `requests` (in Standard-ComfyUI-Installationen bereits vorhanden)
- Windows / Linux unterstützt (der Button „im Ordner anzeigen“ ist nur unter Windows verfügbar; Linux fällt sauber zurück)

### aria2 installieren

- **Windows**: ZIP von <https://github.com/aria2/aria2/releases> herunterladen (z. B. `aria2-1.37.0-win-64bit-build1.zip`), entpacken und den Ordner mit `aria2c.exe` zum Benutzer-`PATH` hinzufügen.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Prüfen: ein Terminal öffnen und `aria2c --version` ausführen.

## Installation

### Methode 1 — ComfyUI Manager

1. ComfyUI öffnen → **Manager** → **Custom Nodes Manager**.
2. `ComfyUI-Model-Downloader` suchen und installieren.
3. ComfyUI neu starten.

### Methode 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Desktop-App (Comfy Desktop)**: Der Ordner `custom_nodes` liegt innerhalb der Installation, z. B. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (Pfad je nach Layout unterschiedlich). Im Zweifel prüfen Sie den Abschnitt „Import times for custom nodes“ im Serverprotokoll, um zu sehen, welches Verzeichnis tatsächlich gescannt wird.

## Verwendung

1. **ComfyUI nach der Installation neu starten** (das Plugin hat keine Oberfläche, wenn der Server es nicht neu geladen hat).
2. Eine beliebige **Vorlage** öffnen (oder einen Workflow, dessen Nodes `properties.models`-Metadaten einbetten — offizielle Vorlagen tun das).
3. ~2 Sekunden warten. Unten rechts erscheint ein schwebender Button:
   - `⬇ Download missing models (N)` — N Modelle fehlen/sind defekt. **Klicken Sie darauf**, um den Download zu starten.
4. Das **Download-Manager-Panel** öffnet sich automatisch und zeigt jede Datei: Statussymbol, Fortschrittsbalken, Prozentsatz, Live-Geschwindigkeit, Zielordner, Fehlermeldungen.
5. Während des Downloads können Sie:
   - Die Vorlage wechseln → der Button zeigt `Downloading x/y · Pending N (click to enqueue)`. **Es wird nichts automatisch heruntergeladen**; klicken Sie auf den Button, um die fehlenden Modelle der neuen Vorlage in die Warteschlange aufzunehmen.
   - Im Panel: ⏫/⏬ eingereihte Einträge neu ordnen, einen einzelnen Eintrag **Abbrechen**, **Alle stoppen**, fehlgeschlagene Einträge **erneut versuchen**, **Datei löschen**, **Im Ordner anzeigen**.
6. Wenn alles fertig ist, behält das Panel die Endergebnisse (✅/⚠️), bis Sie es mit ✕ schließen.

### Was der Button anzeigt

| Situation | Button-Text | Klick-Aktion |
|---|---|---|
| Kein Download aktiv, Modelle fehlen | `⬇ Download missing models (N)` | Download starten |
| Download aktiv, nichts Neues fehlt | `Downloading x/y · file 45%` | Panel öffnen |
| Download aktiv, neue Vorlage hat fehlende Modelle | `Downloading x/y · Pending N (click to enqueue)` | Sie einreihen |
| Alles fertig, einige fehlgeschlagen | `⚠ x ok / y failed (click to retry)` | Fehlschläge erneut versuchen |
| Nichts fehlt | (ausgeblendet) | — |

## Download-Logik & Integrität

Für jedes Modell prüft das Plugin (in dieser Reihenfolge):

1. Datei fehlt oder ≤ 1 MB → **fehlend** → herunterladen.
2. `<file>.aria2` existiert → **unvollständig** → aria2c setzt fort.
3. Größe ≠ HF-LFS-Eintrag → **beschädigt** → löschen und erneut herunterladen.
4. SHA256 ≠ HF-LFS-Eintrag → **beschädigt** → löschen und erneut herunterladen (nur einmal pro Sitzung und Datei geprüft, außer die Datei ändert sich).
5. Nach jedem abgeschlossenen Download wird der SHA256 erneut geprüft; eine Abweichung markiert den Eintrag als fehlgeschlagen.

Erwartete Größen/Hashes stammen von `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` und werden pro URL gecacht. Nicht-Hugging-Face-URLs (z. B. Civitai) fallen auf reine Existenz- + `.aria2`- + Größenprüfungen zurück.

## Gesperrte Repositories (lizenzpflichtige Modelle)

Einige Modelle (z. B. LTX-2.5, Gemma) sind auf Hugging Face **gesperrt** (gated) — Sie müssen die Lizenz akzeptieren / den Zugriff beantragen, bevor Sie sie herunterladen können. Das Plugin erkennt dies und schlägt mit einer klaren Meldung statt eines kryptischen Fehlers fehl.

1. Öffnen Sie die Modellseite auf huggingface.co (z. B. https://huggingface.co/Lightricks/LTX-2.5), melden Sie sich an und akzeptieren Sie die Bedingungen / beantragen Sie den Zugriff.
2. Erstellen Sie ein schreibgeschütztes Zugriffstoken: https://huggingface.co/settings/tokens → New token → Typ **Read**.
3. Legen Sie es als Umgebungsvariable für ComfyUI fest und starten Sie neu:
   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (zum ComfyUI-Startskript hinzufügen)
4. Starten Sie ComfyUI neu und versuchen Sie es erneut — die Downloads enthalten dann `Authorization: Bearer <token>`, und auch die Integritätsmetadaten (Größe/SHA256) werden mit dem Token abgerufen.

## Konfiguration

Alle einstellbaren Werte sind Konstanten am Anfang von `__init__.py`:

| Konstante | Standard | Bedeutung |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Parallele Dateien |
| aria2-Flags | `-x16 -s16 -k1M` | 16 Verbindungen/Datei, 1-MB-Chunks |
| `HF_MIRROR` | `https://hf-mirror.com` | Spiegel für `huggingface.co`-URLs |
| `MIN_FILE_SIZE` | `1_000_000` | Dateien kleiner als dieser Wert gelten als fehlend |
| `ARIA2_FALLBACKS` | lokale Pfade | Absolute aria2c-Speicherorte, die versucht werden, wenn nicht im PATH |

## Fehlerbehebung

| Symptom | Lösung |
|---|---|
| Überhaupt kein schwebender Button | ComfyUI vollständig neu starten (Tray → Beenden auf dem Desktop). Im Serverprotokoll nach `Import times for custom nodes: … ComfyUI-Model-Downloader` suchen. Auf der Seite hart neu laden (Strg+R). Health-Check: `http://127.0.0.1:8188/comfy_fetch/ping` öffnen → sollte `{"ok": true}` zurückgeben. |
| Button zeigt nach dem Öffnen einer Vorlage nichts an | Die Nodes des Workflows müssen `properties.models`-Metadaten einbetten (offizielle Vorlagen tun das). Bei handgemachten Workflows ohne Metadaten hat das Plugin nichts zu prüfen — fügen Sie die Modelle manuell hinzu. |
| Download schlägt sofort fehl | `aria2c` nicht gefunden → aria2 installieren und sicherstellen, dass es im PATH liegt, mit dem ComfyUI startet (Neustart erforderlich). |
| Sehr langsam | Ihr Netzwerk erreicht auch `hf-mirror.com` nicht; versuchen Sie einen Proxy. |
| Anzahl wirkt nach Vorlagenwechsel veraltet | ~2 s auf den Poll-Zyklus warten; hart neu laden (Strg+R), falls es anhält. |
| Panel-Aktion tut nichts | Die Datei ist möglicherweise bereits weg (Löschen) oder nicht in der Warteschlange (neu ordnen); prüfen Sie die Statussymbole im Panel. |

## API-Referenz (für Entwickler)

Alle Endpunkte werden vom ComfyUI-Server selbst bereitgestellt (kein zusätzlicher Port):

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

`reason` bei fehlenden Einträgen: `missing` | `incomplete` (automatische Fortsetzung) | `size` | `hash`.

## Lizenz

MIT © 2026 Bosconovitchi
