# Arkham Bot — auditoria consolidada de Mini App, Worker, banco e operação

Este documento consolida em uma única referência tudo que foi validado, alterado, sugerido incorretamente, corrigido, deixado pendente e ainda precisa ser feito no projeto Arkham Bot em relação ao Mini App administrativo, Cloudflare Worker, Supabase, ambiente Oracle/systemd e integrações relacionadas.

Regra central desta auditoria: **não aceitar workaround, wrapper paralelo, proxy interno, rota duplicada, arquivo intermediário, gambiarra ou desvio de arquitetura para mascarar problema real**. Correções devem ocorrer nos arquivos responsáveis e no schema correto, com validação objetiva depois.

---

## 1. Resumo executivo

### Estado atual

```text
Ambiente do servidor: validado e operacional.
Python/systemd: validado e operacional.
Mini App: build/check validados.
Worker: dry-run validado.
Supabase: schema principal validado; arkham_packs corrigido; target_chats preparado para soft delete.
Código do Worker: ainda pendente de hardening.
Código do Mini App: ainda pendente de UX/auth hardening.
Banco: migration segura adicionada; constraint de tópicos ainda pendente.
Cloudflare secrets: ainda pendente de validação.
```

### Conclusão

```text
O projeto está funcional em ambiente, mas ainda não está finalizado em hardening.
As próximas correções devem ser feitas diretamente em worker/src/index.js e depois no Mini App.
Não criar wrapper, hardened.js, proxy ou rota paralela.
```

---

## 2. Validações já executadas no ambiente real

### Servidor e Python

Validações executadas no servidor Oracle/Ubuntu em `/opt/arkham_bot`:

```text
/opt/arkham_bot/venv/bin/python -m compileall -q .: OK
/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py healthcheck: OK
/opt/arkham_bot/venv/bin/python -m pytest -q: 42 passed
```

Healthcheck confirmado:

```text
telegram_get_me_ok
supabase_rest_ok
healthcheck_ok
```

### systemd

Serviço validado:

```text
arkham-bot.service: active (running)
WorkingDirectory=/opt/arkham_bot
User=ubuntu
ExecStart=/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py interactive
```

Logs confirmados:

```text
scheduler_started
bot_commands_worker_started
Application started
scheduler_stopped_cleanly em restart
```

### Dependências Python no venv correto

Venv real usado pelo systemd:

```text
/opt/arkham_bot/venv
```

Confirmado nesse venv:

```text
filelock: instalado
pytest: instalado
requirements.txt: instalado
requirements-dev.txt: instalado
```

### Node / npm

Versões validadas:

```text
node v22.22.2
npm 10.9.7
```

Motivo:

```text
Wrangler 4.95.0 exige Node >= 22.
Node 20 não era suficiente.
```

### Mini App

Validações executadas:

```text
npm install: OK
npm run build: OK
npm run check: OK
```

### Worker

Validações executadas:

```text
npm install: OK
npm run dry-run: OK
wrangler 4.95.0
```

Bindings vistos no dry-run:

```text
SUPABASE_URL
ALLOWED_ORIGINS
```

Pendência: `SUPABASE_SERVICE_ROLE_KEY` e `TELEGRAM_BOT_TOKEN` precisam ser confirmados via `wrangler secret list`, porque secrets podem não aparecer no resumo do dry-run.

---

## 3. Alterações já feitas e classificadas

### 3.1 Heartbeat imediato

Arquivo:

```text
src/arkham_bot/services/heartbeat.py
```

Commit:

```text
38d23f8 fix: write heartbeat immediately
```

Classificação:

```text
CORREÇÃO REAL
NÃO É WORKAROUND
```

Motivo:

```text
Corrigiu diretamente o serviço de heartbeat.
O primeiro heartbeat agora é gravado imediatamente, não só depois de 60 segundos.
Evita status falso de bot inativo logo após restart.
```

Validação posterior:

```text
compileall OK
healthcheck OK
pytest 42 passed
systemd restart OK
```

Status:

```text
OK
```

---

### 3.2 package.json do Mini App formatado

