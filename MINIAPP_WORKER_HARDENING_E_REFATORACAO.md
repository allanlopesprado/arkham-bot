# Mini App e Worker — plano validado contra o código real

Este arquivo é a especificação operacional para evoluir o Mini App administrativo e o Worker do Arkham Bot sem quebrar o bot Python. Esta versão foi revisada contra o estado real do projeto e separa claramente: bug confirmado, hardening aplicável agora, melhoria incremental, refatoração posterior e backlog futuro.

## 1. Como a IA executora deve usar este arquivo

Leia este arquivo inteiro antes de alterar código. Execute primeiro somente o bloco **P0 — Obrigatório agora**. Não implemente backlog futuro como se fosse bug. Não crie migrations, endpoints novos, telas novas complexas ou alterações destrutivas sem autorização explícita.

Se alguma validação não puder ser executada no ambiente atual, registre como `NÃO EXECUTADO + motivo`. Não invente sucesso.

Regra de ouro: **corrigir o mínimo necessário primeiro, validar, e só depois avançar para melhorias**.

## 2. Diagnóstico real do projeto

A leitura do projeto confirmou estes pontos:

```text
CONFIRMADO NO CÓDIGO
- miniapp/src/main.jsx concentra helpers Telegram, API, i18n, settings, componentes e telas.
- O Mini App já tem Telegram helpers, haptic, popup, MainButton, BackButton, safe area e tema Telegram.
- O Mini App já tem Home, Postagem, Configurações, IA, Banco, Fila, Histórico, Manutenção, Saúde e Idioma.
- O Worker já valida initData do Telegram por HMAC.
- O Worker já consulta bot_admins para role owner/admin.
- O Worker já valida boa parte dos settings.
- O Worker já protege a maioria das rotas administrativas com requireAdmin.
- Os wrappers Python em src/arkham_bot/handlers/ já existem e estão corretos.

BUGS / AJUSTES CONFIRMADOS
- Auth gate do Mini App ainda faz fail-open: catch de /me chama setAuthState('ready').
- saveSettings ainda loga payload completo e day_config no console.
- miniapp/package.json ainda não tem script check.
- /status no Worker ainda usa requireAuth em vez de requireAdmin.
- /packs no Worker ainda busca ArkhamDB pública diretamente, sem tentar arkham_packs no Supabase primeiro.

NÃO TRATAR COMO BUG IMEDIATO
- Separar main.jsx em módulos é correto, mas é refatoração posterior.
- CRUD de Administradores é futuro; não há endpoint /admins hoje.
- CRUD de Destinos é futuro; há dados de target_chats no overview, mas não há tela/endpoint CRUD completo.
- /bot-runtime e /health/deep são futuros e podem exigir tabela/migration.
- Testes automatizados amplos são desejáveis, mas não bloqueiam P0.
```

## 3. Regra de prioridade

```text
P0 — Fazer agora: bugs confirmados e hardening de baixo risco.
P1 — Fazer depois de P0 passar: melhorias incrementais em telas existentes.
P2 — Fazer depois de build estável: refatoração do main.jsx.
P3 — Backlog futuro: endpoints novos, telas novas completas, migrations e observabilidade avançada.
```

A IA executora deve parar após P0 se qualquer validação crítica falhar.

## 4. Definition of Done para P0

P0 só está concluído se:

```text
- Auth fail-open foi corrigido.
- Logs sensíveis de saveSettings foram removidos ou protegidos por import.meta.env.DEV.
- miniapp/package.json tem script check.
- /status usa requireAdmin.
- /packs tenta Supabase antes da ArkhamDB pública e mantém fallback.
- Wrappers Python foram validados.
- python -m compileall -q . passou ou erro foi corrigido.
- python main.py healthcheck passou ou warnings esperados foram registrados.
- cd miniapp && npm run build passou.
- cd miniapp && npm run check passou.
- cd worker && npm run dry-run passou.
- Nenhum secret/token foi exposto.
```

