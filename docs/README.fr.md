# ComfyUI-Model-Downloader

**Téléchargement en un clic et à pleine vitesse des modèles manquants pour les templates et workflows ComfyUI — avec gestion de file d'attente, actions par fichier et vérification d'intégrité.**

Un pur plugin ComfyUI. Pas de serveur autonome, pas de démon supplémentaire : le backend vit à l'intérieur du processus serveur ComfyUI et l'interface vit à l'intérieur de la page ComfyUI. Fermez ComfyUI et tout s'arrête (téléchargements compris, via `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | **Français** | **Deutsch** | [Русский](docs/README.ru.md) | **Español** | [Português](docs/README.pt-BR.md) | **Italiano** | [한국어](docs/README.ko.md) | [العربية](docs/README.ar.md) | [हिन्दी](docs/README.hi.md) | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | [Bahasa Indonesia](docs/README.id.md)

## Pourquoi ce plugin existe

Le téléchargeur de templates intégré de ComfyUI télécharge les modèles **en monothread** et, dans certaines régions, `huggingface.co` est inaccessible ou fortement bridé, si bien que le bouton « Download » intégré échoue ou avance au ralenti. Ce plugin :

- Détecte **quels modèles sont manquants** pour le template/workflow actuellement ouvert (les mêmes métadonnées que celles utilisées par le panneau intégré des modèles manquants).
- Les télécharge avec **aria2c, 16 connexions par fichier, 3 fichiers en parallèle**, via **hf-mirror.com** automatiquement (un miroir rapide de Hugging Face) — saturant généralement votre bande passante.
- Reprend les téléchargements interrompus, **vérifie l'intégrité des fichiers** (taille + SHA256 par rapport aux enregistrements LFS officiels de Hugging Face) et vous offre un **panneau complet de gestionnaire de téléchargements** : réessayer, annuler, tout arrêter, réordonner la file, supprimer le fichier, afficher dans le dossier.

## Comment ça marche

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

- **Cycle de vie lié** : tout s'exécute à l'intérieur de ComfyUI. Arrêtez ComfyUI → les routes disparaissent et chaque `aria2c` en cours se termine de lui-même (`--stop-with-process=<server pid>`). Le frontend met également en pause le polling lorsque la page est masquée et nettoie au déchargement.
- **Téléchargements uniquement manuels** : changer de template ne fait que rafraîchir le nombre de modèles manquants. Rien ne se télécharge tant que vous ne cliquez pas sur le bouton (ou que vous ne cliquez pas à nouveau pendant qu'un téléchargement est en cours, pour mettre en file les modèles manquants du nouveau template).

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| Détection automatique | Ouvrez un template → le bouton flottant affiche combien de modèles sont manquants. Changez de template → le compteur se met à jour automatiquement. |
| Téléchargements rapides | aria2c, 16 connexions/fichier, 3 fichiers en parallèle, miroir automatique `hf-mirror.com` pour les URL Hugging Face. |
| Gestion de file d'attente | Mettez d'autres modèles en file pendant un téléchargement, déplacez les éléments vers le haut/bas, annulez des éléments individuels, arrêtez tout. |
| Vérification d'intégrité | À chaque contrôle : fichier manquant, `.aria2` résiduel (incomplet → reprise automatique), taille incohérente, SHA256 incohérent (vs enregistrements HF LFS). Après chaque téléchargement : re-vérification du SHA256. Les fichiers vérifiés sont mis en cache par session (mtime+taille) afin que les gros fichiers ne soient pas re-hachés à chaque changement de template. |
| Actions par fichier | Réessayer, annuler, réordonner ⏫/⏬, supprimer le fichier du disque (avec confirmation), afficher dans l'Explorateur Windows. |
| Reprise | Les téléchargements interrompus conservent leur fichier de contrôle `.aria2` ; cliquer à nouveau sur télécharger reprend au lieu de redémarrer. |

## Prérequis

- **ComfyUI** (toute version récente avec prise en charge des nœuds personnalisés ; testé sur ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** dans le `PATH` de l'environnement qui démarre ComfyUI
- Le paquet Python `requests` (déjà présent dans les installations ComfyUI standard)
- Windows / Linux pris en charge (le bouton « afficher dans le dossier » est réservé à Windows ; Linux se replie proprement)

### Installer aria2

- **Windows** : téléchargez le ZIP depuis <https://github.com/aria2/aria2/releases> (par ex. `aria2-1.37.0-win-64bit-build1.zip`), extrayez-le, puis ajoutez le dossier contenant `aria2c.exe` à votre `PATH` utilisateur.
- **Linux** : `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Vérification : ouvrez un terminal et lancez `aria2c --version`.

## Installation

### Méthode 1 — ComfyUI Manager

1. Ouvrez ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Recherchez `ComfyUI-Model-Downloader` et installez-le.
3. Redémarrez ComfyUI.

### Méthode 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **Application de bureau (Comfy Desktop)** : le dossier `custom_nodes` se trouve à l'intérieur de l'installation, par ex. `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (le chemin varie selon l'agencement). En cas de doute, consultez la section « Import times for custom nodes » du journal du serveur pour voir quel répertoire est réellement analysé.

## Utilisation

1. **Redémarrez ComfyUI** après l'installation (le plugin n'a pas d'interface si le serveur ne l'a pas rechargé).
2. Ouvrez n'importe quel **template** (ou n'importe quel workflow dont les nœuds embarquent les métadonnées `properties.models` — les templates officiels le font).
3. Attendez ~2 secondes. Un bouton flottant apparaît en **bas à droite** :
   - `⬇ Download missing models (N)` — N modèles sont manquants/endommagés. **Cliquez dessus** pour lancer le téléchargement.
