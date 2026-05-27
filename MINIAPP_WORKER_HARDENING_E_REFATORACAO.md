# Mini App e Worker — hardening, validação, menus e refatoração

Este arquivo é o plano operacional para corrigir, validar e evoluir o Mini App administrativo e o Worker do Arkham Bot. Ele inclui ajustes no `main.jsx`, validação das correções já feitas, hardening de segurança, melhorias de UX, novos menus administrativos, itens a remover/migrar e a refatoração completa do Mini App em módulos.

## Objetivo

Transformar o Mini App em um painel administrativo estável, seguro e sustentável, sem quebrar o bot Python. A execução deve ser feita em fases pequenas, com build e validação após cada fase.

## Regras obrigatórias

- Não alterar secrets, tokens, `.env`, chaves ou credenciais.
- Não imprimir secrets, headers de autenticação, `x-telegram-init-data` ou payloads sensíveis em logs.
- Não alterar migrations/banco sem autorização explícita.
- Não alterar backend Python, exceto para corrigir import quebrado diretamente relacionado a `/status`, `/cotd` ou processamento de comandos do Mini App.
- Não recriar documentação antiga.
- Não alterar README nesta tarefa, salvo autorização explícita.
- Não fazer commit automático antes de validar.
- Fazer alterações pequenas, reversíveis e testáveis.
- Rodar validações após cada fase.
- Se uma fase quebrar build, reverter somente a última alteração.

## Visão alvo do Mini App

O Mini App deve ser um painel administrativo real, não apenas informativo. A estrutura ideal de menus é:

```text
Home
├── Postagem
│   ├── Postar carta agora
│   ├── Repostar carta
│   ├── Pular carta do ciclo
│   ├── Buscar carta
│   └── Escolher destino/tópico
├── Agenda
│   ├── Postagem automática
│   ├── Todos os dias
│   ├── Configuração por dia da semana
│   ├── Horários por dia
│   ├── Filtros por ciclo/pack
│   └── Filtros por tipo de carta
├── IA
│   ├── Ativar/desativar IA
│   ├── Provedor/modelo
│   ├── Idioma
│   ├── Tom narrativo
│   ├── Criatividade
│   ├── Mensagem antes da carta
│   ├── Pergunta após a carta
│   └── Teste de geração
├── Banco de Dados
│   ├── Status do banco
│   ├── Sincronizar ArkhamDB
│   ├── Agendamento de sincronização
│   ├── Cartas sincronizadas
│   ├── Packs/ciclos sincronizados
│   └── Último erro de sync
├── Fila
│   ├── Pendentes
│   ├── Processando
│   ├── Falhas
│   ├── Executados recentes
│   ├── Cancelar comando
│   └── Reenfileirar falhas
├── Histórico
│   ├── Postagens recentes
│   ├── Filtro por data
│   ├── Filtro por carta
│   ├── Origem manual/automática
│   └── Link para mensagem Telegram quando existir
├── Destinos
│   ├── Grupos/canais configurados
│   ├── Tópicos Telegram
│   ├── Chat ID
│   ├── Message Thread ID
│   ├── Destino padrão
│   └── Teste de envio
├── Administradores
│   ├── Listar admins
│   ├── Adicionar admin
│   ├── Remover admin
│   └── Alterar role
├── Manutenção
│   ├── Resetar ciclo de cartas
│   ├── Limpar fila
│   ├── Reprocessar falhas
│   ├── Limpar cache
│   └── Executar diagnóstico
├── Saúde
│   ├── Worker
│   ├── Supabase
│   ├── Bot Python
│   ├── Scheduler
│   ├── Próxima postagem
│   ├── Último heartbeat
│   ├── Último erro
│   └── Versão/commit em execução
└── Aplicativo
    ├── Idioma do app
    ├── Tema Telegram
    ├── Informações da sessão
    └── Diagnóstico técnico
```

## Fase 0 — Validar correções já feitas nos handlers Python

Foram criados wrappers de compatibilidade porque `telegram_handlers.py` tinha imports relativos antigos dentro de `arkham_bot.handlers`.

Validar estes arquivos:

```text
src/arkham_bot/handlers/supabase_client.py
src/arkham_bot/handlers/config.py
src/arkham_bot/handlers/local_storage.py
src/arkham_bot/handlers/scheduler.py
```

