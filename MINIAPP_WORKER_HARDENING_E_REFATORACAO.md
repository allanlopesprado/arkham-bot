# Mini App e Worker — plano profissional completo de hardening, UX, menus, validação e refatoração

Este arquivo é a especificação operacional canônica para a IA executora evoluir o Mini App administrativo e o Worker do Arkham Bot a nível profissional. Ele deve ser lido inteiro antes de qualquer alteração. O objetivo é reduzir risco operacional, corrigir segurança, melhorar UX, organizar menus, validar runtime real, documentar pendências e refatorar `miniapp/src/main.jsx` sem quebrar o bot Python.

## 1. Instrução principal para a IA executora

Leia este arquivo inteiro antes de alterar código. Execute as fases na ordem indicada. Não pule validações. Não peça confirmação para tarefas já descritas aqui. Se uma etapa falhar, corrija apenas o problema diretamente relacionado à etapa e rode a validação novamente. Se uma mudança exigir migration, secret, deploy externo, criação de tabela, alteração destrutiva ou decisão de produto não descrita neste arquivo, registre como pendência e não implemente sem autorização explícita.

Não faça commit automático antes de validar. Ao final, responda no formato obrigatório definido no final deste arquivo.

## 2. Objetivo do trabalho

Transformar o Mini App em um painel administrativo estável, seguro, auditável, previsível e sustentável, preservando o funcionamento do bot Python. O app deve operar bem dentro do Telegram em mobile, com autenticação robusta, menus claros, validação de payloads, prevenção de erro humano, observabilidade operacional e rollback possível.

## 3. Regras obrigatórias

- Não alterar `.env`, secrets, tokens, chaves ou credenciais.
- Não imprimir `SUPABASE_SERVICE_ROLE_KEY`, `TELEGRAM_BOT_TOKEN`, `x-telegram-init-data`, Authorization headers, service role ou payloads completos de settings.
- Não alterar migrations/banco sem autorização explícita.
- Não alterar backend Python, exceto para corrigir import quebrado diretamente relacionado a `/status`, `/cotd` ou processamento de comandos do Mini App.
- Não recriar documentação antiga.
- Não alterar `README.md` nesta tarefa, salvo autorização explícita.
- Não remover fallback ArkhamDB enquanto o banco local puder estar vazio.
- Não depender somente do front para segurança; Worker deve validar autorização e payload.
- Não fazer refatoração estrutural antes de corrigir P0 e passar build.
- Se uma fase quebrar build, reverter somente a última alteração.

## 4. Definition of Done

Só considerar o trabalho concluído quando todos estes itens estiverem satisfeitos ou formalmente reportados como `NÃO EXECUTADO + motivo`:

```text
- Python compileall passou.
- Python healthcheck passou ou retornou apenas warnings esperados por falta de ambiente real.
- Testes Python disponíveis passaram, se existirem.
- Mini App build passou.
- Mini App check passou.
- Worker dry-run passou.
- Auth fail-open foi removido.
- Logs sensíveis foram removidos ou protegidos por DEV.
- /status é admin-only.
- /packs prefere Supabase com fallback ArkhamDB.
- Não há segredo no bundle/front.
- Fluxo admin no Telegram foi validado ou registrado como pendente.
- Fluxo não-admin bloqueado foi validado ou registrado como pendente.
- Fluxo postagem manual foi validado ou registrado como pendente.
- Fluxo salvar configurações foi validado ou registrado como pendente.
- Risco residual foi classificado como baixo, médio ou alto com justificativa.
```

## 5. Matriz de severidade

Classifique todo achado assim:

```text
CRÍTICO
- Expõe secret/token/service role.
- Permite acesso admin sem validação.
- Quebra bot Python em produção.
- Impede postagem automática/manual.
- Worker retorna 500 em endpoints centrais como /me, /settings, /bot-command.
- Perde dados ou executa ação destrutiva sem confirmação.

ALTO
- Não salva configurações.
- Duplica comandos por clique duplo.
- Sync roda simultaneamente sem controle.
- /status, /settings, /commands ou /packs quebram para admin.
- Payload inválido é aceito pelo Worker.
- Admin comum consegue executar ação owner-only.

MÉDIO
- UX confusa.
- Tela sem empty/error state.
- Erro técnico sem mensagem amigável.
- Histórico/fila sem paginação adequada.
- Dados operacionais incompletos.

BAIXO
- Texto, layout, organização, ícone, nomenclatura ou melhoria futura sem impacto operacional imediato.
```

