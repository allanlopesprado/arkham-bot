# Mini App e Worker — auditoria integral, achados e plano de correção

Este arquivo é a documentação operacional canônica desta auditoria do Mini App administrativo, Worker Cloudflare e integrações adjacentes do Arkham Bot. Ele substitui a leitura anterior que tratava apenas P0 como escopo principal: agora documenta **tudo que foi possível validar estaticamente**, incluindo P0, P1, P2, P3, riscos de schema, riscos de runtime, segurança, UX, deploy, observabilidade e regressão.

Esta auditoria foi feita em modo somente leitura sobre o repositório `allanlopesprado/arkham-bot`. Nenhum código funcional foi alterado nesta etapa; apenas este documento foi atualizado.

---

## 1. Escopo da auditoria

### Validado estaticamente

```text
- Mini App React/Vite.
- Worker Cloudflare.
- Wrappers Python em src/arkham_bot/handlers.
- Heartbeat Python.
- Estrutura modular atual do Mini App.
- Contratos visíveis entre Mini App e Worker.
- Contratos visíveis entre Worker e Supabase.
- Contratos visíveis entre Worker e Telegram API.
- Riscos de banco/schema inferidos pelo código.
- Riscos de autenticação/autorização.
- Riscos de logs e vazamento de dados.
- Riscos de UX/estado visual.
- Riscos de deploy/CI/runtime.
```

### Não validado nesta auditoria

```text
- Build real do Mini App.
- Dry-run real do Worker.
- Execução real de pytest.
- Execução real de python -m compileall.
- Schema real do Supabase remoto.
- Permissões reais RLS/policies do Supabase.
- Runtime real do Telegram Mini App.
- Fluxo real com Telegram Bot API.
- Cloudflare deploy real.
- Logs reais de produção.
```

Qualquer item acima deve ser tratado como pendência até ser executado no ambiente real.

---

## 2. Resumo executivo

O projeto evoluiu bastante desde o plano inicial. O Mini App deixou de concentrar tudo em `main.jsx` e foi modularizado parcialmente. O Worker também recebeu funcionalidades que antes estavam classificadas como backlog: `/ai-models`, `/bot-runtime`, `/admins` e `/destinations`.

Isso aumenta a maturidade funcional, mas também aumenta o risco operacional porque parte dessas novas rotas depende de tabelas/colunas que não foram comprovadas no repositório durante esta auditoria.

### Status por frente

```text
P0 — Correções mínimas: majoritariamente OK, com ressalva de auth sem API configurada.
P1 — Melhorias incrementais: parcialmente implementadas.
P2 — Refatoração Mini App: parcialmente implementada; main.jsx virou bootstrap, mas App.jsx ainda concentra muitas telas.
P3 — Backlog futuro: parcialmente implementado antes de validar schema remoto; requer auditoria de banco.
```

### Risco residual geral

```text
RISCO RESIDUAL: MÉDIO/ALTO

Motivo:
- P3 foi parcialmente implementado sem evidência visível de migrations/schema correspondente.
- Há dependência forte de tabelas e colunas Supabase não comprovadas.
- Não houve validação de build/dry-run/runtime real nesta etapa.
- O app ainda pode abrir visualmente se a API não estiver configurada.
```

---

## 3. Evidências estáticas positivas

### 3.1 Modularização do Mini App

```text
STATUS: OK

main.jsx virou bootstrap e importa App.jsx.
App.jsx importa módulos separados: telegram.js, api.js, i18n.js, settings.js, icons.jsx e components.jsx.
```

Impacto:

```text
- Reduz complexidade do entrypoint.
- Facilita evolução futura.
- Ainda não finaliza P2, porque App.jsx continua concentrando muitas telas e regras.
```

### 3.2 Auth fail-open original de /me foi corrigido

```text
STATUS: OK COM RESSALVA

Quando /me falha, o app agora usa auth_error.
Existe AuthErrorGate.
Existem textos PT/EN para authErrorTitle/authErrorText.
```

Ressalva:

```text
Se VITE_COMMANDS_API_URL não estiver configurado, o app ainda faz setAuthState('ready').
Como actionsDisabled bloqueia ações sem API/admin, o risco é reduzido, mas não é fail-closed estrito.
```

