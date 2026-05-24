# ARKHAM BOT — EXECUTION PLAN COMPLETO E OPERACIONAL

Arquivo principal para IA do VSCode/Cline/Copilot.

Local recomendado no projeto:

```txt
docs/ARKHAM_BOT_EXECUTION_PLAN.md
```

Arquivo complementar obrigatório:

```txt
docs/FIX_BOT.md
```

Este documento consolida todo o planejamento, decisões arquiteturais, fases concluídas, checkpoints, fases futuras, critérios de aceite, comandos de teste, regras de segurança e prompts operacionais para o projeto Arkham Horror LCG Telegram Bot.

Este arquivo foi refeito para ser lido diretamente por uma IA de desenvolvimento. Portanto, as instruções são técnicas, diretas e executáveis.

---

# 0. REGRA ABSOLUTA PARA A IA

A IA deve obedecer a estas regras em qualquer execução:

```txt
1. Leia integralmente docs/ARKHAM_BOT_EXECUTION_PLAN.md.
2. Leia integralmente docs/FIX_BOT.md.
3. Execute somente a fase ou fix explicitamente solicitado no prompt.
4. Não execute fases futuras automaticamente.
5. Não execute múltiplas fases/fixes no mesmo passo, salvo se o prompt autorizar explicitamente.
6. Não misture refatoração, feature, limpeza e migration no mesmo passo.
7. Preserve o comportamento público atual do bot.
8. Não altere comandos Telegram existentes sem autorização explícita.
9. Não altere mensagens públicas sem necessidade técnica.
10. Não implemente Supabase, IA, Mini App, OAuth, systemd ou deploy antes da fase correta.
11. Não aplique migration no Supabase remoto sem autorização explícita.
12. Não crie mocks falsos, fallbacks falsos, código morto ou dívida técnica.
13. Não exponha secrets.
14. Não coloque TELEGRAM_BOT_TOKEN, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY ou qualquer secret em Git.
15. Se houver bloqueio real, pare e documente o bloqueio.
```

Se o prompt não informar fase/fix, responder:

```txt
ERRO:
- Causa: nenhuma fase ou fix foi especificado.
- Próximo passo: informe exatamente qual fase ou fix executar.
```

Formato obrigatório ao concluir fase/fix:

```txt
RESULTADO:
- Execução: [Fase/Fix executado]
- Arquivos alterados:
- O que foi feito:
- Testes executados:
- Pendências restantes:
- Status: concluída / bloqueada
```

---

# 1. ESTADO ATUAL DO PROJETO

## 1.1 Estado funcional validado

O projeto atual já passou por refatoração significativa e está em layout modular.

Estado validado até agora:

```txt
Pré-Fase 8: concluída
Fase 8: concluída
ArkhamDB Resource Review: concluído
Validação pós-Fase 8: concluída pela IA local
Documentação antiga: consolidada parcialmente
Próximo passo técnico recomendado: executar fixes críticos antes de aplicar Supabase remoto
```

## 1.2 Estrutura atual esperada

Estrutura de referência:

```txt
.
├─ .env.example
├─ .gitignore
├─ arkham_daily_card_bot.py
├─ main.py
├─ requirements.txt
├─ data/
│  └─ arkhamdb_samples/
├─ docs/
│  ├─ ARKHAM_BOT_EXECUTION_PLAN.md
│  └─ FIX_BOT.md
├─ scripts/
│  ├─ inspect_arkhamdb_api.py
│  └─ sync_arkhamdb.py
├─ src/
│  └─ arkham_bot/
│     ├─ __init__.py
│     ├─ arkhamdb_client.py
│     ├─ arkhamdb_models.py
│     ├─ card_provider.py
│     ├─ config.py
│     ├─ daily_card.py
│     ├─ local_storage.py
│     ├─ logging_config.py
│     ├─ rate_limit.py
│     ├─ scheduler.py
│     ├─ supabase_client.py
│     ├─ telegram_handlers.py
│     ├─ text_formatters.py
│     └─ repositories/
│        ├─ __init__.py
│        ├─ admins_repo.py
│        ├─ audit_repo.py
│        ├─ cards_repo.py
│        ├─ commands_repo.py
│        ├─ errors_repo.py
│        ├─ history_repo.py
│        └─ settings_repo.py
└─ supabase/
   └─ migrations/
      └─ 202605240001_initial_schema.sql
```

