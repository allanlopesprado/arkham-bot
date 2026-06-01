# Operação e Deploy

## Ambiente Local

### Python

Python 3.11+.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Crie `.env` a partir de `.env.example`:

```powershell
cp .env.example .env
# editar .env com os valores reais
```

### Node (Worker e Mini App)

```powershell
cd worker
npm install

cd ..\miniapp
npm install
```

## Variáveis de Ambiente

### Backend Python (`.env`)

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `ENVIRONMENT` | sim | `development` | `development` ou `production` |
| `TELEGRAM_BOT_TOKEN` | sim | — | Token do bot |
| `SUPABASE_URL` | sim | — | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | sim | — | Chave service_role |
| `ADMIN_TELEGRAM_USER_IDS` | não | `""` | IDs de admins fallback (vírgula) |
| `AI_DAILY_CARD_ENABLED` | não | `true` | Seleção por IA habilitada |
| `AI_MODEL` | não | `gemini-2.5-flash` | Modelo de IA |
| `GEMINI_API_KEY` | se usar Gemini | — | |
| `OPENAI_API_KEY` | se usar OpenAI | — | |
| `GROQ_API_KEY` | se usar Groq | — | |
| `MISTRAL_API_KEY` | se usar Mistral | — | |
| `BOT_COMMANDS_POLLING_ENABLED` | não | `true` | Consome fila de comandos |
| `BOT_COMMANDS_POLLING_INTERVAL_SECONDS` | não | `30` | |
| `BOT_COMMANDS_BATCH_SIZE` | não | `10` | |
| `BOT_COMMANDS_MAX_RETRIES` | não | `3` | |
| `BOT_COMMANDS_RETRY_DELAY_SECONDS` | não | `60` | |
| `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS` | não | `900` | |
| `REQUEST_TIMEOUT_SECONDS` | não | `15` | |

Variáveis gerenciadas pelo Mini App via Supabase — **não precisam estar no `.env`**:

| Variável | Descrição |
|---|---|
| `TIMEZONE` | Fuso horário do scheduler |
| `DAILY_POST_ENABLED` | Postagem diária ativa |
| `DAILY_POST_TIMES` | Horários de postagem |
| `DAILY_POST_DAYS` | Dias da semana |

> `TELEGRAM_CHAT_ID` foi **removido**. Destinos de postagem vêm exclusivamente da tabela `target_chats`. O bot auto-detecta grupos quando adicionado e exibe na seção "Bot adicionado a novos grupos" do Mini App.

### Worker (`worker/wrangler.toml` + secrets)

| Variável | Tipo | Descrição |
|---|---|---|
| `SUPABASE_URL` | var (toml) | URL do projeto Supabase |
| `ALLOWED_ORIGINS` | var (toml) | Origens CORS permitidas |
| `SUPABASE_SERVICE_ROLE_KEY` | secret | `wrangler secret put SUPABASE_SERVICE_ROLE_KEY` |
| `TELEGRAM_BOT_TOKEN` | secret | `wrangler secret put TELEGRAM_BOT_TOKEN` |
| `ALLOW_ADMIN_ENV_FALLBACK` | var (opt.) | Se `true`, aceita `ADMIN_TELEGRAM_USER_IDS` |
| `ADMIN_TELEGRAM_USER_IDS` | var (opt.) | IDs fallback para admins |

### Mini App (`miniapp/`)

| Variável | Descrição |
|---|---|
| `VITE_COMMANDS_API_URL` | URL do Worker. Configurada no painel Cloudflare Pages |

## Rodar Localmente

### Bot Python

```powershell
python main.py interactive
```

Postar carta específica:

```powershell
python main.py 01001
```

### Worker (desenvolvimento)

```powershell
cd worker
npx wrangler dev
```

### Mini App (desenvolvimento)

```powershell
cd miniapp
$env:VITE_COMMANDS_API_URL="https://arkham-bot-worker.homerlab.workers.dev"
npm run dev
```

## Validação

### Python

```powershell
python -m compileall -q .
python -m pytest -q
python main.py healthcheck
python main.py healthcheck --strict   # requer .env com valores reais
```

### Worker

```powershell
cd worker
npm run dry-run     # wrangler deploy --dry-run
npm test            # testes unitários
```

### Mini App

```powershell
cd miniapp
npm run build       # build de produção com Vite
```

## Deploy

### Worker

Deploy manual via Wrangler:

```powershell
cd worker
npm run deploy    # wrangler deploy
```

O Worker **não tem** deploy automático via CI/CD — apenas dry-run e syntax check. Qualquer mudança em `worker/` deve ser deployada manualmente após o push.