### 3.3 Logs sensíveis de saveSettings removidos

```text
STATUS: OK

saveSettings não loga mais payload completo nem day_config no front.
```

### 3.4 Script check existe

```text
STATUS: OK

miniapp/package.json contém:
- build: vite build
- check: vite build
```

### 3.5 /status agora é admin-only

```text
STATUS: OK

/status usa requireAdmin.
/health permanece simples e público.
```

### 3.6 /packs usa Supabase antes de ArkhamDB

```text
STATUS: OK COM RESSALVA

/packs tenta arkham_packs no Supabase.
Se não houver dados/falhar, cai para ArkhamDB pública.
```

Ressalva:

```text
A auditoria não confirmou que arkham_packs existe no Supabase remoto nem se as colunas estão corretas.
```

### 3.7 Wrappers Python estão corretos

```text
STATUS: OK

Wrappers existentes:
- handlers/supabase_client.py
- handlers/config.py
- handlers/local_storage.py
- handlers/scheduler.py
```

---

## 4. Achados críticos e altos

### AUD-CRIT-001 — P3 foi implementado sem evidência de schema correspondente

```text
SEVERIDADE: CRÍTICO
ÁREA: Supabase schema / Worker runtime
STATUS: PENDENTE DE VALIDAÇÃO REAL
```

O Worker agora contém rotas e handlers para:

```text
/admins
/admins/:id
/destinations
/destinations/:id
/destinations/:id/test
/bot-runtime
```

Essas rotas dependem de tabelas/colunas como:

```text
bot_admins.telegram_user_id
bot_admins.name
bot_admins.role
bot_admins.enabled
bot_admins.added_by_user_id
bot_admins.added_by_name
bot_admins.removed_by_user_id
bot_admins.removed_by_name
bot_admins.removed_at

target_chats.id
target_chats.chat_id
target_chats.title
target_chats.message_thread_id
target_chats.enabled
target_chats.added_by_user_id
target_chats.added_by_name

audit_logs.actor_telegram_user_id
audit_logs.actor_name
audit_logs.action_type
audit_logs.source
audit_logs.payload

bot_settings.key = last_heartbeat
```

Durante a auditoria estática, não foi encontrada evidência suficiente no repositório de migrations criando todas essas estruturas.

Risco:

```text
- /admins pode retornar 502/500.
- /destinations pode retornar 502/500.
- Auditoria pode falhar silenciosamente.
- /bot-runtime pode mostrar inativo ou erro mesmo com bot rodando.
```

Ação recomendada:

```sql
select table_name, column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name in (
    'bot_admins',
    'target_chats',
    'audit_logs',
    'bot_settings',
    'arkham_packs',
    'bot_commands',
    'bot_posting_history',
    'bot_errors',
    'bot_posted_cards'
  )
order by table_name, ordinal_position;
```

Critério de aceite:

```text
Todas as tabelas e colunas usadas pelo Worker existem no Supabase remoto.
Se não existirem, criar migration controlada e backup antes.
```

---

### AUD-HIGH-001 — O app abre em modo ready quando API não está configurada

```text
SEVERIDADE: ALTO
ÁREA: Auth / UX / Segurança defensiva
STATUS: PENDENTE
```

Comportamento atual inferido:

```text
if (!apiConfigured) { setAuthState('ready'); return; }
```

Risco:

```text
- Em ambiente mal configurado, o painel visual abre.
- Ações ficam bloqueadas por actionsDisabled, mas o estado visual pode confundir.
- Isso viola fail-closed estrito para painel administrativo.
```

Ação recomendada:

```text
Trocar ready por auth_error ou criar estado específico api_not_configured.
Não abrir painel administrativo se não há API configurada.
```

Critério de aceite:

```text
Sem VITE_COMMANDS_API_URL, o app mostra tela de configuração/erro e não renderiza painel administrativo.
```

---

### AUD-HIGH-002 — Destinos usam on_conflict=chat_id e podem impedir múltiplos tópicos no mesmo grupo

```text
SEVERIDADE: ALTO
ÁREA: Telegram tópicos / Supabase constraint
STATUS: PENDENTE
```

O handler de destino usa:

```text
/rest/v1/target_chats?on_conflict=chat_id
```

Risco:

```text
- Grupos com tópicos usam o mesmo chat_id com message_thread_id diferente.
- on_conflict=chat_id pode sobrescrever/impedir múltiplos destinos dentro do mesmo grupo.
- O bot pode não conseguir postar em tópicos diferentes corretamente.
```

Ação recomendada:

```text
Usar unicidade composta por chat_id + message_thread_id.
Se Supabase/PostgREST exigir constraint nomeada, criar constraint composta e ajustar on_conflict.
```

Critério de aceite:

```text
É possível cadastrar dois destinos com mesmo chat_id e message_thread_id diferentes.
```

---

### AUD-HIGH-003 — /bot-command não valida explicitamente backend configurado antes de usar Supabase

```text
SEVERIDADE: ALTO
ÁREA: Worker robustness
STATUS: PENDENTE
```

O fluxo de `/bot-command` usa `env.SUPABASE_URL.replace(...)` e `env.SUPABASE_SERVICE_ROLE_KEY` após autenticação/admin.

Risco:

```text
- Se env estiver incompleto e admin fallback estiver ativo, a rota pode lançar exceção.
- O Worker pode retornar erro não padronizado.
```

Ação recomendada:

```text
Adicionar guarda explícita no início de handleBotCommand:
if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return backend_not_configured.
```

Critério de aceite:

```text
/bot-command retorna JSON controlado backend_not_configured se Supabase não estiver configurado.
```

---

### AUD-HIGH-004 — Auditoria em audit_logs falha silenciosamente

```text
SEVERIDADE: ALTO
ÁREA: Observabilidade / Auditoria
STATUS: PENDENTE
```

`writeAuditLog` captura exceções e ignora.

Risco:

```text
- Ações administrativas podem ocorrer sem rastro auditável.
- Se audit_logs não existir ou falhar, ninguém percebe.
```

Ação recomendada:

```text
No mínimo, registrar safeLog sanitizado quando audit_logs falhar.
Em rotas críticas owner-only, considerar retornar warning no response ou armazenar fallback.
```

Critério de aceite:

```text
Falha de auditoria não vaza segredo, mas deixa evidência sanitizada nos logs.
```

---

### AUD-HIGH-005 — DELETE de destinos remove registro em vez de desabilitar

```text
SEVERIDADE: ALTO
ÁREA: Dados operacionais / Recuperação
STATUS: PENDENTE
```

O endpoint `DELETE /destinations/:id` executa delete real em `target_chats`.

Risco:

```text
- Perda de histórico/configuração operacional.
- Impossibilidade de recuperar destino removido por engano.
- Auditoria fica dependente de audit_logs, que hoje falha silenciosamente.
```

Ação recomendada:

```text
Trocar delete físico por soft delete:
PATCH enabled=false, removed_by_user_id, removed_at.
```

Critério de aceite:

```text
Remover destino desativa, não apaga fisicamente.
```

---

### AUD-HIGH-006 — P3 introduziu funcionalidades owner/admin sem comprovação de UX completa

```text
SEVERIDADE: ALTO
ÁREA: Produto / RBAC / UX
STATUS: PENDENTE
```

Há tela/estado para administradores e destinos no Mini App, além de endpoints Worker.

Risco:

```text
- UI pode chamar endpoints que falham por schema ausente.
- Owner/admin pode ver erro bruto ou comportamento incompleto.
- Fluxos críticos de gestão podem estar sem confirmação ou rollback adequado.
```

Ação recomendada:

```text
Validar manualmente:
- owner lista admins
- owner adiciona admin
- owner remove admin
- admin comum não acessa admins
- admin lista destinos
- admin adiciona destino
- admin testa destino
- admin remove/desativa destino
```

Critério de aceite:

```text
Todos os fluxos retornam JSON controlado e UI amigável.
```

---

## 5. Achados médios

### AUD-MED-001 — P2 está incompleto: App.jsx ainda concentra muitas responsabilidades

```text
SEVERIDADE: MÉDIO
ÁREA: Frontend architecture
STATUS: PENDENTE
```

`main.jsx` foi reduzido, mas `App.jsx` ainda concentra:

```text
- estado global
- auth
- carregamento de dados
- settings
- fila
- histórico
- admins
- destinos
- saúde
- renderização de múltiplas telas
```

