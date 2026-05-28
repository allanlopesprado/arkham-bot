# Mini App e Worker — ordem de serviço técnica validada contra o código real

Este arquivo é uma ordem de serviço técnica para corrigir e evoluir o Mini App administrativo e o Worker do Arkham Bot. Ele foi validado contra o estado real do projeto e separa claramente o que é bug confirmado, hardening de baixo risco, melhoria incremental, refatoração posterior e backlog futuro.

A IA executora deve tratar este arquivo como instrução operacional, não como sugestão genérica.

## 1. Escopo obrigatório desta execução

Executar somente **P0 — Correções obrigatórias agora**.

Não executar automaticamente:

```text
- CRUD de Administradores.
- CRUD de Destinos.
- /ai-models.
- /bot-runtime.
- /health/deep.
- migrations.
- novas tabelas.
- refatoração completa do main.jsx.
- testes automatizados amplos.
- mudanças de arquitetura fora do escopo P0.
```

Esses itens ficam documentados como backlog ou fase posterior.

## 2. Objetivo real de P0

Corrigir problemas confirmados no código atual sem alterar comportamento funcional do bot além do necessário.

P0 deve:

```text
- Fechar falha de autenticação do Mini App.
- Remover logs sensíveis do Mini App.
- Adicionar comando de validação do Mini App.
- Proteger /status como rota admin.
- Fazer /packs preferir dados locais do Supabase e usar ArkhamDB apenas como fallback.
- Validar que os wrappers Python continuam corretos.
- Rodar build/check/dry-run/healthcheck.
```

## 3. Diagnóstico validado contra o código real

```text
CONFIRMADO
- miniapp/src/main.jsx concentra Telegram helpers, API client, i18n, settings, componentes e telas.
- O Mini App já possui base Telegram correta: haptic, popup, MainButton, BackButton, tema e safe area.
- O Mini App já possui Home, Postagem, Configurações, IA, Banco, Fila, Histórico, Manutenção, Saúde e Idioma.
- O Worker já valida initData do Telegram por HMAC.
- O Worker já consulta bot_admins para identificar role owner/admin.
- O Worker já valida boa parte dos settings.
- O Worker já protege a maioria das rotas administrativas com requireAdmin.
- Os wrappers Python em src/arkham_bot/handlers/ já existem e estão corretos.

BUGS CONFIRMADOS
- Auth gate do Mini App faz fail-open: se /me falha, cai em setAuthState('ready').
- saveSettings loga payload completo e day_config no console.
- miniapp/package.json não tem script check.
- /status usa requireAuth, não requireAdmin.
- /packs busca ArkhamDB pública diretamente e não tenta arkham_packs no Supabase primeiro.

PONTOS QUE NÃO SÃO BUG P0
- main.jsx grande é dívida técnica, mas não bug operacional imediato.
- Admins CRUD exige endpoints novos e regra owner-only.
- Destinos CRUD exige endpoints novos.
- /bot-runtime e /health/deep exigem desenho de runtime/heartbeat.
- Rate limit robusto no Worker é melhoria, não correção mínima.
```

## 4. Severidade dos achados

```text
CRÍTICO
- Expõe secret/token/service role.
- Permite acesso admin sem validação.
- Quebra bot Python em produção.
- Impede postagem automática/manual.
- Worker retorna 500 em /me, /settings ou /bot-command.

ALTO
- Não salva configurações.
- /status, /settings, /commands ou /packs quebram para admin.
- Payload inválido é aceito em rota sensível.
- Logs expõem payload operacional sensível.

MÉDIO
- UX confusa.
- Tela sem estado vazio/erro.
- Erro técnico sem mensagem amigável.
- Dados operacionais incompletos.

BAIXO
- Texto, layout, organização, ícone ou melhoria futura sem impacto operacional imediato.
```

Correções P0 envolvem dois achados críticos/altos:

```text
- Auth fail-open: CRÍTICO.
- Logs sensíveis de saveSettings: ALTO.
```

## 5. Definition of Done de P0