Arquivo:

```text
miniapp/package.json
```

Commit:

```text
36b0cf6 chore: format miniapp package json
```

Classificação:

```text
LIMPEZA REAL
NÃO É WORKAROUND
```

Motivo:

```text
Apenas normalizou JSON e preservou scripts.
```

Status:

```text
OK
```

---

### 3.3 Correção de Node 22

Local:

```text
Servidor Ubuntu / NodeSource
```

Classificação:

```text
CORREÇÃO DE DEPENDÊNCIA
NÃO É WORKAROUND
```

Motivo:

```text
Wrangler atual exigia Node 22.
Sem isso, o Worker poderia falhar no build/dry-run/deploy.
```

Status:

```text
OK
```

---

### 3.4 arkham_packs corrigido no Supabase

Banco:

```text
public.arkham_packs
```

Colunas adicionadas/populadas:

```text
cycle_position
position
chapter
total
```

Validação:

```text
total_packs: 114
sem_cycle_position: 0
sem_position: 0
sem_chapter: 0
sem_total: 0
```

Classificação:

```text
CORREÇÃO DE SCHEMA
NÃO É WORKAROUND
```

Motivo:

```text
O Worker espera essas colunas em /packs.
Corrigir o schema reduz dependência do fallback externo ArkhamDB.
```

Status:

```text
BANCO OK
MIGRATION VERSIONADA
```

---

### 3.5 target_chats preparado para soft delete

Banco:

```text
public.target_chats
```

Colunas adicionadas:

```text
removed_by_user_id bigint
removed_by_name text
removed_at timestamptz
```

Classificação:

```text
PREPARAÇÃO CORRETA DE SCHEMA
NÃO É WORKAROUND
```

Motivo:

```text
Permite trocar DELETE físico por PATCH enabled=false no Worker.
```

Status:

```text
BANCO OK
CÓDIGO PENDENTE
```

---

### 3.6 Migration versionada para alterações seguras de banco

Arquivo criado:

```text
supabase/migrations/20260528_worker_hardening_schema.sql
```

Commit:

```text
8336d97 db: add worker hardening schema migration
```

Classificação:

```text
CORREÇÃO DE RASTREABILIDADE
NÃO É WORKAROUND
```

Motivo:

```text
As alterações tinham sido aplicadas diretamente no Supabase real.
A migration registra no Git as mudanças seguras já validadas.
```

Inclui:

```text
arkham_packs.cycle_position
arkham_packs.position
arkham_packs.chapter
arkham_packs.total
target_chats.removed_by_user_id
target_chats.removed_by_name
target_chats.removed_at
```

Não inclui:

```text
Alteração da constraint de tópicos.
```

Motivo para não incluir constraint ainda:

```text
A constraint de tópicos depende de alteração coordenada no Worker.
Aplicar só o banco agora pode quebrar on_conflict=chat_id.
```

Status:

```text
OK PARA ALTERAÇÕES SEGURAS
PENDENTE PARA TÓPICOS
```

---

## 4. Erros operacionais cometidos durante a conversa

### ERR-001 — Proposta de `worker/src/hardened.js`

O que foi sugerido:

```text
Criar worker/src/hardened.js para interceptar rotas e delegar ao Worker original.
```

Classificação:

```text
ERRO DO ASSISTENTE
WORKAROUND REJEITADO
NÃO APLICAR
```

Por que é errado:

```text
Criaria camada paralela.
Duplicaria CORS/auth/rotas.
Mascararia problemas reais do worker/src/index.js.
Aumentaria dívida técnica.
```

Estado real:

```text
worker/src/hardened.js não existe.
worker/wrangler.toml continua com main = "src/index.js".
Nenhum wrapper foi aplicado.
```

Regra:

```text
Corrigir diretamente worker/src/index.js.
```

---

### ERR-002 — Risco de update cego em arquivo grande

Problema:

```text
worker/src/index.js é grande.
As respostas do conector GitHub foram truncadas.
GitHub update_file substitui arquivo inteiro.
```

Classificação:

```text
RISCO OPERACIONAL
NÃO EXECUTAR UPDATE CEGO
```

