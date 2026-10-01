# ComfyUI-Model-Downloader

**Download com um clique e em velocidade máxima dos modelos ausentes para templates e workflows do ComfyUI — com gerenciamento de fila, ações por arquivo e verificação de integridade.**

Um plugin puro do ComfyUI. Sem servidor autônomo, sem daemons extras: o backend roda dentro do processo do servidor ComfyUI e a interface vive dentro da página do ComfyUI. Feche o ComfyUI e tudo para (downloads incluídos, via `aria2c --stop-with-process`).

> English | [简体中文](README.zh-CN.md) | [日本語](docs/README.ja.md) | [Français](docs/README.fr.md) | [Deutsch](docs/README.de.md) | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | **Português** | [Italiano](docs/README.it.md) | [한국어](docs/README.ko.md) | **العربية** | **हिन्दी** | [Türkçe](docs/README.tr.md) | [Nederlands](docs/README.nl.md) | [Polski](docs/README.pl.md) | [Tiếng Việt](docs/README.vi.md) | [ไทย](docs/README.th.md) | **Bahasa Indonesia**

## Por que este plugin existe

O downloader de templates embutido do ComfyUI baixa modelos em **thread única**, e em algumas regiões o `huggingface.co` fica inacessível ou severamente limitado, então o botão embutido "Download" falha ou se arrasta. Este plugin:

- Detecta **quais modelos estão ausentes** para o template/workflow aberto no momento (os mesmos metadados usados pelo painel de modelos ausentes embutido).
- Baixa-os com **aria2c, 16 conexões por arquivo, 3 arquivos em paralelo**, via **hf-mirror.com** automaticamente (um espelho rápido do Hugging Face) — normalmente saturando sua banda.
- Retoma downloads interrompidos, **verifica a integridade dos arquivos** (tamanho + SHA256 contra os registros LFS oficiais do Hugging Face) e oferece um **painel gerenciador de downloads** completo: tentar novamente, cancelar, parar tudo, reordenar fila, excluir o arquivo, revelar na pasta.

## Como funciona

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

- **Vínculo com o ciclo de vida**: tudo roda dentro do ComfyUI. Pare o ComfyUI → as rotas desaparecem e todo `aria2c` em execução se encerra sozinho (`--stop-with-process=<pid do servidor>`). O frontend também pausa a sondagem enquanto a página está oculta e faz a limpeza ao descarregar.
- **Downloads apenas manuais**: trocar de template apenas atualiza a contagem de modelos ausentes. Nada é baixado até você clicar no botão (ou clicar de novo no botão durante um download, para enfileirar os modelos ausentes do novo template).

## Recursos

| Recurso | Descrição |
|---|---|
| Detecção automática | Abra um template → o botão flutuante mostra quantos modelos estão ausentes. Troque de template → a contagem é atualizada automaticamente. |
| Downloads rápidos | aria2c, 16 conexões/arquivo, 3 arquivos em paralelo, espelho `hf-mirror.com` automático para URLs do Hugging Face. |
| Gerenciamento de fila | Enfileire mais modelos durante o download, mova itens para cima/baixo, cancele itens individuais, pare tudo. |
| Verificação de integridade | A cada verificação: arquivo ausente, `.aria2` remanescente (incompleto → retomada automática), tamanho divergente, SHA256 divergente (vs registros LFS do HF). Após cada download: reverificação do SHA256. Arquivos verificados são armazenados em cache por sessão (mtime+tamanho) para que arquivos grandes não sejam re-hasheados a cada troca de template. |
| Ações por arquivo | Tentar novamente, cancelar, reordenar ⏫/⏬, excluir o arquivo do disco (com confirmação), revelar no Windows Explorer. |
| Retomada | Downloads interrompidos mantêm seu arquivo de controle `.aria2`; clicar em baixar novamente retoma em vez de reiniciar. |

## Requisitos

