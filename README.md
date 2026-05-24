# Arkham Bot — Documento Técnico Canônico

Este é o único documento operacional do projeto. Qualquer documentação antiga em `docs/`, `miniapp/README.md`, relatórios de auditoria, planos de execução, arquivos de fix, runbooks separados ou relatórios gerados por ferramentas foi removida para evitar contradições.

Toda IA que trabalhar neste repositório deve ler este `README.md` antes de agir. Não recrie documentação paralela sem autorização explícita.

---

## 1. Status real do projeto

Estado local atual:

```txt
Implementação local: concluída e validada
Final hardening: concluído
Documentação antiga: consolidada neste README.md
Documentação operacional ativa: somente este README.md
Testes locais esperados: 21 passed
Healthcheck sem .env real: passa em modo normal com warnings
Healthcheck --strict sem .env real: falha corretamente
Supabase remoto: não aplicado
Telegram real: não testado
Oracle/systemd real: não instalado/executado
Cloudflare Pages/Worker real: não publicado
GitHub Actions remoto: não validado em ambiente real
ArkhamDB OAuth real: não implementado; apenas stub/fase futura
```

O projeto está pronto para versionamento e para a próxima fase de validação real de ambiente, desde que nenhuma pendência local reapareça em `git status` ou nos testes.

---

## 2. O que estava errado na documentação anterior

A auditoria final identificou os seguintes problemas no ZIP recebido:

```txt
1. Havia múltiplos arquivos .md com instruções concorrentes.
2. README.md estava antigo e mandava executar FIX-003 como próximo passo, embora os hardenings posteriores já tivessem sido aplicados.
3. docs/ARKHAM_BOT_EXECUTION_PLAN.md e docs/FIX_BOT.md ainda continham fases/fixes históricos que poderiam reabrir trabalho já concluído.
4. docs/IMPLEMENTATION_STATUS.md e outros documentos misturavam estado real, estado histórico e próximos passos.
5. miniapp/README.md criava uma segunda fonte de verdade para o Mini App.
6. data/arkhamdb_samples/schema_report.md era relatório técnico útil historicamente, mas não deve competir com documentação operacional.
7. O ZIP continha venv/ e artefatos locais, o que nunca deve ir para Git ou para pacote final.
8. .gitignore estava incompleto para node_modules, dist, build, .idea, .vscode, *.zip e *.egg-info.
9. GitHub Actions instalava requirements-dev.txt, mas não instalava requirements.txt em linha explícita antes, o que contrariava o padrão final definido.
```

Correção aplicada neste pacote:

```txt
- Todos os arquivos .md antigos foram removidos.
- Este README.md foi recriado como documento técnico canônico único.
- venv/ foi removido do pacote.
- Caches, logs, zip antigo e metadados locais foram removidos.
- .gitignore foi ampliado.
- GitHub Actions foi ajustado para instalar requirements.txt e requirements-dev.txt explicitamente e usar python -m pytest -q.
```

---

## 3. Regra absoluta para qualquer IA

A IA deve obedecer a estas regras:

```txt
1. Ler somente este README.md como fonte operacional principal.
2. Não procurar documentação antiga removida.
3. Não recriar docs/ com planos antigos, FIX_BOT ou execution plans sem autorização explícita.
4. Não alterar código se a tarefa for apenas documentação, Git ou validação.
5. Não alterar migrations sem autorização explícita.
6. Não aplicar migrations no Supabase remoto sem autorização explícita.
7. Não chamar Telegram real sem .env configurado e autorização explícita.
8. Não publicar Cloudflare Pages/Worker sem autorização explícita.
9. Não executar systemctl/systemd real sem autorização explícita.
10. Não fazer push direto na main.
11. Não expor secrets.
12. Não transformar erro real em warning apenas para passar teste.
13. Não remover validações de segurança.
14. Não tratar OAuth ArkhamDB como pronto.
15. Não usar pytest -q direto; usar python -m pytest -q.
16. Não instalar apenas requirements.txt em ambiente de desenvolvimento; instalar também requirements-dev.txt.
17. Não usar service_role no frontend.
18. Não usar CORS * em produção.
19. Não ler bot_settings via anon key se isso expuser configuração interna.
20. Se houver bloqueio por credencial ou serviço real, marcar como bloqueado por ambiente real.
```

---

## 4. Arquitetura final

Visão geral:

```txt
Telegram Bot Long Polling
        |
        v
Python backend em Oracle VM
        |
        +--> ArkhamDB API pública via arkhamdb_client.py
        +--> Supabase REST via supabase_client.py e repositories/
        +--> Scheduler interno para carta diária
        +--> bot_commands_worker para comandos enfileirados
        +--> Logs e fallback local em data/ e logs/

Mini App React/Vite
        |
        +--> Supabase anon key somente para tabelas públicas ArkhamDB
        +--> Cloudflare Worker para comandos críticos

Cloudflare Worker
        |
        +--> valida Telegram initData
        +--> usa SUPABASE_SERVICE_ROLE_KEY no backend do Worker
        +--> insere comandos em bot_commands
```

Decisões finais:

```txt
Backend principal: Python
Execução do bot: Oracle VM
Modo Telegram: long polling
Reverse proxy: não obrigatório agora
Docker: não obrigatório agora
Scheduler: interno no modo interactive
Horário padrão: 08:00 America/Sao_Paulo
Dias padrão: todos os dias
Banco/cache/fila/logs: Supabase
Mini App: React + Vite
Hospedagem futura do Mini App: Cloudflare Pages
Backend seguro do Mini App: Cloudflare Worker
IA: opcional, desligada por padrão
OAuth ArkhamDB: fase futura/stub
```

---

## 5. Estrutura esperada do projeto

Estrutura de alto nível:

```txt
.
├── .env.example
├── .github/workflows/deploy.yml
├── .gitignore
├── README.md
├── arkham_daily_card_bot.py
├── deploy/systemd/arkham-bot.service
├── main.py
├── miniapp/
├── pyproject.toml
├── requirements-dev.txt
├── requirements.txt
├── scripts/
├── src/arkham_bot/
├── supabase/migrations/
├── tests/
└── worker/
```

Arquivos e diretórios que não devem estar no Git:

```txt
.env
.env.* exceto .env.example
venv/
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.log
logs/
debug_logs/
backups/
*.zip
*.egg-info/
node_modules/
dist/
build/
.vscode/
.idea/
```

---

## 6. Entrypoints e modos de execução

### `main.py`

É o entrypoint principal.

Comandos:

```powershell
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
python main.py interactive
python main.py 01001
python main.py
```

Comportamento:

```txt
python main.py --help
- imprime uso básico
- não exige Telegram
- deve retornar exit code 0

python main.py healthcheck
- executa validação local não estrita
- sem .env real deve retornar exit code 0 com warnings

python main.py healthcheck --strict
- exige TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY
- sem .env real deve retornar exit code diferente de 0

python main.py interactive
- inicia bot Telegram em long polling
- exige TELEGRAM_BOT_TOKEN
- registra handlers
- inicia scheduler interno no post_init

python main.py 01001
- tenta postar carta específica
- exige env Telegram real
```

### `arkham_daily_card_bot.py`

Wrapper de compatibilidade legado. Deve encaminhar para `main.py`. Não deve conter lógica própria relevante.

---

## 7. Variáveis de ambiente

Arquivo exemplo: `.env.example`.

Variáveis principais:

```env
ENVIRONMENT=development
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TIMEZONE=America/Sao_Paulo
DAILY_POST_ENABLED=true
DAILY_POST_TIMES=08:00
DAILY_POST_DAYS=mon,tue,wed,thu,fri,sat,sun
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
REQUEST_TIMEOUT_SECONDS=15
BOT_COMMANDS_POLLING_ENABLED=true
BOT_COMMANDS_POLLING_INTERVAL_SECONDS=30
BOT_COMMANDS_BATCH_SIZE=10
BOT_COMMANDS_MAX_RETRIES=3
BOT_COMMANDS_RETRY_DELAY_SECONDS=60
ARKHAMDB_SAMPLE_DECKLIST_ID=
ADMIN_TELEGRAM_USER_IDS=
AI_DAILY_CARD_ENABLED=false
AI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=
ARKHAMDB_OAUTH_CLIENT_ID=
ARKHAMDB_OAUTH_CLIENT_SECRET=
```

Regras:

```txt
- .env nunca deve ir para Git.
- SUPABASE_SERVICE_ROLE_KEY nunca deve ir para frontend.
- TELEGRAM_BOT_TOKEN nunca deve aparecer em logs, docs preenchidos ou commits.
- OPENAI_API_KEY só deve ser usada se AI_DAILY_CARD_ENABLED=true.
- OAuth ArkhamDB não deve ser exigido para rodar o bot.
```

---

## 8. Dependências

### Runtime: `requirements.txt`

```txt
python-telegram-bot
requests
python-dotenv
pillow
filelock
httpx
tenacity
tzdata
```