## 5. P0 — Obrigatório agora

### 5.1 Validar wrappers Python já existentes

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

Rodar:

```bash
python -m compileall -q .
python main.py healthcheck
```

Critério:

```text
/status e /cotd não podem quebrar por ModuleNotFoundError.
```

### 5.2 Corrigir auth fail-open no Mini App

Arquivo:

```text
miniapp/src/main.jsx
```

Localizar o Auth Gate que chama `apiFetch('/me')`.

Proibido:

```javascript
}).catch(() => setAuthState('ready'));
```

Trocar para:

```javascript
}).catch(() => {
  setAuthState('auth_error');
});
```

Adicionar tratamento visual para `auth_error`. Reutilizar o padrão de gate existente, sem criar arquitetura nova.

Implementação recomendada no `I18N.pt`:

```javascript
authErrorTitle: 'Falha na validação administrativa',
authErrorText: 'Não foi possível validar o acesso administrativo. Reabra pelo Telegram ou verifique o Worker.',
```

Implementação recomendada no `I18N.en`:

```javascript
authErrorTitle: 'Admin validation failed',
authErrorText: 'Could not validate admin access. Reopen from Telegram or check the Worker.',
```

Criar componente simples, se ainda não existir:

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

Adicionar no render do Auth Gate:

```javascript
if (authState === 'auth_error') return <AuthErrorGate copy={copy} />;
```

Critério:

```text
Se /me falhar por rede, CORS, Worker fora, 500 ou JSON inválido, o painel não abre.
```

Armadilha a evitar:

```text
Não trocar auth_error por no_telegram. no_telegram significa ausência de Telegram/initData; auth_error significa falha ao validar admin no Worker.
```

### 5.3 Remover logs sensíveis de saveSettings

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

Preferência para P0:

```text
Remover completamente os logs de payload e day_config.
Manter erro apenas sanitizado, se realmente necessário.
```

Substituição segura sugerida:

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
Produção não deve logar payload completo, telegram_chat_id, day_config, initData, token ou header.
```

### 5.4 Adicionar script check no Mini App

Arquivo:

```text
miniapp/package.json
```

Adicionar:

```json
"check": "vite build"
```

Preservar scripts existentes.

Exemplo esperado:

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
npm run build e npm run check devem executar o mesmo build com sucesso.
```

### 5.5 Tornar /status admin-only

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

Preservar o restante da rota:

```javascript
if (auth.response) return auth.response;
return handleStatus(request, env, ao);
```

Critério:

```text
Admin continua recebendo status.
Usuário autenticado mas não admin recebe unauthorized.
/health continua público/simples como hoje.
```

### 5.6 Fazer /packs preferir Supabase com fallback ArkhamDB

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

Query sugerida:

```javascript
/rest/v1/arkham_packs?select=code,name,cycle_position,position,chapter,total&order=cycle_position.asc,position.asc&limit=500
```

Formato de resposta Supabase:

```javascript
{
  ok: true,
  packs,
  source: 'supabase'
}
```

Formato dos packs:

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

Critério:

```text
Se arkham_packs tem dados, /packs retorna source='supabase'.
Se Supabase falhar ou estiver vazio, /packs ainda funciona via ArkhamDB.
```

## 6. Validações obrigatórias de P0

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

## 7. Teste manual mínimo após P0

No Telegram/Mini App:

```text
- Admin abre o Mini App.
- Não admin é bloqueado.
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

## 8. P1 — Melhorias incrementais aplicáveis depois de P0

Estas melhorias são aplicáveis ao projeto atual, mas não devem bloquear P0.

### 8.1 Separar Agenda de Configurações

O Mini App já tem configuração semanal dentro do fluxo de settings/day_detail. Melhorar a navegação criando menu `Agenda`, mas sem mudar payloads nem nomes de settings.

Regra:

```text
Se Todos os dias estiver ativo, ele prevalece.
Se inativo, respeitar configuração individual de cada dia.
```

Critério prático:

```text
- Criar activeTab='schedule' apenas se for reaproveitar o código existente.
- Não mudar day_config.
- Não mudar settingsPatchPayload.
- Não mudar nomes de chaves salvas.
```

### 8.2 Melhorar estados vazios e erros

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

### 8.3 Melhorar Fila

Já existe listagem/cancelamento. Melhorar sem criar endpoints novos:

```text
- Separar visualmente pending, retrying, processing, failed, executed.
- Não mostrar JSON bruto por padrão.
- Exibir erro técnico em details.
- Manter cancelamento apenas para pending/retrying.
```

### 8.4 Melhorar Histórico

Já existe histórico com data e paginação. Melhorar sem mudar schema:

```text
- Busca por código/nome se o endpoint suportar q.
- Link ArkhamDB por card_code.
- Badge por status.
- Empty state quando não houver postagens.
```

### 8.5 Melhorar Destinos sem CRUD

O Worker já retorna `target_chats` no overview. Antes de criar CRUD, melhorar uso atual:

```text
- Mostrar destino padrão/selecionado com chat_id e message_thread_id.
- Deixar claro quando destino está desativado.
- Evitar postagem para destino desativado.
```

Não criar `/destinations` nesta fase.

### 8.6 Melhorar Saúde com dados já existentes

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

## 9. P2 — Refatoração do main.jsx

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

## 10. P3 — Backlog futuro, não executar sem autorização

Estes itens são válidos como evolução profissional, mas não devem ser executados automaticamente agora.

### 10.1 CRUD de Administradores

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

### 10.2 CRUD de Destinos

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

### 10.3 /ai-models

Motivo para backlog:

```text
Hoje há lista de modelos no front e no Worker. Melhor centralizar, mas isso não é bug P0.
```

### 10.4 /bot-runtime e /health/deep

Motivo para backlog:

```text
Exigiria heartbeat do bot Python e provavelmente tabela/registro novo.
```

Não criar migration sem autorização.

### 10.5 Rate limit robusto e idempotência backend

Motivo para backlog:

```text
O front já bloqueia clique duplo com loadingCmd. O Worker ainda pode melhorar idempotência, mas isso deve ser planejado.
```

### 10.6 Testes automatizados amplos

Backlog recomendado:

```text
- unit tests para validateSettingsPatch
- unit tests para validateTelegramInitData
- unit tests para command payload validation
- smoke tests para rotas do Worker
- testes de settingsPatchPayload no Mini App após refatoração
```

### 10.7 Versionamento front/Worker

Backlog recomendado:

```text
- Mini App mostrar versão/commit
- Worker expor versão/commit sem secrets
- Saúde mostrar compatibilidade front/Worker
```

## 11. Política de logs

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

## 12. Severidade dos achados

```text
CRÍTICO
- Expõe secret/token/service role.
- Permite acesso admin sem validação.
- Quebra bot Python em produção.
- Impede postagem automática/manual.
- Worker retorna 500 em /me, /settings ou /bot-command.

ALTO
- Não salva configurações.
- Duplica comandos por clique duplo.
- /status, /settings, /commands ou /packs quebram para admin.
- Payload inválido é aceito em rota sensível.

MÉDIO
- UX confusa.
- Tela sem estado vazio/erro.
- Erro técnico sem mensagem amigável.
- Dados operacionais incompletos.

BAIXO
- Texto, layout, organização, ícone ou melhoria futura sem impacto operacional imediato.
```

## 13. Checklist final para a IA executora

Marcar cada item como `[OK]`, `[ERRO]` ou `[NÃO EXECUTADO: motivo]`.

```text
[ ] Leu este arquivo inteiro.
[ ] Não executou backlog P3 sem autorização.
[ ] Validou wrappers Python.
[ ] Corrigiu auth fail-open.
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

## 14. Formato obrigatório de resposta

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