### Mini App

O Mini App é deployado automaticamente pelo **Cloudflare Pages** a cada push em `main` que altere arquivos em `miniapp/`.

**Nunca execute `wrangler deploy` na pasta `miniapp/`.** O arquivo `miniapp/wrangler.jsonc` é apenas para build local e dry-run.

### Bot Python (Oracle)

O deploy é automático via GitHub Actions (`deploy-oracle.yml`) quando há mudanças em `main.py`, `src/`, `scripts/`, `requirements*.txt` ou `pyproject.toml`.

Também pode ser acionado manualmente em: GitHub → Actions → Deploy Oracle → Run workflow.

#### Atualização manual no servidor

```bash
cd /opt/arkham_bot
git fetch origin main
git reset --hard origin/main
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m compileall -q .
python main.py healthcheck --strict
sudo systemctl restart arkham-bot
```

## Supabase — Migrations

As migrations devem ser aplicadas manualmente no SQL Editor do Supabase em ordem cronológica:

```
supabase/migrations/202605240001_initial_schema.sql
supabase/migrations/202605240002_public_read_and_admin_policy_notes.sql
supabase/migrations/202605260001_add_source_to_posting_history.sql
supabase/migrations/202605260002_fix_arkham_cards_schema.sql
supabase/migrations/202605270001_p3_admins_destinations_audit.sql
supabase/migrations/202605280001_claim_bot_commands_rpc.sql
supabase/migrations/202605280002_pending_destinations.sql
supabase/migrations/202605280003_telegram_topics_support.sql
supabase/migrations/202605280004_worker_hardening_schema.sql
```

| Migration | O que faz |
|---|---|
| `202605280001_claim_bot_commands_rpc.sql` | Cria RPC `claim_bot_commands` com `FOR UPDATE SKIP LOCKED` — evita execução dupla |
| `202605280002_pending_destinations.sql` | Cria tabela `pending_destinations` — grupos aguardando confirmação no Mini App |
| `202605280003_telegram_topics_support.sql` | Troca `UNIQUE(chat_id)` por índices únicos parciais de destinos ativos em `target_chats` |
| `202605280004_worker_hardening_schema.sql` | Adiciona colunas de hardening usadas pelo Worker/Mini App |

## Sincronização ArkhamDB

Dry-run (sem escrita):

```powershell
python scripts/sync_arkhamdb.py --dry-run
```

Sync real (cartas, packs, facções, taboos):

```powershell
python scripts/sync_arkhamdb.py
```

O sync normal **também atualiza** FAQs que já estão em cache no banco (`arkham_faq`), sem buscar os ~5900 cards do zero.

Sync com FAQ completo (lento — uma chamada por carta):

```powershell
python scripts/sync_arkhamdb.py --sync-faq
```

O sync também pode ser disparado pelo Mini App via botão na aba "Database" (comando `sync_arkhamdb` na fila).

### Estratégia de cache de FAQ

O `/faq` popula `arkham_faq` por demanda (cache-on-demand):
- Consulta o banco primeiro (TTL: 7 dias)
- Se ausente ou desatualizado, busca na ArkhamDB API e salva no banco
- O sync diário refresca apenas os FAQs já cacheados

## Oracle — Comandos Úteis

```bash
# Status do serviço
sudo systemctl status arkham-bot --no-pager -l

# Logs em tempo real
sudo journalctl -u arkham-bot -f

# Últimas 100 linhas de log
sudo journalctl -u arkham-bot -n 100 --no-pager -l

# Branch e commit atual
cd /opt/arkham_bot
git branch --show-current
git log -1 --oneline

# Reiniciar serviço
sudo systemctl restart arkham-bot

# Parar / iniciar
sudo systemctl stop arkham-bot
sudo systemctl start arkham-bot
```

## Monitoramento

Itens mínimos a monitorar:

- `arkham-bot.service` ativo
- Worker `/health` respondendo
- `python main.py healthcheck --strict` na Oracle
- Heartbeat: `/bot-runtime` no Worker — `alive: true`
- Comandos em `processing` por tempo excessivo (> 15 min)
- Comandos `failed` recentes
- Logs sem erros recorrentes de postagem Telegram

Verificação rápida na Oracle:

```bash
sudo systemctl is-active --quiet arkham-bot && echo "running" || echo "STOPPED"
cd /opt/arkham_bot && source venv/bin/activate && python main.py healthcheck --strict
```

Consulta de comandos problemáticos no Supabase:

```sql
select id, command_type, status, attempt_count, max_attempts, updated_at, last_error
from public.bot_commands
where status in ('processing', 'retrying', 'failed')
order by updated_at desc
limit 20;
```

## Comandos Presos

O `command_worker` recupera comandos presos em `processing` automaticamente quando `updated_at` é mais antigo que `BOT_COMMANDS_PROCESSING_TIMEOUT_SECONDS` (padrão: 15 min).

Política:
- `attempt_count < max_attempts` → volta para `retrying`
- `attempt_count >= max_attempts` → vira `failed`

## Checklist de Release

### Backend Python

```
[ ] python -m compileall -q .
[ ] python -m pytest -q
[ ] python main.py healthcheck --strict
[ ] push para main
[ ] deploy-oracle.yml executou com sucesso
[ ] arkham-bot.service active
[ ] journalctl sem erros novos
[ ] /bot-runtime retorna alive: true
```

### Worker

```
[ ] npm run dry-run (sem erros)
[ ] npm run deploy
[ ] GET /health → { ok: true }
[ ] GET /me → valida initData
[ ] POST /bot-command sem admin → 403
[ ] GET /status → versão correta
```

### Mini App

```
[ ] npm run build (sem erros)
[ ] Cloudflare Pages build concluído
[ ] Abre dentro do Telegram
[ ] initData presente
[ ] Todas as abas carregando corretamente
[ ] Postagem manual funciona (sem [COTD])
[ ] Postagem diária agendada funciona (com [COTD])
```

## Troubleshooting

### Healthcheck strict falha

- Verificar `.env` (TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
- Verificar conectividade da Oracle com `curl https://api.telegram.org`
- Verificar que o venv está ativado

### Mini App não carrega dados

- Confirmar `VITE_COMMANDS_API_URL` nas variáveis do Cloudflare Pages
- Verificar se o Worker está deployado: `GET /health`
- Verificar CORS: `ALLOWED_ORIGINS` deve conter `arkham-bot-miniapp.pages.dev`
- Abrir DevTools do Telegram e verificar erros no console

### `invalid_telegram_init_data`

- Abrir pelo Telegram (não funciona no browser diretamente)
- Confirmar que `TELEGRAM_BOT_TOKEN` no Worker é o mesmo do bot
- Confirmar que `x-telegram-init-data` está sendo enviado (`api.js` → `authHeaders()`)

### Usuário não-admin conseguiu executar comando

- Verificar `/me` no Mini App: campo `admin` deve ser `false`
- Verificar `bot_admins` no Supabase
- Verificar se `ALLOW_ADMIN_ENV_FALLBACK=true` está ativo no Worker com `ADMIN_TELEGRAM_USER_IDS` contendo o ID
- Redeployar Worker após qualquer mudança de secret

### Comando fica `pending`

- Verificar `arkham-bot.service` está active
- Verificar `BOT_COMMANDS_POLLING_ENABLED=true` no `.env`
- Verificar logs: `journalctl -u arkham-bot -f`
- Verificar conectividade Oracle → Supabase

### Postagem diária não acontece

- Verificar `daily_post_enabled` no Supabase (`bot_settings`)
- Verificar `daily_post_times` e `daily_post_days`
- Verificar `telegram_chat_id` ou `target_chats` com `enabled=true`
- Verificar timezone (`TIMEZONE` em `bot_settings`)
- Verificar scheduler: `journalctl -u arkham-bot | grep scheduler`

### Postagem duplicada após restart

O slot é gravado em `posted_slots` antes de `post_daily_card` ser chamado. Se ainda assim houver duplicata, verificar se `data/daily_scheduler_state.json` está preservado entre restarts.

### Mensagem de abertura da IA duplicada

`pre_message_sent` é declarado fora do loop de tentativas em `daily_card.py`. Se a flag estiver sendo resetada, verificar se há mais de uma instância do bot rodando simultaneamente.

### `[COTD]` aparecendo em postagem manual

- Confirmar que `command_type` é `post_now` (não `sync_arkhamdb` ou similar)
- O prefixo `[COTD]` só deve aparecer quando `is_scheduled=True` (scheduler automático)

### Worker retorna 403 para todas as requisições

- Verificar `ALLOWED_ORIGINS` no `wrangler.toml`
- Confirmar que o Mini App está sendo acessado de `arkham-bot-miniapp.pages.dev`

## Backup Supabase

Script em `scripts/backup_supabase.sh`.

Recomendações:
- Executar via timer systemd ou cron externo
- Salvar arquivo com timestamp
- Manter retenção definida fora do repo
- Testar restore em ambiente separado
- Não imprimir secrets nos logs