Prioridade de correção: CRÍTICO > ALTO > MÉDIO > BAIXO.

## 6. Visão alvo dos menus

```text
Home
├── Operação
│   ├── Postagem
│   ├── Agenda
│   ├── Fila
│   └── Histórico
├── Configuração
│   ├── IA
│   ├── Banco de Dados
│   ├── Destinos
│   └── Administradores
├── Sistema
│   ├── Manutenção
│   ├── Saúde
│   └── Aplicativo
```

A Home deve ser um hub. Não deve haver excesso de botões soltos. Cada menu precisa ter nome curto, subtítulo opcional, ícone consistente e badge quando houver alerta.

## 7. Matriz tela × endpoint

Use esta matriz para validar dependências e evitar quebrar telas ao alterar Worker:

```text
Home
- /me
- /overview
- /status

Postagem
- /cards
- /bot-command
- futuro /destinations

Agenda
- /settings
- /status ou /overview para resumo operacional

IA
- /settings
- futuro /ai-models

Banco de Dados
- /status
- /packs
- /bot-command com sync_arkhamdb
- /overview

Fila
- /commands
- /commands/:id
- futuro /commands/:id/retry

Histórico
- /history

Destinos
- futuro /destinations
- futuro /destinations/:id
- futuro /test-message

Administradores
- futuro /admins
- futuro /admins/:id

Manutenção
- /bot-command
- /commands

Saúde
- /health
- /status
- futuro /health/deep
- futuro /bot-runtime

Aplicativo
- /me
- /bot-info
```

## 8. Matriz role × permissão

```text
owner
- Pode acessar todo o painel.
- Pode gerenciar admins.
- Pode gerenciar destinos.
- Pode alterar configurações.
- Pode executar manutenção.
- Pode acionar sync/reset/limpeza.

admin
- Pode acessar operação normal.
- Pode postar carta.
- Pode alterar agenda, IA e configurações operacionais se permitido.
- Pode ver banco, fila, histórico e saúde.
- Não pode remover owner.
- Não pode gerenciar lista crítica de admins se a tela owner-only existir.

member/none
- Não pode acessar o painel.
- Deve receber erro amigável de acesso negado.
```

Regra: todo endpoint administrativo deve validar role no Worker, nunca apenas no front.

## 9. Tabelas esperadas pelo painel

Validar existência e uso seguro. Se alguma tabela não existir, registrar pendência; não criar migration sem autorização.

```text
bot_settings
- Configurações gerais, agenda, IA, filtros e chat padrão.

bot_admins
- Controle de administradores por Telegram user id e role.

bot_commands
- Fila de comandos emitidos pelo Mini App para o bot Python processar.

arkham_cards
- Cartas sincronizadas localmente.

arkham_packs
- Packs/ciclos sincronizados localmente.

target_chats ou tabela equivalente
- Destinos, grupos, canais e tópicos Telegram.

daily_card_posts ou histórico equivalente
- Histórico de cartas postadas.

error_logs, posting_history, sync_logs ou equivalente
- Diagnóstico, erros e eventos operacionais, se existir.
```

## 10. P0 — Correções obrigatórias imediatas

### 10.1 Validar wrappers Python

Validar estes arquivos:

```text
src/arkham_bot/handlers/supabase_client.py
src/arkham_bot/handlers/config.py
src/arkham_bot/handlers/local_storage.py
src/arkham_bot/handlers/scheduler.py
```

Conteúdo esperado de `supabase_client.py`:

```python
"""Compatibility wrapper for legacy handler-local imports.

Runtime handlers should use ``arkham_bot.core.supabase_client`` directly.
This module exists to keep older relative imports working while the
handler module is consolidated.
"""

from ..core.supabase_client import SupabaseRestClient, get_supabase_client

__all__ = ["SupabaseRestClient", "get_supabase_client"]
```

