# Mini App e Worker — hardening, validação e refatoração

Este arquivo descreve tudo que deve ser feito para corrigir, validar e melhorar o Mini App administrativo e o Worker do Arkham Bot, incluindo o ajuste no `main.jsx` e a refatoração posterior em módulos.

## Objetivo

Aplicar correções de segurança e consistência no Mini App e no Worker sem quebrar o bot Python. Depois, separar o `miniapp/src/main.jsx` em módulos menores, preservando comportamento visual e funcional.

## Regras obrigatórias

- Não alterar secrets, tokens, `.env`, chaves ou credenciais.
- Não imprimir secrets ou payloads sensíveis em logs.
- Não alterar migrations/banco sem autorização explícita.
- Não alterar backend Python, exceto para corrigir import quebrado diretamente relacionado a `/status` ou `/cotd`.
- Não recriar documentação antiga.
- Não refatorar arquitetura fora das fases abaixo.
- Não fazer commit automático antes de validar.
- Fazer alterações pequenas, reversíveis e testáveis.
- Rodar validações após cada fase.

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

Preferência: remover completamente. Alternativa aceitável: proteger por ambiente de desenvolvimento:

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

### 1.3 Não refatorar o `main.jsx` nesta fase

Nesta fase, fazer apenas as alterações pontuais acima. A separação em módulos fica para a Fase 4.

## Fase 2 — Ajustar `miniapp/package.json`

Arquivo:

```text
miniapp/package.json
```

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

Critério de aceite:

- Build deve passar.
- Check deve passar.

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

Se estiver assim:

```javascript
const auth = await requireAuth(request, env, ao, '/status');
if (auth.response) return auth.response;
return handleStatus(request, env, ao);
```

Trocar para:

```javascript
const auth = await requireAdmin(request, env, ao, '/status');
if (auth.response) return auth.response;
return handleStatus(request, env, ao);
```

Critério de aceite:

- `/status` só deve responder para admin autorizado.
- Usuário não admin deve receber `unauthorized`.
- Admin deve continuar recebendo status normalmente.

### 3.2 Alterar `/packs` para preferir Supabase com fallback ArkhamDB

Localizar função:

```javascript
handleGetPacks
```

Hoje ela busca ArkhamDB pública:

```javascript
https://arkhamdb.com/api/public/packs/
```

Antes desse fallback, implementar tentativa de leitura do Supabase quando `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` existirem.

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

Formato de resposta quando o Supabase retornar dados válidos:

```javascript
{
  ok: true,
  packs,
  source: 'supabase'
}
```

Formato de cada pack:

```javascript
{
  code: p.code,
  name: p.name || p.code,
  cycle_position: p.cycle_position ?? null,
  position: p.position ?? null,
  chapter: p.chapter ?? 1,
  total: p.total ?? 0
}
```

Regras:

- Se Supabase falhar, estiver vazio ou não estiver configurado, manter fallback atual para ArkhamDB pública.
- Não remover cache atual.
- Não cachear falha.
- Pode cachear payload vindo do Supabase.
- Não imprimir `SUPABASE_SERVICE_ROLE_KEY`, headers Authorization ou tokens em logs.

Critério de aceite:

- `/packs` retorna `source: 'supabase'` quando `arkham_packs` tem dados.
- `/packs` continua funcionando com ArkhamDB se Supabase falhar.
- UI de ciclos reflete banco local quando disponível.

### 3.3 Validar Worker

Rodar:

```bash
cd worker
npm install
npm run dry-run
```

Critério de aceite:

- `dry-run` deve passar.

## Fase 4 — Refatorar `miniapp/src/main.jsx` em módulos

Executar somente depois que Fases 1, 2 e 3 estiverem validadas.

Objetivo: reduzir o tamanho de `main.jsx` sem mudar comportamento.

Regras:

- Não mudar UX.
- Não mudar textos.
- Não mudar endpoints.
- Não mudar payloads.
- Não mudar nomes de settings.
- Não mudar autenticação já corrigida.
- Não alterar Worker.
- Não alterar backend Python.
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
    SettingsScreen.jsx
    DayDetailScreen.jsx
    AiScreen.jsx
    DatabaseScreen.jsx
    MaintenanceScreen.jsx
    QueueScreen.jsx
    HistoryScreen.jsx
    HealthScreen.jsx
    LanguageScreen.jsx