## 1.3 Artefatos que não devem estar versionados

Estes arquivos/diretórios não devem entrar no ZIP final nem no Git:

```txt
__pycache__/
*.pyc
*.log
debug_logs/
backups/local/
posted_cards.txt
posted_cards.txt.lock
card_cache.json
card_cache.json.lock
main_process.lock
.env
.env.local
.env.production
venv/
```

Se aparecerem, executar `FIX-002`.

---

# 2. DECISÕES ARQUITETURAIS FECHADAS

## 2.1 Backend

```txt
Python continua como backend principal.
```

Motivo:

```txt
- O bot já existe e funciona.
- Python é adequado para Telegram, jobs, integração ArkhamDB, scripts e IA futura.
- Reescrever em Node/Next agora seria troca de stack sem ganho proporcional.
```

## 2.2 Telegram

```txt
Modo principal: long polling.
Webhook: não usar agora.
Reverse proxy: não usar agora.
```

Regras:

```txt
- O bot roda como processo persistente na Oracle VM.
- O Telegram não precisa chamar endpoint HTTP público.
- Não expor porta pública apenas para o bot.
```

## 2.3 Scheduler

```txt
Scheduler da carta diária: interno dentro do modo interactive.
```

Proibido agora:

```txt
- cron separado
- systemd timer separado
- webhook
```

Configuração base:

```json
{
  "daily_post_enabled": true,
  "daily_post_times": ["08:00"],
  "daily_post_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
  "timezone": "America/Sao_Paulo",
  "daily_scheduler_mode": "internal_bot_loop"
}
```

## 2.4 Pin/unpin da carta diária

Regra de produto:

```txt
1. Postar nova carta diária.
2. Desafixar a carta diária anterior fixada pelo bot.
3. Fixar a nova carta.
4. Salvar telegram_message_id da nova carta.
5. Se unpin/pin falhar por permissão, registrar warning/erro e continuar sem derrubar o bot.
```

Configuração:

```json
{
  "pin_daily_card": true,
  "unpin_previous_daily_card": true,
  "pin_disable_notification": true,
  "pin_mode": "configurable"
}
```

## 2.5 Supabase

Supabase será usado para:

```txt
- cache ArkhamDB
- histórico
- logs
- configs
- fila
- bot_commands
- admins
- auditoria
- fallback
- dados para Mini App
```

Regra crítica:

```txt
SUPABASE_SERVICE_ROLE_KEY somente no backend Python/Oracle.
Frontend/Mini App nunca recebe service role.
Frontend usa anon/publishable key com RLS.
```

## 2.6 Mini App

Stack futura:

```txt
React + Vite + Cloudflare Pages
```

Regra:

```txt
Mini App insere comandos em bot_commands.
Bot Python valida e executa.
Ações críticas não são executadas diretamente pelo frontend.
```

Workers:

```txt
Cloudflare Workers não são obrigatórios no início.
Entram apenas se for necessário validar Telegram initData server-side ou intermediar ações sensíveis.
```

## 2.7 IA

Configuração padrão:

```json
{
  "ai_daily_card_enabled": false
}
```

Regras:

```txt
- IA desligada por padrão.
- Ativável no painel.
- Python valida qualquer resposta da IA.
- IA só pode escolher entre cartas candidatas já filtradas.
- IA não pode inventar regra, lore, FAQ, taboo, combo ou popularidade.
```

## 2.8 ArkhamDB OAuth

```txt
Collection e Deck autenticados são fase futura.
Não implementar OAuth antes de segurança, admins, Mini App e storage seguro.
```

---