Conteúdo esperado de `config.py`:

```python
"""Compatibility wrapper for legacy handler-local config imports."""

from ..core.config import *  # noqa: F403
```

Conteúdo esperado de `local_storage.py`:

```python
"""Compatibility wrapper for legacy handler-local local_storage imports."""

from ..services.local_storage import *  # noqa: F403
```

Conteúdo esperado de `scheduler.py`:

```python
"""Compatibility wrapper for legacy handler-local scheduler imports."""

from ..services.scheduler import *  # noqa: F403
```

Comandos:

```bash
grep -n "from \.supabase_client\|from \.config\|from \.local_storage\|from \.scheduler" src/arkham_bot/handlers/telegram_handlers.py || true
python -m compileall -q .
python main.py healthcheck
```

Critério: `/status` e `/cotd` não podem quebrar por `ModuleNotFoundError`.

### 10.2 Corrigir fail-open do Mini App

Arquivo:

```text
miniapp/src/main.jsx
```

Localizar o Auth Gate que chama:

```javascript
apiFetch('/me')
```

Proibido:

```javascript
.catch(() => setAuthState('ready'))
```

Obrigatório:

```javascript
.catch(() => {
  setAuthState('auth_error');
});
```

Adicionar tratamento visual para `auth_error`:

```text
Não foi possível validar o acesso administrativo. Reabra pelo Telegram ou verifique o Worker.
```

Critério: se `/me` falhar por rede, CORS, Worker fora, 500 ou JSON inválido, o painel não abre.

### 10.3 Remover logs sensíveis do `saveSettings()`

Remover ou proteger com `import.meta.env.DEV`:

```javascript
console.log('[saveSettings] payload:', ...)
console.log('[saveSettings] response ok=%s status=%s', ...)
console.error('[saveSettings] error:', ...)
console.log('[saveSettings] returned day_config:', ...)
```

Critério: produção não deve logar `telegram_chat_id`, `day_config`, payload de settings ou detalhes operacionais sensíveis.

### 10.4 Adicionar `check` no Mini App

Arquivo:

```text
miniapp/package.json
```

Adicionar:

```json
"check": "vite build"
```

### 10.5 Tornar `/status` admin-only

Arquivo:

```text
worker/src/index.js
```

Na rota `/status`, trocar `requireAuth` por `requireAdmin`:

```javascript
const auth = await requireAdmin(request, env, ao, '/status');
if (auth.response) return auth.response;
return handleStatus(request, env, ao);
```

### 10.6 `/packs` deve preferir Supabase

`handleGetPacks` deve tentar primeiro:

```text
arkham_packs: code,name,cycle_position,position,chapter,total
```

Resposta se Supabase tiver dados:

```javascript
{ ok: true, packs, source: 'supabase' }
```

Fallback obrigatório para ArkhamDB pública quando Supabase falhar ou estiver vazio.

## 11. P1 — Validação profissional por tela

### Home

Critérios:

- Mostra badge de fila pendente/falha.
- Mostra alerta se Worker ou Supabase estiverem com erro.
- Não mostra informação técnica crua na Home.
- Agrupa menus em Operação, Configuração e Sistema.
- Não duplica funções em múltiplos lugares sem necessidade.

### Postagem

Deve conter:

- Busca por código/nome.
- Preview mínimo da carta selecionada.
- Tipo, pack e ciclo da carta.
- Aviso se a carta já foi postada.
- Destino selecionável.
- Botão `Postar agora`.
- Botão `Repostar carta`.
- Botão `Pular carta`.
- Estado de sucesso/erro do comando enfileirado.

Critérios:

- `repost_card` e `skip_card` devem exigir `card_code`.
- `post_now` pode aceitar payload vazio para escolha automática.
- Clique duplo não pode criar dois comandos.
- Após enfileirar, atualizar fila/overview.
- Se destino estiver desativado, não permitir envio.

### Agenda

A agenda deve sair de `Configurações` e virar menu próprio.

Critérios:

- Se `Todos os dias` estiver ativo, ele prevalece.
- Se estiver inativo, usar configuração de cada dia.
- Não salvar postagem automática sem dia ativo.
- Não salvar horário inválido.
- Não permitir estado visual que pareça salvo quando está pendente.
- Exibir resumo por dia: horários, ciclos e tipos.

### IA

Critérios:

- Modelos não devem ficar duplicados indefinidamente no front e Worker.
- Criar futuro endpoint `/ai-models`.
- Se modelo escolhido não for suportado, mostrar erro amigável.
- Deixar claro quando IA não roda em post manual por `ai_auto_only=true`.

### Banco de Dados

Critérios:

- `last_sync` deve vir de fonte confiável, não apenas do último comando criado.
- `/packs` deve refletir `arkham_packs` local quando possível.
- Botão sync deve confirmar antes de enfileirar.
- Se sync estiver em execução, bloquear novo sync ou avisar.

### Fila

Critérios:

- Não mostrar JSON bruto por padrão.
- Detalhe técnico deve ficar em `details`.
- Comando já processando não deve ser cancelado sem regra explícita.
- Status deve ter badge visual consistente.

### Histórico

Critérios:

- Filtro por data.
- Busca por código/nome.
- Paginação.
- Link ArkhamDB.
- Link Telegram quando possível.
- Badge sucesso/falha.

### Destinos

Novo menu recomendado.

Dados:

```text
chat_id
title
message_thread_id
enabled
is_default
description
created_at
updated_at
```

Critérios:

- Postagem manual permite escolher destino.
- Postagem automática usa destino padrão.
- Destino sem permissão do bot deve ser sinalizado.
- Message Thread ID deve ficar explícito para tópicos.

### Administradores

Novo menu restrito a `owner`.

Critérios:

- Apenas `owner` gerencia admins.
- Não permitir remover o último `owner`.
- Admin comum não promove usuários.
- Toda alteração deve registrar `updated_by`.

### Manutenção

Critérios:

- Ações destrutivas usam confirmação Telegram com botão destrutivo.
- Cada ação gera comando rastreável.
- Exibir resultado do comando, não assumir sucesso imediato.

### Saúde

Critério: Saúde deve responder à pergunta “o bot está funcionando agora e vai postar na hora certa?”.

Deve mostrar:

```text
Worker online
Supabase online
Bot Python online
Scheduler ativo
Polling/command worker ativo
Próxima postagem
Última postagem
Último erro
Último heartbeat
Versão/commit em execução
Ambiente
```

### Aplicativo

Critérios:

- Dados técnicos ficam recolhidos em `details`.
- Não exibir `initData` completo.
- Exibir somente tamanho/presença da sessão.

## 12. P2 — Padrões profissionais de UX

Cada tela deve implementar:

```text
loading
empty
ready
error
saving/sending
success
```

Cada erro deve ter:

```text
Título amigável
Descrição curta
Detalhe técnico opcional recolhido
Ação recomendada
```

Prevenção obrigatória:

```text
Confirmação em ação destrutiva
Botão desabilitado durante envio
Proteção contra clique duplo
Aviso de alterações não salvas
Validação antes de enviar para Worker
Validação duplicada no Worker
Resumo antes de salvar agenda complexa
```

Feedback visual:

```text
Badges ok/warn/err/pending
Spinner apenas em operação real
Haptic feedback em sucesso/erro/seleção
MainButton apenas com alteração pendente
BackButton coerente
```

Acessibilidade mínima:

```text
Botões com texto
Ícones não são única informação
Inputs com label
Disabled visível
Área de toque adequada
Não depender só de cor
```

## 13. P3 — Segurança, auditoria, logs e rate limit

### Política de logs

Pode logar:

```text
command_type
status
erro sanitizado
telegram_user_id
source seguro
request_id
```

Não pode logar:

```text
token
service role
initData completo
authorization header
payload sensível completo
secrets
```

### Auditoria

Toda ação administrativa deve registrar, quando houver suporte de banco:

```text
requested_by_telegram_user_id
requested_by_name
command_type
target_chat_id
payload sanitizado
created_at
status
result
last_error
```

