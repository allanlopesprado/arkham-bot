# Mini App e Worker — ordem de serviço técnica de nível profissional

Este arquivo é uma ordem de serviço técnica, um contrato de qualidade e uma matriz de aceite para corrigir e evoluir o Mini App administrativo e o Worker do Arkham Bot. Ele foi validado contra o código real do projeto e deve ser tratado pela IA executora como instrução obrigatória, não como sugestão.

A prioridade é corrigir problemas confirmados sem gerar regressão. Melhorias maiores ficam separadas em fases posteriores.

---

## 1. Mandato da IA executora

A IA executora deve:

```text
1. Ler este arquivo inteiro antes de alterar qualquer código.
2. Executar primeiro apenas P0.
3. Fazer a menor alteração correta possível.
4. Preservar comportamento existente que não esteja explicitamente marcado como problema.
5. Não criar endpoints, migrations, tabelas, telas novas complexas ou mudanças estruturais fora da fase autorizada.
6. Rodar validações e registrar evidências.
7. Se algo não puder ser validado, responder NÃO EXECUTADO + motivo.
8. Não declarar sucesso sem comando executado ou evidência manual.
9. Não misturar correção, refatoração e melhoria visual no mesmo passo.
10. Não executar backlog P3 sem autorização explícita.
```

Este documento substitui qualquer decisão genérica da IA. Se houver conflito entre este arquivo e uma interpretação automática, este arquivo prevalece.

---

## 2. Escopo desta execução

### Executar agora: P0

```text
- Corrigir auth fail-open no Mini App.
- Remover logs sensíveis em saveSettings.
- Adicionar script check no miniapp/package.json.
- Tornar /status admin-only no Worker.
- Fazer /packs tentar Supabase antes da ArkhamDB pública.
- Validar wrappers Python existentes.
- Rodar validações técnicas obrigatórias.
```

### Não executar agora

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
- alterações em README.md.
- alterações em workflows.
- alterações em wrangler.toml.
- alterações em .env ou secrets.
```

Esses itens são backlog/fase posterior.

---

## 3. Diagnóstico confirmado no código real

```text
CONFIRMADO
- miniapp/src/main.jsx concentra Telegram helpers, API client, i18n, settings, componentes e telas.
- O Mini App já possui base Telegram funcional: haptic, popup, MainButton, BackButton, tema e safe area.
- O Mini App já possui Home, Postagem, Configurações, IA, Banco, Fila, Histórico, Manutenção, Saúde e Idioma.
- O Worker já valida initData do Telegram por HMAC.
- O Worker já consulta bot_admins para identificar role owner/admin.
- O Worker já valida boa parte dos settings.
- O Worker já protege a maioria das rotas administrativas com requireAdmin.
- Os wrappers Python em src/arkham_bot/handlers/ já existem e estão corretos.

BUGS / AJUSTES CONFIRMADOS
- Auth gate do Mini App faz fail-open: se /me falha, cai em setAuthState('ready').
- saveSettings loga payload completo e day_config no console.
- miniapp/package.json não tem script check.
- /status usa requireAuth, não requireAdmin.
- /packs busca ArkhamDB pública diretamente e não tenta arkham_packs no Supabase primeiro.

NÃO É BUG P0
- main.jsx grande é dívida técnica, não bug operacional imediato.
- CRUD de Administradores exige endpoints novos.
- CRUD de Destinos exige endpoints novos.
- /bot-runtime e /health/deep exigem desenho de runtime/heartbeat.
- Rate limit robusto no Worker é melhoria planejada, não correção mínima.
```

---

## 4. Requisitos rastreáveis de P0

Cada alteração de P0 deve ser vinculada a um requisito abaixo.

```text
REQ-P0-001 — Auth fail-closed
O Mini App não pode liberar painel administrativo quando /me falha por rede, CORS, Worker fora, resposta 500 ou JSON inválido.

REQ-P0-002 — Logs sanitizados
O Mini App não pode logar payload completo de settings, day_config, telegram_chat_id, initData, tokens, service role ou Authorization headers.

REQ-P0-003 — Check local do Mini App
O Mini App deve ter npm run check executando vite build.

REQ-P0-004 — /status admin-only
A rota /status deve exigir requireAdmin, preservando /health como rota simples e pública.

REQ-P0-005 — /packs com fonte local preferencial
A rota /packs deve tentar arkham_packs no Supabase antes de chamar ArkhamDB pública.