# 3. REFERÊNCIAS OFICIAIS

A IA deve consultar estas referências quando alterar partes relacionadas.

## 3.1 ArkhamDB API

```txt
https://arkhamdb.com/api/doc
https://arkhamdb.com/api/doc#section-Card
https://arkhamdb.com/api/doc#section-Collection
https://arkhamdb.com/api/doc#section-Deck
https://arkhamdb.com/api/doc#section-Decklist
https://arkhamdb.com/api/doc#section-Faction
https://arkhamdb.com/api/doc#section-Faq
https://arkhamdb.com/api/doc#section-Pack
https://arkhamdb.com/api/doc#section-Taboo
```

Recursos oficiais:

```txt
Card
Collection
Deck
Decklist
Faction
Faq
Pack
Taboo
```

## 3.2 Telegram Bot API

```txt
https://core.telegram.org/bots/api
```

Usar para:

```txt
sendMessage
sendPhoto
pinChatMessage
unpinChatMessage
InlineKeyboardMarkup
CallbackQuery
message_thread_id
getMe
permissões de grupo/canal
limites e erros Telegram
```

## 3.3 Telegram Mini Apps

```txt
https://core.telegram.org/bots/webapps
```

Regra crítica:

```txt
Não confiar apenas em initDataUnsafe.
Ações sensíveis exigem validação server-side.
```

## 3.4 python-telegram-bot

```txt
https://docs.python-telegram-bot.org/
```

Usar para:

```txt
ApplicationBuilder
run_polling
JobQueue se aplicável
handlers
callback queries
RetryAfter
lifecycle/shutdown
```

## 3.5 Supabase

```txt
https://supabase.com/docs
https://supabase.com/docs/guides/database/postgres/row-level-security
https://supabase.com/docs/guides/getting-started/api-keys
https://supabase.com/docs/guides/database/secure-data
https://supabase.com/docs/guides/deployment/database-migrations
https://supabase.com/docs/guides/local-development
```

## 3.6 Cloudflare Pages

```txt
https://developers.cloudflare.com/pages/
https://developers.cloudflare.com/pages/framework-guides/deploy-a-vite3-project/
https://developers.cloudflare.com/pages/configuration/git-integration/
```

## 3.7 GitHub Actions

```txt
https://docs.github.com/actions
https://docs.github.com/actions/security-guides/using-secrets-in-github-actions
```

## 3.8 systemd

```txt
https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
https://man7.org/linux/man-pages/man5/systemd.unit.5.html
```

---

# 4. ARKHAMDB — MATRIZ OFICIAL

A matriz ArkhamDB deve ser tratada como fechada para o escopo público inicial.

| Recurso | Tipo | Implementar agora? | Endpoint/uso | Código permitido agora | Observação |
|---|---|---:|---|---|---|
| Card | Público | Sim | `/api/public/card/{card_code}`, `/api/public/cards/`, `/api/public/cards/?encounter=1` | Sim | Base das cartas |
| Pack | Público | Sim | `/api/public/packs/`, `/api/public/cards/{pack_code}` | Sim | Pacotes e cartas por pacote |
| Faction | Público | Sim | `/api/public/factions/` | Sim | Facções |
| Faq | Público | Sim | `/api/public/faq/{card_code}` | Sim | FAQ por carta |
| Taboo | Público | Sim | `/api/public/taboos/` | Sim | Listas taboo |
| Decklist | Público | Sim | `/api/public/decklist/{decklist_id}` | Sim | Decklist pública |
| Collection | OAuth/autenticado | Não | Recurso autenticado | Não | Fase futura OAuth |
| Deck | OAuth/autenticado | Não | Recurso autenticado | Não | Fase futura OAuth; não confundir com Decklist pública |

Regras:

```txt
- `arkhamdb_client.py` centraliza chamadas ArkhamDB.
- `arkhamdb_models.py` valida payloads públicos.
- Nenhum módulo fora de `arkhamdb_client.py` deve fazer request direto para ArkhamDB.
- Collection e Deck autenticados não devem ser implementados antes da fase OAuth.
```