- **ComfyUI** (qualquer versão recente com suporte a custom nodes; testado no ComfyUI 0.3.x + Comfy Desktop 1.x)
- **aria2c** no `PATH` do ambiente que inicia o ComfyUI
- Pacote Python `requests` (já presente em instalações padrão do ComfyUI)
- Windows / Linux suportados (o botão "revelar na pasta" é exclusivo do Windows; no Linux há um fallback suave)

### Instalando o aria2

- **Windows**: baixe o ZIP em <https://github.com/aria2/aria2/releases> (ex.: `aria2-1.37.0-win-64bit-build1.zip`), extraia e adicione a pasta que contém o `aria2c.exe` ao seu `PATH` de usuário.
- **Linux**: `sudo apt install aria2` / `sudo dnf install aria2` / `brew install aria2` (macOS).
- Verifique: abra um terminal e execute `aria2c --version`.

## Instalação

### Método 1 — ComfyUI Manager

1. Abra o ComfyUI → **Manager** → **Custom Nodes Manager**.
2. Pesquise por `ComfyUI-Model-Downloader` e instale.
3. Reinicie o ComfyUI.

### Método 2 — git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Bosconovitchi/comfyuimodeldownloader.git ComfyUI-Model-Downloader
# restart ComfyUI
```

> **App desktop (Comfy Desktop)**: a pasta `custom_nodes` fica dentro da instalação, ex.: `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Installs\<instance>\ComfyUI\custom_nodes` (o caminho varia conforme o layout). Na dúvida, consulte a seção "Import times for custom nodes" do log do servidor para ver qual diretório é realmente escaneado.

## Uso

1. **Reinicie o ComfyUI** após a instalação (o plugin fica sem interface se o servidor não o recarregar).
2. Abra qualquer **template** (ou qualquer workflow cujos nós incorporem metadados `properties.models` — os templates oficiais fazem isso).
3. Aguarde ~2 segundos. Um botão flutuante aparece no **canto inferior direito**:
   - `⬇ Download missing models (N)` — N modelos estão ausentes/quebrados. **Clique nele** para iniciar o download.
4. O **painel gerenciador de downloads** abre automaticamente, mostrando cada arquivo: ícone de status, barra de progresso, porcentagem, velocidade em tempo real, pasta de destino, mensagens de erro.
5. Durante o download você pode:
   - Trocar de template → o botão mostra `Downloading x/y · Pending N (click to enqueue)`. **Nada baixa automaticamente**; clique no botão para adicionar os modelos ausentes do novo template à fila.
   - No painel: reordenar itens enfileirados ⏫/⏬, **Cancelar** um item, **Parar tudo**, **Tentar novamente** itens com falha, **Excluir arquivo**, **Revelar na pasta**.
6. Quando tudo termina, o painel mantém os resultados finais (✅/⚠️) até você fechá-lo com ✕.

### O que o botão mostra

| Situação | Texto do botão | Ação do clique |
|---|---|---|
| Nenhum download em andamento, modelos ausentes | `⬇ Download missing models (N)` | Iniciar download |
| Download em andamento, nada novo ausente | `Downloading x/y · file 45%` | Abrir o painel |
| Download em andamento, modelos do novo template ausentes | `Downloading x/y · Pending N (click to enqueue)` | Enfileirá-los |
| Tudo concluído, alguns falharam | `⚠ x ok / y failed (click to retry)` | Tentar novamente as falhas |
| Nada ausente | (oculto) | — |

## Lógica de download e integridade

Para cada modelo, o plugin verifica (em ordem):

1. Arquivo ausente ou ≤ 1 MB → **ausente** → baixar.
2. `<file>.aria2` existe → **incompleto** → o aria2c o retoma.
3. Tamanho ≠ registro LFS do Hugging Face → **corrompido** → excluir e baixar novamente.
4. SHA256 ≠ registro LFS do Hugging Face → **corrompido** → excluir e baixar novamente (verificado apenas uma vez por sessão por arquivo, a menos que o arquivo mude).
5. Após cada download concluído, o SHA256 é reverificado; uma divergência marca o item como falho.

Os tamanhos/hashes esperados vêm de `https://hf-mirror.com/api/models/{owner}/{repo}/tree/{rev}?recursive=true` e são armazenados em cache por URL. URLs fora do Hugging Face (ex.: Civitai) recorrem apenas às verificações de existência + `.aria2` + tamanho.