4. Le **panneau du gestionnaire de téléchargements** s'ouvre automatiquement et affiche chaque fichier : icône d'état, barre de progression, pourcentage, vitesse en direct, dossier cible, messages d'erreur.
5. Pendant le téléchargement, vous pouvez :
   - Changer de template → le bouton affiche `Downloading x/y · Pending N (click to enqueue)`. **Rien ne se télécharge automatiquement** ; cliquez sur le bouton pour ajouter à la file les modèles manquants du nouveau template.
   - Dans le panneau : réordonner les éléments en file ⏫/⏬, **Annuler** un élément individuel, **Tout arrêter**, **Réessayer** les éléments en échec, **Supprimer le fichier**, **Afficher dans le dossier**.
6. Lorsque tout est terminé, le panneau conserve les résultats finaux (✅/⚠️) jusqu'à ce que vous le fermiez avec ✕.

### Ce que le bouton affiche

| Situation | Texte du bouton | Action au clic |
|---|---|---|
| Aucun téléchargement en cours, modèles manquants | `⬇ Download missing models (N)` | Lancer le téléchargement |
| Téléchargement en cours, rien de nouveau ne manque | `Downloading x/y · file 45%` | Ouvrir le panneau |
| Téléchargement en cours, modèles manquants d'un nouveau template | `Downloading x/y · Pending N (click to enqueue)` | Les mettre en file |
| Tout est terminé, certains ont échoué | `⚠ x ok / y failed (click to retry)` | Réessayer les échecs |
| Rien ne manque | (masqué) | — |

## Logique de téléchargement et intégrité