---

# 5. FASES — STATUS GERAL

## 5.1 Fases concluídas/validadas

```txt
Fase 0  — Preparação inicial: concluída historicamente
Fase 1  — Encoding: concluída
Fase 2  — Extração de text_formatters: concluída
Fase 3  — Extração de config: concluída
Fase 4  — Extração de logging_config: concluída
Fase 5  — Extração ArkhamDB client: concluída
Fase 5.1 — Validação JSON ArkhamDB: concluída
Fase 6  — Extração local_storage: concluída
Fase 7  — Extração daily_card: concluída
Fase 7.1 — Reorganização src/arkham_bot e nomes: concluída
Fase 8  — telegram_handlers: concluída
Checkpoint ArkhamDB Resource Review: concluído
Validação pós-Fase 8: concluída por relatório local da IA
```

## 5.2 Fases criadas, mas ainda exigem hardening

```txt
Fase 9  — main.py: criado; precisa continuar validando em ambiente com deps
Fase 10 — scheduler.py: criado; precisa FIX-004 antes de produção
Fase 11 — rate_limit.py: criado; admin exemption real depende de Fase 17
Fase 12 — Supabase schema: migration criada; precisa FIX-003 antes de aplicar remoto
Fase 13 — Supabase client/repositories: criados; conexão real ainda não testada
Fase 14 — sync ArkhamDB: script criado; precisa completar upsert de packs/factions/taboos/FAQ
```

## 5.3 Fases futuras não concluídas

```txt
Fase 15 — Supabase fallback/cache completo
Fase 16 — bot_commands executor
Fase 17 — Admins/permissões
Fase 18 — Comandos públicos completos
Fase 19 — FAQ/Taboo/Decklist no bot
Fase 20 — IA da carta diária
Fase 21 — Healthcheck CLI real
Fase 22 — systemd arkham-bot
Fase 23 — GitHub Actions deploy
Fase 24 — Mini App React/Vite
Fase 25 — Backups automatizados
Fase 26 — OAuth ArkhamDB
```

---

# 6. ORDEM RECOMENDADA DAQUI PARA FRENTE

Executar nesta ordem:

```txt
1. FIX-003 — Hardening migration Supabase
2. FIX-004 — Segurança scheduler/daily_card
3. FIX-005 — Unpin carta anterior
4. FIX-006 — Normalizar paths data/logs
5. Fase 12 — Aplicar/validar Supabase schema
6. Fase 13 — Testar Supabase client/repositories com conexão real
7. Fase 14 — Completar sync ArkhamDB
8. Fase 15 — Supabase fallback/cache
9. Fase 16 — bot_commands executor
10. Fase 17 — Admins/permissões
11. Fase 18 — Comandos públicos completos
12. Fase 19 — FAQ/Taboo/Decklist
13. Fase 20 — IA
14. Fase 21 — Healthcheck CLI
15. FIX-007 — Package layout/imports, antes de CI/deploy
16. Fase 22 — systemd
17. Fase 23 — GitHub Actions
18. Fase 24 — Mini App
19. Fase 25 — Backups
20. Fase 26 — OAuth ArkhamDB
```

---

# 7. FASES DETALHADAS

## Fase 9 — Entry point `main.py`

### Status

```txt
Criado, mas deve ser mantido sob validação.
```

### Objetivo

Ter entrypoint limpo para:

```bash
python main.py
python main.py interactive
python main.py --help
python main.py healthcheck
```

### Requisitos

```txt
1. `main.py` deve ser fino.
2. Deve delegar lógica para módulos.
3. Não deve conter lógica de Telegram handler.
4. Não deve conter lógica ArkhamDB.
5. Deve manter wrapper `arkham_daily_card_bot.py`.
```

### Critérios de aceite

```txt
[ ] python main.py --help funciona.
[ ] python main.py interactive sobe o bot.
[ ] python main.py executa postagem única.
[ ] arkham_daily_card_bot.py continua compatível.
[ ] Nenhum secret é impresso.
```