Ação recomendada:

```text
Fase P2 real deve extrair screens/ e hooks/:
- useAuth
- useSettings
- useCommands
- useHistory
- useAdmins
- useDestinations
- useBotRuntime
- screens/HomeScreen.jsx
- screens/PostScreen.jsx
- screens/ScheduleScreen.jsx
- screens/QueueScreen.jsx
- screens/HistoryScreen.jsx
- screens/AdminsScreen.jsx
- screens/DestinationsScreen.jsx
- screens/HealthScreen.jsx
```

Critério de aceite:

```text
App.jsx vira orquestrador leve, sem blocos massivos de UI por tela.
```

---

### AUD-MED-002 — AI providers continuam duplicados entre front e Worker

```text
SEVERIDADE: MÉDIO
ÁREA: Configuração / Consistência
STATUS: PENDENTE
```

O Worker expõe `/ai-models`, mas o front ainda possui `AI_PROVIDERS` e `AI_MODELS` em `settings.js`.

Risco:

```text
- Divergência entre catálogo local e catálogo do Worker.
- Build pode aceitar modelo que Worker não aceita ou vice-versa.
```

Ação recomendada:

```text
Definir fonte única:
- Worker como fonte canônica via /ai-models; ou
- arquivo compartilhado gerado; ou
- manter duplicado, mas adicionar teste de consistência.
```

Critério de aceite:

```text
Lista de modelos do front e Worker não diverge sem teste falhar.
```

---

### AUD-MED-003 — /ai-models está público após CORS

```text
SEVERIDADE: MÉDIO/BAIXO
ÁREA: API surface
STATUS: ACEITÁVEL COM DECISÃO EXPLÍCITA
```

`/ai-models` não exige admin. Como expõe apenas catálogo de modelos, não é crítico.

Ação recomendada:

```text
Decidir explicitamente:
- manter público via CORS; ou
- exigir requireAdmin por consistência.
```

Critério de aceite:

```text
Decisão registrada no README ou neste arquivo.
```

---

### AUD-MED-004 — Heartbeat só começa após 60 segundos

```text
SEVERIDADE: MÉDIO
ÁREA: Observabilidade
STATUS: PENDENTE
```

Heartbeat Python dorme antes de escrever o primeiro `last_heartbeat`.

Risco:

```text
- Após restart, /bot-runtime pode mostrar inativo por até 60 segundos.
```

Ação recomendada:

```text
Escrever heartbeat imediato antes do primeiro sleep.
```

Critério de aceite:

```text
/bot-runtime mostra alive logo após inicialização do bot, sem aguardar 60s.
```

---

### AUD-MED-005 — /bot-runtime usa updated_at, não value

```text
SEVERIDADE: MÉDIO
ÁREA: Observabilidade / Dados
STATUS: ACEITÁVEL COM RESSALVA
```

O Python escreve value com o timestamp, mas Worker calcula vida pelo `updated_at` da linha.

Risco:

```text
- Funciona se updated_at for atualizado no upsert.
- Se trigger/updated_at não atualizar, bot-runtime fica incorreto.
```

Ação recomendada:

```text
Confirmar que bot_settings.updated_at atualiza em upsert.
Alternativamente, parsear value como fonte primária e usar updated_at como fallback.
```

---

### AUD-MED-006 — Histórico com filtro por origem é apenas client-side

```text
SEVERIDADE: MÉDIO
ÁREA: Performance / UX
STATUS: PENDENTE
```

O histórico filtra `scheduled/manual` no front após carregar a página.

Risco:

```text
- Paginação pode ficar inconsistente: página carregada pode ter poucos itens após filtro.
- Usuário pode achar que não há mais posts de uma origem quando existem em páginas seguintes.
```

Ação recomendada:

```text
Adicionar parâmetro source em /history e filtrar no Worker/Supabase.
```

Critério de aceite:

```text
Filtro de origem funciona corretamente com paginação.
```

---

### AUD-MED-007 — Cancelamento de comando depende apenas de status pending/retrying no Worker

```text
SEVERIDADE: MÉDIO
ÁREA: Concorrência / Fila
STATUS: PARCIALMENTE OK
```

