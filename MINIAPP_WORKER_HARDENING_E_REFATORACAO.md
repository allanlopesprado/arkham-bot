# Mini App e Worker — auditoria de workarounds, pendências e plano sem gambiarra

Este arquivo é a documentação operacional canônica desta auditoria do Mini App administrativo, Worker Cloudflare, Supabase e integrações adjacentes do Arkham Bot.

Regra principal desta revisão: **não aceitar workaround, wrapper paralelo, proxy interno, rota duplicada, arquivo intermediário ou desvio de arquitetura para mascarar problema real**.

As correções devem ser feitas diretamente nos arquivos responsáveis, preservando a arquitetura existente.

---

## 1. Estado validado em ambiente real

Validações executadas no servidor Oracle/Ubuntu em `/opt/arkham_bot`:

```text
Python compileall: OK
Python healthcheck: OK
pytest: 42 passed
Mini App npm install: OK
Mini App npm run build: OK
Mini App npm run check: OK
Worker npm install: OK
Worker npm run dry-run: OK
Node: v22.22.2
npm: 10.9.7
systemd: active/running
systemd Python: /opt/arkham_bot/venv/bin/python
```

Healthcheck confirmado:

```text
telegram_get_me_ok
supabase_rest_ok
healthcheck_ok
```

Systemd confirmado:

```text
/opt/arkham_bot/venv/bin/python /opt/arkham_bot/main.py interactive
```

Resultado: o ambiente de execução está funcional. As pendências restantes são de código, schema/constraint e hardening.

---

## 2. Auditoria adicional desta conversa

Esta seção consolida o que aconteceu durante a conversa atual, separando correções reais, validações, tentativas rejeitadas e pendências.

### 2.1 Ajustes feitos por aqui que NÃO são workaround

#### Heartbeat imediato

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
A alteração corrigiu diretamente a função responsável pelo heartbeat.
Não criou wrapper, fallback paralelo, serviço auxiliar ou desvio de fluxo.
```

Risco residual:

```text
Baixo. A validação posterior confirmou compileall, healthcheck e pytest OK.
```

---

#### Formatação do package.json do Mini App

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
A alteração só normalizou JSON e preservou scripts existentes.
```

Risco residual:

```text
Baixo. Mini App build/check passou depois.
```

---