Para alteração direta de settings/admins/destinos:

```text
updated_by
updated_at
previous_value quando seguro
new_value quando seguro
```

### Rate limit e abuso

Mesmo admin deve ter proteção contra abuso:

```text
bloquear múltiplos sync simultâneos
bloquear duplo clique em bot-command
limitar refresh automático agressivo
limitar busca muito ampla
limitar comandos destrutivos repetidos
```

### Idempotência

Garantir ou registrar pendência:

```text
post_now não duplica por clique duplo
sync_arkhamdb não executa duas vezes em paralelo
clear_queue afeta apenas comandos pendentes
retry não duplica comando processado
cancelar comando processando tem regra explícita
```

## 14. P4 — Worker e contratos de API

Endpoints atuais a manter:

```text
/me
/status
/overview
/settings
/commands
/commands/:id
/cards
/packs
/history
/bot-info
/bot-command
/health
```

Endpoints recomendados:

```text
/ai-models
/destinations
/destinations/:id
/admins
/admins/:id
/health/deep
/bot-runtime
/test-message
/commands/:id/retry
```

Formato de sucesso:

```json
{ "ok": true }
```

Formato de erro:

```json
{
  "error": "machine_readable_code",
  "detail": "technical detail safe to show",
  "request_id": "optional"
}
```

Códigos recomendados:

```text
invalid_telegram_init_data
unauthorized
forbidden_owner_only
origin_not_allowed
method_not_allowed
not_found
invalid_json
invalid_command_payload
settings_fetch_failed
settings_upsert_failed
commands_fetch_failed
cards_search_failed
packs_fetch_failed
history_fetch_failed
bot_info_fetch_failed
backend_not_configured
rate_limited
conflict_already_running
```

## 15. P5 — Refatoração do `main.jsx`

Executar somente depois de P0 e P1 estarem validados.

Estrutura alvo:

```text
miniapp/src/
  main.jsx
  App.jsx
  api.js
  telegram.js
  i18n.js
  settings.js
  constants.js
  icons.jsx
  components/
    Badge.jsx
    Notice.jsx
    Section.jsx
    Row.jsx
    MenuRow.jsx
    DangerRow.jsx
    ToggleRow.jsx
    SelectRow.jsx
    InfoTooltip.jsx
    Spinner.jsx
    CardResult.jsx
    CommandRow.jsx
    ChatIdInputRow.jsx
    DayScheduleRow.jsx
  screens/
    HomeScreen.jsx
    PostScreen.jsx
    ScheduleScreen.jsx
    SettingsScreen.jsx
    DayDetailScreen.jsx
    AiScreen.jsx
    DatabaseScreen.jsx
    QueueScreen.jsx
    HistoryScreen.jsx
    DestinationsScreen.jsx
    AdminsScreen.jsx
    MaintenanceScreen.jsx
    HealthScreen.jsx
    AppSettingsScreen.jsx
    LanguageScreen.jsx
```

Ordem:

```text
1. telegram.js
2. api.js
3. i18n.js
4. constants.js e settings.js
5. icons.jsx
6. componentes simples
7. componentes complexos
8. screens
9. App.jsx
10. main.jsx como bootstrap
```

`main.jsx` final:

```jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(<App />);
```

Após cada etapa:

```bash
cd miniapp
npm run build
```

## 16. P6 — Remover, migrar e manter

### Remover

```text
Logs de produção em saveSettings
Fallback que libera painel sem admin confirmado
JSON bruto aberto por padrão
Duplicação permanente de modelos IA no front e Worker
Busca primária de packs na ArkhamDB quando Supabase local estiver populado
Menus misturados sem domínio claro
```

### Migrar

```text
Agenda para menu próprio
Destinos para menu próprio
Admins para menu próprio owner-only
Modelos IA para /ai-models
Diagnóstico do bot Python para /bot-runtime
Status de sync para fonte confiável no banco
```

### Manter

```text
Telegram theme variables
Safe area handling
Haptic feedback
Telegram MainButton
Telegram BackButton
Fallback ArkhamDB de packs
Worker como única camada entre Mini App e Supabase
```

