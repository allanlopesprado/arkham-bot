# Mini App e Worker — auditoria de workarounds, erros operacionais e pendências

Este arquivo é a documentação operacional canônica desta auditoria do Mini App administrativo, Worker Cloudflare, Supabase e integrações adjacentes do Arkham Bot.

Regra principal desta revisão: **não aceitar workaround, wrapper paralelo, proxy interno, rota duplicada, arquivo intermediário ou desvio de arquitetura para mascarar problema real**.

As correções devem ser feitas diretamente nos arquivos responsáveis, preservando a arquitetura existente. Qualquer solução que funcione por fora do fluxo real deve ser tratada como gambiarra até prova contrária.

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

Resultado: o ambiente de execução está funcional. As pendências restantes são de código, schema/constraint, secrets/deploy e limpeza operacional.

---

## 2. Ajustes feitos nesta conversa e classificação

### 2.1 Heartbeat imediato

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

### 2.2 Formatação do package.json do Mini App

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

### 2.3 Node 22

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

### 2.4 arkham_packs no Supabase

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

### 2.5 target_chats preparado para soft delete

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

## 3. Erros operacionais do assistente nesta conversa

Esta seção registra o que foi feito ou sugerido de forma inadequada durante a conversa, para não repetir.

### ERR-001 — Proposta de wrapper `worker/src/hardened.js`

O que aconteceu:

```text
Foi sugerido criar worker/src/hardened.js para interceptar rotas problemáticas e delegar ao Worker original.
```

Classificação:

```text
ERRO DO ASSISTENTE
WORKAROUND REJEITADO
NÃO APLICAR
```

Por que foi errado:

```text
Criaria camada paralela para corrigir sintomas em vez de corrigir worker/src/index.js diretamente.
Duplicaria lógica de CORS/autenticação/autorização.
Aumentaria complexidade e dívida técnica.
Poderia esconder bugs reais do Worker principal.
```

Estado real verificado:

```text
worker/src/hardened.js não existe no repositório.
worker/wrangler.toml continua apontando para src/index.js.
Nenhum wrapper foi aplicado.
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

### ERR-002 — Risco de substituir arquivo grande/truncado pelo conector GitHub

O que aconteceu:

```text
Foi cogitado corrigir worker/src/index.js diretamente via GitHub update_file.
O arquivo é grande e as leituras pelo conector foram truncadas.
```

Classificação:

```text
RISCO OPERACIONAL IDENTIFICADO
NÃO EXECUTAR UPDATE CEGO
```

Por que seria errado:

```text
Substituir arquivo grande sem ter conteúdo completo pode apagar código não lido.
A ferramenta update_file substitui o arquivo inteiro, não aplica patch parcial.
```

Regra correta:

```text
Para worker/src/index.js, usar patch local no servidor ou diff completo obtido de clone local.
Nunca substituir o arquivo inteiro a partir de conteúdo truncado.
```

Status:

```text
NENHUMA SUBSTITUIÇÃO CEGA FOI APLICADA
```

---

### ERR-003 — Sugestão de patch manual sem entregar diff validável completo

O que aconteceu:

```text
Foi sugerido editar manualmente handleDeleteDestination() no nano.
```

Classificação:

```text
PROCESSO ACEITÁVEL EM EMERGÊNCIA
MAS NÃO IDEAL
```

Por que é risco:

```text
Edição manual pode gerar erro humano.
Fica mais difícil auditar exatamente o que mudou.
Pode divergir do repositório se não houver git diff antes do commit.
```

Forma correta daqui para frente:

```text
Gerar patch/diff explícito e pequeno.
Aplicar localmente com git apply quando possível.
Depois rodar npm run dry-run e git diff.
```

Comandos esperados:

```bash
cd /opt/arkham_bot
git diff -- worker/src/index.js
cd /opt/arkham_bot/worker
npm run dry-run
```

Status:

```text
PENDÊNCIA DE PROCESSO
```

---

### ERR-004 — Criação/uso de `.venv` quando systemd usava `venv`

O que aconteceu:

```text
Foi orientado criar/usar /opt/arkham_bot/.venv durante validação.
Depois foi confirmado que o systemd usa /opt/arkham_bot/venv.
```

Classificação:

```text
ERRO OPERACIONAL PARCIAL
GEROU DÍVIDA DE AMBIENTE DUPLICADO
```

Por que é problema:

```text
Dois virtualenvs no mesmo projeto confundem instalação e validação.
Pode-se instalar dependência em .venv enquanto o serviço roda em venv.
```

Estado atual:

```text
/opt/arkham_bot/venv está validado e é o ambiente correto do systemd.
/opt/arkham_bot/.venv é redundante se ainda existir.
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
PENDENTE OPCIONAL DE LIMPEZA
```

---

### ERR-005 — Afirmar “ambiente OK” antes de resolver pendências de código

O que aconteceu:

```text
Foi corretamente validado que o ambiente estava OK, mas isso não significa que a aplicação estava completamente corrigida.
```

Classificação:

```text
RISCO DE COMUNICAÇÃO
```

Por que pode confundir:

```text
Ambiente OK não equivale a hardening completo.
Dependências, tests e systemd passam, mas Worker/Mini App ainda têm pendências funcionais.
```

Regra correta:

```text
Separar sempre:
- ambiente validado
- banco validado
- código corrigido
- deploy validado
```

Status:

```text
REGISTRADO
```

---

### ERR-006 — SQL de unicidade com `coalesce(message_thread_id, 0)` precisa de cautela

O que aconteceu:

```text
Foi sugerida futura unicidade por chat_id + coalesce(message_thread_id, 0).
```

Classificação:

```text
POTENCIAL ARMADILHA TÉCNICA
```

Por que exige cautela:

```text
Um índice único com expressão pode não casar diretamente com on_conflict do PostgREST da forma esperada.
PostgREST normalmente trabalha melhor com constraint/colunas explícitas para upsert.
```

Correção mais segura:

```text
Antes de alterar constraint, validar estratégia com PostgREST/Supabase.
Preferir uma coluna normalizada explícita, por exemplo thread_key, ou constraint composta real em colunas simples, se compatível.
```

Opções a validar antes de executar:

```text
1. Usar UNIQUE(chat_id, message_thread_id) e tratar null corretamente na aplicação.
2. Criar coluna generated/stored thread_key = coalesce(message_thread_id, 0) e UNIQUE(chat_id, thread_key).
3. Evitar upsert por on_conflict e fazer fluxo explícito: buscar destino por chat_id + thread_id, depois PATCH ou POST.
```

Regra:

```text
Não aplicar SQL de constraint de tópicos sem ajustar e validar o Worker junto.
```

Status:

```text
PENDENTE DE DESENHO CORRETO
```

---

### ERR-007 — Busca textual por termos de gambiarra não prova ausência de gambiarra

O que aconteceu:

```text
Foram buscados termos como workaround, hack, TODO, FIXME, stub, fallback, legacy, temporary.
```

Classificação:

```text
EVIDÊNCIA FRACA
```

Por que é insuficiente:

```text
Workaround pode existir sem esses termos no código.
A validação precisa ser estrutural: fluxo, dependências, contratos, schema e runtime.
```

Regra:

```text
Não concluir “sem workaround” apenas por busca textual.
Usar leitura de código e testes comportamentais.
```

Status:

```text
REGISTRADO
```

---

## 4. Workarounds, atalhos e dívida técnica existentes no projeto

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

### WRK-003 — OAuth ArkhamDB como stub/futuro

Local:

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
Wrappers preservam imports relativos antigos usados por telegram_handlers.py.
```