#### Correção de ambiente Node 22

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
Wrangler 4.95.0 exige Node >= 22.
Atualizar Node foi correção da dependência real, não desvio.
```

Risco residual:

```text
Baixo, desde que Node 22 continue instalado e package-lock.json validado seja versionado.
```

---

#### Correção de arkham_packs no Supabase

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

Classificação:

```text
CORREÇÃO DE SCHEMA
NÃO É WORKAROUND
```

Motivo:

```text
O Worker já esperava essas colunas.
Adicionar as colunas ao schema real corrige a fonte primária em vez de depender do fallback ArkhamDB.
```

Resultado validado:

```text
total_packs: 114
sem_cycle_position: 0
sem_position: 0
sem_chapter: 0
sem_total: 0
```

Risco residual:

```text
Baixo para /packs, desde que futuras sincronizações continuem populando essas colunas.
```

---

#### Preparação de target_chats para soft delete

Banco:

```text
public.target_chats
```

Colunas adicionadas:

```text
removed_at
removed_by_name
removed_by_user_id
```

Classificação:

```text
PREPARAÇÃO CORRETA DE SCHEMA
NÃO É WORKAROUND
```

Motivo:

```text
A mudança prepara o banco para substituir DELETE físico por PATCH enabled=false.
Isso corrige a modelagem de dados sem mascarar o problema.
```

Risco residual:

```text
Médio, porque o código do Worker ainda não foi alterado.
```

---

### 2.2 Ajustes/condições que são dívida técnica ou operação pendente

#### Dois virtualenvs no servidor

Locais:

```text
/opt/arkham_bot/venv
/opt/arkham_bot/.venv
```

Classificação:

```text
DÍVIDA OPERACIONAL
```

Motivo:

```text
O serviço systemd usa /opt/arkham_bot/venv.
Durante a validação foi criado/ativado .venv.
Dois ambientes Python no mesmo projeto podem causar validação em um ambiente e execução em outro.
```

Estado validado:

```text
/opt/arkham_bot/venv está OK.
filelock existe nesse venv.
pytest existe nesse venv.
healthcheck OK.
42 passed.
systemd active/running.
```

Ação correta:

```bash
sudo systemctl show arkham-bot -p ExecStart -p WorkingDirectory -p User
/opt/arkham_bot/venv/bin/python -m pytest -q /opt/arkham_bot
cd /opt/arkham_bot
rm -rf .venv
```

Status:

```text
PENDENTE OPCIONAL
```

---

#### package-lock.json alterados por npm install

Arquivos:

```text
miniapp/package-lock.json
worker/package-lock.json
```

Classificação:

```text
PENDÊNCIA DE VERSIONAMENTO
```

Motivo:

```text
Node 22 e npm install podem ter atualizado lockfiles.
Se o build/dry-run validado depende desses locks, eles devem ser versionados.
```

Ação correta:

```bash
cd /opt/arkham_bot
git status
git diff -- miniapp/package-lock.json worker/package-lock.json | head -80
git add miniapp/package-lock.json worker/package-lock.json
git commit -m "chore: update npm lockfiles after node 22 validation"
git push
```

Status:

```text
VERIFICAR SE JÁ FOI COMMITADO
```

---

#### Kernel pendente no Ubuntu

Indicação do sistema durante atualização:

```text
Running kernel: 6.14.0-1016-oracle
Expected kernel: 6.17.0-1014-oracle
```

Classificação:

```text
PENDÊNCIA OPERACIONAL
NÃO É BLOQUEANTE PARA APP/WORKER AGORA
```

Ação correta:

```text
Agendar reboot controlado da instância em janela segura.
```

Status:

```text
PENDENTE OPERACIONAL
```

---

### 2.3 Tentativa rejeitada que NÃO deve ser retomada

#### hardened.js / wrapper Worker

Durante a conversa foi considerada a criação de:

```text
worker/src/hardened.js
```

com mudança de entrada do Worker para interceptar rotas e delegar ao `index.js` original.

Classificação:

```text
WORKAROUND REJEITADO
NÃO APLICAR
```

Motivo:

```text
Criaria uma camada paralela para corrigir sintomas em vez de corrigir worker/src/index.js diretamente.
Isso tornaria a arquitetura menos clara, duplicaria lógica de autenticação/CORS e aumentaria a dívida técnica.
```

Estado real verificado:

```text
worker/src/hardened.js não existe no repositório.
worker/wrangler.toml continua apontando para src/index.js.
```

Regra permanente:

```text
Não criar hardened.js.
Não criar proxy interno.
Não duplicar handlers.
Não trocar wrangler.toml para arquivo intermediário.
Toda correção de Worker deve entrar diretamente em worker/src/index.js.
```

Status:

```text
CANCELADO / NÃO APLICADO
```

---

## 3. Banco Supabase validado

### 3.1 Tabelas principais existentes

Foram confirmadas no schema real:

```text
arkham_packs
audit_logs
bot_admins
bot_commands
bot_errors
bot_posted_cards
bot_posting_history
bot_settings
target_chats
```

Status:

```text
OK
```

---

### 3.2 arkham_packs corrigido

Foram adicionadas/populadas colunas:

```text
cycle_position
position
chapter
total
```

Validação retornou:

```text
total_packs: 114
sem_cycle_position: 0
sem_position: 0
sem_chapter: 0
sem_total: 0
```

Motivo:

```text
O Worker tenta usar arkham_packs no Supabase antes de cair para ArkhamDB.
Sem essas colunas, /packs falharia no Supabase e cairia sempre no fallback externo.
```

Status:

```text
OK
```

---

### 3.3 target_chats preparado para soft delete

Foram adicionadas colunas:

```text
removed_at
removed_by_name
removed_by_user_id
```

Motivo:

```text
O Worker ainda faz DELETE físico em destinos.
Para corrigir sem perda de histórico, o banco precisa aceitar PATCH com enabled=false e metadados de remoção.
```

Status:

```text
BANCO OK
CÓDIGO PENDENTE
```

---

### 3.4 Constraint problemática em target_chats

Constraint real encontrada:

```text
target_chats_chat_id_key | UNIQUE | chat_id
```

Problema:

```text
Essa constraint impede múltiplos registros para o mesmo chat_id.
Grupos com tópicos do Telegram usam o mesmo chat_id com message_thread_id diferente.
```

Risco:

```text
Não será possível cadastrar múltiplos tópicos do mesmo grupo como destinos independentes.
O Worker atual também usa on_conflict=chat_id, reforçando a limitação.
```

Correção correta:

```text
Alterar banco e Worker juntos.
Não remover a constraint antes de ajustar o código.
```

SQL futuro recomendado, somente junto da alteração do Worker:

```sql
alter table public.target_chats
  drop constraint if exists target_chats_chat_id_key;