O Worker só cancela `pending/retrying`, o que é correto. Porém, a UI/UX precisa deixar claro quando `processing` não pode mais ser cancelado.

Ação recomendada:

```text
Adicionar caption/tooltip para comandos não canceláveis.
```

---

### AUD-MED-008 — Estado unauthorized fica em LoadingGate

```text
SEVERIDADE: MÉDIO
ÁREA: UX auth
STATUS: PENDENTE
```

Quando usuário não admin é detectado, o app tenta fechar via Telegram e define `authState='unauthorized'`. O render mostra LoadingGate para `unauthorized`.

Risco:

```text
- Se o app não fechar, usuário vê spinner indefinido.
```

Ação recomendada:

```text
Criar UnauthorizedGate com mensagem explícita.
```

Critério de aceite:

```text
Usuário não admin vê mensagem clara caso o app não feche.
```

---

### AUD-MED-009 — Busca GitHub não encontrou workflow CI no caminho esperado

```text
SEVERIDADE: MÉDIO
ÁREA: CI/CD
STATUS: PENDENTE
```

Tentativa de ler `.github/workflows/deploy.yml` retornou 404 durante auditoria.

Risco:

```text
- CI pode estar ausente, renomeado ou fora do esperado.
- Build/check/dry-run podem depender só de execução manual.
```

Ação recomendada:

```text
Validar existência de workflow real.
Se ausente, criar workflow separado para:
- python -m compileall -q .
- pytest -q
- cd miniapp && npm ci && npm run build && npm run check
- cd worker && npm ci && npm run dry-run
```

---

## 6. Achados baixos / melhorias

### AUD-LOW-001 — `miniapp/package.json` está formatado de forma incomum

```text
SEVERIDADE: BAIXO
ÁREA: Estilo / Manutenção
STATUS: NÃO BLOQUEANTE
```

O JSON é válido, mas a indentação parece gerada por PowerShell/serializer.

Ação recomendada:

```text
Formatar com npm/prettier em fase de manutenção.
```

---

### AUD-LOW-002 — ChatIdInputRow força prefixo negativo

```text
SEVERIDADE: BAIXO/MÉDIO
ÁREA: UX Telegram
STATUS: DEPENDE DO USO
```

Para grupos/supergrupos/canais, IDs negativos são esperados. Para outros alvos, pode limitar.

Ação recomendada:

```text
Manter se o app só aceita grupos/canais.
Documentar a regra no placeholder/tooltip.
```

---

## 7. Validações obrigatórias agora

Executar no ambiente local/servidor:

```bash
python -m compileall -q .
python main.py healthcheck
pytest -q
cd miniapp && npm install && npm run build && npm run check
cd ../worker && npm install && npm run dry-run
```

Validar Supabase schema:

```sql
select table_name, column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name in (
    'bot_admins',
    'target_chats',
    'audit_logs',
    'bot_settings',
    'arkham_packs',
    'bot_commands',
    'bot_posting_history',
    'bot_errors',
    'bot_posted_cards'
  )
order by table_name, ordinal_position;
```

Validar endpoints no Worker com sessão admin real:

```text
GET /health
GET /me
GET /status
GET /overview
GET /settings
PATCH /settings
GET /commands
PATCH /commands/:id
GET /cards?q=Roland
GET /packs
GET /history
GET /bot-info
GET /ai-models
GET /bot-runtime
GET /admins
POST /admins
DELETE /admins/:id
GET /destinations
POST /destinations
PATCH /destinations/:id
DELETE /destinations/:id
POST /destinations/:id/test
POST /bot-command
```

Validar Telegram Mini App real:

```text
- admin abre painel
- não-admin recebe erro claro
- API não configurada não abre painel administrativo
- settings salvam e recarregam
- fila carrega
- comando é enfileirado
- histórico carrega
- agenda salva
- IA salva
- banco/sync funciona
- destinos funcionam
- admins funcionam apenas para owner
- saúde mostra Worker/Supabase/Python Bot coerentes
```

---

## 8. Ordem recomendada de correção

### Etapa 1 — Bloqueadores de runtime

```text
1. Validar schema Supabase.
2. Corrigir/criar migrations faltantes, se houver.
3. Validar Worker dry-run.
4. Validar Mini App build/check.
```

### Etapa 2 — Segurança/autorização

