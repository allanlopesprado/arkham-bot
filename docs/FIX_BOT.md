# FIX_BOT — CORREÇÕES OPERACIONAIS PENDENTES

Arquivo complementar ao plano mestre.

Local recomendado:

```txt
docs/FIX_BOT.md
```

Este arquivo lista fixes técnicos pendentes que devem ser executados antes de avançar para produção ou fases mais complexas.

A IA deve executar apenas o fix solicitado.

---

# 0. REGRA ABSOLUTA

A IA deve:

```txt
1. Ler docs/ARKHAM_BOT_EXECUTION_PLAN.md.
2. Ler docs/FIX_BOT.md.
3. Executar somente o FIX solicitado.
4. Não executar outros fixes.
5. Não executar fases futuras.
6. Não aplicar migration no Supabase remoto sem autorização explícita.
7. Não implementar feature nova dentro de fix.
8. Não alterar comportamento público fora do escopo.
9. Ao finalizar, responder no formato RESULTADO do fix.
```

---

# FIX-001 — Consolidar documentação

## Status

```txt
Concluído no pacote consolidado, mas deve ser mantido.
```

## Resultado esperado

```txt
docs/ARKHAM_BOT_EXECUTION_PLAN.md
docs/FIX_BOT.md
```

Documentos antigos podem ficar em `docs/archive/` ou serem removidos do ZIP final.

---

# FIX-002 — Limpar artefatos de runtime

## Status

```txt
Concluído no pacote consolidado, mas deve ser repetido antes de cada ZIP/commit.
```

## Comandos

```bash
rm -f bot_errors.log bot_execution.log posting_history.log
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf debug_logs
```

## Garantir no `.gitignore`

```gitignore
*.log
debug_logs/
backups/local/
__pycache__/
*.pyc
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

## Resposta obrigatória

```txt
RESULTADO:
- Execução: FIX-002 — Limpeza de artefatos
- Arquivos removidos:
- .gitignore validado:
- Testes executados:
- Status: concluída / bloqueada
```

---

# FIX-003 — Hardening da migration Supabase antes de aplicar no remoto

## Objetivo

Ajustar o schema Supabase local antes de criar tabelas no projeto Supabase real.

## Arquivos permitidos

```txt
supabase/migrations/202605240001_initial_schema.sql
src/arkham_bot/repositories/commands_repo.py
docs/ARKHAM_BOT_EXECUTION_PLAN.md
docs/FIX_BOT.md
```

## Problemas a corrigir

```txt
1. bot_commands.status precisa CHECK constraint.
2. bot_admins.role precisa CHECK constraint.
3. audit_logs.source precisa CHECK constraint.
4. bot_commands precisa coluna result jsonb.
5. commands_repo.mark_command_executed() deve gravar result, não sobrescrever payload.
6. RLS está habilitado, mas policies finais precisam ser documentadas como fase futura.
```

## Status permitidos para bot_commands

```txt
pending
processing
retrying
executed
failed
cancelled
```

## Roles permitidas para bot_admins

```txt
owner
admin
viewer
```

## Sources permitidos para audit_logs

```txt
telegram_command
telegram_button
mini_app
system_job
ai_process
github_deploy
manual_script
```

## Alterações SQL obrigatórias

Se a tabela for criada do zero, incluir constraints no `create table`.

Exemplo para `bot_commands`:

```sql
status text not null default 'pending'
  check (status in ('pending','processing','retrying','executed','failed','cancelled')),
result jsonb,
```

Exemplo para `bot_admins`:

```sql
role text not null default 'admin'
  check (role in ('owner','admin','viewer')),
```

Exemplo para `audit_logs`:

```sql
source text not null
  check (source in (
    'telegram_command',
    'telegram_button',
    'mini_app',
    'system_job',
    'ai_process',
    'github_deploy',
    'manual_script'
  )),