```

### 4.1 Extrair helpers Telegram

Criar:

```text
miniapp/src/telegram.js
```

Mover funções:

- `tg`
- `initData`
- `tgUser`
- `haptic`
- `tgShowPopup`

Atualizar imports em `App.jsx` ou `main.jsx`.

Rodar:

```bash
cd miniapp
npm run build
```

### 4.2 Extrair API client

Criar:

```text
miniapp/src/api.js
```

Mover funções:

- `getBotPhotoUrl`
- `getApiBase`
- `apiUrl`
- `authHeaders`
- `apiFetch`

Atenção: `authHeaders` depende de `initData`; importar de `telegram.js`.

Rodar:

```bash
npm run build
```

### 4.3 Extrair i18n

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

Atenção: `readLangStorage` e `writeLangStorage` dependem de `tg`; importar de `telegram.js`.

Rodar:

```bash
npm run build
```

### 4.4 Extrair constantes e settings

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

Atenção: `settings.js` pode depender de constantes de `constants.js`.

Rodar:

```bash
npm run build
```

### 4.5 Extrair ícones

Criar:

```text
miniapp/src/icons.jsx
```

Mover:

- `ICON_PATHS`
- `Icon`

Rodar:

```bash
npm run build
```

### 4.6 Extrair componentes reutilizáveis

Criar pasta:

```text
miniapp/src/components/
```

Extrair primeiro componentes simples:

- `Spinner.jsx`
- `Badge.jsx`
- `Notice.jsx`
- `Section.jsx`
- `Row.jsx`
- `MenuRow.jsx`
- `DangerRow.jsx`

Depois extrair componentes com mais dependências:

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

para exportar todos.

Rodar após cada grupo:

```bash
npm run build
```

### 4.7 Extrair telas

Criar pasta:

```text
miniapp/src/screens/
```

Extrair telas uma por vez:

- `HomeScreen.jsx`
- `PostScreen.jsx`
- `SettingsScreen.jsx`
- `DayDetailScreen.jsx`
- `AiScreen.jsx`
- `DatabaseScreen.jsx`
- `MaintenanceScreen.jsx`
- `QueueScreen.jsx`
- `HistoryScreen.jsx`
- `HealthScreen.jsx`
- `LanguageScreen.jsx`

Regra para telas:

- Receber via props tudo que vier de estado global do `App`.
- Não duplicar estado sem necessidade.
- Não mudar nomes de callbacks.
- Não mudar payloads enviados ao Worker.

Rodar após cada tela ou grupo pequeno:

```bash
npm run build
```

### 4.8 Simplificar `main.jsx`

Após extrair `App.jsx`, deixar `main.jsx` somente como bootstrap:

```jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(<App />);
```

Rodar:

```bash
npm run build
npm run check
```

Critério de aceite da Fase 4:

- Build passa.
- UI abre.
- Navegação entre telas funciona.
- Configurações carregam e salvam.
- Postar carta enfileira comando.
- Histórico carrega.
- Banco carrega packs.
- Saúde carrega status.
- Idioma alterna.
- Não houve alteração de comportamento funcional.

## Fase 5 — Validação final completa

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

Validação manual no Telegram/Mini App:

```text
/status
/cotd
/search Roland
/faq 01001
```

No Mini App:

- Abrir como admin.
- Confirmar que não admin é bloqueado.
- Confirmar que falha de `/me` não libera painel.
- Abrir Postagem.
- Buscar carta.
- Enfileirar `post_now`.
- Abrir Configurações.
- Salvar configuração.
- Abrir Banco de Dados.
- Confirmar packs/ciclos.
- Abrir Histórico.
- Abrir Saúde.
- Alternar idioma.

## Pendências futuras fora deste escopo

Estas melhorias são recomendadas, mas não devem ser feitas nesta tarefa:

- Tela de gestão de administradores.
- Tela de gerenciamento de destinos/tópicos Telegram.
- Endpoint `/ai-models` para o Worker servir modelos válidos dinamicamente.
- Diagnóstico avançado do bot Python com heartbeat, commit em execução, scheduler e próximo post.
- Testes automatizados de UI.
- Lint/ESLint formal.
- Migrações adicionais.

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