Conteúdo esperado de `src/arkham_bot/handlers/supabase_client.py`:

```python
"""Compatibility wrapper for legacy handler-local imports.

Runtime handlers should use ``arkham_bot.core.supabase_client`` directly.
This module exists to keep older relative imports working while the
handler module is consolidated.
"""

from ..core.supabase_client import SupabaseRestClient, get_supabase_client

__all__ = ["SupabaseRestClient", "get_supabase_client"]
```

Conteúdo esperado de `src/arkham_bot/handlers/config.py`:

```python
"""Compatibility wrapper for legacy handler-local config imports."""

from ..core.config import *  # noqa: F403
```

Conteúdo esperado de `src/arkham_bot/handlers/local_storage.py`:

```python
"""Compatibility wrapper for legacy handler-local local_storage imports."""

from ..services.local_storage import *  # noqa: F403
```

Conteúdo esperado de `src/arkham_bot/handlers/scheduler.py`:

```python
"""Compatibility wrapper for legacy handler-local scheduler imports."""

from ..services.scheduler import *  # noqa: F403
```

Validar imports legados em `src/arkham_bot/handlers/telegram_handlers.py`:

```bash
grep -n "from \.supabase_client\|from \.config\|from \.local_storage\|from \.scheduler" src/arkham_bot/handlers/telegram_handlers.py || true
```

Eles podem continuar existindo desde que os wrappers acima existam e compilem.

Rodar:

```bash
python -m compileall -q .
python main.py healthcheck
```

Critério de aceite:

- `/status` e `/cotd` não podem quebrar por `ModuleNotFoundError`.
- `compileall` deve passar.
- `healthcheck` deve passar ou retornar apenas warnings esperados por falta de ambiente real.

## Fase 1 — Hardening pontual do Mini App

Arquivo principal:

```text
miniapp/src/main.jsx
```

### 1.1 Corrigir autenticação fail-open

Localizar o `useEffect` de autenticação que chama:

```javascript
apiFetch('/me')
```

Se existir fallback assim:

```javascript
}).catch(() => setAuthState('ready'));
```

Trocar para fail-closed:

```javascript
}).catch(() => {
  setAuthState('auth_error');
});
```

Se `auth_error` ainda não for renderizado na UI, adicionar tratamento no gate de autenticação usando o mesmo padrão visual de `no_telegram` ou `unauthorized`.

Mensagem em português:

```text
Não foi possível validar o acesso administrativo. Reabra pelo Telegram ou verifique o Worker.
```

Mensagem em inglês:

```text
Could not validate admin access. Reopen from Telegram or check the Worker.
```

Critério de aceite:

- O painel administrativo não pode entrar em `ready` se `/me` falhar.
- Falha de rede, Worker fora, CORS, erro 500 ou resposta inválida devem bloquear acesso.

### 1.2 Remover ou proteger logs sensíveis de `saveSettings()`

Localizar logs como:

```javascript
console.log('[saveSettings] payload:', ...)
console.log('[saveSettings] response ok=%s status=%s', ...)
console.error('[saveSettings] error:', ...)
console.log('[saveSettings] returned day_config:', ...)
```

Preferência: remover completamente. Alternativa aceitável:

```javascript
if (import.meta.env.DEV) {
  console.log(...);
}
```

Não deixar em produção logs com:

- `telegram_chat_id`
- `day_config`
- payload completo de settings
- dados operacionais sensíveis

### 1.3 Melhorar estado de erro de API

Adicionar estados visuais claros para:

- Worker não configurado.
- Worker fora do ar.
- CORS/origin não autorizado.
- Sessão Telegram ausente.
- Sessão Telegram expirada.
- Usuário autenticado, mas não admin.

Não liberar painel em nenhum desses casos.

### 1.4 Não refatorar `main.jsx` nesta fase

Nesta fase, fazer apenas alterações pontuais. A separação em módulos fica para a Fase 4.

## Fase 2 — Ajustar `miniapp/package.json`

Adicionar script:

```json
"check": "vite build"
```

Preservar scripts existentes. Exemplo aceitável:

```json
"scripts": {
  "dev": "vite --host 0.0.0.0",
  "deploy": "wrangler deploy",
  "dry-run": "wrangler deploy --dry-run",
  "build": "vite build",
  "check": "vite build",
  "preview": "vite preview"
}
```