Pour chaque modèle, le plugin vérifie (dans l'ordre) :

1. Fichier absent ou ≤ 1 Mo → **manquant** → téléchargement.
2. `<file>.aria2` existe → **incomplet** → aria2c le reprend.
3. Taille ≠ enregistrement HF LFS → **corrompu** → suppression et re-téléchargement.
4. SHA256 ≠ enregistrement HF LFS → **corrompu** → suppression et re-téléchargement (vérifié une seule fois par session et par fichier, sauf si le fichier change).
5. Après chaque téléchargement terminé, le SHA256 est re-contrôlé ; une incohérence marque l'élément comme en échec.

Les tailles/hachages attendus proviennent de `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` et sont mis en cache par URL. Les URL non-Hugging-Face (par ex. Civitai) se replient sur des contrôles d'existence + `.aria2` + taille uniquement.

## Dépôts restreints (modèles soumis à licence)

Certains modèles (par ex. LTX-2.5, Gemma) sont **restreints** (gated) sur Hugging Face — vous devez accepter la licence / demander l'accès avant de pouvoir les télécharger. Le plugin détecte ce cas et échoue avec un message clair au lieu d'une erreur cryptique.

1. Ouvrez la page du modèle sur huggingface.co (par ex. https://huggingface.co/Lightricks/LTX-2.5), connectez-vous, puis acceptez les conditions / demandez l'accès.
2. Créez un jeton d'accès en lecture seule : https://huggingface.co/settings/tokens → New token → type **Read**.
3. Définissez-le comme variable d'environnement pour ComfyUI et redémarrez :
   - Windows (PowerShell) : `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS : `export HF_TOKEN=hf_xxxxxxxx` (à ajouter à votre script de démarrage ComfyUI)
4. Redémarrez ComfyUI et réessayez — les téléchargements incluent alors `Authorization: Bearer <token>`, et les métadonnées d'intégrité (taille/SHA256) sont aussi récupérées avec le jeton.

## Configuration

Tous les paramètres réglables sont des constantes en haut de `__init__.py` :

| Constante | Défaut | Signification |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Fichiers en parallèle |
| Options aria2 | `-x16 -s16 -k1M` | 16 connexions/fichier, morceaux de 1 Mo |
| `HF_MIRROR` | `https://hf-mirror.com` | Miroir utilisé pour les URL `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | Les fichiers plus petits que ceci comptent comme manquants |
| `ARIA2_FALLBACKS` | chemins locaux | Emplacements absolus d'aria2c essayés s'il n'est pas dans le PATH |

## Dépannage

| Symptôme | Correctif |
|---|---|
| Aucun bouton flottant du tout | Redémarrez complètement ComfyUI (barre d'état système → quitter sur le bureau). Vérifiez dans le journal du serveur la présence de `Import times for custom nodes: … ComfyUI-Model-Downloader`. Dans la page, faites un rechargement forcé (Ctrl+R). Contrôle de santé : ouvrez `http://127.0.0.1:8188/comfy_fetch/ping` → devrait renvoyer `{"ok": true}`. |
| Le bouton n'affiche rien après l'ouverture d'un template | Les nœuds du workflow doivent embarquer les métadonnées `properties.models` (les templates officiels le font). Pour les workflows faits main sans métadonnées, le plugin n'a rien à vérifier — ajoutez les modèles manuellement. |
| Le téléchargement échoue immédiatement | `aria2c` introuvable → installez aria2 et assurez-vous qu'il est dans le PATH avec lequel ComfyUI démarre (redémarrage requis). |
| Très lent | Votre réseau n'atteint pas non plus `hf-mirror.com` ; essayez un proxy. |
| Le compteur semble obsolète après un changement de template | Attendez ~2 s le cycle de polling ; faites un rechargement forcé (Ctrl+R) si cela persiste. |
| Une action du panneau ne fait rien | Le fichier a peut-être déjà disparu (suppression) ou n'est pas dans la file (réordonnancement) ; vérifiez les icônes d'état du panneau. |

## Référence API (pour les développeurs)

Tous les endpoints sont servis par le serveur ComfyUI lui-même (pas de port supplémentaire) :

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

`reason` sur les éléments manquants : `missing` | `incomplete` (reprise automatique) | `size` | `hash`.

## Licence

MIT © 2026 Bosconovitchi
