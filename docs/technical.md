# Documentação Técnica

## Visão Geral

O Arkham Bot é composto por quatro partes que se comunicam via Supabase:

```
Telegram Bot (Python, Oracle)
  ├── long polling — recebe comandos de usuários no Telegram
  ├── scheduler interno — posta carta diária nos horários configurados
  ├── command_worker — consome fila bot_commands a cada 30s
  └── heartbeat — escreve last_heartbeat no Supabase a cada 60s

Cloudflare Worker (arkham-bot-worker.homerlab.workers.dev)
  ├── valida initData Telegram + admin
  ├── serve API para o Mini App
  └── insere comandos em bot_commands

Mini App React (arkham-bot-miniapp.pages.dev)
  ├── painel administrativo dentro do Telegram
  └── se comunica exclusivamente com o Worker

Supabase
  └── banco de dados compartilhado entre Python e Worker
```

## Estrutura do Repositório

```
.
├── main.py                          # Entrada do backend Python
├── src/arkham_bot/
│   ├── core/
│   │   ├── config.py                # Variáveis de ambiente e constantes
│   │   ├── logging_config.py        # Logging com mascaramento de secrets
│   │   ├── permissions.py           # is_admin_user(), admin_source()
│   │   ├── rate_limiter.py          # Rate limit in-memory (por usuário e chat)
│   │   └── supabase_client.py       # Cliente REST HTTP para Supabase
│   ├── clients/
│   │   ├── arkhamdb_client.py       # Cliente da API pública ArkhamDB
│   │   └── arkhamdb_models.py       # Validação e normalização de payloads
│   ├── formatters/
│   │   └── text_formatters.py       # Formatação de legendas de carta (HTML Telegram)
│   ├── handlers/
│   │   ├── common.py                # Utilitários compartilhados, caches in-memory (10 min)
│   │   ├── registry.py              # Registro de todos os handlers no Application
│   │   ├── command_worker.py        # Executa comandos da fila bot_commands
│   │   ├── status_handler.py        # /start, /status
│   │   ├── card_handler.py          # /card (ConversationHandler com paginação)
│   │   ├── search_handler.py        # /search (ConversationHandler com paginação)
│   │   ├── sets_handler.py          # /sets (paginado, 10/página)
│   │   ├── taboo_handler.py         # /taboo (paginado, 5/página)
│   │   ├── faq_handler.py           # /faq (cache-on-demand, TTL 7 dias)
│   │   ├── decklist_handler.py      # /decklist (cache Supabase, TTL 24h)
│   │   ├── cotd_handler.py          # /cotd (histórico por ano/mês)
│   │   └── telegram_handlers.py     # Shim de compatibilidade (re-exporta todos os módulos)
│   ├── repositories/
│   │   ├── admins_repo.py           # bot_admins
│   │   ├── audit_repo.py            # audit_logs
│   │   ├── cards_repo.py            # arkham_cards
│   │   ├── commands_repo.py         # bot_commands
│   │   ├── factions_repo.py         # arkham_factions
│   │   ├── faq_repo.py              # arkham_faq (cache-on-demand)
│   │   ├── history_repo.py          # bot_posting_history
│   │   ├── packs_repo.py            # arkham_packs
│   │   ├── pending_destinations_repo.py # pending_destinations
│   │   ├── settings_repo.py         # bot_settings (cache 60s)
│   │   └── taboos_repo.py           # arkham_taboos
│   ├── services/
│   │   ├── card_provider.py         # Seleciona carta para postagem (aleatória ou por ciclo)
│   │   ├── daily_card.py            # Executa postagem de carta no Telegram
│   │   ├── heartbeat.py             # Background task: escreve last_heartbeat a cada 60s
│   │   ├── local_storage.py         # Cache local de cartas em disco (JSON)
│   │   └── scheduler.py             # Scheduler interno: agenda postagem diária
│   ├── ai/
│   │   └── daily_card_selector.py   # Seleção de carta via IA (Gemini, OpenAI, Groq, Mistral)
│   └── i18n/
│       ├── pt_br.py                 # Strings em português
│       └── en.py                    # Strings em inglês
├── scripts/
│   ├── sync_arkhamdb.py             # Sincroniza cartas/packs do ArkhamDB para Supabase
│   └── backup_supabase.sh           # Backup do banco Supabase
├── tests/                           # Testes unitários (pytest)
├── supabase/migrations/             # Schema SQL em ordem cronológica
├── worker/
│   ├── src/
│   │   ├── index.js                 # Entry point: CORS preflight + route dispatch
│   │   ├── http.js                  # Helpers de resposta JSON, CORS e origem
│   │   ├── supabase.js              # Helpers REST Supabase (service-role key)
│   │   ├── auth.js                  # Validação initData Telegram + guards requireAuth/requireAdmin/requireOwner
│   │   ├── validation.js            # Constantes e validadores de settings/input
│   │   ├── audit.js                 # Logging estruturado + escrita em audit_logs
│   │   └── handlers/                # Um módulo por grupo de endpoints
│   │       ├── admins.js            # /admins
│   │       ├── bot-info.js          # /bot-info
│   │       ├── cards.js             # /cards, /card-post
│   │       ├── commands.js          # /commands
│   │       ├── destinations.js      # /destinations, /destinations/pending
│   │       ├── history.js           # /history
│   │       ├── packs.js             # /packs
│   │       ├── runtime.js           # /bot-runtime
│   │       ├── settings.js          # /settings
│   │       └── status.js            # /status
│   └── wrangler.toml                # Configuração Wrangler
├── miniapp/
│   ├── src/                         # Fonte React
│   └── wrangler.jsonc               # Configuração Wrangler (apenas assets, deploy via Pages)
├── deploy/systemd/
│   └── arkham-bot.service           # Unit file systemd para Oracle
└── .github/workflows/
    ├── test.yml                     # CI: validação Python + Worker + Mini App
    └── deploy-oracle.yml            # CD: deploy automático para Oracle
```