Notas:

```txt
- tzdata é runtime porque ZoneInfo("America/Sao_Paulo") precisa funcionar no Windows e em ambientes sem base IANA do sistema.
- pytest não deve ficar em requirements.txt.
```

### Desenvolvimento/testes: `requirements-dev.txt`

```txt
-r requirements.txt
pytest
```

### Empacotamento: `pyproject.toml`

Requisitos:

```txt
- build backend: setuptools
- package discovery: src/
- pacote: arkham-bot
- requires-python: >=3.11
- optional dev inclui pytest
- dependências alinhadas ao requirements.txt
```

---

## 9. Instalação local no Windows PowerShell

Use sempre PowerShell dentro da raiz do projeto.

```powershell
cd C:\Users\allan\Desktop\arkham-bot
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Confirmar Python do venv:

```powershell
python -c "import sys; print(sys.executable)"
```

Esperado:

```txt
C:\Users\allan\Desktop\arkham-bot\venv\Scripts\python.exe
```

---

## 10. Validação local obrigatória

Após qualquer alteração relevante:

```powershell
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
python main.py healthcheck --strict
```

Resultado esperado sem `.env` real:

```txt
python -m compileall -q .        -> exit code 0
python -m pytest -q              -> 21 passed
python main.py --help            -> exit code 0
python main.py healthcheck       -> exit code 0 com warnings
python main.py healthcheck --strict -> exit code diferente de 0
```

A falha do `healthcheck --strict` sem `.env` real é comportamento correto.

---

## 11. Testes automatizados

Diretório: `tests/`.

Cobertura atual esperada:

```txt
tests/test_arkhamdb_models.py
tests/test_commands_repo.py
tests/test_healthcheck_cli.py
tests/test_main_cli.py
tests/test_package_imports.py
tests/test_rate_limit.py
tests/test_scheduler_logic.py
tests/test_text_formatters.py
```

Características:

```txt
- Não chamam Telegram real.
- Não chamam Supabase real.
- Não chamam OpenAI real.
- Não chamam ArkhamDB real.
- Usam stubs quando telegram/tenacity não existem.
- Validam healthcheck strict/non-strict.
- Validam timezone America/Sao_Paulo com tzdata.
- Validam rate limit.
- Validam formatters.
- Validam models ArkhamDB.
- Validam commands_repo com fake client.
```

Nunca usar:

```powershell
pytest -q
```

Sempre usar:

```powershell
python -m pytest -q
```

---

## 12. Módulos Python principais

### `src/arkham_bot/config.py`

Responsável por:

```txt
- carregar .env
- definir paths data/logs
- definir env vars
- configurar scheduler
- configurar Telegram
- configurar Supabase
- configurar rate limit
- configurar bot_commands
- configurar IA opcional
- configurar OAuth ArkhamDB como variáveis futuras
```

Ponto crítico: `ensure_runtime_dirs()` cria `data/`, `logs/` e `logs/debug_logs/` em runtime. Esses diretórios não devem ser commitados se estiverem vazios ou com artefatos.

### `src/arkham_bot/arkhamdb_client.py`

Único local autorizado para chamadas HTTP diretas à ArkhamDB API pública.

Recursos públicos esperados:

```txt
Card: /api/public/card/{card_code}
Cards: /api/public/cards/
Encounter cards: /api/public/cards/?encounter=1
Pack: /api/public/packs/
Cards by pack: /api/public/cards/{pack_code}
Faction: /api/public/factions/
FAQ: /api/public/faq/{card_code}
Taboo: /api/public/taboos/
Decklist: /api/public/decklist/{decklist_id}
```

Regras:

```txt
- Não criar requests diretos à ArkhamDB em handlers, daily_card ou scripts fora do client.
- Usar timeout.
- Validar payloads em arkhamdb_models.py quando aplicável.
```

### `src/arkham_bot/arkhamdb_models.py`

Valida payloads mínimos:

```txt
validate_card_payload
validate_pack_payload
validate_faction_payload
validate_decklist_payload
```

Não deve tentar modelar todos os campos possíveis da ArkhamDB de forma rígida, porque a API pode variar por tipo de carta.

### `src/arkham_bot/daily_card.py`

Responsável por postar a carta diária.

Fluxo:

```txt
1. Validar TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.
2. Criar Bot.
3. Carregar cartas já postadas.
4. Buscar carta específica ou selecionar carta válida.
5. Usar IA opcional se AI_DAILY_CARD_ENABLED=true e OPENAI_API_KEY existir.
6. Baixar imagem.
7. Validar imagem com Pillow.
8. Enviar foto para Telegram.
9. Registrar carta postada.
10. Registrar histórico.
11. Se dupla face, postar verso quando houver conteúdo.
12. Tentar unpin da carta anterior e pin da nova.
13. Retornar DailyPostResult, nunca sys.exit.
```

Regras:

```txt
- Não derrubar o processo do bot com sys.exit.
- Falhas de pin/unpin devem virar warning/log, não falha fatal.
- Se Telegram real não estiver configurado, retornar erro controlado.
```

### `src/arkham_bot/scheduler.py`

Scheduler interno iniciado no modo `interactive`.

Configuração:

```txt
TIMEZONE=America/Sao_Paulo
DAILY_POST_TIMES=08:00
DAILY_POST_DAYS=mon,tue,wed,thu,fri,sat,sun
DAILY_POST_ENABLED=true
```

Regras:

```txt
- Não usar cron para a carta diária nesta fase.
- Não usar systemd timer separado nesta fase.
- Não postar duas vezes no mesmo horário/data.
- Usar arquivo local de estado como fallback.
- Pode ler settings do Supabase quando disponível.
```

### `src/arkham_bot/telegram_handlers.py`

Registra comandos Telegram.

Comandos públicos esperados:

```txt
/help
/menu
/status
/card
/today
/random
/faq
/taboo
/decklist
/search
/pack
/faction
/type
/xp
```

Comandos/admin helpers esperados podem incluir:

```txt
/admin
/admin_status
```

Regras:

```txt
- Rate limit deve proteger comandos públicos.
- Admins podem ter bypass conforme configuração.
- Não imprimir token ou secrets.
- Comandos básicos devem degradar com fallback quando Supabase estiver indisponível, se a lógica permitir.
```

### `src/arkham_bot/rate_limit.py`

Rate limit em memória.

Padrões:

```txt
10 comandos/min por usuário
60 comandos/min por chat/grupo
admins isentos quando RATE_LIMIT_EXEMPT_ADMINS=true
```

### `src/arkham_bot/bot_commands_worker.py`

Processa comandos enfileirados no Supabase.

Tipos permitidos:

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

Regras:

```txt
- Validar autorização admin para comandos criados por usuário.
- Comandos de sistema podem omitir actor.
- Usar retry com next_attempt_at.
- Separar payload original de result.
- Notificar admins quando falhar após max_attempts, se configurado.
```

### `src/arkham_bot/arkhamdb_oauth.py`

Status: stub/fase futura.

Regras:

```txt
- Não está integrado ao fluxo principal.
- Não deve bloquear runtime se env OAuth estiver ausente.
- Não armazena tokens.
- Não valida callback real.
- Não deve ser anunciado como pronto.
- Fase futura exige client_id, client_secret, callback seguro, storage seguro, revogação, auditoria e testes reais.
```

---

## 13. Supabase

Migrations:

```txt
supabase/migrations/202605240001_initial_schema.sql
supabase/migrations/202605240002_public_read_and_admin_policy_notes.sql
```

Tabelas principais:

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

Decisões de segurança:

```txt
- RLS habilitado nas tabelas.
- Policies públicas apenas para leitura de tabelas ArkhamDB não sensíveis.
- Sem escrita pública anon.
- bot_settings não deve ter leitura pública irrestrita.
- bot_commands não deve ser escrito diretamente pelo frontend com anon key.
- Worker usa service_role no backend para inserir comandos depois de validar Telegram initData.
- Python/Oracle usa service_role.
```

Constraints relevantes:

```txt
bot_commands.status in pending, processing, retrying, executed, failed, cancelled
bot_admins.role in owner, admin, viewer
audit_logs.source in telegram_command, telegram_button, mini_app, system_job, ai_process, github_deploy, manual_script
```

Campos importantes de `bot_commands`:

```txt
payload: entrada original do comando
result: saída/resultado do processamento
status: estado do comando
attempt_count: tentativas já feitas
max_attempts: limite de tentativas
next_attempt_at: próxima tentativa em caso de retry
last_error: último erro textual
```

Nunca aplicar migrations remotas sem autorização explícita.

---

## 14. Sync ArkhamDB

Script:

```txt
scripts/sync_arkhamdb.py
```

Uso local seguro:

```powershell
python scripts/sync_arkhamdb.py --dry-run
```

Uso real, somente com Supabase configurado:

```powershell
python scripts/sync_arkhamdb.py
```

Regras:

```txt
- Rodar dry-run antes de sync real.
- Sync real exige SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.
- Não chamar sync real em CI público sem secrets.
- Não commitar dados de runtime gerados.
```

---

## 15. Telegram

Variáveis exigidas para uso real:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ADMIN_TELEGRAM_USER_IDS=
```