REQ-P0-006 — Fallback ArkhamDB preservado
Se Supabase falhar, estiver vazio ou não estiver configurado, /packs deve continuar usando ArkhamDB pública.

REQ-P0-007 — Wrappers Python preservados
Os wrappers em src/arkham_bot/handlers devem continuar resolvendo imports legados sem refatorar telegram_handlers.py.

REQ-P0-008 — Sem alteração fora do escopo
P0 não pode alterar migrations, README, workflows, .env, wrangler.toml ou backend Python fora dos wrappers.
```

---

## 5. Matriz requisito × arquivo × validação

```text
REQ-P0-001
Arquivo: miniapp/src/main.jsx
Validação: grep setAuthState('ready'); teste manual de falha /me; npm run build.

REQ-P0-002
Arquivo: miniapp/src/main.jsx
Validação: grep [saveSettings] e console; revisão de payloads logados; npm run build.

REQ-P0-003
Arquivo: miniapp/package.json
Validação: npm run check.

REQ-P0-004
Arquivo: worker/src/index.js
Validação: grep rota /status; dry-run; teste não-admin se possível.

REQ-P0-005
Arquivo: worker/src/index.js
Validação: grep handleGetPacks; /packs retorna source='supabase' quando há dados.

REQ-P0-006
Arquivo: worker/src/index.js
Validação: simular/registrar fallback; /packs não quebra se Supabase falha ou vazio.