Regra:

```text
Não substituir index.js inteiro a partir de conteúdo truncado.
Usar patch local/diff completo/git apply.
```

Status:

```text
Nenhuma substituição cega foi aplicada.
```

---

### ERR-003 — Patch manual via nano sem diff completo

O que ocorreu:

```text
Foi sugerido editar handleDeleteDestination() manualmente.
```

Classificação:

```text
PROCESSO ACEITÁVEL EM EMERGÊNCIA
MAS NÃO IDEAL
```

Risco:

```text
Erro humano.
Dificuldade de auditoria.
Divergência se não houver git diff.
```

Forma correta:

```text
Gerar patch explícito.
Aplicar com git apply quando possível.
Rodar npm run dry-run.
Revisar git diff antes de commit.
```

---

### ERR-004 — Criação/uso de `.venv` quando systemd usa `venv`

O que ocorreu:

```text
Foi orientado criar/usar /opt/arkham_bot/.venv.
Depois foi confirmado que systemd usa /opt/arkham_bot/venv.
```

Classificação:

```text
ERRO OPERACIONAL PARCIAL
GEROU DÍVIDA DE AMBIENTE DUPLICADO
```

Estado correto:

```text
/opt/arkham_bot/venv é o ambiente real do serviço.
/opt/arkham_bot/.venv é redundante se ainda existir.
```

Correção recomendada:

```bash
sudo systemctl show arkham-bot -p ExecStart -p WorkingDirectory -p User
/opt/arkham_bot/venv/bin/python -m pytest -q /opt/arkham_bot
cd /opt/arkham_bot
rm -rf .venv
```

---

### ERR-005 — Ambiente OK não significa código finalizado

Problema:

```text
Foi validado que o ambiente está OK, mas isso não encerra o hardening.
```

Classificação:

```text
RISCO DE COMUNICAÇÃO
```

Regra:

```text
Separar sempre:
- ambiente validado
- banco validado
- código corrigido
- deploy validado
```

---

### ERR-006 — SQL de tópicos com coalesce exige cautela

O que foi sugerido:

```text
Criar índice UNIQUE(chat_id, coalesce(message_thread_id, 0)).
```

Classificação:

```text
POTENCIAL ARMADILHA TÉCNICA
```

Risco:

```text
Índice com expressão pode não funcionar bem com on_conflict do PostgREST.
```

Alternativas corretas a validar antes:

```text
1. UNIQUE(chat_id, message_thread_id) e tratar null no código.
2. Coluna thread_key gerada/stored com coalesce e UNIQUE(chat_id, thread_key).
3. Remover dependência de on_conflict e fazer fluxo explícito: SELECT, depois POST ou PATCH.
```

Regra:

```text
Não aplicar constraint de tópicos sem ajustar Worker junto.
```

---

### ERR-007 — Busca textual não prova ausência de gambiarra

O que ocorreu:

```text
Foram buscados termos como workaround, hack, TODO, FIXME, stub, fallback, legacy, temporary.
```

Classificação:

```text
EVIDÊNCIA FRACA
```

Regra:

```text
Não concluir ausência de workaround só porque a busca textual não encontrou termos.
Validar estruturalmente fluxo, schema, dependências, logs e runtime.
```

---

### ERR-008 — Banco alterado antes de migration versionada

O que ocorreu:

```text
As alterações em arkham_packs e target_chats foram aplicadas primeiro no Supabase real.
A migration só foi criada depois.
```

Classificação:

```text
ERRO DE RASTREABILIDADE
CORRIGIDO PARCIALMENTE
```

Correção aplicada:

```text
supabase/migrations/20260528_worker_hardening_schema.sql
```

Pendência:

```text
Constraint de tópicos ainda precisa de migration futura coordenada com Worker.
```

---

## 5. Workarounds/dívidas técnicas existentes no projeto

### WRK-001 — Admin fallback por env

Local:

```text
worker/src/index.js
getAdminAccess()
ALLOW_ADMIN_ENV_FALLBACK
ADMIN_TELEGRAM_USER_IDS
```