P0 só está concluído se todos os itens abaixo estiverem OK ou reportados com erro objetivo:

```text
- Auth fail-open foi removido.
- auth_error possui tela própria e não libera painel.
- Logs sensíveis de saveSettings foram removidos ou protegidos por import.meta.env.DEV.
- miniapp/package.json tem script check.
- /status usa requireAdmin.
- /packs tenta Supabase antes de ArkhamDB.
- /packs mantém fallback ArkhamDB.
- Wrappers Python foram validados.
- python -m compileall -q . passou.
- python main.py healthcheck passou ou warnings esperados foram registrados.
- cd miniapp && npm run build passou.
- cd miniapp && npm run check passou.
- cd worker && npm run dry-run passou.
- Mini App não contém service role/token/Authorization header.
- Backlog P3 não foi executado sem autorização.
```

## 6. Arquivos autorizados para P0

A IA executora pode alterar somente estes arquivos em P0:

```text
miniapp/src/main.jsx
miniapp/package.json
worker/src/index.js
```

A IA executora pode apenas validar, sem alterar, estes arquivos:

```text
src/arkham_bot/handlers/supabase_client.py
src/arkham_bot/handlers/config.py
src/arkham_bot/handlers/local_storage.py
src/arkham_bot/handlers/scheduler.py
```

Não alterar em P0:

```text
README.md
supabase/migrations/*
src/arkham_bot/**, exceto se compileall apontar erro diretamente relacionado aos wrappers
worker/wrangler.toml
.env*
.github/workflows/*
```

## 7. P0.1 — Validar wrappers Python

Validar estes arquivos:

```text
src/arkham_bot/handlers/supabase_client.py
src/arkham_bot/handlers/config.py
src/arkham_bot/handlers/local_storage.py
src/arkham_bot/handlers/scheduler.py
```

Conteúdo esperado:

```python
# supabase_client.py
from ..core.supabase_client import SupabaseRestClient, get_supabase_client
__all__ = ["SupabaseRestClient", "get_supabase_client"]

# config.py
from ..core.config import *  # noqa: F403

# local_storage.py
from ..services.local_storage import *  # noqa: F403

# scheduler.py
from ..services.scheduler import *  # noqa: F403
```

Comandos:

```bash
python -m compileall -q .
python main.py healthcheck
```

Critério:

```text
/status e /cotd não podem quebrar por ModuleNotFoundError.
```

Se algum wrapper estiver diferente, corrigir apenas o wrapper divergente. Não refatorar `telegram_handlers.py` nesta fase.

## 8. P0.2 — Corrigir auth fail-open no Mini App

Arquivo:

```text
miniapp/src/main.jsx
```

Localizar o Auth Gate que chama:

```javascript
apiFetch('/me')
```

Código proibido:

```javascript
}).catch(() => setAuthState('ready'));
```

Trocar por:

```javascript
}).catch(() => {
  setAuthState('auth_error');
});
```

Adicionar mensagens no `I18N.pt`:

```javascript
authErrorTitle: 'Falha na validação administrativa',
authErrorText: 'Não foi possível validar o acesso administrativo. Reabra pelo Telegram ou verifique o Worker.',
```

Adicionar mensagens no `I18N.en`:

```javascript
authErrorTitle: 'Admin validation failed',
authErrorText: 'Could not validate admin access. Reopen from Telegram or check the Worker.',
```

Criar componente simples próximo aos demais gate screens:

```jsx
function AuthErrorGate({ copy }) {
  return (
    <GateScreen>
      <Icon name="server" className="gate-icon" />
      <p className="gate-title">{copy.authErrorTitle}</p>
      <p className="gate-text">{copy.authErrorText}</p>
    </GateScreen>
  );
}
```

Adicionar no bloco de renderização do Auth Gate:

```javascript
if (authState === 'auth_error') return <AuthErrorGate copy={copy} />;
```

Não alterar o comportamento de:

```text
no_telegram
unauthorized
loading
ready
```

Critério de aceite:

