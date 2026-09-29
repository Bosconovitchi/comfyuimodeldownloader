# ComfyUI-Model-Downloader

**Pobieranie brakujących modeli do szablonów i workflow ComfyUI jednym kliknięciem z pełną prędkością — z zarządzaniem kolejką, akcjami dla poszczególnych plików i weryfikacją integralności.**

Czysta wtyczka ComfyUI. Bez osobnego serwera, bez dodatkowych demonów: backend działa wewnątrz procesu serwera ComfyUI, a interfejs — wewnątrz strony ComfyUI. Zamknij ComfyUI, a wszystko się zatrzyma (w tym pobierania, dzięki `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | **Русский** | [Español](docs/README.es.md) | [Português](docs/README.pt-BR.md) | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | **Türkçe** | **Nederlands** | **Polski** | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Po co ta wtyczka

Wbudowany program pobierający szablonów ComfyUI pobiera modele **jednowątkowo**, a w niektórych regionach `huggingface.co` jest nieosiągalny lub mocno dławiony, przez co wbudowany przycisk "Download" zawodzi lub pełznie. Ta wtyczka:

- Wykrywa, **których modeli brakuje** dla aktualnie otwartego szablonu/workflow (te same metadane, których używa wbudowany panel brakujących modeli).
- Pobiera je za pomocą **aria2c, 16 połączeń na plik, 3 pliki równolegle**, automatycznie przez **hf-mirror.com** (szybkie lustro Hugging Face) — zwykle wykorzystując całą przepustowość łącza.
- Wznawia przerwane pobierania, **weryfikuje integralność plików** (rozmiar + SHA256 względem oficjalnych rekordów LFS Hugging Face) i daje pełny **panel menedżera pobierania**: ponów, anuluj, zatrzymaj wszystko, zmień kolejność w kolejce, usuń plik, pokaż w folderze.

## Jak to działa

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

- **Powiązanie z cyklem życia**: wszystko działa wewnątrz ComfyUI. Zatrzymaj ComfyUI → trasy znikają, a każdy uruchomiony `aria2c` sam się kończy (`--stop-with-process=<server pid>`). Frontend wstrzymuje też odpytywanie, gdy strona jest ukryta, i sprząta przy jej zamknięciu.
- **Pobieranie tylko ręczne**: przełączanie szablonów jedynie odświeża licznik brakujących modeli. Nic nie jest pobierane, dopóki nie klikniesz przycisku (albo nie klikniesz go ponownie podczas pobierania, aby dodać do kolejki brakujące modele nowego szablonu).

## Funkcje

| Funkcja | Opis |
|---|---|
| Automatyczne wykrywanie | Otwórz szablon → pływający przycisk pokazuje, ilu modeli brakuje. Przełącz szablon → licznik zaktualizuje się automatycznie. |
| Szybkie pobieranie | aria2c, 16 połączeń na plik, 3 pliki równolegle, automatyczne lustro `hf-mirror.com` dla adresów Hugging Face. |
| Zarządzanie kolejką | Dodawaj kolejne modele w trakcie pobierania, przesuwaj elementy w górę/w dół, anuluj pojedyncze elementy, zatrzymaj wszystko. |
| Weryfikacja integralności | Przy każdym sprawdzeniu: brak pliku, pozostały `.aria2` (niekompletny → automatyczne wznowienie), niezgodność rozmiaru, niezgodność SHA256 (względem rekordów LFS HF). Po każdym pobraniu: ponowna weryfikacja SHA256. Zweryfikowane pliki są cache'owane na sesję (mtime+rozmiar), więc duże pliki nie są ponownie haszowane przy każdym przełączeniu szablonu. |
| Akcje na plikach | Ponów, anuluj, zmień kolejność ⏫/⏬, usuń plik z dysku (z potwierdzeniem), pokaż w Eksploratorze Windows. |
| Wznawianie | Przerwane pobierania zachowują plik kontrolny `.aria2`; ponowne kliknięcie pobierania wznawia zamiast zaczynać od nowa. |

## Wymagania

- **ComfyUI** (dowolna nowsza wersja z obsługą niestandardowych węzłów; testowane na ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** w `PATH` środowiska, które uruchamia ComfyUI
- pakiet Pythona `requests` (jest już obecny w standardowych instalacjach ComfyUI)
- Obsługa Windows / Linux (przycisk „pokaż w folderze" działa tylko w Windows; w Linuxie wtyczka radzi sobie bez niego)

### Instalacja aria2

- **Windows**: pobierz ZIP z <https://github.com/aria2/aria2/releases> (np. `aria2-1.37.0-win-64bit-build1.zip`), rozpakuj i dodaj folder zawierający `aria2c.exe` do swojego użytkownika `PATH`.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Weryfikacja: otwórz terminal i uruchom `aria2c --version`.

## Instalacja

### Metoda 1 — ComfyUI Manager

1. Otwórz ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Wyszukaj `ComfyUI-Model-Downloader` i zainstaluj.
3. Uruchom ponownie ComfyUI.

### Metoda 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Aplikacja desktopowa (Comfy Desktop)**: folder `custom_nodes` znajduje się wewnątrz instalacji, np. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (ścieżka zależy od układu). W razie wątpliwości sprawdź w logu serwera sekcję "Import times for custom nodes", aby zobaczyć, który katalog jest faktycznie skanowany.

## Użycie

1. **Uruchom ponownie ComfyUI** po instalacji (wtyczka nie ma interfejsu, dopóki serwer jej nie przeładuje).
2. Otwórz dowolny **szablon** (lub dowolny workflow, którego węzły zawierają metadane `properties.models` — oficjalne szablony je zawierają).
3. Poczekaj ~2 sekundy. W **prawym dolnym** rogu pojawi się pływający przycisk:
   - `⬇ Download missing models (N)` — brakuje/uszkodzonych jest N modeli. **Kliknij go**, aby rozpocząć pobieranie.
4. **Panel menedżera pobierania** otworzy się automatycznie i pokaże każdy plik: ikonę statusu, pasek postępu, procent, prędkość na żywo, folder docelowy, komunikaty błędów.
5. Podczas pobierania możesz:
   - Przełączać szablony → przycisk pokaże `Downloading x/y · Pending N (click to enqueue)`. **Nic nie pobiera się automatycznie**; kliknij przycisk, aby dodać brakujące modele nowego szablonu do kolejki.
   - W panelu: zmiana kolejności elementów ⏫/⏬, **Anuluj** pojedynczy element, **Zatrzymaj wszystko**, **Ponów** nieudane elementy, **Usuń plik**, **Pokaż w folderze**.
6. Gdy wszystko się zakończy, panel zachowa końcowe wyniki (✅/⚠️), dopóki nie zamkniesz go ✕.

### Co pokazuje przycisk

| Sytuacja | Tekst przycisku | Akcja kliknięcia |
|---|---|---|
| Brak aktywnego pobierania, brakuje modeli | `⬇ Download missing models (N)` | Rozpocznij pobieranie |
| Pobieranie trwa, brak nowych braków | `Downloading x/y · file 45%` | Otwórz panel |
| Pobieranie trwa, nowy szablon ma brakujące modele | `Downloading x/y · Pending N (click to enqueue)` | Dodaj je do kolejki |
| Wszystko zakończone, część nieudana | `⚠ x ok / y failed (click to retry)` | Ponów nieudane |
| Niczego nie brakuje | (ukryty) | — |

## Logika pobierania i integralność

Dla każdego modelu wtyczka sprawdza (po kolei):

1. Plik nie istnieje lub ≤ 1 MB → **brakuje** → pobierz.
2. Istnieje `<file>.aria2` → **niekompletny** → aria2c go wznawia.
3. Rozmiar ≠ rekord LFS Hugging Face → **uszkodzony** → usuń i pobierz ponownie.
4. SHA256 ≠ rekord LFS Hugging Face → **uszkodzony** → usuń i pobierz ponownie (weryfikowane tylko raz na sesję dla danego pliku, chyba że plik się zmieni).
5. Po każdym zakończonym pobraniu SHA256 jest ponownie sprawdzany; niezgodność oznacza element jako nieudany.

Oczekiwane rozmiary/hasze pochodzą z `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` i są cache'owane per URL. Adresy spoza Hugging Face (np. Civitai) są sprawdzane tylko pod kątem istnienia + `.aria2` + rozmiaru.

## Konfiguracja

Wszystkie parametry do dostrojenia to stałe na początku pliku `__init__.py`:

| Stała | Domyślnie | Znaczenie |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Równoległe pliki |
| flagi aria2 | `-x16 -s16 -k1M` | 16 połączeń na plik, fragmenty 1 MB |
| `HF_MIRROR` | `https://hf-mirror.com` | Lustro używane dla adresów `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | Pliki mniejsze niż ta wartość liczą się jako brakujące |
| `ARIA2_FALLBACKS` | ścieżki lokalne | Absolutne lokalizacje aria2c próbowane, gdy nie ma go w PATH |

## Rozwiązywanie problemów

| Objaw | Rozwiązanie |
|---|---|
| W ogóle brak pływającego przycisku | Uruchom całkowicie ponownie ComfyUI (na desktopie: zasobnik → zamknij). Sprawdź w logu serwera wpis `Import times for custom nodes: … ComfyUI-Model-Downloader`. Na stronie odśwież na twardo (Ctrl+R). Kontrola stanu: otwórz `http://127.0.0.1:8188/comfy_fetch/ping` → powinno zwrócić `{"ok": true}`. |
| Przycisk nic nie pokazuje po otwarciu szablonu | Węzły workflow muszą zawierać metadane `properties.models` (oficjalne szablony je zawierają). Dla ręcznie robionych workflow bez metadanych wtyczka nie ma czego sprawdzać — dodaj modele ręcznie. |
| Pobieranie natychmiast się nie udaje | Nie znaleziono `aria2c` → zainstaluj aria2 i upewnij się, że jest w PATH, z którym startuje ComfyUI (wymagany restart). |
| Bardzo wolno | Twoja sieć też nie może dotrzeć do `hf-mirror.com`; spróbuj proxy. |
| Licznik wygląda na nieaktualny po przełączeniu szablonu | Poczekaj ~2 s na cykl odpytywania; jeśli się utrzymuje — twarde odświeżenie (Ctrl+R). |
| Akcja w panelu nic nie robi | Plik mógł już zostać usunięty albo nie ma go w kolejce (przy zmianie kolejności); sprawdź ikony statusu w panelu. |

## Dokumentacja API (dla programistów)

Wszystkie endpointy obsługuje sam serwer ComfyUI (bez dodatkowego portu):

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

`reason` przy brakujących elementach: `missing` | `incomplete` (automatyczne wznowienie) | `size` | `hash`.

## Licencja

MIT © 2026 Bosconovitchi