## 17. P7 — Diagnóstico avançado futuro

Criar futuramente tabela/registro de runtime, somente com autorização para migration:

```text
bot_runtime_status
- id
- process_name
- status
- last_heartbeat_at
- version
- git_commit
- scheduler_enabled
- next_post_at
- last_post_at
- last_error
- updated_at
```

Objetivo: a tela Saúde deve mostrar se o bot Python está vivo e se a próxima postagem está planejada corretamente.

## 18. P8 — Release, deploy e rollback

### Plano de release

```text
1. Confirmar git status limpo antes de começar.
2. Criar branch de trabalho se possível.
3. Aplicar P0.
4. Rodar validações locais.
5. Aplicar P1/P2.
6. Rodar build/check/dry-run.
7. Commitar com mensagem clara.
8. Push.
9. Deploy Mini App.
10. Deploy Worker.
11. Testar Telegram real.
12. Monitorar logs.
13. Executar rollback se erro crítico aparecer.
```

### Rollback obrigatório se ocorrer

```text
Mini App não abre para admin
/me ou /settings retornam 500
Worker quebra /bot-command
Bot Python para de processar comandos
Postagem automática quebra
Token/segredo aparece em log ou resposta
Configurações deixam de salvar
```

### Comandos úteis de rollback

```bash
git log --oneline -n 10
git status
git diff
git revert <commit>
```

Não executar revert sem necessidade; apenas garantir que commits sejam pequenos e reversíveis.

### Backup obrigatório antes de alteração destrutiva

Antes de migration, limpeza de fila, reset de ciclo amplo, exclusão de dados ou alteração destrutiva:

```text
gerar backup
registrar comando usado
confirmar escopo afetado
validar rollback
executar apenas com autorização explícita
```

## 19. P9 — Validações profissionais ainda não executadas e que a IA deve tentar executar

A IA executora deve rodar o máximo possível no ambiente local/servidor. O que não puder executar deve ser reportado em `Pendências` com motivo objetivo.

### 19.1 Build real

```bash
cd miniapp
npm install
npm run build
npm run check

cd ../worker
npm install
npm run dry-run
```

### 19.2 Runtime local

```bash
cd miniapp
npm run dev

cd ../worker
npx wrangler dev
```

### 19.3 Teste real no Telegram

```text
admin abre
não-admin bloqueia
sessão expirada bloqueia
BackButton funciona
MainButton funciona
safe area funciona
tema claro funciona
tema escuro funciona
teclado aberto não quebra layout
```

### 19.4 Autenticação e autorização

Testar:

```text
sem initData
initData inválido
initData expirado
user não admin
admin válido
owner válido
origin não permitido
Worker sem TELEGRAM_BOT_TOKEN
Supabase fora
```

### 19.5 Contrato de API

Validar status HTTP e JSON de:

```text
/me
/status
/overview
/settings
/commands
/commands/:id
/cards
/packs
/history
/bot-info
/bot-command
/health
```

### 19.6 Payload inválido

Testar recusa de:

```text
repost_card sem card_code
skip_card sem card_code
update_setting desconhecido
horário inválido
timezone inválido
modelo IA inválido
tipo de carta inválido
day_config malformado
payload com campos extras
payload com tipos errados
```

### 19.7 Persistência

```text
alterar configuração no Mini App
salvar
recarregar Mini App
confirmar valor salvo
confirmar Supabase atualizado
confirmar /status ou /overview refletindo valor
confirmar bot Python lendo o mesmo valor quando aplicável
```

### 19.8 End-to-end real

```text
buscar carta > postar agora > comando entra na fila > bot processa > mensagem sai no Telegram > histórico registra
alterar agenda > salvar > bot respeita próxima execução
sync ArkhamDB > comando entra > bot processa > banco atualiza
repost_card > comando processa > mensagem sai
skip_card > ciclo avança corretamente
```

### 19.9 Regressão do bot Python

```bash
python -m compileall -q .
python main.py healthcheck
pytest -q
```

Comandos reais:

```text
/status
/cotd
/search Roland
/faq 01001
/card 01001
```

### 19.10 Visual, responsivo e compatibilidade Telegram

Validar:

```text
iPhone pequeno
iPhone grande
Android
Telegram iOS
Telegram Android
Telegram tema claro
Telegram tema escuro
fonte ampliada
teclado aberto em inputs
safe area com notch
scroll longo em telas grandes
BackButton
MainButton
haptic sem quebrar quando API ausente
```

### 19.11 Estados vazios

Validar:

```text
sem comandos na fila
sem histórico
sem packs
sem cartas
sem target_chats
sem settings
sem bot_admins
sem last_sync
sem erros recentes
```

### 19.12 Erros controlados

Simular:

```text
Worker offline
Supabase 500
Supabase timeout
ArkhamDB fora
CORS errado
sem internet
JSON inválido
resposta vazia
```

### 19.13 Segurança

Comandos úteis:

```bash
grep -R "SUPABASE_SERVICE_ROLE_KEY\|TELEGRAM_BOT_TOKEN\|x-telegram-init-data\|authorization" -n miniapp/src || true
grep -R "console.log\|console.error\|console.warn" -n miniapp/src worker/src || true
```

Critérios:

```text
nenhum service role no front
nenhum token no bundle
nenhum initData logado
CORS fechado
admin validado no Worker
payload validado no Worker
roles respeitadas
sem stack trace público
```

### 19.14 Observabilidade

Confirmar se é possível responder:

```text
qual foi o último erro?
qual foi o último comando?
quem executou?
quando executou?
qual payload seguro foi usado?
qual foi a última postagem?
qual será a próxima postagem?
o bot Python está vivo?
o Worker está vivo?
o Supabase está respondendo?
```

### 19.15 CI/CD

Validar ou registrar pendência:

```text
instala dependências Python
roda pytest
roda compileall
roda miniapp build
roda worker dry-run
falha se build quebrar
não expõe secrets nos logs
```

### 19.16 Performance

Critérios recomendados:

```text
Mini App abre em até 3s em rede normal
/overview responde em até 2s
/cards responde em até 3s
/history pagina, não carrega tudo
/packs usa cache
bundle não cresce sem justificativa
```

### 19.17 Versionamento

Recomendações:

```text
Mini App mostra versão/commit em Aplicativo ou Saúde
Worker expõe versão/commit sem secrets
Saúde mostra compatibilidade front/Worker
Deploy registra commit ativo
```

### 19.18 Testes automatizados futuros

Registrar como pendência se não existirem:

```text
unit tests para settingsPatchPayload
unit tests para validateSettingsPatch
unit tests para validateTelegramInitData
unit tests para command payload validation
smoke tests para rotas do Worker
smoke tests para auth failure
```

### 19.19 Documentação operacional mínima

Validar se há instrução clara para:

```text
deploy Mini App
deploy Worker
configurar ALLOWED_ORIGINS
configurar BotFather Web App URL
configurar Supabase
adicionar admin
descobrir chat_id
descobrir message_thread_id de tópico Telegram
validar bot em produção
fazer rollback
```

Se faltar, registrar como pendência. Não alterar README sem autorização explícita.

## 20. Checklist final para o bot validar

A IA executora deve marcar cada item como `[OK]`, `[ERRO]` ou `[NÃO EXECUTADO: motivo]`.