### Testes

```bash
python -m compileall -q .
python main.py --help
python arkham_daily_card_bot.py --help
```

---

## Fase 10 — Scheduler interno

### Status

```txt
Criado, mas precisa FIX-004 antes de produção.
```

### Objetivo

Rodar carta diária dentro do processo interactive.

### Regras

```txt
1. Usar timezone America/Sao_Paulo.
2. Postar às 08:00 por padrão.
3. Não postar duplicado no mesmo dia.
4. Não bloquear comandos Telegram.
5. Não derrubar bot se a postagem falhar.
6. Registrar sucesso/falha.
```

### Bloqueio atual

```txt
daily_card.py ainda pode conter sys.exit(1) em fluxo usado pelo scheduler.
Executar FIX-004.
```

---

## Fase 11 — Rate limit

### Status

```txt
Criado baseline.
```

Configuração padrão:

```json
{
  "public_commands_rate_limit_enabled": true,
  "rate_limit_per_user": {
    "max_requests": 10,
    "window_seconds": 60
  },
  "rate_limit_per_chat": {
    "max_requests": 60,
    "window_seconds": 60
  },
  "rate_limit_exempt_admins": true
}
```

Pendência:

```txt
Admin exemption depende de admins/permissões reais.
```

---

## Fase 12 — Supabase schema

### Status

```txt
Migration criada, mas não aplicar remoto antes do FIX-003.
```

### Objetivo

Criar schema inicial Supabase.

### Tabelas obrigatórias

```txt
arkham_cards
arkham_packs
arkham_factions
arkham_faq
arkham_taboos
arkham_decklists_cache
bot_settings
target_chats
bot_admins
bot_commands
bot_posted_cards
bot_posting_history
bot_errors
audit_logs
```

### Requisitos obrigatórios

```txt
1. raw jsonb nas tabelas ArkhamDB.
2. created_at e updated_at onde aplicável.
3. índices básicos.
4. RLS habilitado.
5. CHECK constraints para enums críticos.
6. Não criar policy aberta.
7. Documentar policies futuras.
8. Não usar secrets no SQL.
```

### Pré-requisito

```txt
FIX-003 concluído.
```

### Testes

```bash
python -m compileall -q .
supabase db lint
supabase db reset
```

Se CLI Supabase não existir:

```txt
bloqueio parcial documentado
```

### Resposta esperada

```txt
RESULTADO:
- Execução: Fase 12 — Supabase schema
- Arquivos alterados:
- Tabelas revisadas:
- Constraints:
- RLS:
- Testes executados:
- Pendências:
- Status: concluída / bloqueada
```

---

## Fase 13 — Supabase client/repositories

### Status

```txt
Criados, conexão real ainda não testada.
```

### Objetivo

Usar Supabase service role no backend Python.

### Arquivos

```txt
src/arkham_bot/supabase_client.py
src/arkham_bot/repositories/
```

### Regras

```txt
1. SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY vêm do .env.
2. Não imprimir service role.
3. Se Supabase não estiver configurado, erro deve ser claro.
4. Repositories devem separar responsabilidades.
5. Não acoplar handlers Telegram direto ao Supabase sem camada de serviço.
```

### Testes

```bash
python -m compileall -q .
python - <<'PY'
from arkham_bot.supabase_client import get_supabase_client
print("import ok")
PY
```

Com credenciais reais:

```bash
python scripts/healthcheck.py
```

quando existir.

---

## Fase 14 — Sync ArkhamDB para Supabase

### Status

```txt
Script criado, mas precisa completar upserts além de cards.
```

### Objetivo

Popular Supabase com dados ArkhamDB.

### Deve sincronizar

```txt
cards player
cards encounter
packs
factions
taboos
faq
decklist cache sob demanda
```

### Regras