## Backend Python

### `main.py`

Entrada principal. Comandos disponíveis:

```bash
python main.py --help
python main.py healthcheck           # Valida configuração (sem conectividade real)
python main.py healthcheck --strict  # Valida conectividade Telegram e Supabase
python main.py interactive           # Inicia bot em long polling (modo produção)
python main.py <card_code>           # Posta carta específica manualmente (ex: 01001)
```

`interactive` inicializa:
1. handlers Telegram
2. scheduler diário
3. command_worker (polling de bot_commands)
4. heartbeat (background task)

Shutdown gracioso: `post_shutdown` cancela o scheduler e o heartbeat antes de encerrar o event loop.

### `config.py`

Centraliza todas as variáveis de ambiente e constantes de runtime.

Variáveis obrigatórias para modo `interactive`:

| Variável | Padrão | Descrição |
|---|---|---|
| `ENVIRONMENT` | `development` | Ambiente (`development` ou `production`) |
| `TELEGRAM_BOT_TOKEN` | — | Token do bot Telegram |
| `SUPABASE_URL` | — | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | — | Chave service_role (bypassa RLS) |

Variáveis opcionais com defaults:

| Variável | Padrão | Descrição |
|---|---|---|
| `ADMIN_TELEGRAM_USER_IDS` | `""` | IDs Telegram de admins fallback (separados por vírgula) |
| `AI_DAILY_CARD_ENABLED` | `true` | Habilita seleção de carta por IA |
| `AI_MODEL` | `gemini-2.5-flash` | Modelo IA padrão |
| `GEMINI_API_KEY` | — | Chave Google Gemini |
| `OPENAI_API_KEY` | — | Chave OpenAI |
| `GROQ_API_KEY` | — | Chave Groq |
| `MISTRAL_API_KEY` | — | Chave Mistral |
| `BOT_COMMANDS_POLLING_ENABLED` | `true` | Habilita consumo da fila de comandos |
| `BOT_COMMANDS_POLLING_INTERVAL_SECONDS` | `30` | Intervalo de polling |
| `BOT_COMMANDS_BATCH_SIZE` | `10` | Comandos por ciclo |
| `BOT_COMMANDS_MAX_RETRIES` | `3` | Tentativas antes de `failed` |
| `BOT_COMMANDS_RETRY_DELAY_SECONDS` | `60` | Espera entre tentativas |
| `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS` | `900` | Timeout para comandos presos em `processing` |
| `REQUEST_TIMEOUT_SECONDS` | `15` | Timeout HTTP geral |