Validação mínima real, depois de `.env` configurado:

```powershell
python main.py healthcheck --strict
python main.py interactive
```

Atenção:

```txt
- O bot usa long polling.
- Não usar webhook nesta fase.
- Não configurar reverse proxy agora.
- Não expor token em prints, logs, docs ou Git.
- Se token já foi exposto em conversa, revogar no BotFather e criar outro.
```

---

## 16. Mini App

Diretório:

```txt
miniapp/
```

Tecnologias:

```txt
React
Vite
Supabase JS anon key
Cloudflare Pages futuro
```

Variáveis frontend esperadas:

```env
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_COMMANDS_API_URL=
```

Regras:

```txt
- Não usar SUPABASE_SERVICE_ROLE_KEY no frontend.
- Não ler bot_settings diretamente via anon key se isso expuser configuração interna.
- Pode ler arkham_cards, arkham_packs, arkham_factions, arkham_faq, arkham_taboos e arkham_decklists_cache se as policies públicas estiverem aplicadas.
- Ações críticas devem passar pelo Worker.
- Build não deve depender de secrets.
```

Comandos de desenvolvimento:

```powershell
cd miniapp
npm install
npm run dev
npm run build
```

Esses comandos não foram executados nesta validação local final.

---

## 17. Cloudflare Worker

