# Arkham Bot

Bot para Telegram dedicado a **Arkham Horror: The Card Game**. Posta uma carta do dia com seleção por IA, suporta múltiplos destinos (incluindo tópicos de grupos), e vem com um painel administrativo React acessível diretamente no Telegram.

---

## Arquitetura

```
Telegram Bot (Python — Oracle Linux)
  ├── long polling — recebe comandos dos usuários
  ├── scheduler interno — posta carta diária nos horários configurados
  ├── command_worker — consome fila bot_commands a cada 30s
  └── heartbeat — registra sinal de vida no Supabase a cada 60s

Cloudflare Worker (JavaScript)
  ├── valida initData do Telegram (HMAC-SHA256)
  ├── serve API REST para o Mini App
  └── insere comandos na fila bot_commands

Mini App React (Cloudflare Pages)
  ├── painel administrativo dentro do Telegram
  └── comunica-se exclusivamente com o Worker (sem secrets)

Supabase (PostgreSQL + PostgREST)
  └── banco compartilhado: cartas, fila, configurações, histórico, admins
```

---

## Comandos do Bot

| Comando | Descrição |
|---|---|
| `/start` | Ajuda com descrição de todos os comandos |
| `/status` | Status operacional: uptime, próximo post, último card, Supabase |
| `/card` | Busca guiada por pack (paginado) → número → imagem com stats |
| `/search <nome>` | Busca livre de cartas por nome com paginação |
| `/faq <código>` | FAQ oficial da carta (cache local, TTL 7 dias) |
| `/taboo` | Lista taboo atual com restrições e erratas (paginada, 5/página) |
| `/decklist <id>` | Deck do ArkhamDB: imagem do investigador + lista agrupada por tipo |
| `/sets` | Navega cartas por set/expansão (paginado, 10/página) |
| `/cotd` | Histórico de cartas do dia por ano/mês |

---

## Stack

| Camada | Tecnologia |
|---|---|
| Bot | Python 3.11+, python-telegram-bot v22 |
| Worker | Cloudflare Workers (JavaScript ES Modules) v1.3.0 |
| Mini App | React 18 + Vite 5 (labels associados, headings semânticos, foco por aba, `focus-visible` em todos os controles, `prefers-reduced-motion`) |
| Banco | Supabase (PostgreSQL + PostgREST) |
| Deploy bot | Oracle Linux, systemd, GitHub Actions |
| Deploy Worker | Wrangler CLI |
| Deploy Mini App | Cloudflare Pages (CI automático via GitHub) |

---

## Provedores de IA

O bot seleciona a carta do dia e gera mensagens de abertura/encerramento usando IA. Provedores suportados:

| Provedor | Modelos | Variável |
|---|---|---|
| Google Gemini | `gemini-2.5-flash` ★, `gemini-2.0-flash`, `gemini-2.5-pro` | `GEMINI_API_KEY` |
| OpenAI | `gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`, `gpt-4.1` | `OPENAI_API_KEY` |
| Groq | `llama-3.3-70b-versatile` ★, `llama-3.1-8b-instant` | `GROQ_API_KEY` |
| Mistral | `mistral-small-latest`, `mistral-medium-latest` | `MISTRAL_API_KEY` |

★ = padrão do provedor. Basta ter a chave de um único provedor.

---

## Estrutura do Repositório

```
.
├── main.py                        # Entrada principal do bot
├── src/arkham_bot/
│   ├── core/                      # Config, logging, permissões, Supabase client
│   ├── clients/                   # ArkhamDB API
│   ├── formatters/                # HTML para Telegram
│   ├── handlers/                  # Comandos Telegram + command worker
│   │   ├── common.py              # Utilitários compartilhados e caches
│   │   ├── registry.py            # Registro de todos os handlers
│   │   ├── status_handler.py      # /start, /status
│   │   ├── card_handler.py        # /card
│   │   ├── search_handler.py      # /search
│   │   ├── sets_handler.py        # /sets
│   │   ├── taboo_handler.py       # /taboo
│   │   ├── faq_handler.py         # /faq
│   │   ├── decklist_handler.py    # /decklist
│   │   ├── cotd_handler.py        # /cotd
│   │   └── command_worker.py      # Consumer da fila de comandos
│   ├── repositories/              # Acesso às tabelas Supabase
│   ├── services/                  # Scheduler, daily_card, heartbeat, IA
│   ├── ai/                        # Seletor de carta por IA (4 provedores)
│   └── i18n/                      # Strings PT-BR e EN
├── worker/src/                    # Cloudflare Worker (index.js: dispatch; módulos: http, supabase, auth, validation, audit, handlers/*)
├── miniapp/src/                   # React Mini App
├── scripts/                       # healthcheck.py, sync_arkhamdb.py
├── supabase/migrations/           # 8 migrations SQL em ordem cronológica
├── deploy/systemd/                # arkham-bot.service
└── .github/workflows/             # CI (test.yml) + CD (deploy-oracle.yml)
```

---

## Documentação

- **[docs/technical.md](docs/technical.md)** — Arquitetura detalhada, tabelas Supabase, Worker endpoints, fluxos
- **[docs/operations.md](docs/operations.md)** — Deploy, variáveis de ambiente, troubleshooting, backup
- **[docs/PENDENCIAS.md](docs/PENDENCIAS.md)** — Itens pendentes priorizados
- **[SECURITY.md](SECURITY.md)** — Modelo de segurança e práticas adotadas
- **[CHANGELOG.md](CHANGELOG.md)** — Histórico de versões

---

## Quick Start

```bash
# 1. Clone e instale dependências
git clone https://github.com/allanlopesprado/arkham-bot
cd arkham-bot
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .

# 2. Configure variáveis
cp .env.example .env
# edite .env com TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

# 3. Valide
python main.py healthcheck

# 4. Execute
python main.py interactive
```

---

## Versões

| Componente | Versão |
|---|---|
| Bot Python | 0.1.0 |
| Worker | 1.3.0 |
| Mini App | 1.5.1 |
| Testes automatizados | 54 (pytest) + 10 (worker) |