Rodar:

```bash
cd miniapp
npm install
npm run build
npm run check
```

## Fase 3 — Hardening do Worker

Arquivo:

```text
worker/src/index.js
```

### 3.1 Tornar `/status` admin-only

Localizar rota:

```javascript
if (pathname === '/status' && request.method === 'GET') {
```

Trocar `requireAuth` por `requireAdmin`:

```javascript
const auth = await requireAdmin(request, env, ao, '/status');
if (auth.response) return auth.response;
return handleStatus(request, env, ao);
```

Critério de aceite:

- `/status` só responde para admin autorizado.
- Usuário não admin recebe `unauthorized`.
- Admin continua recebendo status normalmente.

### 3.2 Alterar `/packs` para preferir Supabase com fallback ArkhamDB

Localizar função:

```javascript
handleGetPacks
```

Antes de buscar ArkhamDB pública, tentar ler do Supabase quando `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` existirem.

Tabela:

```text
arkham_packs
```

Campos:

```text
code,name,cycle_position,position,chapter,total
```

Query sugerida:

```javascript
/rest/v1/arkham_packs?select=code,name,cycle_position,position,chapter,total&order=cycle_position.asc,position.asc&limit=500
```

Resposta quando houver dados válidos:

```javascript
{
  ok: true,
  packs,
  source: 'supabase'
}
```

Fallback obrigatório: se Supabase falhar, estiver vazio ou não configurado, manter fallback atual para:

```text
https://arkhamdb.com/api/public/packs/
```

### 3.3 Melhorar validação de comandos

Validar no Worker, antes de inserir em `bot_commands`:

- `post_now` aceita payload vazio ou `{ card_code }` válido.
- `repost_card` exige `card_code`.
- `skip_card` exige `card_code`.
- `sync_arkhamdb` aceita opções controladas, como `sync_faq` boolean.
- `reset_cycle` não precisa de payload.
- `clear_queue` não precisa de payload.

Se payload inválido, retornar:

```json
{ "error": "invalid_command_payload" }
```

### 3.4 Validar Worker

Rodar:

```bash
cd worker
npm install
npm run dry-run
```

## Fase 4 — Ajustar e organizar menus do Mini App

Antes da refatoração estrutural, validar se a navegação atual atende ao fluxo administrativo.

### 4.1 Menu Home

Manter Home como hub principal. Itens recomendados:

```text
Postagem
Agenda
IA
Banco de Dados
Fila
Histórico
Destinos
Administradores
Manutenção
Saúde
Aplicativo/Idioma
```

Se a tela ficar grande demais, agrupar em seções:

```text
Operação
- Postagem
- Agenda
- Fila
- Histórico

Configuração
- IA
- Banco de Dados
- Destinos
- Administradores

Sistema
- Manutenção
- Saúde
- Aplicativo
```

### 4.2 Menu Postagem

Deve conter:

- Busca de carta por código/nome.
- Preview mínimo da carta selecionada.
- Destino selecionável.
- Botão `Postar agora`.
- Botão `Repostar carta`.
- Botão `Pular carta`.
- Resultado da ação enfileirada.

Melhoria recomendada:

- Mostrar se a carta já foi postada.
- Mostrar pack/ciclo/tipo da carta.
- Mostrar aviso quando `ai_auto_only=true` e a postagem manual não usará IA.

### 4.3 Menu Agenda

Migrar a configuração semanal para um menu próprio chamado `Agenda`, em vez de ficar misturada em `Configurações`.

Deve conter:

- Toggle `Postagem automática`.
- Fuso horário.
- Modo `Todos os dias`.
- Lista dos dias da semana.
- Horários por dia.
- Filtros por ciclo/pack.
- Filtros por tipo.
- Botão salvar via MainButton ou botão visível.

Regra de negócio:

- Se `Todos os dias` estiver ativo, ele é a regra principal.
- Se `Todos os dias` estiver inativo, respeitar a configuração individual de cada dia.
- Nunca permitir salvar sem nenhum dia ativo quando postagem automática estiver ligada.
- Nunca permitir horário inválido.

### 4.4 Menu IA

Deve conter:

- IA habilitada.
- IA apenas em posts automáticos.
- Idioma da IA.
- Tom narrativo.
- Provedor.
- Modelo.
- Criatividade.
- Mensagem de abertura.
- Delay antes da carta.
- Pergunta pós-carta.
- Delay após a carta.
- Teste de geração com carta selecionada.

Melhoria importante:

- Migrar lista de modelos hardcoded para endpoint `/ai-models` no Worker.
- Worker deve retornar apenas modelos aceitos pelo backend real.
- Front deve consumir `/ai-models` e parar de duplicar whitelist.

### 4.5 Menu Banco de Dados

Deve conter:

- Total de cartas.
- Total de packs.
- Última sincronização.
- Status atualizado/desatualizado.
- Botão `Sincronizar ArkhamDB`.
- Agendamento de sync.
- Último erro de sync.
- Resultado do último comando `sync_arkhamdb`.

Migrar para Worker/Supabase:

- `/packs` deve vir preferencialmente de `arkham_packs`.
- `last_sync` deve vir de tabela/registro confiável, não só do último comando criado.

### 4.6 Menu Fila

Deve conter abas ou filtros:

- Pendentes.
- Processando.
- Retrying.
- Falhas.
- Executados recentes.
- Cancelados.

Ações:

- Cancelar comando pendente.
- Reenfileirar falha.
- Limpar pendentes.
- Ver erro completo.

Migrar/remover:

- Não mostrar JSON bruto por padrão.
- JSON técnico deve ficar dentro de `details` ou modo diagnóstico.

### 4.7 Menu Histórico

Deve conter:

- Data.
- Código da carta.
- Nome da carta.
- Status.
- Origem: manual/automática.
- Mensagem Telegram, se existir.
- Filtro por data.
- Busca por código/nome.
- Paginação.

Melhorias:

- Link para ArkhamDB.
- Link para mensagem Telegram quando possível.
- Badge para falha/sucesso.

### 4.8 Menu Destinos

Novo menu recomendado.

Objetivo: gerenciar grupos, canais e tópicos Telegram.

Dados esperados:

- `chat_id`
- `title`
- `message_thread_id`
- `enabled`
- `is_default`
- `description`
- `created_at`
- `updated_at`

Funcionalidades:

- Listar destinos.
- Criar destino.
- Editar título amigável.
- Ativar/desativar.
- Definir padrão.
- Informar `message_thread_id` para tópicos.
- Enviar mensagem de teste.

Regra:

- Postagem manual deve permitir escolher destino.
- Postagem automática deve usar destino padrão ou configuração do agendamento.

### 4.9 Menu Administradores

Novo menu recomendado, restrito a role `owner`.

Funcionalidades:

- Listar admins.
- Adicionar Telegram user id.
- Definir role `owner` ou `admin`.
- Ativar/desativar admin.
- Remover admin.
- Mostrar origem da permissão.

Regras:

- Apenas `owner` pode gerenciar admins.
- Um `admin` comum não pode promover outro usuário.
- Não permitir remover o último `owner`.

### 4.10 Menu Manutenção

Deve conter:

- Resetar ciclo.
- Limpar fila.
- Reprocessar falhas.
- Limpar cache local do bot, se existir comando seguro.
- Rodar diagnóstico.

Ações destrutivas devem usar confirmação Telegram `showPopup` com botão destrutivo.

### 4.11 Menu Saúde

Deve conter:

- Worker online.
- Supabase online.
- Bot Python online.
- Polling/command worker ativo.
- Scheduler ativo.
- Próxima postagem calculada.
- Última postagem.
- Último erro.
- Último heartbeat.
- Versão/commit em execução.
- Ambiente: produção/desenvolvimento.

Dados recomendados a expor via Worker:

```text
/status
/health/deep
/bot-runtime
```

Não expor secrets.

### 4.12 Menu Aplicativo

Deve conter:

- Idioma do app.
- Idioma da IA, se ainda estiver acoplado.
- Sessão Telegram ativa.
- Usuário atual.
- Role atual.
- Origem da permissão.
- Endpoint do Worker.
- Versão do Mini App.

## Fase 5 — Refatorar `miniapp/src/main.jsx` em módulos

Executar somente depois que Fases 1 a 4 estiverem validadas.

Objetivo: reduzir o tamanho de `main.jsx` sem mudar comportamento.

Regras:

- Não mudar UX durante a refatoração.
- Não mudar textos.
- Não mudar endpoints.
- Não mudar payloads.
- Não mudar nomes de settings.
- Não mudar autenticação já corrigida.
- Não alterar Worker nesta fase.
- Não alterar backend Python nesta fase.
- Não refatorar CSS agora, salvo imports necessários.
- Fazer extração incremental.
- Rodar `npm run build` após cada grupo de extração.
- Se quebrar build, reverter a última extração.

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

### 5.1 Extrair helpers Telegram

Criar:

```text
miniapp/src/telegram.js
```

Mover:

- `tg`
- `initData`
- `tgUser`
- `haptic`
- `tgShowPopup`

Rodar:

```bash
cd miniapp
npm run build
```

### 5.2 Extrair API client

Criar:

```text
miniapp/src/api.js
```

Mover:

- `getBotPhotoUrl`
- `getApiBase`
- `apiUrl`
- `authHeaders`
- `apiFetch`

Atenção: `authHeaders` depende de `initData`; importar de `telegram.js`.

### 5.3 Extrair i18n

Criar:

```text
miniapp/src/i18n.js
```

Mover:

- `LANGUAGE_KEY`
- `I18N`
- `readLangStorage`
- `writeLangStorage`
- `getInitialLanguage`

### 5.4 Extrair constantes e settings

Criar:

```text
miniapp/src/constants.js
miniapp/src/settings.js
```

Mover para `constants.js`:

- `WEEKDAYS`
- `ALL_CARD_TYPES`
- `DEFAULT_CARD_TYPES`
- `TIMEZONES`

Mover para `settings.js`:

- `AI_TONES`
- `AI_PROVIDERS`
- `AI_MODELS`
- `DEFAULT_SETTINGS`
- `SETTINGS_PATCH_KEYS`
- `parseJsonArray`
- `normalizeSettings`
- `settingsPatchPayload`
- `isValidTimeValue`
- `validateTimes`
- `settingsEqual`
- `deriveCycles`

### 5.5 Extrair ícones

Criar:

```text
miniapp/src/icons.jsx
```

Mover:

- `ICON_PATHS`
- `Icon`

### 5.6 Extrair componentes reutilizáveis

Criar:

```text
miniapp/src/components/
```

Extrair primeiro:

- `Spinner.jsx`
- `Badge.jsx`
- `Notice.jsx`
- `Section.jsx`
- `Row.jsx`
- `MenuRow.jsx`
- `DangerRow.jsx`

Depois:

- `InfoTooltip.jsx`
- `ToggleRow.jsx`
- `SelectRow.jsx`
- `CardResult.jsx`
- `CommandRow.jsx`
- `ChatIdInputRow.jsx`
- `DayScheduleRow.jsx`

Criar opcionalmente:

```text
miniapp/src/components/index.js
```

### 5.7 Extrair telas

Criar:

```text
miniapp/src/screens/
```

Extrair uma por vez:

- `HomeScreen.jsx`
- `PostScreen.jsx`
- `ScheduleScreen.jsx`
- `SettingsScreen.jsx`
- `DayDetailScreen.jsx`
- `AiScreen.jsx`
- `DatabaseScreen.jsx`
- `QueueScreen.jsx`
- `HistoryScreen.jsx`
- `DestinationsScreen.jsx`
- `AdminsScreen.jsx`
- `MaintenanceScreen.jsx`
- `HealthScreen.jsx`
- `AppSettingsScreen.jsx`
- `LanguageScreen.jsx`

Regra para telas:

- Receber via props tudo que vier de estado global do `App`.
- Não duplicar estado sem necessidade.
- Não mudar nomes de callbacks.
- Não mudar payloads enviados ao Worker.

### 5.8 Simplificar `main.jsx`

Após extrair `App.jsx`, deixar `main.jsx` somente como bootstrap:

```jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(<App />);
```

## Fase 6 — O que remover, migrar ou manter

### Remover

- Logs de produção em `saveSettings`.
- Qualquer fallback que libere painel sem autenticação admin confirmada.
- JSON bruto visível por padrão para usuário comum/admin comum.
- Lista duplicada de modelos de IA no front, depois que `/ai-models` existir.
- Busca de packs diretamente na ArkhamDB, quando o Supabase local estiver populado.

### Migrar