Problema:

```text
Permite admin fora da tabela bot_admins quando ALLOW_ADMIN_ENV_FALLBACK=true.
```

Risco:

```text
Pode mascarar falha de Supabase.
Reduz rastreabilidade de administração.
Diverge entre ambientes.
```

Ação correta:

```text
Produção deve manter ALLOW_ADMIN_ENV_FALLBACK desativado.
Se mantido, documentar como modo de emergência, não fluxo normal.
```

Status:

```text
PENDENTE DE DECISÃO OPERACIONAL
```

---

### WRK-002 — Fallback ArkhamDB em /packs

Local:

```text
worker/src/index.js
handleGetPacks()
```

Problema:

```text
Se Supabase falha, Worker busca packs direto na API pública ArkhamDB.
```

Risco:

```text
Pode mascarar falha de Supabase.
Pode exibir dados divergentes.
Cria dependência externa em painel administrativo.
```

Ação correta:

```text
Manter apenas como degradação controlada.
Registrar safeLog quando fallback for usado.
```

Status:

```text
PENDENTE
```

---

### WRK-003 — OAuth ArkhamDB como stub/futuro

Local:

```text
src/arkham_bot/arkhamdb_oauth.py
```

Problema:

```text
Módulo marcado como futuro/stub pode ser confundido com funcional.
```

Ação correta:

```text
Decidir: implementar, remover, ou manter como stub explicitamente isolado e sem uso runtime.
```

Status:

```text
PENDENTE DE DECISÃO
```

---

### WRK-004 — Wrappers de compatibilidade em handlers

Locais:

```text
src/arkham_bot/handlers/supabase_client.py
src/arkham_bot/handlers/config.py
src/arkham_bot/handlers/local_storage.py
src/arkham_bot/handlers/scheduler.py
```

Problema:

```text
Wrappers preservam imports antigos em vez de refatorar todos os imports para módulos canônicos.
```

Risco:

```text
Arquitetura fica menos clara.
Novos imports podem usar wrapper por engano.
```

Ação correta:

```text
Planejar refatoração futura dos imports antigos em telegram_handlers.py.
Remover wrappers se ficarem sem uso.
```

Status:

```text
ACEITO TEMPORARIAMENTE
PENDENTE DE LIMPEZA FUTURA
```

---

### WRK-005 — Dois venvs no servidor

Locais:

```text
/opt/arkham_bot/venv
/opt/arkham_bot/.venv
```

Problema:

```text
Ambiente duplicado pode confundir validações e instalações.
```

Ação correta:

```text
Manter /opt/arkham_bot/venv.
Remover .venv se não estiver em uso.
```

Status:

```text
PENDENTE OPCIONAL
```

---

## 6. Pendências reais de código

### PEND-001 — Worker: soft delete de destinos

Arquivo:

```text
worker/src/index.js
```

Função:

```text
handleDeleteDestination()
```

Problema:

```text
Executa DELETE físico em target_chats.
```

Correção correta:

```text
Trocar DELETE por PATCH:
- enabled=false
- removed_by_user_id=user.id
- removed_by_name=user.name
- removed_at=new Date().toISOString()
```

Status:

```text
PENDENTE
```

---

### PEND-002 — Worker: backend_not_configured em /bot-command

Arquivo:

```text
worker/src/index.js
```

Função:

```text
handleBotCommand()
```

Problema:

```text
Usa env.SUPABASE_URL.replace(...) sem guarda explícita.
```

Correção correta:

```text
Antes de qualquer uso de Supabase, retornar backend_not_configured se SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY estiver ausente.
```

Status:

```text
PENDENTE
```

---

### PEND-003 — Worker: writeAuditLog falha silenciosamente

Arquivo:

```text
worker/src/index.js
```

Função:

```text
writeAuditLog()
```

Problema:

```text
catch {} ignora falha de auditoria.
```

Correção correta:

```text
Registrar safeLog sanitizado quando audit_logs falhar.
Nunca vazar token, initData ou payload sensível.
```

Status:

```text
PENDENTE
```

---

