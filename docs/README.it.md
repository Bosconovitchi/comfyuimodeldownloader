# ComfyUI-Model-Downloader

**Download in un clic e a piena velocità dei modelli mancanti per template e workflow di ComfyUI — con gestione della coda, azioni per singolo file e verifica dell'integrità.**

Un plugin puro per ComfyUI. Nessun server autonomo, nessun demone aggiuntivo: il backend vive dentro il processo del server ComfyUI e l'interfaccia dentro la pagina di ComfyUI. Chiudi ComfyUI e tutto si ferma (download inclusi, tramite `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | **Français** | **Deutsch** | [Русский](docs/README.ru.md) | **Español** | [Português](docs/README.pt-BR.md) | **Italiano** | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Perché esiste questo plugin

Il downloader di template integrato di ComfyUI scarica i modelli **in single-thread** e, in alcune regioni, `huggingface.co` è irraggiungibile o fortemente limitato, per cui il pulsante «Download» integrato fallisce o procede a rilento. Questo plugin:

- Rileva **quali modelli mancano** per il template/workflow attualmente aperto (gli stessi metadati usati dal pannello integrato dei modelli mancanti).
- Li scarica con **aria2c, 16 connessioni per file, 3 file in parallelo**, tramite **hf-mirror.com** automaticamente (un mirror veloce di Hugging Face) — saturando in genere la tua banda.
- Riprende i download interrotti, **verifica l'integrità dei file** (dimensione + SHA256 rispetto ai record LFS ufficiali di Hugging Face) e ti offre un **pannello completo di gestore download**: riprova, annulla, ferma tutto, riordina la coda, elimina il file, mostra nella cartella.

## Come funziona

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

- **Vincolo al ciclo di vita**: tutto gira dentro ComfyUI. Ferma ComfyUI → le route spariscono e ogni `aria2c` in esecuzione si termina da solo (`--stop-with-process=<server pid>`). Il frontend inoltre mette in pausa il polling quando la pagina è nascosta e fa pulizia allo scaricamento.
- **Download solo manuali**: cambiare template aggiorna solo il conteggio dei modelli mancanti. Non viene scaricato nulla finché non fai clic sul pulsante (o non fai di nuovo clic durante un download in corso, per accodare i modelli mancanti del nuovo template).

## Funzionalità

| Funzionalità | Descrizione |
|---|---|
| Rilevamento automatico | Apri un template → il pulsante flottante mostra quanti modelli mancano. Cambia template → il conteggio si aggiorna automaticamente. |
| Download veloci | aria2c, 16 connessioni/file, 3 file in parallelo, mirror automatico `hf-mirror.com` per gli URL di Hugging Face. |
| Gestione della coda | Accoda altri modelli durante il download, sposta gli elementi su/giù, annulla singoli elementi, ferma tutto. |
| Verifica dell'integrità | A ogni controllo: file mancante, `.aria2` residuo (incompleto → ripresa automatica), dimensione errata, SHA256 errato (rispetto ai record HF LFS). Dopo ogni download: nuova verifica SHA256. I file verificati vengono memorizzati nella cache per sessione (mtime+dimensione), così i file grandi non vengono ri-hashati a ogni cambio di template. |
| Azioni per file | Riprova, annulla, riordina ⏫/⏬, elimina il file dal disco (con conferma), mostra in Esplora file di Windows. |
| Ripresa | I download interrotti conservano il loro file di controllo `.aria2`; cliccare di nuovo su download riprende invece di ricominciare. |

## Requisiti

- **ComfyUI** (qualsiasi versione recente con supporto ai nodi personalizzati; testato su ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** nel `PATH` dell'ambiente che avvia ComfyUI
- Pacchetto Python `requests` (già presente nelle installazioni standard di ComfyUI)
- Windows / Linux supportati (il pulsante «mostra nella cartella» è solo per Windows; Linux ripiega con eleganza)

### Installare aria2

- **Windows**: scarica lo ZIP da <https://github.com/aria2/aria2/releases> (es. `aria2-1.37.0-win-64bit-build1.zip`), estrailo e aggiungi la cartella che contiene `aria2c.exe` al tuo `PATH` utente.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Verifica: apri un terminale ed esegui `aria2c --version`.

## Installazione

### Metodo 1 — ComfyUI Manager

1. Apri ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Cerca `ComfyUI-Model-Downloader` e installalo.
3. Riavvia ComfyUI.

### Metodo 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **App desktop (Comfy Desktop)**: la cartella `custom_nodes` si trova dentro l'installazione, es. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (il percorso varia in base alla struttura). Nel dubbio, controlla la sezione «Import times for custom nodes» del log del server per vedere quale directory viene effettivamente scandita.

## Utilizzo

1. **Riavvia ComfyUI** dopo l'installazione (il plugin non ha interfaccia se il server non l'ha ricaricato).
2. Apri un qualsiasi **template** (o un workflow i cui nodi incorporano i metadati `properties.models` — i template ufficiali lo fanno).
3. Attendi ~2 secondi. In basso a destra appare un pulsante flottante:
   - `⬇ Download missing models (N)` — mancano/sono corrotti N modelli. **Fai clic** per iniziare il download.