## Repositórios fechados (modelos que exigem licença)

Alguns modelos (ex.: LTX-2.5, Gemma) são **fechados** (gated) no Hugging Face — você precisa aceitar a licença / solicitar acesso antes de baixar. O plugin detecta isso e falha com uma mensagem clara em vez de um erro enigmático.

1. Abra a página do modelo em huggingface.co (ex.: https://huggingface.co/Lightricks/LTX-2.5), entre na sua conta e aceite os termos / solicite acesso.
2. Crie um token de acesso somente leitura: https://huggingface.co/settings/tokens → New token → tipo **Read**.
3. Defina-o como variável de ambiente do ComfyUI e reinicie:
   - Windows (PowerShell): `setx HF_TOKEN hf_xxxxxxxx`
   - Linux/macOS: `export HF_TOKEN=hf_xxxxxxxx` (adicione ao script de inicialização do ComfyUI)
4. Reinicie o ComfyUI e tente novamente — os downloads passam a incluir `Authorization: Bearer <token>`, e os metadados de integridade (tamanho/SHA256) também são buscados com o token.

## Configuração

Todos os ajustes são constantes no topo de `__init__.py`:

| Constante | Padrão | Significado |
|---|---|---|
| `MAX_CONCURRENT` | `3` | Arquivos em paralelo |
| flags do aria2 | `-x16 -s16 -k1M` | 16 conexões/arquivo, blocos de 1 MB |
| `HF_MIRROR` | `https://hf-mirror.com` | Espelho usado para URLs `huggingface.co` |
| `MIN_FILE_SIZE` | `1_000_000` | Arquivos menores que isso contam como ausentes |
| `ARIA2_FALLBACKS` | caminhos locais | Locais absolutos do aria2c tentados se não estiver no PATH |

## Solução de problemas

| Sintoma | Correção |
|---|---|
| Nenhum botão flutuante aparece | Reinicie o ComfyUI por completo (bandeja → sair no desktop). Verifique no log do servidor por `Import times for custom nodes: … ComfyUI-Model-Downloader`. Na página, faça uma atualização forçada (Ctrl+R). Verificação de saúde: abra `http://127.0.0.1:8188/comfy_fetch/ping` → deve retornar `{"ok": true}`. |
| O botão não mostra nada após abrir um template | Os nós do workflow devem incorporar metadados `properties.models` (os templates oficiais fazem isso). Para workflows feitos à mão sem metadados, o plugin não tem o que verificar — adicione os modelos manualmente. |
| O download falha imediatamente | `aria2c` não encontrado → instale o aria2 e garanta que esteja no PATH com o qual o ComfyUI inicia (é preciso reiniciar). |
| Muito lento | Sua rede também não alcança o `hf-mirror.com`; tente um proxy. |
| A contagem parece desatualizada após trocar de template | Aguarde ~2s pelo ciclo de sondagem; faça uma atualização forçada (Ctrl+R) se persistir. |
| A ação do painel não faz nada | O arquivo pode já ter sido removido (excluir) ou não estar na fila (reordenar); verifique os ícones de status do painel. |

## Referência da API (para desenvolvedores)

Todos os endpoints são servidos pelo próprio servidor do ComfyUI (sem porta extra):

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

`reason` nos itens ausentes: `missing` | `incomplete` (retomada automática) | `size` | `hash`.

## Licença

MIT © 2026 Bosconovitchi