### PEND-004 — Worker: /bot-runtime deve usar value do heartbeat

Arquivo:

```text
worker/src/index.js
```

Função:

```text
handleBotRuntime()
```

Problema:

```text
Usa updated_at como last_seen.
Heartbeat grava timestamp real em bot_settings.value.
```

Correção correta:

```text
Parsear value como fonte primária.
Usar updated_at só como fallback.
```

Status:

```text
PENDENTE
```

---

### PEND-005 — Worker/Mini App: filtro source do histórico deve ser backend-side

Arquivos:

```text
worker/src/index.js
miniapp/src/App.jsx
```

Problema:

```text
Filtro source client-side quebra paginação e pode ocultar dados.
```

Correção correta:

```text
Worker /history aceitar source.
Mini App enviar source na query.
Remover filtro local como fonte principal.
```

Status:

```text
PENDENTE
```

---

### PEND-006 — Worker: /ai-models público por decisão implícita

Arquivo:

```text
worker/src/index.js
```

Problema:

```text
/ai-models fica acessível após CORS, sem requireAdmin.
```

Correção recomendada:

```text
Proteger com requireAdmin, pois pertence ao painel administrativo.
```

Status:

```text
PENDENTE DE DECISÃO
```

---

### PEND-007 — Mini App: API ausente abre painel visual

Arquivo:

```text
miniapp/src/App.jsx
```

Problema:

```text
if (!apiConfigured) { setAuthState('ready'); return; }
```

Correção correta:

```text
Criar estado api_not_configured ou usar AuthErrorGate.
Não renderizar painel administrativo sem API.
```

Status:

```text
PENDENTE
```

---

### PEND-008 — Mini App: unauthorized usa LoadingGate

Arquivos:

```text
miniapp/src/App.jsx
miniapp/src/components.jsx
miniapp/src/i18n.js
```

Problema:

```text
authState === 'unauthorized' renderiza LoadingGate.
```

Correção correta:

```text
Criar UnauthorizedGate com texto claro.
```

Status:

```text
PENDENTE
```

---

### PEND-009 — target_chats: múltiplos tópicos por grupo

Arquivos/objetos:

```text
worker/src/index.js
public.target_chats constraint
future migration
```

Problema atual:

```text
target_chats_chat_id_key UNIQUE(chat_id)
Worker usa on_conflict=chat_id
```

Impacto:

```text
Não permite cadastrar vários tópicos do mesmo grupo.
```

Correção correta:

```text
Definir estratégia de unicidade compatível com PostgREST.
Alterar banco e Worker juntos.
Testar dois destinos com mesmo chat_id e message_thread_id diferentes.
```

Status:

```text
PENDENTE
```

---

### PEND-010 — PTBUserWarning nos ConversationHandlers

Arquivo provável:

```text
src/arkham_bot/handlers/telegram_handlers.py
```

Aviso:

```text
PTBUserWarning: If 'per_message=False', 'CallbackQueryHandler' will not be tracked for every message.
```

Classificação:

```text
NÃO CRÍTICO
LIMPEZA FUTURA
```

Correção:

```text
Revisar ConversationHandler de card_conv_handler e search_conv_handler.
Decidir per_message/per_chat/per_user explicitamente.
```

Status:

```text
PENDENTE BAIXO
```

---

### PEND-011 — Cloudflare secrets

Comando obrigatório:

```bash
cd /opt/arkham_bot/worker
npx wrangler secret list
```

Secrets esperados:

```text
SUPABASE_SERVICE_ROLE_KEY
TELEGRAM_BOT_TOKEN
```

Variáveis não secret esperadas:

```text
SUPABASE_URL
ALLOWED_ORIGINS
```

Status:

```text
PENDENTE
```

---

## 7. Pendências operacionais

### OPS-001 — Lockfiles

Arquivos:

```text
miniapp/package-lock.json
worker/package-lock.json
```

Ação:

```bash
cd /opt/arkham_bot
git status
git diff -- miniapp/package-lock.json worker/package-lock.json | head -80
git add miniapp/package-lock.json worker/package-lock.json
git commit -m "chore: update npm lockfiles after node 22 validation"
```