create unique index if not exists target_chats_chat_id_thread_id_key
on public.target_chats (chat_id, coalesce(message_thread_id, 0));
```

E no Worker trocar:

```text
on_conflict=chat_id
```

por estratégia compatível com unicidade composta.

Status:

```text
PENDENTE
```

---

## 4. Workarounds, atalhos e dívida técnica identificados

### WRK-001 — Fallback de admin via variável de ambiente

Local:

```text
worker/src/index.js
getAdminAccess()
ALLOW_ADMIN_ENV_FALLBACK
ADMIN_TELEGRAM_USER_IDS
```

Descrição:

```text
Se Supabase não estiver configurado ou falhar, existe possibilidade de fallback por env quando ALLOW_ADMIN_ENV_FALLBACK=true.
```

Por que é workaround:

```text
Administração deveria depender da tabela bot_admins como fonte canônica.
Fallback por env pode mascarar falha de Supabase e criar comportamento diferente entre produção, homologação e debug.
```

Risco:

```text
- Permissão administrativa fora do banco.
- Dificulta auditoria.
- Pode permitir admin mesmo quando Supabase está quebrado.
```

Ação correta:

```text
Manter apenas como modo de emergência documentado e desativado por padrão.
Em produção, ALLOW_ADMIN_ENV_FALLBACK deve ser false ou ausente.
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

Descrição:

```text
/packs tenta Supabase e, se falhar, busca https://arkhamdb.com/api/public/packs/.
```

Por que pode ser workaround:

```text
Se Supabase deveria ser fonte primária confiável, fallback externo pode mascarar erro de schema, sincronização ou dados vazios.
```

Risco:

```text
- Diferença de dados entre Supabase e ArkhamDB.
- Falha intermitente externa pode afetar painel.
- Problemas no banco podem passar despercebidos.
```

Ação correta:

```text
Agora que arkham_packs foi corrigido, manter fallback apenas como degradação controlada.
Adicionar log sanitizado quando Supabase falhar e fallback for usado.
```

Status:

```text
PENDENTE
```

---

### WRK-003 — OAuth ArkhamDB marcado como stub/futuro

Local conhecido pelo histórico do projeto:

```text
src/arkham_bot/arkhamdb_oauth.py
```

Descrição:

```text
Módulo OAuth ArkhamDB foi mantido como stub/fase futura.
```

Por que é dívida técnica:

```text
Stub em produção pode confundir manutenção futura se parecer funcional.
```

Ação correta:

