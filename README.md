# Arkham Bot

Bot Telegram para **Arkham Horror: The Card Game**, com postagem diária automática de cartas, painel administrativo e seleção por IA.

## Componentes

| Componente | Tecnologia | URL de produção |
|---|---|---|
| Bot Python | python-telegram-bot, long polling | Oracle Linux (`/opt/arkham_bot`) |
| Cloudflare Worker | JavaScript (Cloudflare Workers) | `arkham-bot-worker.homerlab.workers.dev` |
| Mini App Admin | React 18 + Vite (Cloudflare Pages) | `arkham-bot-miniapp.pages.dev` |
| Banco de dados | Supabase (PostgreSQL REST) | `uqtmwnjxrxiylstbezhy.supabase.co` |

## O que o bot faz

- Posta uma carta aleatória de Arkham Horror todo dia, nos horários configurados
- Usa IA (Gemini, OpenAI, Groq ou Mistral) para escolher a carta com contexto narrativo
- Aceita comandos administrativos via Mini App: postar agora, pular carta, pausar, sincronizar dados
- Expõe `/card`, `/search`, `/faq`, `/taboo`, `/decklist`, `/sets`, `/cotd` para usuários no Telegram
- Mantém histórico de postagens, fila de comandos e auditoria de ações administrativas no Supabase

## Documentação

- [Documentação técnica](docs/technical.md) — arquitetura, módulos, endpoints, schema
- [Operação e deploy](docs/operations.md) — setup, deploy, monitoramento, troubleshooting

## Estrutura do Repositório

```
.
├── main.py                    # Entrada do backend Python
├── src/arkham_bot/            # Pacote principal do bot
│   ├── core/                  # Config, logging, permissions, rate limiter
│   ├── clients/               # Cliente ArkhamDB
│   ├── formatters/            # Formatação de legendas (HTML Telegram)
│   ├── handlers/              # Handlers Telegram e command_worker
│   ├── repositories/          # Acesso ao Supabase (uma classe por tabela)
│   ├── services/              # daily_card, scheduler, heartbeat
│   ├── ai/                    # Seleção de carta por IA
│   └── i18n/                  # Strings PT/EN
├── scripts/                   # sync_arkhamdb.py, backup_supabase.sh
├── tests/                     # Testes unitários (pytest)
├── supabase/migrations/       # Schema SQL (aplicar manualmente no Supabase)
├── worker/                    # Cloudflare Worker (src/index.js)
├── miniapp/                   # Mini App React/Vite
├── deploy/systemd/            # arkham-bot.service
└── .github/workflows/         # test.yml, deploy-oracle.yml
```

## Setup Local

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e .
cp .env.example .env
# editar .env com TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

## Comandos

```powershell
# Validação
python -m compileall -q .
python -m pytest -q
python main.py healthcheck --strict

# Rodar o bot
python main.py interactive

# Postar carta específica
python main.py 01001

# Sincronizar cartas do ArkhamDB
python scripts/sync_arkhamdb.py --dry-run
python scripts/sync_arkhamdb.py
```

## Worker

```powershell
cd worker
npm install
npm run dry-run    # valida sem deployar
npm run deploy     # deploy para Cloudflare Workers
```

## Mini App

O Mini App faz deploy automático via Cloudflare Pages em cada push para `main`.

Build local:

```powershell
cd miniapp
npm install
$env:VITE_COMMANDS_API_URL="https://arkham-bot-worker.homerlab.workers.dev"
npm run build
```

## Deploy

- **Bot Python**: automático via `deploy-oracle.yml` em push para `main` (alterações em `src/`, `main.py`, `requirements.txt`)
- **Worker**: manual com `npm run deploy` em `worker/`
- **Mini App**: automático via Cloudflare Pages em push para `main`

## Segurança

- `.env` nunca deve ser commitado
- `SUPABASE_SERVICE_ROLE_KEY` e `TELEGRAM_BOT_TOKEN` ficam apenas no servidor Oracle, secrets do Worker e secrets do GitHub Actions
- O Mini App não contém secrets — opera via Worker autenticado com `initData` Telegram
- CORS restringe o Worker à origem `arkham-bot-miniapp.pages.dev`
- Logs mascaram tokens e chaves automaticamente