Diretório:

```txt
worker/
```

Endpoint principal:

```txt
POST /bot-command
```

Responsabilidades:

```txt
- Validar Telegram initData.
- Rejeitar initData ausente/inválido/expirado.
- Aplicar CORS por allowlist.
- Inserir comandos em bot_commands usando service_role no backend do Worker.
```

Variáveis/secrets esperados:

```txt
ALLOWED_ORIGINS
TELEGRAM_BOT_TOKEN
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

Regras de CORS:

```txt
- Não usar CORS * em produção.
- ALLOWED_ORIGINS deve conter domínios explícitos.
- Desenvolvimento local pode usar http://localhost:5173 e http://localhost:3000.
- Não usar credentials com wildcard.
```

Comandos futuros:

```powershell
cd worker
npm install
npx wrangler dev
npx wrangler deploy
```

Não publicar sem autorização explícita.

---

## 18. GitHub Actions

Workflow:

```txt
.github/workflows/deploy.yml
```

O job de teste deve executar:

```yaml
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
```

Regras:

```txt
- Não executar healthcheck --strict no job de teste sem secrets reais.
- Deploy real só em push para main, depois do job test.
- Deploy usa SSH para Oracle via secrets.
- Secrets não devem ser impressos.
- Rollback deve voltar para PREV_REV se healthcheck pós-restart falhar.
```

Secrets esperados para deploy real:

```txt
ORACLE_HOST
ORACLE_USER
ORACLE_SSH_KEY
ORACLE_PROJECT_PATH
```

Secrets de runtime do bot devem preferencialmente ficar no `.env` da Oracle, não no GitHub Actions, salvo decisão explícita.

---

## 19. Oracle/systemd

Template:

```txt
deploy/systemd/arkham-bot.service
```

Instalação futura na Oracle:

```bash
sudo cp deploy/systemd/arkham-bot.service /etc/systemd/system/arkham-bot.service
sudo systemctl daemon-reload
sudo systemctl enable arkham-bot
sudo systemctl start arkham-bot
sudo systemctl status arkham-bot
journalctl -u arkham-bot -f
```

Regras:

```txt
- WorkingDirectory esperado: /opt/arkham_bot
- ExecStart deve usar /opt/arkham_bot/venv/bin/python main.py interactive
- EnvironmentFile deve apontar para arquivo .env seguro fora do Git ou com permissões adequadas.
- Restart=always é esperado para manter o bot vivo.
- Não executar systemctl em ambiente local Windows.
```

---

## 20. Backup Supabase

Script:

```txt
scripts/backup_supabase.sh
```

Regras:

```txt
- Não hardcodar senha.
- Usar env vars.
- Não commitar dumps.
- Diretórios de backup local devem estar no .gitignore.
```

---

## 21. Segurança

Regras críticas:

```txt
- Nunca commitar .env.
- Nunca commitar venv.
- Nunca commitar ZIP final.
- Nunca commitar dumps de banco.
- Nunca expor TELEGRAM_BOT_TOKEN.
- Nunca expor SUPABASE_SERVICE_ROLE_KEY no frontend.
- Nunca expor OPENAI_API_KEY.
- Não usar CORS * em produção.
- Não liberar SELECT irrestrito em bot_settings para anon.
- Não liberar INSERT/UPDATE/DELETE anon em tabelas administrativas.
- Não confiar no Mini App para comandos críticos sem validação server-side.
- Não marcar integrações externas como concluídas sem teste real.
```

---

## 22. Fluxo Git recomendado

Antes de qualquer commit:

```powershell
git status
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
```

Criar branch:

```powershell
git checkout -b final-hardening-20260524
```

Conferir diff:

```powershell
git status
git diff --stat
```

Commit:

```powershell
git add .
git commit -m "Final hardening before production validation"
```

Push:

```powershell
git push -u origin final-hardening-20260524
```

Regras:

```txt
- Não fazer push direto na main.
- Abrir Pull Request.
- Aguardar GitHub Actions.
- Fazer merge na main somente após CI passar.
```

---

## 23. Pendências antes do Git

Após esta consolidação, as pendências antes do Git devem ser zero se os comandos abaixo passarem e `git status` não mostrar artefatos indevidos.

Checklist:

```txt
[ ] README.md é o único arquivo .md do repositório.
[ ] Não existe docs/ com documentação antiga.
[ ] Não existe miniapp/README.md.
[ ] Não existe data/arkhamdb_samples/schema_report.md.
[ ] Não existe venv/ no projeto a commitar.
[ ] Não existe .pytest_cache/.
[ ] Não existe __pycache__/.
[ ] Não existe *.pyc.
[ ] Não existe *.log.
[ ] Não existe *.zip.
[ ] .gitignore bloqueia artefatos principais.
[ ] Workflow instala requirements.txt e requirements-dev.txt explicitamente.
[ ] python -m compileall -q . passa.
[ ] python -m pytest -q passa com 21 passed.
[ ] python main.py --help passa.
[ ] python main.py healthcheck passa com warnings esperados sem .env.
```

---

## 24. Pendências depois do Git

Estas etapas dependem de ambiente real:

```txt
1. Configurar .env real.
2. Criar/configurar Supabase remoto.
3. Aplicar migrations no Supabase remoto.
4. Rodar sync ArkhamDB real.
5. Configurar Telegram real.
6. Testar getMe/chat real.
7. Testar python main.py healthcheck --strict com env real.
8. Testar python main.py interactive.
9. Testar comandos Telegram reais.
10. Testar postagem real de carta.
11. Testar pin/unpin real no grupo/canal.
12. Configurar Oracle VM.
13. Instalar systemd real.
14. Publicar Worker Cloudflare.
15. Publicar Mini App Cloudflare Pages.
16. Configurar GitHub Actions secrets.
17. Validar deploy real.
18. Decidir quando implementar OAuth ArkhamDB real.
```

---

## 25. Checklist para próxima IA

Antes de qualquer alteração:

```txt
1. Leia este README.md inteiro.
2. Identifique a tarefa exata.
3. Diga se a tarefa é local ou depende de ambiente real.
4. Não altere arquivos fora do escopo.
5. Não recrie documentação antiga.
6. Não rode serviços reais sem autorização.
7. Ao final, reporte arquivos alterados, testes executados e pendências reais.
```

Formato recomendado de resposta da IA:

```txt
RESULTADO:
- Execução:
- Arquivos alterados:
- Arquivos removidos:
- Testes executados:
- Resultado dos testes:
- Testes externos não executados:
- Pendências antes do Git:
- Pendências depois do Git:
- Status: concluída / bloqueada
```

---

## 26. Comando final de validação local

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m compileall -q .
python -m pytest -q
python main.py --help
python main.py healthcheck
```

Esperado:

```txt
compileall: OK
pytest: 21 passed
help: OK
healthcheck: OK com warnings se não houver .env real
```

---

## 27. Estado final deste pacote

Este pacote foi consolidado para que exista somente uma documentação técnica operacional: `README.md`.

O próximo passo recomendado é:

```txt
1. Extrair o ZIP.
2. Rodar validação local.
3. Conferir git status.
4. Criar branch.
5. Commitar.
6. Subir Pull Request.
7. Só depois iniciar validação real de Supabase, Telegram, Oracle, Cloudflare e GitHub Actions.
```