```

## Ajuste obrigatório em commands_repo.py

Se existir método:

```python
mark_command_executed(command_id, result)
```

Ele deve atualizar:

```txt
status = executed
executed_at = now
result = result
updated_at = now
```

Não deve sobrescrever:

```txt
payload
```

## RLS

Não criar policies abertas.

Adicionar comentário/documentação:

```txt
RLS está habilitado.
Policies finais para Mini App/admins serão definidas após autenticação/admins.
Backend Python usa service_role.
```

## Proibido

```txt
Não aplicar migration no Supabase remoto.
Não criar policies permissivas.
Não implementar Mini App.
Não implementar bot_commands executor.
Não alterar schema fora do necessário.
Não inserir secrets.
```

## Testes

```bash
python -m compileall -q .
```

Se Supabase CLI estiver disponível:

```bash
supabase db lint
supabase db reset
```

## Resposta obrigatória

```txt
RESULTADO:
- Execução: FIX-003 — Hardening Supabase migration
- Arquivos alterados:
- Constraints adicionadas:
- commands_repo ajustado:
- Testes executados:
- Pendências:
- Status: concluída / bloqueada
```

---

# FIX-004 — Segurança do scheduler/daily_card

## Objetivo

Impedir que falha na postagem diária derrube o bot interactive.

## Problema

`daily_card.py` pode conter `sys.exit(1)` dentro de `post_daily_card()`.

Isso era aceitável no modo cron antigo, mas é perigoso no scheduler interno.

## Arquivos permitidos

```txt
src/arkham_bot/daily_card.py
src/arkham_bot/scheduler.py
main.py
```

## Tarefas

```txt
1. Remover sys.exit() de dentro de daily_card.py.
2. Fazer post_daily_card retornar bool ou resultado estruturado.
3. main.py deve converter falha de execução única em exit code 1.
4. scheduler.py deve capturar falha sem encerrar processo.
5. Registrar erro em log.
6. Preservar comportamento público.
```

## Contrato recomendado

```python
@dataclass
class DailyPostResult:
    success: bool
    card_code: str | None = None
    message_id: int | None = None
    error: str | None = None
```

Se quiser menor alteração:

```python
async def post_daily_card(...) -> bool:
    ...
```

## Critérios de aceite

```txt
[ ] Nenhum sys.exit em daily_card.py.
[ ] python main.py retorna 1 se postagem única falhar.
[ ] scheduler não derruba bot.
[ ] Erro é logado.
[ ] python -m compileall -q . passa.
```

## Resposta obrigatória

```txt
RESULTADO:
- Execução: FIX-004 — Scheduler/daily_card safety
- Arquivos alterados:
- Contrato adotado:
- Testes executados:
- Pendências:
- Status: concluída / bloqueada
```

---

# FIX-005 — Unpin da carta anterior

## Objetivo

Implementar a regra já decidida:

```txt
Nova carta diária fixa substitui a anterior.
```

## Arquivos permitidos

```txt
src/arkham_bot/daily_card.py
src/arkham_bot/local_storage.py
src/arkham_bot/config.py
```

## Persistência local temporária

Enquanto Supabase não estiver ativo, usar:

```txt
data/last_pinned_daily_card.json
```

Estrutura sugerida:

```json
{
  "chat_id": "-100...",
  "message_id": 123,
  "card_code": "01001",
  "posted_date": "2026-05-24",
  "created_at": "2026-05-24T08:00:00-03:00"
}
```

## Fluxo

```txt
1. Ler último pinned salvo.
2. Se existir, tentar unpin.
3. Se unpin falhar, logar warning e continuar.
4. Postar/fixar nova carta.
5. Salvar novo message_id.
6. Não derrubar bot se unpin/pin falhar.
```

## Proibido

```txt
Não exigir Supabase para isso agora.
Não alterar texto da carta.
Não alterar comandos Telegram.
```

## Resposta obrigatória

```txt
RESULTADO:
- Execução: FIX-005 — Unpin previous daily card
- Arquivos alterados:
- Persistência criada:
- Testes executados:
- Pendências:
- Status: concluída / bloqueada
```

---

# FIX-006 — Normalizar paths de data/logs

## Objetivo

Mover arquivos operacionais para pastas próprias.

## Estado desejado

```txt
data/
  posted_cards.txt
  posted_cards.txt.lock
  card_cache.json
  card_cache.json.lock
  daily_scheduler_state.json
  last_pinned_daily_card.json