Por que pode ser dívida técnica:

```text
Resolve erro de import sem refatorar completamente os imports antigos.
Não é necessariamente incorreto, mas mantém compatibilidade em vez de limpar a origem do acoplamento.
```

Ação correta:

```text
Planejar refatoração futura para trocar imports antigos pelos módulos canônicos.
Depois remover wrappers se não houver mais uso.
```

Status:

```text
ACEITO TEMPORARIAMENTE
PENDENTE DE LIMPEZA FUTURA
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
Adicionar backend_not_configured antes de usar Supabase.
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
Worker /history aceitar source.
Mini App enviar source na query.
Remover filtro local quando source não for all.
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
Decidir explicitamente: público documentado ou protegido por requireAdmin.
Recomendação: proteger, por ser endpoint do painel administrativo.
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

Status:

```text
PENDENTE
```

---

### PEND-008 — Unauthorized mostra LoadingGate

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

### PEND-009 — target_chats não suporta múltiplos tópicos do mesmo grupo

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
Validar estratégia de upsert com PostgREST antes de aplicar.
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

Ação correta:

```text
Revisar card_conv_handler e search_conv_handler.
Decidir explicitamente per_message/per_chat/per_user conforme comportamento desejado.
```

Status:

```text
PENDENTE BAIXO
```

---

### PEND-011 — Secrets reais do Cloudflare precisam ser validados

Durante dry-run, bindings exibidos:

```text
env.SUPABASE_URL
env.ALLOWED_ORIGINS
```

`SUPABASE_SERVICE_ROLE_KEY` e `TELEGRAM_BOT_TOKEN` não foram confirmados visualmente no resumo.

Ação correta:

```bash
cd /opt/arkham_bot/worker
npx wrangler secret list
```

Secrets esperados:

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

Comandos:

```bash
cd /opt/arkham_bot
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

Comandos:

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

Ação:

```text
Agendar reboot da instância em janela segura.
```

Status:

```text
PENDENTE OPERACIONAL
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
- Substituir index.js inteiro a partir de conteúdo truncado.
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
1. Definir estratégia correta para múltiplos tópicos.
2. Validar compatibilidade com PostgREST upsert/on_conflict.
3. Alterar constraint ou fluxo de POST/PATCH.
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

Cloudflare secrets:

```bash
cd /opt/arkham_bot/worker
npx wrangler secret list
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