4. Il **pannello del gestore download** si apre automaticamente e mostra ogni file: icona di stato, barra di avanzamento, percentuale, velocità in tempo reale, cartella di destinazione, messaggi di errore.
5. Durante il download puoi:
   - Cambiare template → il pulsante mostra `Downloading x/y · Pending N (click to enqueue)`. **Non viene scaricato nulla automaticamente**; fai clic sul pulsante per aggiungere alla coda i modelli mancanti del nuovo template.
   - Nel pannello: riordina gli elementi in coda ⏫/⏬, **Annulla** un singolo elemento, **Ferma tutto**, **Riprova** gli elementi falliti, **Elimina file**, **Mostra nella cartella**.
6. Quando tutto finisce, il pannello conserva i risultati finali (✅/⚠️) finché non lo chiudi con ✕.

### Cosa mostra il pulsante

| Situazione | Testo del pulsante | Azione al clic |
|---|---|---|
| Nessun download in corso, mancano modelli | `⬇ Download missing models (N)` | Avvia il download |
| Download in corso, nessun nuovo mancante | `Downloading x/y · file 45%` | Apri il pannello |
| Download in corso, mancano modelli di un nuovo template | `Downloading x/y · Pending N (click to enqueue)` | Accodali |
| Tutto finito, alcuni falliti | `⚠ x ok / y failed (click to retry)` | Riprova i falliti |
| Non manca nulla | (nascosto) | — |

## Logica di download e integrità

Per ogni modello il plugin controlla (in ordine):

1. File assente o ≤ 1 MB → **mancante** → scarica.
2. Esiste `<file>.aria2` → **incompleto** → aria2c lo riprende.
3. Dimensione ≠ record HF LFS → **corrotto** → elimina e riscarica.
4. SHA256 ≠ record HF LFS → **corrotto** → elimina e riscarica (verificato una sola volta per sessione e per file, a meno che il file non cambi).
5. Dopo ogni download completato l'SHA256 viene ricontrollato; una discrepanza marca l'elemento come fallito.

Dimensioni/hash attesi provengono da `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` e sono memorizzati nella cache per URL. Gli URL non di Hugging Face (es. Civitai) ripiegano su soli controlli di esistenza + `.aria2` + dimensione.

## Repository con accesso limitato (modelli soggetti a licenza)

Alcuni modelli (es. LTX-2.5, Gemma) sono **protetti** (gated) su Hugging Face — devi accettare la licenza / richiedere l'accesso prima di poterli scaricare. Il plugin lo rileva e fallisce con un messaggio chiaro invece di un errore criptico.

1. Apri la pagina del modello su huggingface.co (es. https://huggingface.co/Lightricks/LTX-2.5), accedi e accetta i termini / richiedi l'accesso.
2. Crea un token di accesso in sola lettura: https://huggingface.co/settings/tokens → New token → tipo **Read**.
3. Impostalo come variabile d'ambiente per ComfyUI e riavvia:
   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (aggiungilo allo script di avvio di ComfyUI)
4. Riavvia ComfyUI e riprova — i download includono quindi `Authorization: Bearer <token>` e anche i metadati di integrità (dimensione/SHA256) vengono recuperati con il token.

## Configurazione

Tutti i parametri regolabili sono costanti all'inizio di `__init__.py`:

| Costante | Predefinito | Significato |
|---|---|---|
| `MAX_CONCURRENT` | `3` | File in parallelo |
| Opzioni aria2 | `-x16 -s16 -k1M` | 16 connessioni/file, blocchi da 1 MB |
| `HF_MIRROR` | `https://hf-mirror.com` | Mirror usato per gli URL `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | I file più piccoli di questo valore contano come mancanti |
| `ARIA2_FALLBACKS` | percorsi locali | Posizioni assolute di aria2c provate se non è nel PATH |

## Risoluzione dei problemi

| Sintomo | Soluzione |
|---|---|
| Nessun pulsante flottante | Riavvia completamente ComfyUI (vassoio → esci sul desktop). Controlla nel log del server la presenza di `Import times for custom nodes: … ComfyUI-Model-Downloader`. Nella pagina, fai un aggiornamento forzato (Ctrl+R). Controllo di salute: apri `http://127.0.0.1:8188/comfy_fetch/ping` → dovrebbe restituire `{"ok": true}`. |
| Il pulsante non mostra nulla dopo l'apertura di un template | I nodi del workflow devono incorporare i metadati `properties.models` (i template ufficiali lo fanno). Per i workflow fatti a mano senza metadati, il plugin non ha nulla da controllare — aggiungi i modelli manualmente. |
| Il download fallisce immediatamente | `aria2c` non trovato → installa aria2 e assicurati che sia nel PATH con cui si avvia ComfyUI (richiede riavvio). |
| Molto lento | La tua rete non raggiunge nemmeno `hf-mirror.com`; prova un proxy. |
| Il conteggio sembra non aggiornato dopo il cambio di template | Attendi ~2 s per il ciclo di polling; fai un aggiornamento forzato (Ctrl+R) se persiste. |
| Un'azione del pannello non fa nulla | Il file potrebbe essere già sparito (eliminazione) o non essere in coda (riordino); controlla le icone di stato del pannello. |

## Riferimento API (per sviluppatori)

Tutti gli endpoint sono serviti dal server ComfyUI stesso (nessuna porta aggiuntiva):

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

`reason` sugli elementi mancanti: `missing` | `incomplete` (ripresa automatica) | `size` | `hash`.

## Licenza

MIT © 2026 Bosconovitchi