logs/
  posting_history.log
  bot_execution.log
  bot_errors.log
  debug_logs/
```

## Arquivos permitidos

```txt
src/arkham_bot/config.py
src/arkham_bot/logging_config.py
src/arkham_bot/local_storage.py
src/arkham_bot/scheduler.py
.gitignore
```

## Tarefas

```txt
1. Criar DATA_DIR.
2. Criar LOG_DIR.
3. Atualizar paths em config.py.
4. Garantir mkdir no bootstrap.
5. Preservar compatibilidade com arquivos antigos ou documentar migração.
6. Atualizar .gitignore.
```

## Atenção

Este fix muda paths. Executar isolado e testar.

## Resposta obrigatória

```txt
RESULTADO:
- Execução: FIX-006 — Normalize data/log paths
- Arquivos alterados:
- Paths antigos:
- Paths novos:
- Compatibilidade:
- Testes executados:
- Status: concluída / bloqueada
```

---

# FIX-007 — Package layout/imports

## Objetivo

Substituir imports do tipo:

```python
from arkham_bot...
```

por:

```python
from arkham_bot...
```

## Estado atual esperado

Imports `arkham_bot` foram substituídos por `arkham_bot` após package layout. Verificar apenas se regressão aparecer em:

```txt
main.py
scripts/inspect_arkhamdb_api.py
scripts/sync_arkhamdb.py
```

## Tarefas

```txt
1. Criar pyproject.toml.
2. Configurar src layout.
3. Permitir pip install -e .
4. Atualizar imports.
5. Garantir scripts funcionando.
```

## Não executar agora

Executar somente antes de CI/deploy, depois de estabilizar Supabase schema.

---

# FIX-008 — Completar sync ArkhamDB

## Objetivo

Completar `scripts/sync_arkhamdb.py`.

## Estado provável

Script já busca vários recursos, mas pode fazer upsert apenas de cards.

## Tarefas futuras

```txt
1. Upsert packs.
2. Upsert factions.
3. Upsert taboos.
4. Estratégia FAQ por card_code.
5. Audit log do sync.
6. Dry-run detalhado.
```

Executar dentro da Fase 14.

---

# FIX-009 — Ajustar bot_commands repositories

## Objetivo

Preparar repositories para executor real.

## Tarefas

```txt
1. Usar result jsonb.
2. Não sobrescrever payload.
3. Definir mark_processing.
4. Definir mark_retrying.
5. Definir mark_failed.
6. Definir lock/claim de comandos pending.
```

Executar junto ou depois de FIX-003/Fase 16.

---

# FIX-010 — Healthcheck CLI

## Objetivo

Criar healthcheck real antes de systemd/GitHub Actions.

## Arquivos esperados

```txt
scripts/healthcheck.py
```

ou implementar em:

```txt
python main.py healthcheck
```

## Deve validar

```txt
1. Imports principais.
2. .env carregado.
3. TELEGRAM_BOT_TOKEN presente.
4. TELEGRAM_CHAT_ID presente.
5. Telegram getMe.
6. Acesso ao chat se possível.
7. Supabase se configurado.
8. Escrita de log.
9. Não imprimir secrets.
```

## Resposta obrigatória

```txt
RESULTADO:
- Execução: FIX-010 — Healthcheck CLI
- Arquivos alterados:
- Checks implementados:
- Testes executados:
- Pendências:
- Status: concluída / bloqueada
```

---

# ORDEM DE EXECUÇÃO DOS FIXES

Executar agora:

```txt
FIX-003
FIX-004
FIX-005
FIX-006
```

Executar antes de CI/deploy:

```txt
FIX-007
FIX-010
```

Executar nas fases Supabase/comandos:

```txt
FIX-008
FIX-009
```

---

# PROMPT PADRÃO PARA IA

```txt
Leia integralmente:

docs/ARKHAM_BOT_EXECUTION_PLAN.md
docs/FIX_BOT.md

Execute somente:

FIX-[NÚMERO] — [NOME]

Não execute outros fixes.
Não execute fases futuras.
Não implemente feature nova fora do escopo.
Não aplique migration no Supabase remoto sem autorização explícita.
Ao finalizar, responda no formato RESULTADO definido no fix.
```
