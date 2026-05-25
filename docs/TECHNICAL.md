# Documentacao Tecnica

## Visao Geral

O Arkham Bot e composto por quatro partes:

- Backend Python: executa o bot Telegram em long polling, agenda cartas diarias, consulta ArkhamDB e consome comandos administrativos.
- Supabase: armazena cartas, packs, configuracoes, admins, fila de comandos, historico e auditoria.
- Cloudflare Worker: valida `initData` do Telegram Mini App, valida admin e insere comandos na fila `bot_commands`.
- Mini App React/Vite: painel administrativo aberto dentro do Telegram.

Fluxo principal:

```txt
Telegram Bot -> main.py interactive
             -> scheduler.py
             -> daily_card.py
             -> Telegram API
             -> Supabase repositories

Telegram Mini App -> Cloudflare Worker
                  -> Supabase bot_commands
                  -> bot_commands_worker.py
                  -> backend Python executa comando
```

## Estrutura

```txt
.
|-- main.py
|-- arkham_daily_card_bot.py
|-- src/arkham_bot/
|-- scripts/
|-- tests/
|-- supabase/migrations/
|-- worker/
|-- miniapp/
|-- deploy/systemd/
|-- .github/workflows/
`-- docs/
```

## Backend Python

### `main.py`

Entrada principal.

Comandos:

- `python main.py --help`
- `python main.py healthcheck`
- `python main.py healthcheck --strict`
- `python main.py interactive`
- `python main.py <card_code>`

`interactive` inicia o bot Telegram, registra handlers, usa long polling e chama os workers internos.

### `config.py`

Centraliza variaveis de ambiente e caminhos locais.

Variaveis principais:

- `ENVIRONMENT`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ADMIN_TELEGRAM_USER_IDS`
- `DAILY_POST_ENABLED`
- `DAILY_POST_TIMES`
- `DAILY_POST_DAYS`
- `BOT_COMMANDS_POLLING_ENABLED`
- `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS`
- `OPENAI_API_KEY`

### `logging_config.py`

Configura console e arquivos rotativos em `logs/`.

Tambem:

- reduz logs de `httpx`, `httpcore`, `telegram` e `telegram.ext` em producao;
- mascara tokens no formato `bot<id>:<token>`;
- mascara valores carregados de `TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY` e `OPENAI_API_KEY`.

### `arkhamdb_client.py`

Cliente para a API publica do ArkhamDB.

Funcoes principais:

- `fetch_all_cards_sync(include_encounter=False)`
- `fetch_card_by_code_sync(card_code)`
- `fetch_cards_by_pack_sync(pack_code)`
- `fetch_packs_sync()`
- `fetch_factions_sync()`
- `fetch_faq_by_card_code_sync(card_code)`
- `fetch_taboos_sync()`
- `fetch_decklist_sync(decklist_id)`
- `download_image_sync(url)`

### `arkhamdb_models.py`

Valida e normaliza payloads recebidos da API ArkhamDB antes de persistir ou usar dados.

### `daily_card.py`

Executa postagem de carta:

- seleciona carta especifica, aleatoria ou via IA opcional;
- baixa imagem;
- monta legenda;
- envia foto/mensagem para Telegram;
- registra historico;
- atualiza estado de carta postada;
- faz pin/unpin quando configurado.

### `scheduler.py`

Scheduler interno usado no processo `interactive`.

Le configuracoes de `bot_settings` quando Supabase esta disponivel e usa `.env` como fallback.

### `bot_commands_worker.py`

Consome `public.bot_commands`.

Antes de buscar novos comandos, recupera comandos presos em `processing` ha mais tempo que `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS`.

Comandos aceitos:

- `post_now`
- `skip_card`
- `pause_daily_post`
- `resume_daily_post`
- `sync_arkhamdb`

Estados usados:

- `pending`
- `processing`
- `retrying`
- `executed`
- `failed`
- `cancelled`

### `telegram_handlers.py`

Registra handlers de comandos publicos e administrativos.

Comandos publicos:

- `/start`
- `/help`
- `/menu`
- `/status`
- `/today`
- `/random`
- `/card`
- `/faq`
- `/taboo`
- `/decklist`
- `/search`
- `/pack`
- `/faction`
- `/type`
- `/xp`

Comandos administrativos:

- `/admin`
- `/admin_status`
- `/post`
- `/repost`
- `/skip`
- `/pause`
- `/resume`
- `/settings`
- `/errors`
- `/queue`
- `/sync`
- `/reset_cycle`
- `/add_admin`
- `/remove_admin`

### `repositories/`

Camada de acesso ao Supabase.