REQ-P0-007
Arquivos: src/arkham_bot/handlers/*.py
Validação: python -m compileall -q .; python main.py healthcheck.

REQ-P0-008
Escopo: repositório
Validação: git diff --name-only deve listar apenas arquivos autorizados, salvo justificativa explícita.
```

---

## 6. Arquivos permitidos e proibidos em P0

### Pode alterar

```text
miniapp/src/main.jsx
miniapp/package.json
worker/src/index.js
```

### Pode validar, mas não alterar salvo erro direto

```text
src/arkham_bot/handlers/supabase_client.py
src/arkham_bot/handlers/config.py
src/arkham_bot/handlers/local_storage.py
src/arkham_bot/handlers/scheduler.py
```

### Não alterar em P0

```text
README.md
docs/**
supabase/migrations/**
src/arkham_bot/**, exceto wrappers se compileall apontar erro direto
worker/wrangler.toml
worker/wrangler.toml.example
.env*
.github/workflows/**
```

Se a IA achar que precisa alterar arquivo proibido, deve registrar como pendência e parar essa parte.

---

## 7. Classificação de severidade

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
- Fallback removido sem substituto funcional.

MÉDIO
- UX confusa.
- Tela sem estado vazio/erro.
- Erro técnico sem mensagem amigável.
- Dados operacionais incompletos.

BAIXO
- Texto, layout, organização, ícone ou melhoria futura sem impacto operacional imediato.
```

Correções P0 atacam principalmente:

```text
- Auth fail-open: CRÍTICO.
- Logs sensíveis de saveSettings: ALTO.
- /status com autorização fraca: ALTO.
- /packs dependente de ArkhamDB externa: MÉDIO/ALTO, conforme operação.
```

---

## 8. Definition of Done de P0

P0 só está concluído se todos estes itens estiverem OK ou documentados com erro objetivo:

```text
- REQ-P0-001 atendido.
- REQ-P0-002 atendido.
- REQ-P0-003 atendido.
- REQ-P0-004 atendido.
- REQ-P0-005 atendido.
- REQ-P0-006 atendido.
- REQ-P0-007 atendido.
- REQ-P0-008 atendido.
- python -m compileall -q . passou.
- python main.py healthcheck passou ou warnings esperados foram registrados.
- cd miniapp && npm run build passou.
- cd miniapp && npm run check passou.
- cd worker && npm run dry-run passou.
- Evidências foram reportadas.
- Backlog P3 não foi executado sem autorização.
```

---

## 9. Critérios de bloqueio

A execução deve parar e reportar ERRO se ocorrer:

```text
- Build do Mini App quebra e a causa não é corrigida.
- Worker dry-run quebra e a causa não é corrigida.
- Python compileall quebra fora dos wrappers.
- Correção exige migration.
- Correção exige secret, .env ou deploy externo.
- Correção exige mudar contrato de payload existente.
- Correção exige alterar backend Python além dos wrappers.
- Algum token/secret aparece no front, logs ou resposta.
- git diff inclui arquivo proibido sem justificativa.
```

---

## 10. P0.1 — Validar wrappers Python

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

---

## 11. P0.2 — Corrigir auth fail-open no Mini App

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

Não alterar comportamento de:

```text
no_telegram
unauthorized
loading
ready
```

Critérios de aceite:

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
- Não refatorar todo o Auth Gate nesta fase.
```

---

## 12. P0.3 — Remover logs sensíveis de saveSettings

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

Substituição segura recomendada:

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

Validar:

```bash
grep -R "\[saveSettings\]\|saveSettings.*console" -n miniapp/src || true
```

Resultado aceitável:

```text
Nenhum resultado, ou apenas logs protegidos por import.meta.env.DEV e sem payload sensível.
```

---

## 13. P0.4 — Adicionar script check no Mini App

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

---

## 14. P0.5 — Tornar /status admin-only

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

Não alterar `/health`. Ele deve continuar simples e público.

Critérios:

```text
- Admin recebe status.
- Não-admin recebe unauthorized.
- /health continua respondendo { ok: true }.
```

---

## 15. P0.6 — Fazer /packs preferir Supabase com fallback ArkhamDB

Arquivo:

```text
worker/src/index.js
```

Função:

```javascript
handleGetPacks
```

Comportamento desejado:

```text
1. Se SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY existirem, tentar ler arkham_packs.
2. Se arkham_packs retornar array não vazio, devolver source='supabase'.
3. Se Supabase falhar, estiver vazio ou env estiver incompleto, manter fallback ArkhamDB.
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
{ ok: true, packs, source: 'supabase' }
```

Resposta fallback recomendada:

```javascript
{ ok: true, packs, source: 'arkhamdb' }
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

---

## 16. Plano de testes de P0

### TC-P0-001 — Build Python

```text
Comando: python -m compileall -q .
Espera: exit code 0.
Falha bloqueia P0: sim.
```

### TC-P0-002 — Healthcheck Python

```text
Comando: python main.py healthcheck
Espera: OK ou warnings esperados por ambiente sem credenciais reais.
Falha bloqueia P0: sim, se erro indicar regressão de código.
```

### TC-P0-003 — Build Mini App

```text
Comando: cd miniapp && npm run build
Espera: build concluído.
Falha bloqueia P0: sim.
```

### TC-P0-004 — Check Mini App

```text
Comando: cd miniapp && npm run check
Espera: build concluído.
Falha bloqueia P0: sim.
```

### TC-P0-005 — Worker dry-run

```text
Comando: cd worker && npm run dry-run
Espera: dry-run concluído.
Falha bloqueia P0: sim.
```

### TC-P0-006 — Busca de fail-open

```text
Comando: grep -R "setAuthState('ready')" -n miniapp/src || true
Espera: não existir catch de /me liberando ready.
Falha bloqueia P0: sim se ainda existir fail-open.
```

### TC-P0-007 — Busca de logs sensíveis

```text
Comando: grep -R "\[saveSettings\]\|saveSettings.*console" -n miniapp/src || true
Espera: nenhum log sensível de payload/day_config.
Falha bloqueia P0: sim se payload sensível ainda for logado.
```

### TC-P0-008 — Busca de secrets no front

```text
Comando: grep -R "SUPABASE_SERVICE_ROLE_KEY\|TELEGRAM_BOT_TOKEN\|x-telegram-init-data\|authorization" -n miniapp/src || true
Espera: nenhum service role/token/authorization no front. x-telegram-init-data pode aparecer apenas como header esperado de authHeaders.
Falha bloqueia P0: sim se token/service role/authorization aparecer no front.
```

### TC-P0-009 — Validação manual admin

```text
Ação: abrir Mini App como admin.
Espera: painel abre.
Falha bloqueia P0: sim se ambiente real disponível.
```

### TC-P0-010 — Validação manual não-admin

```text
Ação: abrir Mini App como usuário não admin.
Espera: painel não abre.
Falha bloqueia P0: sim se ambiente real disponível.
```

### TC-P0-011 — Validação manual /me falhando

```text
Ação: simular Worker fora, CORS inválido ou falha de /me.
Espera: Mini App mostra auth_error e não abre painel.
Falha bloqueia P0: sim se ambiente permitir simulação.
```

### TC-P0-012 — Validação /packs

```text
Ação: chamar /packs com auth admin válida.
Espera: se arkham_packs tem dados, source='supabase'; se não, fallback ArkhamDB funciona.
Falha bloqueia P0: sim se /packs quebrar.
```

---

## 17. Evidência obrigatória

No resultado final, a IA deve registrar evidência para cada validação:

```text
- ID do teste.
- Comando executado ou ação manual.
- Resultado: OK/ERRO/NÃO EXECUTADO.
- Trecho curto do erro se falhou.
- Motivo objetivo se não executou.
```

Não aceitar como evidência:

```text
- “parece ok”
- “validado visualmente” sem descrever ação
- “não testei mas deve funcionar”
- “corrigido” sem comando ou justificativa
```

---

## 18. Plano de rollback de P0

Se algum erro crítico aparecer após as alterações:

```text
- Mini App não abre para admin.
- /me, /settings ou /bot-command retornam 500.
- Worker dry-run falha.
- Bot Python para de compilar.
- Postagem manual deixa de enfileirar comando.
- Configurações deixam de salvar.
- Secret aparece no front/log/resposta.
```

Então executar análise de rollback:

```bash
git status
git diff
git log --oneline -n 5
```

Não fazer rollback automático sem reportar. Informar qual commit/arquivo seria revertido.

---

## 19. P1 — Melhorias incrementais aplicáveis depois de P0

Estas melhorias são aplicáveis ao projeto atual, mas não devem bloquear P0.

```text
- Separar Agenda de Configurações reaproveitando código existente.
- Melhorar estados vazios e erros nas telas atuais.
- Melhorar Fila sem endpoints novos.
- Melhorar Histórico sem mudar schema.
- Melhorar visualização de Destinos usando target_chats já vindo no overview.
- Melhorar Saúde usando /status, /overview, /health e /bot-info.
```

Restrições P1:

```text
- Não mudar day_config.
- Não mudar settingsPatchPayload.
- Não mudar nomes de settings.
- Não criar /destinations.
- Não criar /admins.
- Não criar migrations.
```

---

## 20. P2 — Refatoração do main.jsx

Executar somente depois de P0 passar e P1 não estar quebrado.

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

Proibido durante refatoração:

```text
- mudar endpoints
- mudar payloads
- mudar nomes de settings
- mudar UX junto com extração
- alterar Worker
- alterar backend Python
```

---

## 21. P3 — Backlog futuro, não executar sem autorização

```text
- CRUD de Administradores.
- CRUD de Destinos.
- /ai-models.
- /bot-runtime.
- /health/deep.
- Rate limit robusto e idempotência backend.
- Testes automatizados amplos.
- Versionamento front/Worker.
```

Motivos:

```text
- Exigem endpoints novos.
- Podem exigir migrations.
- Alteram arquitetura operacional.
- Não são necessários para corrigir P0.
```

---

## 22. Política de logs

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

---

## 23. Checklist final para a IA executora

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
[ ] Rodou TC-P0-001.
[ ] Rodou TC-P0-002.
[ ] Rodou TC-P0-003.
[ ] Rodou TC-P0-004.
[ ] Rodou TC-P0-005.
[ ] Rodou TC-P0-006.
[ ] Rodou TC-P0-007.
[ ] Rodou TC-P0-008.
[ ] Executou ou registrou pendência de TC-P0-009.
[ ] Executou ou registrou pendência de TC-P0-010.
[ ] Executou ou registrou pendência de TC-P0-011.
[ ] Executou ou registrou pendência de TC-P0-012.
[ ] Classificou achados por severidade.
[ ] Informou risco residual.
[ ] Incluiu evidências no resultado final.
```

---

## 24. Formato obrigatório de resposta

```text
RESULTADO:
- Arquivos alterados:
  - ...
- Requisitos atendidos:
  - REQ-P0-001: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-002: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-003: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-004: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-005: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-006: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-007: OK/ERRO/NÃO EXECUTADO + evidência
  - REQ-P0-008: OK/ERRO/NÃO EXECUTADO + evidência
- Testes executados:
  - TC-P0-001: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-002: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-003: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-004: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-005: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-006: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-007: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-008: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-009: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-010: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-011: OK/ERRO/NÃO EXECUTADO + evidência
  - TC-P0-012: OK/ERRO/NÃO EXECUTADO + evidência
- Achados por severidade:
  - CRÍTICO: ...
  - ALTO: ...
  - MÉDIO: ...
  - BAIXO: ...
- Arquivos fora do escopo alterados:
  - nenhum / listar e justificar
- Itens P1 recomendados após P0:
  - ...
- Backlog P3 não executado:
  - ...
- Pendências manuais:
  - ...
- Plano de rollback se necessário:
  - ...
- Risco residual:
  - baixo/médio/alto + justificativa
```