```text
- Sem Telegram/initData continua mostrando no_telegram.
- Usuário não admin continua bloqueado.
- Falha de /me mostra auth_error.
- Falha de /me não abre painel.
```

Armadilhas:

```text
- Não usar auth_error para ausência de Telegram.
- Não fechar o app automaticamente em auth_error; mostrar mensagem ajuda diagnóstico.
- Não deixar unauthorized preso em LoadingGate para sempre se for possível mostrar erro amigável depois; mas não alterar isso em P0 se gerar risco.
```

## 9. P0.3 — Remover logs sensíveis de saveSettings

Arquivo:

```text
miniapp/src/main.jsx
```

Remover ou proteger com `import.meta.env.DEV`:

```javascript
console.log('[saveSettings] payload:', JSON.stringify(body));
console.log('[saveSettings] response ok=%s status=%s', ok, status, json?.error || '');
console.error('[saveSettings] error:', json);
console.log('[saveSettings] returned day_config:', JSON.stringify(json.settings?.day_config));
```

Preferência em P0: remover completamente os logs de payload e day_config.

Substituição segura recomendada para o bloco de resposta:

```javascript
if (!ok) {
  haptic('notification', 'error');
  const errInfo = resolveError(json.error, `HTTP ${status}`, copy, json);
  setSettingsResult({ ok: false, ...errInfo, detail: json.error || errInfo.detail || `HTTP ${status}` });
} else {
  haptic('notification', 'success');
  applySettings(json.settings);
  setSettingsResult({ ok: true, friendly: copy.settingsSaved, detail: '' });
}
```

Critério:

```text
Produção não deve logar payload completo, telegram_chat_id, day_config, initData, token, service role ou header.
```

Depois de alterar, rodar:

```bash
grep -R "\[saveSettings\]\|saveSettings.*console" -n miniapp/src || true
```

Resultado aceitável:

```text
Nenhum resultado, ou apenas logs protegidos explicitamente por import.meta.env.DEV e sem payload sensível.
```

## 10. P0.4 — Adicionar script check no Mini App

Arquivo:

```text
miniapp/package.json
```

Adicionar:

```json
"check": "vite build"
```

Preservar scripts existentes.

Resultado esperado:

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

Critério:

```text
npm run build e npm run check executam com sucesso.
```

## 11. P0.5 — Tornar /status admin-only

Arquivo:

```text
worker/src/index.js
```

Na rota:

```javascript
if (pathname === '/status' && request.method === 'GET') {
```

Trocar:

```javascript
const auth = await requireAuth(request, env, ao, '/status');
```

por:

```javascript
const auth = await requireAdmin(request, env, ao, '/status');
```

Preservar:

```javascript
if (auth.response) return auth.response;
return handleStatus(request, env, ao);
```

Não alterar `/health`. Ele deve continuar simples e público como hoje.

Critério:

```text
- Admin recebe status.
- Não-admin recebe unauthorized.
- /health continua respondendo { ok: true }.
```

## 12. P0.6 — Fazer /packs preferir Supabase com fallback ArkhamDB

Arquivo:

```text
worker/src/index.js
```

Função:

```javascript
handleGetPacks
```

Comportamento atual confirmado:

```text
Busca https://arkhamdb.com/api/public/packs/ diretamente.
```

Comportamento desejado:

```text
1. Se SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY existirem, tentar ler arkham_packs.
2. Se arkham_packs retornar array não vazio, devolver source='supabase'.
3. Se Supabase falhar, estiver vazio ou env estiver incompleto, manter fallback atual ArkhamDB.
4. Não remover cache atual.
5. Não cachear falha.
6. Não logar service role ou headers.
```

Query Supabase:

```javascript
/rest/v1/arkham_packs?select=code,name,cycle_position,position,chapter,total&order=cycle_position.asc,position.asc&limit=500
```

Resposta Supabase esperada:

```javascript
{
  ok: true,
  packs,
  source: 'supabase'
}
```

Resposta fallback ArkhamDB pode continuar sem `source`, mas preferencialmente deve retornar:

```javascript
{
  ok: true,
  packs,
  source: 'arkhamdb'
}
```

Implementação orientativa:

```javascript
async function handleGetPacks(env, ao) {
  const now = Date.now();
  if (_packsCache.payload && now - _packsCache.ts < PACKS_CACHE_TTL_MS) {
    return withCors(jsonResponse(_packsCache.payload), ao);
  }

  if (env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY) {
    try {
      const rows = await fetchSupabaseJson(
        env,
        '/rest/v1/arkham_packs?select=code,name,cycle_position,position,chapter,total&order=cycle_position.asc,position.asc&limit=500',
      );
      if (Array.isArray(rows) && rows.length > 0) {
        const packs = rows.map((p) => ({
          code: p.code,
          name: p.name || p.code,
          cycle_position: p.cycle_position ?? null,
          position: p.position ?? null,
          chapter: p.chapter ?? 1,
          total: p.total ?? 0,
        }));
        _packsCache.payload = { ok: true, packs, source: 'supabase' };
        _packsCache.ts = now;
        return withCors(jsonResponse(_packsCache.payload), ao);
      }
    } catch {
      // fallback ArkhamDB abaixo; não logar service role nem headers
    }
  }

  // manter fallback ArkhamDB existente aqui
}
```

Critérios:

```text
- Se arkham_packs tem dados, /packs retorna source='supabase'.
- Se Supabase falhar, /packs ainda funciona via ArkhamDB.
- Se ArkhamDB falhar também, retorna packs_fetch_failed.
- Nenhum header ou service role é logado.
```

## 13. Validações obrigatórias de P0

Rodar na raiz:

```bash
python -m compileall -q .
python main.py healthcheck
```

Rodar no Mini App:

```bash
cd miniapp
npm install
npm run build
npm run check
```

Rodar no Worker:

```bash
cd ../worker
npm install
npm run dry-run
```

Buscas obrigatórias:

```bash
grep -R "setAuthState('ready')" -n miniapp/src || true
grep -R "\[saveSettings\]\|saveSettings.*console" -n miniapp/src || true
grep -R "pathname === '/status'" -n worker/src/index.js
grep -R "handleGetPacks" -n worker/src/index.js
grep -R "SUPABASE_SERVICE_ROLE_KEY\|TELEGRAM_BOT_TOKEN\|x-telegram-init-data\|authorization" -n miniapp/src || true
```

Critérios:

```text
- Não pode haver catch de /me liberando ready.
- Não pode haver log de saveSettings com payload completo.
- /status deve usar requireAdmin.
- /packs deve tentar Supabase antes da ArkhamDB.
- Mini App não deve conter service role/token/header Authorization.
```

Validação manual de /packs, se houver ambiente:

```bash
curl -s "$WORKER_URL/packs" -H "origin: $ALLOWED_ORIGIN" -H "x-telegram-init-data: $VALID_INIT_DATA"
```

Critério esperado:

```text
- Retorna JSON.
- Se Supabase tem arkham_packs: source='supabase'.
- Se Supabase não tem dados: retorna packs via fallback sem quebrar.
```

## 14. Teste manual mínimo após P0

No Telegram/Mini App:

```text
- Admin abre o Mini App.
- Não-admin é bloqueado.
- Worker fora ou /me falhando não libera painel.
- Postagem busca carta.
- Postagem enfileira comando.
- Configurações salvam.
- Fila mostra comando.
- Saúde abre.
```

No Telegram bot:

```text
/status
/cotd
/search Roland
/faq 01001
/card 01001
```

## 15. P1 — Melhorias incrementais aplicáveis depois de P0

Estas melhorias são aplicáveis ao projeto atual, mas não devem bloquear P0.

### 15.1 Separar Agenda de Configurações

O Mini App já tem configuração semanal dentro do fluxo de settings/day_detail. Melhorar a navegação criando menu `Agenda`, mas sem mudar payloads nem nomes de settings.

Critério prático:

```text
- Criar activeTab='schedule' apenas se for reaproveitar o código existente.
- Não mudar day_config.
- Não mudar settingsPatchPayload.
- Não mudar nomes de chaves salvas.
- Todos os dias prevalece se ativo.
- Se Todos os dias estiver inativo, respeitar configuração por dia.
```

### 15.2 Melhorar estados vazios e erros

Aplicar nas telas existentes:

```text
Postagem
Configurações
IA
Banco
Fila
Histórico
Manutenção
Saúde
Idioma
```

Cada uma deve ter, quando aplicável:

```text
loading
empty
ready
error
saving/sending
success
```

### 15.3 Melhorar Fila

Já existe listagem/cancelamento. Melhorar sem criar endpoints novos:

```text
- Separar visualmente pending, retrying, processing, failed, executed.
- Não mostrar JSON bruto por padrão.
- Exibir erro técnico em details.
- Manter cancelamento apenas para pending/retrying.
```

### 15.4 Melhorar Histórico

Já existe histórico com data e paginação. Melhorar sem mudar schema:

```text
- Busca por código/nome se o endpoint suportar q.
- Link ArkhamDB por card_code.
- Badge por status.
- Empty state quando não houver postagens.
```

### 15.5 Melhorar Destinos sem CRUD

O Worker já retorna `target_chats` no overview. Antes de criar CRUD, melhorar uso atual:

```text
- Mostrar destino padrão/selecionado com chat_id e message_thread_id.
- Deixar claro quando destino está desativado.
- Evitar postagem para destino desativado.
```

Não criar `/destinations` nesta fase.

### 15.6 Melhorar Saúde com dados já existentes

Sem criar `/bot-runtime`, usar o que já existe:

```text
/status
/overview
/health
/bot-info
```

Mostrar:

```text
Worker
Supabase
cards
packs
fila pendente/retrying/processing/failed
último sync aproximado
últimos erros de overview se disponíveis
```

## 16. P2 — Refatoração do main.jsx

Executar somente depois de P0 passar e P1 não estar quebrado.

A refatoração é aplicável porque `main.jsx` contém helpers Telegram, API, i18n, settings, componentes e telas no mesmo arquivo.

Ordem segura:

```text
1. Extrair telegram.js.
2. Rodar npm run build.
3. Extrair api.js.
4. Rodar npm run build.
5. Extrair i18n.js.
6. Rodar npm run build.
7. Extrair constants.js/settings.js.
8. Rodar npm run build.
9. Extrair icons.jsx.
10. Rodar npm run build.
11. Extrair componentes simples.
12. Rodar npm run build.
13. Extrair telas uma por vez.
14. Rodar npm run build após cada tela.
15. Criar App.jsx.
16. Reduzir main.jsx para bootstrap.
17. Rodar npm run build e npm run check.
```

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
  screens/
```

`main.jsx` final:

```jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './style.css';

