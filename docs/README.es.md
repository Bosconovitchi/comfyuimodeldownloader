# ComfyUI-Model-Downloader

**Descarga en un clic y a plena velocidad de los modelos que faltan para plantillas y flujos de trabajo de ComfyUI — con gestión de cola, acciones por archivo y verificación de integridad.**

Un plugin puro de ComfyUI. Sin servidor independiente ni demonios adicionales: el backend vive dentro del proceso del servidor de ComfyUI y la interfaz dentro de la página de ComfyUI. Cierra ComfyUI y todo se detiene (descargas incluidas, mediante `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | **Français** | **Deutsch** | [Русский](docs/README.ru.md) | **Español** | [Português](docs/README.pt-BR.md) | **Italiano** | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Por qué existe este plugin

El descargador de plantillas integrado de ComfyUI descarga modelos **en un solo hilo** y, en algunas regiones, `huggingface.co` es inaccesible o está muy limitado, por lo que el botón «Download» integrado falla o avanza a paso de tortuga. Este plugin:

- Detecta **qué modelos faltan** para la plantilla/flujo de trabajo abierto actualmente (los mismos metadatos que usa el panel integrado de modelos faltantes).
- Los descarga con **aria2c, 16 conexiones por archivo, 3 archivos en paralelo**, a través de **hf-mirror.com** automáticamente (un espejo rápido de Hugging Face) — saturando normalmente tu ancho de banda.
- Reanuda descargas interrumpidas, **verifica la integridad de los archivos** (tamaño + SHA256 contra los registros LFS oficiales de Hugging Face) y te ofrece un **panel completo de gestor de descargas**: reintentar, cancelar, detener todo, reordenar la cola, eliminar el archivo, mostrar en la carpeta.

## Cómo funciona

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

- **Vinculación al ciclo de vida**: todo se ejecuta dentro de ComfyUI. Detén ComfyUI → las rutas desaparecen y cada `aria2c` en ejecución se termina a sí mismo (`--stop-with-process=<server pid>`). El frontend también pausa el sondeo mientras la página está oculta y limpia al descargarla.
- **Descargas solo manuales**: cambiar de plantilla solo actualiza el recuento de modelos faltantes. Nada se descarga hasta que haces clic en el botón (o vuelves a hacer clic durante una descarga en curso, para encolar los modelos faltantes de la nueva plantilla).

## Funciones

| Función | Descripción |
|---|---|
| Detección automática | Abre una plantilla → el botón flotante muestra cuántos modelos faltan. Cambia de plantilla → el recuento se actualiza automáticamente. |
| Descargas rápidas | aria2c, 16 conexiones/archivo, 3 archivos en paralelo, espejo automático `hf-mirror.com` para las URL de Hugging Face. |
| Gestión de cola | Encola más modelos durante la descarga, mueve elementos arriba/abajo, cancela elementos individuales, detén todo. |
| Verificación de integridad | En cada comprobación: archivo faltante, `.aria2` residual (incompleto → reanudación automática), tamaño incorrecto, SHA256 incorrecto (frente a registros HF LFS). Después de cada descarga: re-verificación SHA256. Los archivos verificados se almacenan en caché por sesión (mtime+tamaño) para no volver a calcular el hash de archivos grandes en cada cambio de plantilla. |
| Acciones por archivo | Reintentar, cancelar, reordenar ⏫/⏬, eliminar el archivo del disco (con confirmación), mostrar en el Explorador de Windows. |
| Reanudación | Las descargas interrumpidas conservan su archivo de control `.aria2`; hacer clic de nuevo en descargar reanuda en lugar de reiniciar. |

## Requisitos

- **ComfyUI** (cualquier versión reciente con soporte de nodos personalizados; probado en ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** en el `PATH` del entorno que inicia ComfyUI
- Paquete Python `requests` (ya presente en las instalaciones estándar de ComfyUI)
- Windows / Linux compatibles (el botón «mostrar en la carpeta» es solo para Windows; Linux se degrada con elegancia)

### Instalar aria2

- **Windows**: descarga el ZIP desde <https://github.com/aria2/aria2/releases> (p. ej. `aria2-1.37.0-win-64bit-build1.zip`), extráelo y añade la carpeta que contiene `aria2c.exe` a tu `PATH` de usuario.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Verifica: abre un terminal y ejecuta `aria2c --version`.

## Instalación

### Método 1 — ComfyUI Manager

1. Abre ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Busca `ComfyUI-Model-Downloader` e instálalo.
3. Reinicia ComfyUI.

### Método 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Aplicación de escritorio (Comfy Desktop)**: la carpeta `custom_nodes` está dentro de la instalación, p. ej. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (la ruta varía según la distribución). En caso de duda, consulta la sección «Import times for custom nodes» del registro del servidor para ver qué directorio se analiza realmente.

## Uso

1. **Reinicia ComfyUI** tras la instalación (el plugin no tiene interfaz si el servidor no lo ha recargado).
2. Abre cualquier **plantilla** (o cualquier flujo de trabajo cuyos nodos incrusten metadatos `properties.models` — las plantillas oficiales lo hacen).
3. Espera ~2 segundos. Aparece un botón flotante **abajo a la derecha**:
   - `⬇ Download missing models (N)` — faltan/están dañados N modelos. **Haz clic** para empezar a descargar.
4. El **panel del gestor de descargas** se abre automáticamente y muestra cada archivo: icono de estado, barra de progreso, porcentaje, velocidad en vivo, carpeta de destino, mensajes de error.
5. Mientras descargas puedes:
   - Cambiar de plantilla → el botón muestra `Downloading x/y · Pending N (click to enqueue)`. **Nada se descarga automáticamente**; haz clic en el botón para añadir a la cola los modelos faltantes de la nueva plantilla.
   - En el panel: reordenar los elementos en cola ⏫/⏬, **Cancelar** un elemento individual, **Detener todo**, **Reintentar** los elementos fallidos, **Eliminar archivo**, **Mostrar en la carpeta**.
6. Cuando todo termina, el panel conserva los resultados finales (✅/⚠️) hasta que lo cierras con ✕.

### Qué muestra el botón

| Situación | Texto del botón | Acción al hacer clic |
|---|---|---|
| Sin descarga en curso, faltan modelos | `⬇ Download missing models (N)` | Empezar a descargar |
| Descarga en curso, no falta nada nuevo | `Downloading x/y · file 45%` | Abrir el panel |
| Descarga en curso, faltan modelos de una plantilla nueva | `Downloading x/y · Pending N (click to enqueue)` | Encolarlos |
| Todo terminado, algunos fallaron | `⚠ x ok / y failed (click to retry)` | Reintentar los fallos |
| No falta nada | (oculto) | — |

## Lógica de descarga e integridad

Para cada modelo, el plugin comprueba (en orden):

1. Archivo ausente o ≤ 1 MB → **falta** → descargar.
2. Existe `<file>.aria2` → **incompleto** → aria2c lo reanuda.
3. Tamaño ≠ registro HF LFS → **dañado** → eliminar y volver a descargar.
4. SHA256 ≠ registro HF LFS → **dañado** → eliminar y volver a descargar (solo se verifica una vez por sesión y archivo, salvo que el archivo cambie).
5. Después de cada descarga completada se vuelve a comprobar el SHA256; una discrepancia marca el elemento como fallido.

Los tamaños/hashes esperados proceden de `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` y se almacenan en caché por URL. Las URL que no son de Hugging Face (p. ej. Civitai) se limitan a comprobaciones de existencia + `.aria2` + tamaño.

## Configuración

Todos los ajustes son constantes al principio de `__init__.py`:

| Constante | Predeterminado | Significado |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Archivos en paralelo |
| Opciones de aria2 | `-x16 -s16 -k1M` | 16 conexiones/archivo, fragmentos de 1 MB |
| `HF_MIRROR` | `https://hf-mirror.com` | Espejo usado para las URL de `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | Los archivos más pequeños que esto cuentan como faltantes |
| `ARIA2_FALLBACKS` | rutas locales | Ubicaciones absolutas de aria2c que se prueban si no está en el PATH |

## Solución de problemas

| Síntoma | Solución |
|---|---|
| No aparece ningún botón flotante | Reinicia ComfyUI por completo (bandeja → salir en el escritorio). Comprueba en el registro del servidor que aparezca `Import times for custom nodes: … ComfyUI-Model-Downloader`. En la página, haz un refresco forzado (Ctrl+R). Comprobación de estado: abre `http://127.0.0.1:8188/comfy_fetch/ping` → debería devolver `{"ok": true}`. |
| El botón no muestra nada tras abrir una plantilla | Los nodos del flujo de trabajo deben incrustar metadatos `properties.models` (las plantillas oficiales lo hacen). Para flujos de trabajo hechos a mano sin metadatos, el plugin no tiene nada que comprobar — añade los modelos manualmente. |
| La descarga falla de inmediato | No se encuentra `aria2c` → instala aria2 y asegúrate de que esté en el PATH con el que se inicia ComfyUI (requiere reinicio). |
| Muy lento | Tu red tampoco alcanza `hf-mirror.com`; prueba un proxy. |
| El recuento parece obsoleto tras cambiar de plantilla | Espera ~2 s al ciclo de sondeo; haz un refresco forzado (Ctrl+R) si persiste. |
| Una acción del panel no hace nada | Es posible que el archivo ya no exista (eliminación) o no esté en la cola (reordenación); comprueba los iconos de estado del panel. |

## Referencia de la API (para desarrolladores)

Todos los endpoints los sirve el propio servidor de ComfyUI (sin puerto adicional):

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

`reason` en los elementos faltantes: `missing` | `incomplete` (reanudación automática) | `size` | `hash`.

## Licencia

MIT © 2026 Bosconovitchi