```text
Decidir formalmente:
1. manter como stub documentado e sem uso em runtime; ou
2. remover até a fase correta; ou
3. implementar de fato.
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

Descrição:

```text
Wrappers foram criados para preservar imports relativos antigos usados por telegram_handlers.py.
```

Por que pode ser dívida técnica:

```text
Resolve o erro de import sem refatorar completamente os imports antigos.
Não é necessariamente incorreto, mas mantém compatibilidade em vez de limpar a origem do acoplamento.
```

Risco:

```text
- Novos arquivos podem importar o wrapper em vez do módulo canônico.
- Dificulta entender a arquitetura real.
```

Ação correta:

```text
Planejar refatoração futura para trocar imports antigos pelos módulos canônicos:
- core/supabase_client.py
- core/config.py
- services/local_storage.py
- services/scheduler.py
Depois remover wrappers se não houver mais uso.
```

Status:

```text
ACEITO TEMPORARIAMENTE
PENDENTE DE LIMPEZA FUTURA
```

---

### WRK-005 — Dois virtualenvs no servidor

Locais:

```text
/opt/arkham_bot/venv
/opt/arkham_bot/.venv
```

Descrição:

```text
Foi criado .venv durante validação, mas o systemd usa /opt/arkham_bot/venv.
O venv do systemd está funcional.
```

Por que é dívida operacional:

```text
Dois ambientes Python podem gerar confusão.
```

Risco:

```text
- Instalar dependência em .venv e o serviço continuar usando venv.
- Validar em um ambiente e executar em outro.
```

Ação correta:

```text
Padronizar um único venv operacional.
Como systemd usa /opt/arkham_bot/venv e ele está validado, considerar remover .venv após confirmar que não está em uso.
```

Status:

```text
PENDENTE DE LIMPEZA OPERACIONAL
```

---

### WRK-006 — Processo manual de patch local por limitação do conector

Descrição:

```text
Foi sugerido aplicar patch localmente em worker/src/index.js porque o conector GitHub substitui arquivo inteiro e o arquivo é grande.
```

Classificação:

```text
NÃO É WORKAROUND DE CÓDIGO
É PROCESSO OPERACIONAL ACEITÁVEL SE O PATCH FOR DIRETO NO ARQUIVO REAL
```

Risco:

```text
- Aplicação manual pode gerar erro humano.
- Precisa ser validada com npm run dry-run antes de commit/push.
```

Regra:

```text
Patch local é aceitável somente se alterar diretamente worker/src/index.js.
Não é aceitável criar arquivo paralelo, wrapper ou entrada alternativa.
```

Status:

```text
ACEITÁVEL COM VALIDAÇÃO
```

---

### WRK-007 — Busca textual por termos explícitos não prova ausência de workaround

Durante esta revisão, buscas por termos como:

```text
workaround
hack
TODO
FIXME
stub
fallback
legacy
gambiarra
dívida técnica
temporary
```

não retornaram resultados relevantes no índice consultado.

Classificação:

```text
EVIDÊNCIA FRACA
NÃO PROVA AUSÊNCIA
```

Motivo:

```text
Workaround pode existir sem usar esses termos.
A validação precisa continuar por leitura estrutural de código e comportamento.
```

Status:

```text
REGISTRADO
```

---

## 5. Pendências reais de código

### PEND-001 — Soft delete de destinos

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
- removed_at=now
```

Por que precisa corrigir:

```text
Evita perda de histórico operacional e permite auditoria/reversão.
```

Status:

```text
PENDENTE
```

---

### PEND-002 — Guard explícito de backend em /bot-command

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
A função usa env.SUPABASE_URL.replace(...) sem guarda explícita no início.
```

Correção correta:

```text
Adicionar no início de handleBotCommand, antes de usar Supabase:
if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return backend_not_configured.
```

Por que precisa corrigir:

```text
Evita erro não padronizado se Worker estiver com env incompleto.
```

Status:

```text
PENDENTE
```

---

### PEND-003 — writeAuditLog falha silenciosamente

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
catch {} ignora erro de auditoria.
```

Correção correta:

```text
Registrar safeLog sanitizado quando audit_logs falhar.
Não vazar token, initData ou payload sensível.
```

Por que precisa corrigir:

```text
Ações administrativas não podem falhar sem rastreabilidade mínima.
```

Status:

```text
PENDENTE
```

---