- Configuração semanal para menu `Agenda`.
- Gestão de destinos para menu próprio `Destinos`.
- Gestão de admins para menu próprio `Administradores`.
- Lista de modelos de IA para endpoint do Worker.
- Diagnóstico operacional do bot Python para endpoint dedicado.
- Status de sync para fonte confiável no banco, não apenas último comando criado.

### Manter

- Telegram theme variables no CSS.
- Safe area handling do Telegram.
- Haptic feedback.
- MainButton para salvar quando houver alteração pendente.
- BackButton do Telegram.
- Fallback ArkhamDB para packs enquanto banco local pode estar vazio.
- Worker como camada de proteção entre Mini App e Supabase.

## Fase 7 — Endpoints recomendados no Worker

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

Endpoints novos recomendados:

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

Regras:

- Todos os endpoints administrativos devem usar `requireAdmin`.
- Endpoints de gestão de admins devem exigir role `owner`.
- Nenhum endpoint deve expor secrets.
- Toda ação destrutiva deve exigir confirmação no front e validação no Worker.

## Fase 8 — Diagnóstico avançado do bot Python

Recomendado criar futuramente um registro de runtime/heartbeat no banco.

Dados úteis:

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

O bot Python atualizaria heartbeat periodicamente. O Worker leria isso em `/bot-runtime` ou `/health/deep`.

Não implementar sem autorização para migration.

## Fase 9 — Validação final completa

Na raiz:

```bash
python -m compileall -q .
python main.py healthcheck
```

Mini App:

```bash
cd miniapp
npm run build
npm run check
```

Worker:

```bash
cd ../worker
npm run dry-run
```

Buscas de regressão:

```bash
grep -R "setAuthState('ready')" -n miniapp/src || true
grep -R "\[saveSettings\]\|saveSettings.*console" -n miniapp/src || true
grep -R "pathname === '/status'" -n worker/src/index.js
grep -R "handleGetPacks" -n worker/src/index.js
grep -R "from \.supabase_client\|from \.config\|from \.local_storage\|from \.scheduler" -n src/arkham_bot/handlers/telegram_handlers.py || true
```

Validação manual no Telegram:

```text
/status
/cotd
/search Roland
/faq 01001
```

Validação manual no Mini App:

- Abrir como admin.
- Confirmar que não admin é bloqueado.
- Confirmar que falha de `/me` não libera painel.
- Abrir Postagem.
- Buscar carta.
- Enfileirar `post_now`.
- Abrir Agenda.
- Alterar dia/horário/filtro.
- Salvar configuração.
- Abrir IA.
- Alterar modelo/tom/idioma.
- Abrir Banco de Dados.
- Confirmar packs/ciclos.
- Abrir Fila.
- Cancelar comando pendente de teste.
- Abrir Histórico.
- Filtrar por data.
- Abrir Saúde.
- Alternar idioma.

## Prioridade de execução

Executar nesta ordem:

```text
P0 — Obrigatório imediato
1. Validar wrappers Python.
2. Corrigir fail-open do Mini App.
3. Remover/proteger logs sensíveis.
4. Tornar /status admin-only.
5. /packs via Supabase com fallback.
6. Build/check/dry-run.

P1 — Organização funcional
7. Separar Agenda de Configurações.
8. Criar/organizar menu Destinos.
9. Melhorar Fila e Histórico.
10. Melhorar Saúde.

P2 — Refatoração técnica
11. Extrair telegram.js.
12. Extrair api.js.
13. Extrair i18n.js.
14. Extrair constants/settings/icons.
15. Extrair components.
16. Extrair screens.
17. Reduzir main.jsx para bootstrap.

P3 — Evolução futura
18. Gestão de admins.
19. /ai-models.
20. Heartbeat/runtime do bot Python.
21. Health deep.
22. Testes automatizados.
```

## Formato de resposta obrigatório da IA executora

Ao final, responder somente:

```text
RESULTADO:
- Arquivos alterados:
  - ...
- Correções aplicadas:
  - ...
- Validações executadas:
  - python -m compileall -q .: OK/ERRO
  - python main.py healthcheck: OK/ERRO
  - cd miniapp && npm run build: OK/ERRO
  - cd miniapp && npm run check: OK/ERRO
  - cd worker && npm run dry-run: OK/ERRO
- Achados adicionais:
  - ...
- Pendências:
  - ...
```