Variáveis gerenciadas pelo Mini App via Supabase — não precisam estar no `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `TIMEZONE` | `America/Sao_Paulo` | Fuso horário do scheduler |
| `DAILY_POST_ENABLED` | `true` | Postagem diária ativa |
| `DAILY_POST_TIMES` | `08:00` | Horários (separados por vírgula) |
| `DAILY_POST_DAYS` | todos | Dias da semana |

> `TELEGRAM_CHAT_ID` foi removido (v1.4.0). Destinos vêm exclusivamente da tabela `target_chats`.

### `logging_config.py`

- Logs rotativos em `logs/bot_execution.log` e `logs/bot_errors.log` (5 MB, 3 backups)
- Nível `INFO` em produção, `DEBUG` em desenvolvimento
- Mascara automaticamente `bot<id>:<token>` e valores de `TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`
- Reduz verbosidade de `httpx`, `httpcore`, `telegram`, `telegram.ext`

### `rate_limiter.py`

Rate limit in-memory para comandos públicos do Telegram:

- Por usuário: 10 requests / 60s
- Por chat: 60 requests / 60s
- Admins são isentos por padrão (`RATE_LIMIT_EXEMPT_ADMINS=true`)
- Implementação: `InMemoryRateLimiter` com sliding window usando `deque`

### `permissions.py`

Verifica permissões de admin para o bot Telegram:

- `is_admin_user(telegram_user_id)` — verifica em `ADMIN_TELEGRAM_USER_IDS` (fallback) e `bot_admins` (Supabase)
- `admin_source(telegram_user_id)` — retorna `"env"`, `"owner"`, `"admin"`, ou `"none"`

### `daily_card.py`

Orquestra postagem de carta no Telegram:

1. Resolve destinos via `_get_destinations()`: lê `target_chats` (enabled, com `message_thread_id`) no Supabase — única fonte de destinos
2. Seleciona carta (IA opcional, ou aleatória, ou por código específico)
3. Baixa imagem da ArkhamDB (frente e verso usam a mesma estratégia: tenta `imagesrc`/`backimagesrc`, senão o caminho do bundle por extensão)
4. Monta legenda HTML com `format_card_caption(is_interactive=not is_scheduled)`
   - `is_scheduled=True` → inclui prefixo `[COTD]`
   - `is_scheduled=False` (postagem manual) → sem `[COTD]`
5. Envia para destino primário com retry (3 tentativas); replica para destinos extras
6. Todos os `send_photo`/`send_message` passam `message_thread_id` para suporte a tópicos do Telegram
7. Registra em `bot_posting_history`
8. Atualiza `bot_posted_cards`
9. Faz pin/unpin quando configurado

`pre_message_sent` é declarado **fora** do loop de tentativas — garante que a mensagem de abertura da IA não seja enviada duas vezes em caso de retry.

### `scheduler.py`

Scheduler interno. A cada 30s verifica:

- Se o horário atual está dentro da janela de ±10 min de algum horário configurado
- Se o dia da semana está habilitado
- Se já postou naquela janela (estado em `data/daily_scheduler_state.json`)
- Lê configurações do Supabase (`bot_settings`) na inicialização e em cada ciclo

**Anti-duplicata em restart:** o slot é marcado como ocupado em `posted_slots` **antes** de chamar `post_daily_card`. Garante que se o bot for reiniciado durante o delay da mensagem de abertura da IA (ex: deploy), a nova instância não redispara o mesmo slot.

**Disparo antecipado:** quando `ai_pre_message_enabled=true` e `ai_pre_message_delay_seconds > 0`, o scheduler dispara o job `delay` segundos **antes** do horário configurado, para que a carta chegue no horário certo.

### `heartbeat.py`

Background task asyncio. A cada 60s faz upsert na tabela `bot_settings`:

```json
{ "key": "last_heartbeat", "value": "<ISO timestamp UTC>" }
```

O Worker usa esse valor em `/bot-runtime` para determinar se o bot está vivo (alive = `seconds_ago < 180`).

A task é cancelada graciosamente no shutdown via `stop_heartbeat()`.

### `command_worker.py`

Consome a fila `bot_commands` do Supabase a cada 30s.

Antes de buscar novos comandos, recupera comandos presos em `processing` há mais de `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS` — se `attempt_count < max_attempts` volta para `retrying`; caso contrário marca como `failed`.

Comandos aceitos:

| Comando | O que faz |
|---|---|
| `post_now` | Posta carta imediatamente (sem `[COTD]`) |
| `repost_card` | Reposta carta específica por código |
| `skip_card` | Marca carta como pulada no ciclo |
| `pause_daily_post` | Desativa `daily_post_enabled` no Supabase |
| `resume_daily_post` | Ativa `daily_post_enabled` no Supabase |
| `reset_cycle` | Limpa histórico de cartas postadas |
| `clear_queue` | Cancela todos os comandos `pending` |
| `update_setting` | Atualiza qualquer chave em `bot_settings` |
| `sync_arkhamdb` | Executa sincronização completa do ArkhamDB |

Estados de um comando:

```
pending → processing → executed
                    ↘ retrying → processing → ...
                              ↘ failed