### PEND-004 — /bot-runtime deve preferir value, não updated_at

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
O Worker lê last_seen de updated_at.
O heartbeat grava a data real em bot_settings.value.
```

Correção correta:

```text
Parsear rows[0].value como fonte primária.
Usar updated_at apenas como fallback.
```

Por que precisa corrigir:

```text
Se updated_at não refletir o valor real, o painel pode indicar status errado do bot.
```

Status:

```text
PENDENTE
```

---

### PEND-005 — Filtro source do histórico deve ser backend-side

Arquivos:

```text
worker/src/index.js
miniapp/src/App.jsx
```

Problema:

```text
Mini App filtra source client-side.
Isso quebra paginação e pode ocultar resultados incorretamente.
```

Correção correta:

```text
Worker /history aceitar source=manual|scheduled|command|auto|all.
Mini App enviar source na query.
Remover filtro local quando source não for all.
```

Por que precisa corrigir:

```text
Filtro com paginação deve ocorrer no banco, não na tela.
```

Status:

```text
PENDENTE
```

---

### PEND-006 — /ai-models público por decisão implícita

Arquivo:

```text
worker/src/index.js
```

Problema:

```text
/ai-models é acessível após CORS, sem requireAdmin.
```

Correção correta:

```text
Decidir explicitamente:
- se catálogo de modelos é público, documentar; ou
- se faz parte do painel admin, proteger com requireAdmin.
```

Recomendação:

```text
Proteger com requireAdmin, pois é endpoint do painel administrativo.
```

Status:

```text
PENDENTE DE DECISÃO / RECOMENDADO PROTEGER
```

---

### PEND-007 — API ausente abre painel visual no Mini App

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
Criar estado api_not_configured ou usar auth_error.
Não renderizar painel administrativo sem API configurada.
```

Por que precisa corrigir:

```text
Painel administrativo deve falhar fechado, não abrir em modo visual sem backend.
```

Status:

```text
PENDENTE
```

---

### PEND-008 — Unauthorized mostra LoadingGate

Arquivo:

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

Por que precisa corrigir:

```text
Usuário sem permissão não deve ver tela infinita de carregamento.
```

Status:

```text
PENDENTE
```

---

### PEND-009 — target_chats ainda não suporta múltiplos tópicos do mesmo grupo

Arquivos:

```text
worker/src/index.js
Supabase target_chats constraint
```

Problema:

```text
Banco tem UNIQUE(chat_id).
Worker usa on_conflict=chat_id.
```

Correção correta:

```text
Mudar constraint e código juntos.
Permitir múltiplos registros por chat_id quando message_thread_id for diferente.
```

Por que precisa corrigir:

```text
Telegram topics usam mesmo chat_id e message_thread_id diferente.
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

Aviso visto no log:

```text
PTBUserWarning: If 'per_message=False', 'CallbackQueryHandler' will not be tracked for every message.
```

Classificação:

```text
AVISO NÃO CRÍTICO
PENDÊNCIA DE LIMPEZA FUTURA
```

Risco:

```text
Pode haver comportamento não ideal em callbacks dentro de ConversationHandler.
Não bloqueia runtime, pois bot subiu, scheduler iniciou e testes passaram.
```

Ação correta:

```text
Revisar ConversationHandler de card_conv_handler e search_conv_handler.
Decidir explicitamente per_message/per_chat/per_user conforme comportamento desejado.
```

Status:

```text
PENDENTE BAIXO
```

---

### PEND-011 — Cloudflare Worker sem SUPABASE_SERVICE_ROLE_KEY visível no dry-run

Durante dry-run, bindings exibidos:

```text
env.SUPABASE_URL
env.ALLOWED_ORIGINS
```

`SUPABASE_SERVICE_ROLE_KEY` não apareceu no resumo.

Classificação:

```text
PENDÊNCIA DE VALIDAÇÃO DE SECRET
```

Possível motivo:

```text
Wrangler pode ocultar secrets no dry-run, ou o secret pode não estar configurado no ambiente Cloudflare.
```

Ação correta:

```bash
cd /opt/arkham_bot/worker
npx wrangler secret list
```

Verificar se existe:

```text
SUPABASE_SERVICE_ROLE_KEY
TELEGRAM_BOT_TOKEN
```

Status:

```text
PENDENTE DE VALIDAÇÃO CLOUDFLARE
```

---

## 6. Pendências operacionais

### OPS-001 — Commitar lockfiles se ainda não foram commitados

Arquivos:

```text
miniapp/package-lock.json
worker/package-lock.json
```

Motivo:

```text
npm install com Node 22 atualizou locks.
Se foram validados, devem ser versionados para reprodutibilidade.
```

Comandos:

```bash
git status
git diff -- miniapp/package-lock.json worker/package-lock.json | head -80
git add miniapp/package-lock.json worker/package-lock.json
git commit -m "chore: update npm lockfiles after node 22 validation"
```

Status:

```text
VERIFICAR
```

---

### OPS-002 — Limpar .venv duplicado

Motivo:

```text
Systemd usa /opt/arkham_bot/venv.
.venv foi criado durante validação e pode confundir.
```

Ação opcional:

```bash
cd /opt/arkham_bot
rm -rf .venv
```

Somente depois de confirmar:

```bash
sudo systemctl show arkham-bot -p ExecStart
```

Status:

```text
PENDENTE OPCIONAL
```

---

### OPS-003 — Kernel pendente no Ubuntu

Durante atualização do Node, o sistema indicou kernel pendente:

```text
Running kernel: 6.14.0-1016-oracle
Expected kernel: 6.17.0-1014-oracle
```

Ação:

```text
Agendar reboot controlado da instância quando possível.
Não é bloqueante para o Worker/Mini App, mas é pendência operacional.
```

Status:

```text
PENDENTE OPERACIONAL
```

---

### OPS-004 — Validar secrets reais do Worker antes de deploy

Motivo:

```text
Dry-run passou, mas isso não garante que secrets de produção estejam configurados corretamente no Cloudflare.
```

Comandos:

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

## 7. Ordem correta de correção sem workaround

### Fase 1 — Worker direto em worker/src/index.js

```text
1. Corrigir handleDeleteDestination para soft delete.
2. Corrigir handleBotCommand com backend_not_configured.
3. Corrigir writeAuditLog para logar falha sanitizada.
4. Corrigir handleBotRuntime para usar value como fonte primária.
5. Proteger /ai-models com requireAdmin ou documentar explicitamente como público.
6. Corrigir /history para aceitar source backend-side.
```

Proibido:

```text
- Criar worker/src/hardened.js.
- Criar wrapper de rotas.
- Alterar wrangler.toml para apontar para arquivo intermediário.
- Duplicar handlers.
```

---

### Fase 2 — Mini App direto em miniapp/src/App.jsx e componentes reais

```text
1. API ausente deve mostrar gate específico.
2. Unauthorized deve mostrar gate específico.
3. Histórico deve enviar source para backend.
4. Remover dependência de filtro source client-side para paginação.
```

---

### Fase 3 — Constraint de tópicos

Somente depois de corrigir Worker:

```text
1. Alterar constraint UNIQUE(chat_id).
2. Criar unicidade composta chat_id + message_thread_id.
3. Ajustar on_conflict no Worker.
4. Testar cadastro de dois tópicos do mesmo grupo.
```

---

## 8. Validação obrigatória após cada fase

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

---

## 9. Definition of Done

O trabalho só estará concluído quando:

```text
- Não houver wrapper/workaround novo.
- Todas as correções forem feitas nos arquivos reais.
- Worker dry-run passar.
- Mini App build/check passar.
- pytest passar.
- systemd subir sem erro.
- target_chats aceitar soft delete.
- /bot-runtime mostrar heartbeat real.
- /history filtrar source pelo backend.
- /destinations não apagar dados fisicamente.
- decisão sobre múltiplos tópicos for implementada no banco e Worker.
- secrets reais do Cloudflare estiverem validados.
```

---

## 10. Próxima ação recomendada

Corrigir diretamente:

```text
worker/src/index.js
```

Começar por:

```text
handleDeleteDestination()
```

Motivo:

```text
O banco já foi preparado com removed_at, removed_by_name e removed_by_user_id.
É a menor correção real e elimina DELETE físico sem exigir arquitetura paralela.
```

Não aplicar nenhuma correção via wrapper.
