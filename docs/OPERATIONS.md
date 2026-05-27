# Operacao e Deploy

## Ambiente Local

Python 3.11+.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Node e npm sao usados em `worker/` e `miniapp/`.

```powershell
cd worker
npm install

cd ..\miniapp
npm install
```

## Variaveis de Ambiente

Backend Python:

```txt
ENVIRONMENT
TELEGRAM_BOT_TOKEN
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
ADMIN_TELEGRAM_USER_IDS
AI_DAILY_CARD_ENABLED
AI_MODEL
GEMINI_API_KEY
OPENAI_API_KEY
GROQ_API_KEY
MISTRAL_API_KEY
BOT_COMMANDS_POLLING_ENABLED
BOT_COMMANDS_POLLING_INTERVAL_SECONDS
BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS
REQUEST_TIMEOUT_SECONDS
```

Variaveis gerenciadas pelo miniapp (Supabase) — nao precisam estar no .env:

```txt
TIMEZONE
DAILY_POST_ENABLED
DAILY_POST_TIMES
DAILY_POST_DAYS
TELEGRAM_CHAT_ID
```

Worker:

```txt
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
TELEGRAM_BOT_TOKEN
ALLOWED_ORIGINS
ADMIN_TELEGRAM_USER_IDS
ALLOW_ADMIN_ENV_FALLBACK
```

Mini App:

```txt
VITE_COMMANDS_API_URL
```

## Validacao Python

```powershell
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
```

Com `.env` real:

```powershell
python main.py healthcheck --strict
```

## Rodar o Bot

```powershell
python main.py interactive
```

Postar carta especifica:

```powershell
python main.py 01001
```

## Sync ArkhamDB

Dry-run:

```powershell
python scripts/sync_arkhamdb.py --dry-run
```

Sync real:

```powershell
python scripts/sync_arkhamdb.py
```

## Worker

```powershell
cd worker
npm run dry-run
```

Deploy:

```powershell
cd worker
npm run deploy
```

Estrategia definida: deploy manual via Wrangler. Mudancas em `miniapp/` e `worker/` nao reiniciam a Oracle.

## Mini App

Build:

```powershell
cd miniapp
$env:VITE_COMMANDS_API_URL="https://<worker>.workers.dev"
npm run build
```

Dry-run:

```powershell
npm run dry-run
```

Deploy:

```powershell
npm run deploy
```

## Oracle

Caminho esperado:

```txt
/opt/arkham_bot
```

Servico:

```txt
arkham-bot.service
```

Comandos uteis:

```bash
cd /opt/arkham_bot
git branch --show-current
git log -1 --oneline
sudo systemctl status arkham-bot --no-pager -l
sudo journalctl -u arkham-bot -n 100 --no-pager -l
sudo journalctl -u arkham-bot -f
```

Atualizacao manual:

```bash
cd /opt/arkham_bot
git fetch origin main
git checkout main
git reset --hard origin/main
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q .
python main.py healthcheck --strict
sudo systemctl restart arkham-bot
```

## GitHub Actions

`deploy.yml` valida o projeto.

`deploy-oracle.yml` sincroniza Oracle com `origin/main` para mudancas de backend e tambem aceita execucao manual.

O CI tambem valida:

- build do Mini App;
- sintaxe do Worker;
- dry-run do Worker.

Secrets necessarios:

```txt
ORACLE_HOST
ORACLE_USER
ORACLE_SSH_PRIVATE_KEY
ORACLE_KNOWN_HOSTS
```

## Checklist de Release

Backend:

```txt
[ ] python -m compileall -q .
[ ] python -m pytest -q
[ ] python main.py healthcheck --strict
[ ] deploy-oracle.yml executou com sucesso
[ ] arkham-bot.service active
[ ] logs sem secrets
```

Worker:

```txt
[ ] npm run dry-run
[ ] npm run deploy
[ ] /health responde ok
[ ] /me valida initData
[ ] /bot-command bloqueia nao-admin
```

Mini App:

```txt
[ ] npm run build
[ ] npm run dry-run
[ ] npm run deploy
[ ] abre dentro do Telegram
[ ] initData presente
[ ] API configurada
[ ] admin validado
```

## Comandos Presos

O worker interno recupera comandos em `processing` quando `updated_at` fica mais antigo que `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS`.

Politica:

- se `attempt_count < max_attempts`, o comando volta para `retrying`;
- se `attempt_count >= max_attempts`, o comando vira `failed`;
- `last_error` e `result` recebem o motivo da recuperacao.

Consulta util:

```sql
select id, command_type, status, attempt_count, max_attempts, updated_at, last_error
from public.bot_commands
where status in ('processing', 'retrying', 'failed')
order by updated_at desc
limit 20;
```

## Monitoramento

Itens minimos para monitorar:

- `arkham-bot.service` ativo;
- Worker `/health`;
- `python main.py healthcheck --strict` na Oracle;
- comandos em `processing` por tempo excessivo;
- comandos `failed` recentes;
- falhas recorrentes de postagem Telegram;
- falhas de sync ArkhamDB.

Exemplo local na Oracle:

```bash
sudo systemctl is-active --quiet arkham-bot
cd /opt/arkham_bot
source venv/bin/activate
python main.py healthcheck --strict
```

Alertas nao devem incluir tokens, URLs Telegram com token, headers `Authorization` ou service role.

## Backup Supabase

O script existente fica em `scripts/backup_supabase.sh`.

Rotina recomendada:

- executar via timer systemd ou scheduler externo;
- salvar arquivo com timestamp;
- manter retencao definida fora do repo;
- testar restore em ambiente separado;
- nao imprimir secrets nos logs.

## Troubleshooting

Healthcheck strict falha:

- verificar `.env`;
- verificar token Telegram;
- verificar `SUPABASE_URL`;
- verificar `SUPABASE_SERVICE_ROLE_KEY`;
- verificar conectividade da Oracle.

Mini App sem API:

- confirmar `VITE_COMMANDS_API_URL`;
- rebuildar e redeployar Mini App;
- validar CORS no Worker.

`invalid_telegram_init_data`:

- abrir pelo Telegram;
- confirmar token do Worker;
- confirmar que o Mini App envia `x-telegram-init-data`.

Usuario nao-admin conseguiu executar comando:

- confirmar que o Worker publicado esta na versao atual;
- chamar `/me` no Mini App e verificar `admin`, `role` e `admin_source`;
- conferir se o usuario nao esta em `public.bot_admins` com role `owner` ou `admin`;
- conferir se `ALLOW_ADMIN_ENV_FALLBACK=true` esta ativo no Worker;
- conferir se `ADMIN_TELEGRAM_USER_IDS` nao contem o id do usuario;
- redeployar Worker apos qualquer mudanca de secret/var.

Comando fica `pending`:

- verificar `arkham-bot.service`;
- verificar `BOT_COMMANDS_POLLING_ENABLED`;
- verificar logs do `bot_commands_worker`;
- verificar Supabase.