pending → cancelled
```

### `telegram_handlers.py`

Comandos Telegram registrados:

| Comando | Descrição |
|---|---|
| `/start` | Ajuda com descrição de todos os comandos por seção |
| `/status` | Status operacional: hora local, catálogo, próximo post, último card do dia, Supabase (admins) |
| `/card` | Busca guiada por pack paginado (10/página) → número da carta → imagem com stats |
| `/search <nome>` | Busca cartas por nome com paginação |
| `/faq <código>` | FAQ oficial da carta: imagem como reply ao usuário, texto do FAQ como reply à imagem, link ArkhamDB e data de atualização |
| `/taboo` | Lista taboo atual com restrições e erratas |
| `/decklist <id>` | Decklist do ArkhamDB: imagem do investigador, cartas agrupadas por tipo com links, descrição limpa |
| `/sets` | Navega cartas por pack paginado (10/página); cartas com link ArkhamDB e spoiler ativo |
| `/cotd` | Histórico de postagens diárias por ano/mês |

Comportamentos:
- Todos os comandos que retornam carta/resultado fazem **reply** à mensagem original do usuário
- `/faq` usa **cache-on-demand**: consulta `arkham_faq` no DB primeiro (TTL 7 dias), busca na API e salva se ausente/desatualizado
- `/card` valida número digitado contra conjunto real de números do pack (evita "não encontrado" enganoso)
- `/status` desabilita preview de links

### `repositories/`

Camada de acesso ao Supabase via REST API (`SupabaseRestClient` com `SUPABASE_SERVICE_ROLE_KEY`). Uma classe por tabela.

### `ai/daily_card_selector.py`

Seleção de carta por IA. Ativada quando `AI_DAILY_CARD_ENABLED=true` e `is_scheduled=True`.

Provedores suportados (configurados em `AI_MODEL`):

| Provedor | Modelos |
|---|---|
| Google Gemini | `gemini-2.5-flash` ★, `gemini-2.0-flash`, `gemini-2.5-pro` |
| Groq | `llama-3.3-70b-versatile` ★, `llama-3.1-8b-instant`, `mixtral-8x7b-32768` |
| Mistral | `mistral-small-latest`, `mistral-medium-latest`, `open-mistral-7b` |
| OpenAI | `gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`, `gpt-4.1` |

★ = modelo padrão do provedor

## Supabase

Todas as migrations estão em `supabase/migrations/` em ordem cronológica. Devem ser aplicadas manualmente no SQL Editor do Supabase.

### Tabelas ArkhamDB (leitura pública via RLS)

| Tabela | Conteúdo |
|---|---|
| `arkham_cards` | Cartas completas com campos normalizados + `raw` JSONB |
| `arkham_packs` | Expansões/packs com metadados de ciclo/posição |
| `arkham_factions` | Facções |
| `arkham_faq` | FAQ por código de carta (populado por cache-on-demand via `/faq`) |
| `arkham_taboos` | Listas taboo |
| `arkham_decklists_cache` | Cache de decklists do ArkhamDB |

### Tabelas operacionais (service_role apenas)

| Tabela | Conteúdo |
|---|---|
| `bot_settings` | Configurações key-value do bot e do scheduler (cache 60s no Python) |
| `target_chats` | Destinos de postagem — **única fonte de destinos** (telegram_chat_id removido) |
| `pending_destinations` | Grupos onde o bot foi adicionado aguardando confirmação no Mini App |
| `bot_admins` | Admins com role (`owner`, `admin`, `viewer`) |
| `bot_commands` | Fila de comandos do Mini App para o bot |
| `bot_posted_cards` | Registro de cartas já postadas (controle de ciclo) |
| `bot_posting_history` | Histórico de cada postagem (source, card_code, timestamp) |
| `bot_errors` | Log de erros do bot |
| `audit_logs` | Auditoria de ações administrativas (add/remove admin/destino/settings/commands) |

### `target_chats` — suporte a tópicos

A constraint `UNIQUE(chat_id)` foi substituída por índices únicos parciais para destinos ativos (migration `202605280003_telegram_topics_support.sql`), permitindo múltiplos tópicos por grupo. `message_thread_id = NULL` representa o chat principal (sem tópico).

O Worker não usa `on_conflict` do PostgREST para este upsert — faz SELECT antes do INSERT para checar duplicata `(chat_id, message_thread_id)`, e re-habilita destinos soft-deletados quando o mesmo par é readicionado.

RLS está habilitado em todas as tabelas. O backend Python e o Worker usam `SUPABASE_SERVICE_ROLE_KEY`, que bypassa RLS.

## Cloudflare Worker

Código em `worker/src/`. Versão atual: **v1.3.0**.

`index.js` é o entry point: recebe o fetch, resolve a origem CORS, trata preflights e despacha para os handlers. Toda a lógica de negócio está nos módulos especializados (`http.js`, `supabase.js`, `auth.js`, `validation.js`, `audit.js`, `handlers/*`).

URL de produção: `https://arkham-bot-worker.homerlab.workers.dev`

Variáveis de ambiente (`worker/wrangler.toml`):

| Variável | Tipo | Descrição |
|---|---|---|
| `SUPABASE_URL` | var | URL do projeto Supabase |
| `ALLOWED_ORIGINS` | var | Lista de origens CORS permitidas (separadas por vírgula) |
| `SUPABASE_SERVICE_ROLE_KEY` | secret | Chave service_role Supabase |
| `TELEGRAM_BOT_TOKEN` | secret | Token do bot Telegram (para validar initData) |
| `ALLOW_ADMIN_ENV_FALLBACK` | var (opt.) | Se `true`, aceita `ADMIN_TELEGRAM_USER_IDS` como admins |
| `ADMIN_TELEGRAM_USER_IDS` | var (opt.) | IDs fallback quando `ALLOW_ADMIN_ENV_FALLBACK=true` |

### Níveis de autenticação

```
público        → CORS + origem válida apenas
requireAuth    → + valida x-telegram-init-data (HMAC-SHA256 + auth_date < 24h)
requireAdmin   → + consulta bot_admins no Supabase (role: owner ou admin)
requireOwner   → + exige role = owner
```

### Endpoints

| Método | Path | Auth | Descrição |
|---|---|---|---|
| `GET` | `/health` | público | Healthcheck simples |
| `GET` | `/me` | requireAuth | Perfil do usuário autenticado |
| `GET` | `/status` | requireAdmin | Status do bot (versão, total de cartas, packs, último comando) |
| `GET` | `/overview` | requireAdmin | Visão geral (settings, contagens, comandos e posts recentes) |
| `GET` | `/settings` | requireAdmin | Configurações atuais do bot |
| `PATCH` | `/settings` | requireAdmin | Atualiza configurações |
| `GET` | `/commands` | requireAdmin | Lista comandos recentes da fila |
| `PATCH` | `/commands/:id` | requireAdmin | Cancela comando pendente |
| `GET` | `/cards` | requireAdmin | Busca cartas por nome/código |
| `GET` | `/packs` | requireAdmin | Lista packs (Supabase first, fallback ArkhamDB API) |
| `GET` | `/history` | requireAdmin | Histórico de postagens com filtros |
| `GET` | `/bot-info` | requireAdmin | Nome, username e foto do bot via Telegram API |
| `POST` | `/bot-command` | requireAuth | Insere comando na fila (admin verificado internamente) |
| `GET` | `/ai-models` | CORS only | Lista provedores e modelos de IA disponíveis |
| `GET` | `/bot-runtime` | requireAdmin | Status heartbeat do bot Python (alive se last_heartbeat < 3 min) |
| `GET` | `/admins` | requireOwner | Lista admins |
| `POST` | `/admins` | requireOwner | Adiciona admin |
| `DELETE` | `/admins/:id` | requireOwner | Remove admin (protegido: não remove último owner) |
| `GET` | `/destinations` | requireAdmin | Lista destinos de postagem |
| `POST` | `/destinations` | requireAdmin | Adiciona destino |
| `PATCH` | `/destinations/:id` | requireAdmin | Atualiza destino |
| `DELETE` | `/destinations/:id` | requireAdmin | Remove destino |
| `POST` | `/destinations/:id/test` | requireAdmin | Envia mensagem de teste para o destino |
| `GET` | `/destinations/resolve` | requireAdmin | Resolve nome do grupo a partir do `chat_id` |
| `GET` | `/destinations/pending` | requireAdmin | Lista grupos detectados aguardando confirmação |
| `POST` | `/destinations/pending/:id/accept` | requireAdmin | Confirma grupo pendente (Thread ID opcional) |
| `DELETE` | `/destinations/pending/:id` | requireAdmin | Ignora grupo pendente |

### Rate limit no Worker

Antes de inserir em `bot_commands`, verifica se existe registro com mesmo `(user_id, command_type)` em status `pending` ou `processing` nos últimos 10 segundos. Se existir, retorna 429.

### Audit log no Worker

Ações que geram registro em `audit_logs`:

- `admin_added` / `admin_removed`
- `destination_added` / `destination_removed` / `destination_updated` / `destination_added_from_pending`
- `settings_updated`
- `command_submitted` / `command_cancelled`

## Mini App React

URL de produção: `https://arkham-bot-miniapp.pages.dev`

Deploy: automático via **Cloudflare Pages** conectado ao repositório GitHub. Qualquer push em `main` que altere arquivos em `miniapp/` dispara rebuild e deploy. **Nunca execute `wrangler deploy` na pasta `miniapp/`.**

### Stack

- React 18 + Vite 5
- Ícones: **Lucide React** (tree-shaken, ~30 ícones importados)
- Sem bibliotecas de estado externas
- CSS custom com variáveis Telegram (`--tg-theme-*`) + variáveis próprias (`--warn`, `--warn-bg`, `--ok`, `--err`, `--toggle-knob`, `--focus-ring`)
- Hierarquia de fontes: 19px / 14px / 13px / 12px / 11px
- Paddings padronizados: `8px 14px` em todos os rows
- Alvos de toque mínimos de 36px nos botões de ícone
- Acessibilidade: `:focus-visible` em todos os controles, `prefers-reduced-motion`, e feedback de ação anunciado via `role`/`aria-live`

### Módulos (`miniapp/src/`)

| Arquivo | Responsabilidade |
|---|---|
| `main.jsx` | Bootstrap: monta `<App />` no `#root` |
| `App.jsx` | Componente raiz; todo estado e navegação |
| `telegram.js` | Acesso ao `window.Telegram.WebApp` com fallbacks |
| `api.js` | `apiFetch()` — constrói URL a partir de `VITE_COMMANDS_API_URL` e injeta `x-telegram-init-data` |
| `i18n.js` | Strings PT/EN, constantes de domínio (WEEKDAYS, ALL_CARD_TYPES, TIMEZONES) |
| `settings.js` | DEFAULT_SETTINGS, normalização, validação, AI_PROVIDERS fallback |
| `icons.jsx` | SVG paths e componente `<Icon name />` |
| `components.jsx` | Componentes de UI reutilizáveis (Row, MenuRow, Section, Toggle, ResultRow, LoadingRow, etc.) |
| `style.css` | Estilos globais com variáveis CSS do tema Telegram |

### Variável de build

```
VITE_COMMANDS_API_URL=https://arkham-bot-worker.homerlab.workers.dev
```

Configurada nas variáveis de ambiente do Cloudflare Pages.

### Navegação por abas

```
home
├── post          — Postar carta com busca por nome; destino selecionável
├── history       — Histórico de postagens (filtro por fonte e data; abre no dia atual)
├── queue         — Fila de comandos; "Limpar Fila" aparece apenas quando há pendentes
├── settings      — Configurações de postagem
│   ├── schedule  — Horários e dias da semana
│   ├── day_detail — Configuração específica por dia (horários, ciclos, tipos)
│   └── ai        — IA: modelo, tom, criatividade, delays de pré/pós mensagem
├── destinations  — Gerenciar destinos de postagem (chat_id + message_thread_id)
├── database      — Sync ArkhamDB, status de cartas/packs, sync agendado
├── maintenance   — Reset de ciclo
├── health        — Heartbeat do bot, capacidades, diagnóstico
└── app_settings  — Idioma do aplicativo + Administradores (somente owners)
```

Seção **Configurações** na home: Postagem · Gerenciar destinos · Aplicativo

O botão BackButton do Telegram é gerenciado pelo `PARENT_TAB` para abas filhas.

## GitHub Actions

### `test.yml`

Disparado em push/PR para `main` e manualmente.

Jobs:
1. **test** (Python 3.11): `compileall` + `pytest` + `healthcheck`
2. **worker** (Node 22): syntax check + testes + `npm run dry-run`
3. **miniapp** (Node 22): `npm run build`

### `deploy-oracle.yml`

Disparado em push para `main` quando há alterações em `main.py`, `src/`, `scripts/`, `requirements*.txt`, `pyproject.toml`. Também aceita `workflow_dispatch`.

Passos:
1. Validação local (Python): `compileall` + `pytest` + `main.py --help`
2. SSH no Oracle
3. `git reset --hard origin/main`
4. Atualiza `.env` com `AI_DAILY_CARD_ENABLED=true`
5. `pip install -r requirements.txt` (no venv)
6. `python main.py healthcheck --strict`
7. `sudo systemctl restart arkham-bot`
8. Valida status do serviço

Secrets necessários (em `oracle-production` environment):

| Secret | Descrição |
|---|---|
| `ORACLE_HOST` | IP/hostname do servidor |
| `ORACLE_USER` | Usuário SSH |
| `ORACLE_SSH_PRIVATE_KEY` | Chave privada PEM |
| `ORACLE_KNOWN_HOSTS` | Fingerprint do servidor |

## Systemd

Unit file em `deploy/systemd/arkham-bot.service`.

```ini
[Service]
WorkingDirectory=/opt/arkham_bot
EnvironmentFile=/opt/arkham_bot/.env
ExecStart=/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py interactive
Restart=always
RestartSec=10
```

## Segurança

- `.env` nunca deve ser commitado
- `SUPABASE_SERVICE_ROLE_KEY` e `TELEGRAM_BOT_TOKEN` ficam apenas em: `.env` Oracle, secrets do Worker, secrets do GitHub Actions
- O Mini App não contém secrets — opera exclusivamente via Worker autenticado
- `initData` tem validade de 24h; o Worker rejeita tokens expirados
- CORS em produção usa allowlist (`ALLOWED_ORIGINS`): apenas `arkham-bot-miniapp.pages.dev`
- Logs mascaram tokens automaticamente
- `requireOwner` protege `/admins` — admins comuns não podem gerenciar outros admins
- Remoção do último owner bloqueada no Worker