```text
1. Corrigir app ready sem API configurada.
2. Padronizar auth gates: no_telegram, auth_error, unauthorized, api_not_configured.
3. Decidir se /ai-models fica público ou admin-only.
4. Adicionar guarda backend_not_configured em /bot-command.
```

### Etapa 3 — Dados operacionais

```text
1. Ajustar destinos para permitir chat_id + message_thread_id.
2. Trocar delete físico de destinos por soft delete.
3. Confirmar audit_logs ou tratar falha de auditoria.
4. Validar last_heartbeat e updated_at.
```

### Etapa 4 — UX/Produto

```text
1. UnauthorizedGate.
2. Estados vazios/erros para admins/destinations/bot-runtime.
3. Histórico com filtro por origem no backend.
4. Tooltips para comandos não canceláveis.
```

### Etapa 5 — Arquitetura/Manutenção

```text
1. Extrair screens de App.jsx.
2. Extrair hooks por domínio.
3. Definir fonte única de modelos IA.
4. Criar CI real.
```

---

## 9. Definition of Done para considerar o projeto estável

```text
- Build Mini App passou.
- Worker dry-run passou.
- Python compileall passou.
- pytest passou ou ausência de testes foi registrada.
- Schema Supabase validado contra todas as rotas atuais.
- Fluxos Telegram reais testados.
- Nenhum endpoint novo retorna 500 por tabela/coluna ausente.
- Admins funciona apenas para owner.
- Destinos suporta tópicos corretamente.
- Audit logs existem ou fallback sanitizado está definido.
- /bot-runtime reflete heartbeat real.
- CI executa validações básicas.
- README ou documentação canônica registra deploy/rollback mínimo.
```

---

## 10. Matriz final de risco

```text
CRÍTICO
- AUD-CRIT-001: P3 implementado sem evidência de schema correspondente.

ALTO
- AUD-HIGH-001: App abre visualmente sem API configurada.
- AUD-HIGH-002: Destinos podem não suportar múltiplos tópicos por grupo.
- AUD-HIGH-003: /bot-command sem guarda explícita de backend configurado.
- AUD-HIGH-004: audit_logs falha silenciosamente.
- AUD-HIGH-005: DELETE físico de destinos.
- AUD-HIGH-006: Fluxos P3 sem comprovação de UX/schema.

MÉDIO
- AUD-MED-001: App.jsx ainda concentra muitas responsabilidades.
- AUD-MED-002: Modelos IA duplicados entre front e Worker.
- AUD-MED-003: /ai-models público por decisão implícita.
- AUD-MED-004: heartbeat só escreve após 60 segundos.
- AUD-MED-005: bot-runtime usa updated_at, não value.
- AUD-MED-006: filtro de origem do histórico é client-side.
- AUD-MED-007: UX de comando não cancelável pode ser melhorada.
- AUD-MED-008: unauthorized mostra LoadingGate.
- AUD-MED-009: CI workflow não confirmado.

BAIXO
- AUD-LOW-001: package.json formatado de forma incomum.
- AUD-LOW-002: ChatIdInputRow força prefixo negativo.
```

---

## 11. Formato obrigatório para a próxima IA que corrigir

```text
RESULTADO:
- Arquivos alterados:
  - ...
- Achados corrigidos:
  - AUD-...: OK/ERRO/NÃO EXECUTADO + evidência
- Validações executadas:
  - python -m compileall -q .: OK/ERRO/NÃO EXECUTADO + motivo
  - python main.py healthcheck: OK/ERRO/NÃO EXECUTADO + motivo
  - pytest -q: OK/ERRO/NÃO EXECUTADO + motivo
  - cd miniapp && npm run build: OK/ERRO/NÃO EXECUTADO + motivo
  - cd miniapp && npm run check: OK/ERRO/NÃO EXECUTADO + motivo
  - cd worker && npm run dry-run: OK/ERRO/NÃO EXECUTADO + motivo
- Validação Supabase:
  - tabelas/colunas OK/ERRO/NÃO EXECUTADO + evidência
- Validação Telegram real:
  - OK/ERRO/NÃO EXECUTADO + evidência
- Risco residual:
  - baixo/médio/alto + justificativa
- Pendências:
  - ...
```