```text
[ ] Leu este arquivo inteiro antes de alterar código.
[ ] Confirmou git status inicial.
[ ] Validou wrappers Python.
[ ] Corrigiu ou confirmou ausência de auth fail-open.
[ ] Removeu/protegeu logs sensíveis.
[ ] Adicionou script check no Mini App.
[ ] Tornou /status admin-only.
[ ] Ajustou /packs para Supabase com fallback ArkhamDB.
[ ] Validou que não há service role/token no front.
[ ] Validou que payloads sensíveis não são logados.
[ ] Validou Home.
[ ] Validou Postagem.
[ ] Validou Agenda.
[ ] Validou IA.
[ ] Validou Banco de Dados.
[ ] Validou Fila.
[ ] Validou Histórico.
[ ] Validou Destinos ou registrou pendência.
[ ] Validou Administradores ou registrou pendência.
[ ] Validou Manutenção.
[ ] Validou Saúde.
[ ] Validou Aplicativo.
[ ] Validou estados loading/empty/ready/error/saving/success.
[ ] Validou mensagens de erro amigáveis.
[ ] Validou confirmação em ações destrutivas.
[ ] Validou proteção contra clique duplo.
[ ] Validou alterações não salvas.
[ ] Validou RBAC owner/admin/none.
[ ] Validou contratos dos endpoints atuais.
[ ] Validou payloads inválidos.
[ ] Validou persistência de settings.
[ ] Validou fluxo E2E de postagem ou registrou pendência.
[ ] Validou fluxo E2E de agenda ou registrou pendência.
[ ] Validou fluxo E2E de sync ou registrou pendência.
[ ] Rodou python -m compileall -q .
[ ] Rodou python main.py healthcheck.
[ ] Rodou pytest -q ou registrou pendência.
[ ] Rodou cd miniapp && npm install, se necessário.
[ ] Rodou cd miniapp && npm run build.
[ ] Rodou cd miniapp && npm run check.
[ ] Rodou cd worker && npm install, se necessário.
[ ] Rodou cd worker && npm run dry-run.
[ ] Validou Mini App no Telegram iOS ou registrou pendência.
[ ] Validou Mini App no Telegram Android ou registrou pendência.
[ ] Validou tema claro/escuro ou registrou pendência.
[ ] Validou safe area/teclado/scroll ou registrou pendência.
[ ] Validou CORS/origin permitido.
[ ] Validou origin não permitido.
[ ] Validou admin válido.
[ ] Validou não-admin bloqueado.
[ ] Validou initData ausente/inválido/expirado.
[ ] Validou estados vazios.
[ ] Validou erros controlados.
[ ] Validou concorrência/idempotência ou registrou pendência.
[ ] Validou rate limit ou registrou pendência.
[ ] Validou observabilidade mínima.
[ ] Validou estratégia de rollback.
[ ] Validou CI/CD ou registrou pendência.
[ ] Validou performance básica ou registrou pendência.
[ ] Classificou todos os achados por severidade.
[ ] Informou risco residual.
[ ] Não deixou mudança destrutiva sem autorização.
[ ] Não alterou README sem autorização.
[ ] Não expôs secrets.
```

## 21. Ordem final de execução recomendada

```text
1. P0 — Segurança e estabilidade imediata.
2. Build/check/dry-run.
3. P1 — Menus e UX profissional.
4. P2 — Estados e prevenção de erro humano.
5. P3 — RBAC, auditoria, logs, rate limit e idempotência.
6. P4 — Contratos do Worker.
7. P8/P9 — Validações profissionais reais.
8. P5 — Refatoração do main.jsx, somente depois de tudo estável.
9. P6/P7 — Migrações futuras e diagnóstico avançado, somente com autorização.
10. Checklist final.
```

## 22. Formato de resposta obrigatório da IA executora

```text
RESULTADO:
- Arquivos alterados:
  - ...
- Correções aplicadas:
  - ...
- Validações executadas:
  - python -m compileall -q .: OK/ERRO/NÃO EXECUTADO + motivo
  - python main.py healthcheck: OK/ERRO/NÃO EXECUTADO + motivo
  - pytest -q: OK/ERRO/NÃO EXECUTADO + motivo
  - cd miniapp && npm run build: OK/ERRO/NÃO EXECUTADO + motivo
  - cd miniapp && npm run check: OK/ERRO/NÃO EXECUTADO + motivo
  - cd worker && npm run dry-run: OK/ERRO/NÃO EXECUTADO + motivo
- Checklist final:
  - [OK/ERRO/NÃO EXECUTADO] itens principais do checklist
- Achados por severidade:
  - CRÍTICO: ...
  - ALTO: ...
  - MÉDIO: ...
  - BAIXO: ...
- Validações manuais necessárias:
  - ...
- Pendências:
  - ...
- Risco residual:
  - baixo/médio/alto + justificativa
```