- `admins_repo.py`: `bot_admins`
- `audit_repo.py`: `audit_logs`
- `cards_repo.py`: `arkham_cards`
- `commands_repo.py`: `bot_commands`
- `decklists_repo.py`: `arkham_decklists_cache`
- `errors_repo.py`: `bot_errors`
- `factions_repo.py`: `arkham_factions`
- `faq_repo.py`: `arkham_faq`
- `history_repo.py`: `bot_posting_history`
- `packs_repo.py`: `arkham_packs`
- `posted_cards_repo.py`: `bot_posted_cards`
- `settings_repo.py`: `bot_settings`
- `taboos_repo.py`: `arkham_taboos`

### `ai/`

Selecao opcional de carta diaria via OpenAI.

Ativada somente com:

```txt
AI_DAILY_CARD_ENABLED=true
OPENAI_API_KEY=<valor>
```

### `arkhamdb_oauth.py`

Modulo preparado para OAuth ArkhamDB. Nao e dependencia operacional do bot atual.

## Supabase

Migrations em `supabase/migrations/`.

Tabelas ArkhamDB:

- `arkham_cards`
- `arkham_packs`
- `arkham_factions`
- `arkham_faq`
- `arkham_taboos`
- `arkham_decklists_cache`

Tabelas operacionais:

- `bot_settings`
- `target_chats`
- `bot_admins`
- `bot_commands`
- `bot_posted_cards`
- `bot_posting_history`
- `bot_errors`
- `audit_logs`

RLS fica habilitado. O backend Python e o Worker usam `SUPABASE_SERVICE_ROLE_KEY`.

## Cloudflare Worker

Codigo em `worker/src/index.js`.

Responsabilidades:

- validar CORS por `ALLOWED_ORIGINS`;
- validar `x-telegram-init-data` com `TELEGRAM_BOT_TOKEN`;
- consultar admin em `bot_admins` ou fallback `ADMIN_TELEGRAM_USER_IDS`;
- usar fallback `ADMIN_TELEGRAM_USER_IDS` somente quando `ALLOW_ADMIN_ENV_FALLBACK=true`;
- normalizar `command_type`;
- inserir comandos em `bot_commands`;
- expor status basico.

Endpoints:

- `GET /health`
- `GET /me`
- `GET /status`
- `POST /bot-command`
- `OPTIONS *`

Comandos aceitos pelo Worker:

- `post_now`
- `skip_card`
- `pause_daily_post`
- `resume_daily_post`
- `sync_arkhamdb`

Aliases:

- `pause_daily -> pause_daily_post`
- `resume_daily -> resume_daily_post`

## Mini App

Codigo em `miniapp/`.

Stack:

- React 18
- Vite
- Wrangler assets deploy

Variavel de build:

```txt
VITE_COMMANDS_API_URL=https://<worker>.workers.dev
```

O Mini App:

- detecta `window.Telegram.WebApp`;
- le `initData`;
- chama `/me`, `/status` e `/bot-command` no Worker;
- nao contem secrets;
- desabilita acoes quando usuario nao e admin ou quando esta fora do Telegram.

## OAuth ArkhamDB

`arkhamdb_oauth.py` existe como modulo futuro. O runtime atual nao depende dele.

## IA

O modulo em `src/arkham_bot/ai/` e opcional. A ativacao depende de `AI_DAILY_CARD_ENABLED=true` e `OPENAI_API_KEY`.

## GitHub Actions

### `.github/workflows/deploy.yml`

Workflow de validacao geral:

- instala dependencias Python;
- roda compile;
- roda testes;
- roda help;
- roda healthcheck nao estrito.

### `.github/workflows/deploy-oracle.yml`

Workflow de deploy/sync Oracle:

- roda em push para `main` quando backend/scripts/deps mudam;
- tambem roda por `workflow_dispatch`;
- acessa Oracle via SSH;
- reseta `/opt/arkham_bot` para `origin/main`;
- instala dependencias;
- roda `healthcheck --strict`;
- reinicia `arkham-bot.service`.

Secrets usados:

- `ORACLE_HOST`
- `ORACLE_USER`
- `ORACLE_SSH_PRIVATE_KEY`
- `ORACLE_KNOWN_HOSTS`

## Systemd

Unit file em `deploy/systemd/arkham-bot.service`.

Servico esperado:

```txt
arkham-bot.service
```

Comando:

```txt
/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py interactive
```

## Seguranca

- `.env` nao deve ser commitado.
- `TELEGRAM_BOT_TOKEN`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY` e chaves SSH nao devem aparecer em logs.
- `SUPABASE_SERVICE_ROLE_KEY` nao deve ir para frontend.
- Worker deve validar Telegram initData antes de aceitar comandos.
- Worker deve validar admin antes de inserir comando critico.
- Worker deve preferir `bot_admins`; fallback por env deve ser opt-in.
- CORS em producao deve usar allowlist.
- Logs do backend mascaram tokens conhecidos.