```txt
1. Usar arkhamdb_client.py.
2. Validar payload com arkhamdb_models.py.
3. Preservar raw jsonb.
4. Upsert idempotente.
5. Não apagar cache em falha.
6. Registrar audit/log.
7. Dry-run deve existir.
```

### Testes

```bash
python scripts/sync_arkhamdb.py --dry-run
```

---

## Fase 15 — Supabase fallback/cache no bot

### Objetivo

Fluxo:

```txt
1. Tentar ArkhamDB.
2. Se funcionar, usar e opcionalmente atualizar Supabase.
3. Se ArkhamDB falhar, tentar Supabase cache.
4. Se cache existir, usar com marcação de origem.
5. Se cache não existir, avisar admin e registrar erro.
```

### Arquivo central

```txt
src/arkham_bot/card_provider.py
```

### Regras

```txt
Não esconder falha real.
Não retornar stale sem marcar origem.
Não apagar cache por falha.
```

---

## Fase 16 — bot_commands executor

### Objetivo

Permitir que Mini App/painel crie comandos em Supabase e o bot execute.

### Fluxo

```txt
pending -> processing -> executed
pending -> processing -> retrying -> failed
```

### Configuração padrão

```json
{
  "bot_commands_polling_enabled": true,
  "bot_commands_polling_interval_seconds": 30,
  "bot_commands_batch_size": 10,
  "bot_commands_retry_enabled": true,
  "bot_commands_max_retries": 3,
  "bot_commands_retry_delay_seconds": 60
}
```

### Comandos iniciais

```txt
post_now
repost_card
skip_card
pause_daily_post
resume_daily_post
sync_arkhamdb
clear_queue
reset_cycle
update_setting
```

### Proibido

```txt
eval
exec
payload arbitrário
ação crítica sem validação
```

---

## Fase 17 — Admins/permissões

### Roles

```txt
owner
admin
viewer
```

### Regras

```txt
1. Começar com owner.
2. Admins por Telegram user_id.
3. Owner adiciona/remove admins.
4. Toda ação admin audita.
5. Admin bypassa anti-spoiler.
```

### Comandos futuros

```txt
/admin
/admin_status
/post
/repost
/skip
/queue
/sync
/reset_cycle
/pause
/resume
/errors
/settings
/add_admin
/remove_admin
```

---

## Fase 18 — Comandos públicos completos

### Comandos alvo

```txt
/menu
/help
/status
/card
/search
/random
/today
/faq
/taboo
/decklist
/filter
/pack
/faction
/type
/xp
```

### Regras de resposta

```txt
Até 5 resultados: grupo com botões.
Mais de 5 resultados: privado.
Se privado indisponível: orientar usuário a enviar /start no bot.
```

---

## Fase 19 — FAQ/Taboo/Decklist

### FAQ/Taboo

```txt
Botões abaixo da carta.
Resposta separada se houver conteúdo.
Aviso curto se não houver.
Nunca inventar.
```

### Decklist

```txt
Aceitar ID ou link ArkhamDB.
Resumo no grupo.
Detalhe no privado se longo.
Cache Supabase.
```

---

## Fase 20 — IA da carta diária

### Estado padrão

```txt
Desligada.
```

### JSON esperado da IA

```json
{
  "selected_card_code": "01001",
  "pre_message": "texto curto",
  "post_question": "texto curto",
  "reason": "motivo interno"
}
```

### Validação obrigatória Python

```txt
selected_card_code precisa estar entre candidatas.
pre_message <= 280 caracteres.
post_question <= 220 caracteres.
Sem regra inventada.
Sem spoiler proibido.
Fallback se falhar.
```

---

## Fase 21 — Healthcheck CLI

### Comando alvo

```bash
python scripts/healthcheck.py
```

ou:

```bash
python main.py healthcheck
```

### Deve validar

```txt
.env
Telegram getMe
chat_id acessível
Supabase se configurado
logs
imports
settings
```

### Não imprimir secrets.

---

## Fase 22 — systemd

### Serviço

```txt
arkham-bot
```

Arquivo:

```txt
/etc/systemd/system/arkham-bot.service
```

Modelo:

```ini
[Unit]
Description=Arkham Horror LCG Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/arkham_bot
EnvironmentFile=/opt/arkham_bot/.env
ExecStart=/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py interactive
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

---

## Fase 23 — GitHub Actions deploy

### Fluxo

```txt
push main
-> tests
-> ssh oracle
-> git pull
-> install deps
-> healthcheck
-> restart systemd
-> healthcheck pós-restart
-> rollback se falhar
```

### Secrets GitHub Actions

```txt
ORACLE_HOST
ORACLE_USER
ORACLE_SSH_KEY
ORACLE_PROJECT_PATH
```

Não colocar no GitHub Actions:

```txt
TELEGRAM_BOT_TOKEN
SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY
```

Esses ficam na Oracle/Vault.

---

## Fase 24 — Mini App React/Vite

### Stack

```txt
React
Vite
Cloudflare Pages
Supabase anon/publishable key
```

### Abas

```txt
Dashboard
Settings
Cards
Queue
History
Errors/Logs
Admins
ArkhamDB Sync
FAQ
Taboo
Decklists
Audit Logs
```

### Regra crítica

```txt
Ações críticas entram em bot_commands.
Service role nunca no frontend.
Validar initData server-side antes de ações sensíveis.
```

---

## Fase 25 — Backups

### Regras

```txt
Backup diário.
Retenção local 30 dias.
Retenção Supabase Storage 90 dias.
Formatos .sql.gz e .json.gz.
Falha avisa admins.
```

---

## Fase 26 — OAuth ArkhamDB

### Escopo

```txt
Collection
Deck autenticado
Decks privados
Coleção do usuário
```

### Requisitos

```txt
OAuth seguro.
Tokens protegidos.
Usuário Telegram vinculado à conta ArkhamDB.
Revogação.
Sem token no frontend.
```

---

# 8. PROMPTS DIRETOS PARA A IA

## Prompt padrão

```txt
Leia integralmente:

docs/ARKHAM_BOT_EXECUTION_PLAN.md
docs/FIX_BOT.md

Execute somente:

[FASE OU FIX]

Não execute fases futuras.
Não execute outros fixes.
Não implemente funcionalidades fora do escopo.
Não aplique migration no Supabase remoto sem autorização explícita.
Não exponha secrets.
Ao finalizar, responda no formato RESULTADO definido no documento.
```

## Prompt recomendado agora

```txt
Leia integralmente:

docs/ARKHAM_BOT_EXECUTION_PLAN.md
docs/FIX_BOT.md

Execute somente:

FIX-003 — Hardening da migration Supabase antes de aplicar no remoto

Não execute outros fixes.
Não execute fases futuras.
Não aplique migration no Supabase remoto.
Não altere comandos Telegram.
Não altere comportamento público.
Não implemente feature nova.

Ao finalizar, responda no formato RESULTADO definido no FIX-003.
```

---

# 9. CONTAGEM DO PROJETO

Total de fases planejadas:

```txt
27 fases: Fase 0 até Fase 26
```

Fases concluídas/validadas:

```txt
12 blocos concluídos/validados:
Fase 0
Fase 1
Fase 2
Fase 3
Fase 4
Fase 5
Fase 5.1
Fase 6
Fase 7
Fase 7.1
Fase 8
Checkpoint ArkhamDB + validação pós-Fase 8
```

Fases restantes:

```txt
15 fases/blocos principais:
Fase 12 até Fase 26
```

Fixes pendentes:

```txt
FIX-003 a FIX-010
```

Fixes críticos antes de produção:

```txt
FIX-003
FIX-004
FIX-005
FIX-006
FIX-010
```

---

# 10. REGRA FINAL

Se houver conflito entre rapidez e segurança, escolher segurança.

Prioridade:

```txt
1. Preservar comportamento existente
2. Reduzir risco
3. Executar a fase correta
4. Só depois implementar feature nova
```