Status:

```text
VERIFICAR SE JÁ FOI FEITO
```

---

### OPS-002 — Remover .venv duplicado

Ação:

```bash
sudo systemctl show arkham-bot -p ExecStart
cd /opt/arkham_bot
rm -rf .venv
```

Status:

```text
PENDENTE OPCIONAL
```

---

### OPS-003 — Reboot controlado por kernel pendente

Motivo:

```text
Sistema indicou kernel novo pendente.
```

Ação:

```text
Agendar reboot em janela segura.
```

Status:

```text
PENDENTE OPERACIONAL
```

---

## 8. Ordem correta de correção

### Fase 1 — Worker, sem workaround

Corrigir diretamente:

```text
worker/src/index.js
```

Itens:

```text
1. handleDeleteDestination: DELETE -> PATCH soft delete.
2. handleBotCommand: backend_not_configured.
3. writeAuditLog: log sanitizado em falha.
4. handleBotRuntime: usar value como fonte primária.
5. /ai-models: decidir/proteger com requireAdmin.
6. /history: filtro source backend-side.
```

Proibido:

```text
- hardened.js
- wrapper de rotas
- proxy interno
- alterar wrangler.toml para outro main
- duplicar handlers
- update cego de index.js truncado
```

---

### Fase 2 — Mini App

Arquivos:

```text
miniapp/src/App.jsx
miniapp/src/components.jsx
miniapp/src/i18n.js
```

Itens:

```text
1. api_not_configured gate.
2. UnauthorizedGate.
3. Histórico enviando source para backend.
4. Remover filtro source client-side como mecanismo principal.
```

---

### Fase 3 — Tópicos Telegram

Só depois da Fase 1:

```text
1. Escolher estratégia de constraint compatível com PostgREST.
2. Criar migration específica para tópicos.
3. Ajustar Worker.
4. Testar múltiplos tópicos no mesmo chat_id.
```

---

## 9. Validação obrigatória após cada fase

Python:

```bash
cd /opt/arkham_bot
/opt/arkham_bot/venv/bin/python -m compileall -q .
/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py healthcheck
/opt/arkham_bot/venv/bin/python -m pytest -q
```

Mini App:

```bash
cd /opt/arkham_bot/miniapp
npm install
npm run build
npm run check
```

Worker:

```bash
cd /opt/arkham_bot/worker
npm install
npm run dry-run
```

Systemd:

```bash
sudo systemctl restart arkham-bot
sudo systemctl status arkham-bot --no-pager
journalctl -u arkham-bot -n 80 --no-pager
```

Cloudflare:

```bash
cd /opt/arkham_bot/worker
npx wrangler secret list
```

---

## 10. Definition of Done

Só considerar concluído quando:

```text
Nenhum wrapper/workaround novo existir.
Todas as correções estiverem nos arquivos reais.
Worker dry-run passar.
Mini App build/check passar.
pytest passar.
systemd subir sem erro.
Migration segura estiver versionada.
Soft delete funcionar em target_chats.
/bot-runtime usar heartbeat real.
/history filtrar source no backend.
/destinations não apagar registro fisicamente.
Tópicos Telegram forem suportados com constraint e Worker compatíveis.
Cloudflare secrets estiverem confirmados.
Lockfiles validados estiverem versionados.
.venv duplicado removido ou explicitamente mantido com justificativa.
```

---

## 11. Próxima ação objetiva

Próxima correção real deve ser:

```text
worker/src/index.js -> handleDeleteDestination()
```

Motivo:

```text
O banco já está preparado para soft delete.
É a menor alteração funcional real.
Remove risco de perda de dados.
Não exige wrapper.
```

Método correto:

```text
Gerar patch pequeno.
Aplicar localmente ou via diff completo.
Rodar npm run dry-run.
Conferir git diff.
Commitar.
```

Não fazer:

```text
Não criar hardened.js.
Não criar arquivo paralelo.
Não mexer em wrangler.toml.
Não substituir index.js inteiro por conteúdo truncado.
```