createRoot(document.getElementById('root')).render(<App />);
```

Proibido durante a refatoração:

```text
- mudar endpoints
- mudar payloads
- mudar nomes de settings
- mudar UX junto com extração
- alterar Worker
- alterar backend Python
```

## 17. P3 — Backlog futuro, não executar sem autorização

Estes itens são válidos como evolução profissional, mas não devem ser executados automaticamente agora.

### 17.1 CRUD de Administradores

Motivo para backlog:

```text
O Worker consulta bot_admins para autenticar, mas não há endpoints /admins e /admins/:id hoje.
```

Requer:

```text
- endpoints owner-only
- regras para não remover último owner
- possível ajuste de schema/auditoria
```

### 17.2 CRUD de Destinos

Motivo para backlog:

```text
O overview já lê target_chats, mas não há endpoints CRUD completos para destinos.
```

Requer:

```text
- endpoints /destinations
- endpoint /test-message
- regras de destino padrão
- validação de message_thread_id
```

### 17.3 /ai-models

Motivo para backlog:

```text
Hoje há lista de modelos no front e no Worker. Melhor centralizar, mas isso não é bug P0.
```

### 17.4 /bot-runtime e /health/deep

Motivo para backlog:

```text
Exigiria heartbeat do bot Python e provavelmente tabela/registro novo.
```

Não criar migration sem autorização.

### 17.5 Rate limit robusto e idempotência backend

Motivo para backlog:

```text
O front já bloqueia clique duplo com loadingCmd. O Worker ainda pode melhorar idempotência, mas isso deve ser planejado.
```

### 17.6 Testes automatizados amplos

Backlog recomendado:

```text
- unit tests para validateSettingsPatch
- unit tests para validateTelegramInitData
- unit tests para command payload validation
- smoke tests para rotas do Worker
- testes de settingsPatchPayload no Mini App após refatoração
```

### 17.7 Versionamento front/Worker

Backlog recomendado:

```text
- Mini App mostrar versão/commit
- Worker expor versão/commit sem secrets
- Saúde mostrar compatibilidade front/Worker
```

## 18. Política de logs

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

## 19. Checklist final para a IA executora

Marcar cada item como `[OK]`, `[ERRO]` ou `[NÃO EXECUTADO: motivo]`.

```text
[ ] Leu este arquivo inteiro.
[ ] Não executou backlog P3 sem autorização.
[ ] Alterou somente arquivos permitidos para P0.
[ ] Validou wrappers Python.
[ ] Corrigiu auth fail-open.
[ ] Criou/validou auth_error visual.
[ ] Removeu/protegeu logs sensíveis de saveSettings.
[ ] Adicionou script check no miniapp/package.json.
[ ] Tornou /status admin-only.
[ ] Ajustou /packs para Supabase com fallback ArkhamDB.
[ ] Rodou python -m compileall -q .
[ ] Rodou python main.py healthcheck.
[ ] Rodou pytest -q ou registrou pendência.
[ ] Rodou cd miniapp && npm install, se necessário.
[ ] Rodou cd miniapp && npm run build.
[ ] Rodou cd miniapp && npm run check.
[ ] Rodou cd worker && npm install, se necessário.
[ ] Rodou cd worker && npm run dry-run.
[ ] Buscou setAuthState('ready') e confirmou que não há fail-open em /me.
[ ] Buscou logs de saveSettings e confirmou que não há payload sensível em produção.
[ ] Buscou secrets no miniapp/src e confirmou que não há service role/token no front.
[ ] Validou admin abrindo Mini App ou registrou pendência.
[ ] Validou não-admin bloqueado ou registrou pendência.
[ ] Validou Worker fora ou /me falhando sem liberar painel ou registrou pendência.
[ ] Validou postagem manual ou registrou pendência.
[ ] Validou salvar configurações ou registrou pendência.
[ ] Validou fila após comando ou registrou pendência.
[ ] Validou /status, /cotd, /search, /faq e /card no Telegram ou registrou pendência.
[ ] Classificou achados por severidade.
[ ] Informou risco residual.
```

## 20. Formato obrigatório de resposta

```text
RESULTADO:
- Arquivos alterados:
  - ...
- Correções P0 aplicadas:
  - ...
- Validações executadas:
  - python -m compileall -q .: OK/ERRO/NÃO EXECUTADO + motivo
  - python main.py healthcheck: OK/ERRO/NÃO EXECUTADO + motivo
  - pytest -q: OK/ERRO/NÃO EXECUTADO + motivo
  - cd miniapp && npm run build: OK/ERRO/NÃO EXECUTADO + motivo
  - cd miniapp && npm run check: OK/ERRO/NÃO EXECUTADO + motivo
  - cd worker && npm run dry-run: OK/ERRO/NÃO EXECUTADO + motivo
- Achados por severidade:
  - CRÍTICO: ...
  - ALTO: ...
  - MÉDIO: ...
  - BAIXO: ...
- Itens P1 recomendados após P0:
  - ...
- Backlog P3 não executado:
  - ...
- Pendências manuais:
  - ...
- Risco residual:
  - baixo/médio/alto + justificativa
```
