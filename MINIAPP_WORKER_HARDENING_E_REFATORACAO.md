# Mini App e Worker — plano profissional de hardening, UX, menus e refatoração

Este arquivo é o plano operacional canônico para elevar o Mini App administrativo e o Worker do Arkham Bot a nível profissional. Ele cobre correções obrigatórias, validações, menus, UX, segurança, RBAC, observabilidade, prevenção de erro humano, itens a remover/migrar e a refatoração completa do `miniapp/src/main.jsx`.

## Objetivo

Transformar o Mini App em um painel administrativo estável, seguro, auditável e sustentável, sem quebrar o bot Python. A execução deve ser incremental, com build e validação após cada fase.

## Princípios de qualidade profissional

- Toda ação administrativa deve ter autenticação e autorização explícitas.
- Toda ação destrutiva deve exigir confirmação clara.
- Toda tela deve ter estado de carregamento, sucesso, erro e vazio.
- Nenhum erro técnico deve aparecer sozinho sem mensagem amigável.
- Nenhum segredo, token, header de autenticação ou payload sensível deve ser logado.
- Nenhuma falha de rede deve liberar acesso administrativo.
- Nenhuma alteração deve depender apenas do front; o Worker deve validar tudo.
- O app deve proteger contra clique duplo, envio duplicado e salvamento parcial confuso.
- O app deve indicar claramente quando há alterações não salvas.
- O app deve ser operável por celular, com toque, safe area e layout Telegram correto.
- A manutenção deve priorizar previsibilidade sobre estética.

## Regras obrigatórias de execução

- Não alterar `.env`, secrets, tokens, chaves ou credenciais.
- Não imprimir `SUPABASE_SERVICE_ROLE_KEY`, `TELEGRAM_BOT_TOKEN`, `x-telegram-init-data`, Authorization headers ou payloads completos de settings.
- Não alterar migrations/banco sem autorização explícita.
- Não alterar backend Python, exceto para corrigir import quebrado diretamente relacionado a `/status`, `/cotd` ou processamento de comandos do Mini App.
- Não recriar documentação antiga.
- Não alterar README nesta tarefa, salvo autorização explícita.
- Não fazer commit automático antes de validar.
- Fazer alterações pequenas, reversíveis e testáveis.
- Rodar validações após cada fase.
- Se uma fase quebrar build, reverter somente a última alteração.

## Visão alvo de menus

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

A Home deve funcionar como hub. Não deve haver excesso de botões soltos. Cada item precisa ter nome curto, ícone consistente, subtítulo opcional e badge quando houver alerta.

## P0 — Correções obrigatórias imediatas

### 0.1 Validar wrappers Python

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

Validar:

```bash
grep -n "from \.supabase_client\|from \.config\|from \.local_storage\|from \.scheduler" src/arkham_bot/handlers/telegram_handlers.py || true
python -m compileall -q .
python main.py healthcheck
```

Critério: `/status` e `/cotd` não podem quebrar por `ModuleNotFoundError`.

### 0.2 Corrigir fail-open no Mini App

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

Adicionar `auth_error` no gate, com mensagem:

```text
Não foi possível validar o acesso administrativo. Reabra pelo Telegram ou verifique o Worker.
```

Critério: se `/me` falhar por rede, CORS, Worker fora, 500 ou JSON inválido, o painel não abre.

### 0.3 Remover logs sensíveis do `saveSettings()`

Remover ou proteger com `import.meta.env.DEV`:

```javascript
console.log('[saveSettings] payload:', ...)
console.log('[saveSettings] response ok=%s status=%s', ...)
console.error('[saveSettings] error:', ...)
console.log('[saveSettings] returned day_config:', ...)
```

Critério: produção não deve logar `telegram_chat_id`, `day_config`, payload de settings ou detalhes operacionais sensíveis.

### 0.4 Adicionar `check` no Mini App

Arquivo:

```text
miniapp/package.json
```

Adicionar:

```json
"check": "vite build"
```

Rodar:

```bash
cd miniapp
npm run build
npm run check
```

### 0.5 Tornar `/status` admin-only

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

Critério: não admin recebe `unauthorized`; admin recebe status.

### 0.6 `/packs` deve preferir Supabase

`handleGetPacks` deve tentar primeiro:

```text
arkham_packs: code,name,cycle_position,position,chapter,total
```

Resposta se Supabase tiver dados:

```javascript
{ ok: true, packs, source: 'supabase' }
```

Fallback obrigatório para ArkhamDB pública quando Supabase falhar ou estiver vazio.

## P1 — Validação profissional por tela

### Home

Deve mostrar somente atalhos úteis e estado operacional resumido.

Critérios:

- Mostra badge de fila pendente/falha.
- Mostra alerta se Worker ou Supabase estiverem com erro.
- Não mostra informação técnica crua na Home.
- Agrupa menus em Operação, Configuração e Sistema.
- Não duplica funções em múltiplos lugares sem necessidade.

### Postagem

Deve permitir postagem manual sem ambiguidade.

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

Deve conter:

- Toggle de postagem automática.
- Fuso horário.
- Modo `Todos os dias`.
- Configuração individual por dia.
- Horários globais e por dia.
- Filtros por ciclo/pack.
- Filtros por tipo de carta.
- Botão salvar claro.

Regras:

- Se `Todos os dias` estiver ativo, ele prevalece.
- Se estiver inativo, usar configuração de cada dia.
- Não salvar postagem automática sem dia ativo.
- Não salvar horário inválido.
- Não permitir estado visual que pareça salvo quando está pendente.
- Exibir resumo por dia: horários, ciclos e tipos.

### IA

Deve conter:

- IA habilitada.
- IA apenas nos posts automáticos.
- Idioma.
- Provedor.
- Modelo.
- Tom.
- Criatividade.
- Mensagem antes da carta.
- Delay antes da carta.
- Pergunta após a carta.
- Delay após a pergunta.
- Teste de geração.

Critérios:

- Modelos não devem ficar duplicados indefinidamente no front e Worker.
- Criar futuro endpoint `/ai-models`.
- Se modelo escolhido não for suportado, mostrar erro amigável.
- Deixar claro quando IA não roda em post manual por `ai_auto_only=true`.

### Banco de Dados

Deve conter:

- Total de cartas.
- Total de packs.
- Última sincronização.
- Status atualizado/desatualizado.
- Botão sincronizar ArkhamDB.
- Agendamento de sync.
- Último erro de sync.
- Resultado do último sync.

Critérios:

- `last_sync` deve vir de fonte confiável, não apenas do último comando criado.
- `/packs` deve refletir `arkham_packs` local quando possível.
- Botão sync deve confirmar antes de enfileirar.
- Se sync estiver em execução, bloquear novo sync ou avisar.

### Fila

Deve conter filtros:

- Pendentes.
- Processando.
- Retrying.
- Falhas.
- Executados.
- Cancelados.

Ações:

- Cancelar pendente.
- Reenfileirar falha.
- Ver erro completo.
- Limpar pendentes.

Critérios:

- Não mostrar JSON bruto por padrão.
- Detalhe técnico deve ficar em `details`.
- Comando já processando não deve ser cancelado sem regra explícita.
- Status deve ter badge visual consistente.

### Histórico

Deve conter:

- Data.
- Código.
- Nome.
- Status.
- Origem manual/automática.
- Telegram message id.
- Filtro por data.
- Busca por código/nome.
- Paginação.

Melhorias:

- Link ArkhamDB.
- Link Telegram quando possível.
- Badge sucesso/falha.
- Export futuro CSV/JSON se necessário.

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

Funcionalidades:

- Listar destinos.
- Criar destino.
- Editar nome amigável.
- Ativar/desativar.
- Definir padrão.
- Informar tópico Telegram via `message_thread_id`.
- Enviar mensagem de teste.

Critérios:

- Postagem manual permite escolher destino.
- Postagem automática usa destino padrão.
- Destino sem permissão do bot deve ser sinalizado.
- Message Thread ID deve ficar explícito para tópicos.

### Administradores

Novo menu restrito a `owner`.

Funcionalidades:

- Listar admins.
- Adicionar Telegram user id.
- Definir role `owner` ou `admin`.
- Ativar/desativar.
- Remover.
- Mostrar origem da permissão.

Regras:

- Apenas `owner` gerencia admins.
- Não permitir remover o último `owner`.
- Admin comum não promove usuários.
- Toda alteração deve registrar `updated_by`.

### Manutenção

Deve conter:

- Resetar ciclo.
- Limpar fila.
- Reprocessar falhas.
- Limpar cache, se existir comando seguro.
- Rodar diagnóstico.

Critérios:

- Ações destrutivas usam confirmação Telegram com botão destrutivo.
- Cada ação gera comando rastreável.
- Exibir resultado do comando, não assumir sucesso imediato.

### Saúde

Deve evoluir para painel operacional real.

Deve conter:

- Worker online.
- Supabase online.
- Bot Python online.
- Scheduler ativo.
- Polling/command worker ativo.
- Próxima postagem.
- Última postagem.
- Último erro.
- Último heartbeat.
- Versão/commit em execução.
- Ambiente.

Endpoints recomendados:

```text
/health/deep
/bot-runtime
```

Critério: Saúde deve responder à pergunta “o bot está funcionando agora e vai postar na hora certa?”.

### Aplicativo

Deve conter:

- Idioma do app.
- Usuário Telegram atual.
- Role atual.
- Origem da permissão.
- Endpoint do Worker.
- Versão do Mini App.
- Estado da sessão.

Critérios:

- Dados técnicos ficam recolhidos em `details`.
- Não exibir `initData` completo.
- Exibir somente tamanho/presença da sessão.

## P2 — Padrões profissionais de UX

### Estados obrigatórios por tela

Cada tela deve implementar:

```text
loading
empty
ready
error
saving/sending
success
```

Nenhuma tela deve parecer quebrada quando dados estiverem vazios.

### Mensagens de erro

Cada erro deve ter:

- Título amigável.
- Descrição curta.
- Detalhe técnico opcional recolhido.
- Ação recomendada.

Exemplo:

```text
Acesso negado
Seu Telegram ID não tem permissão administrativa.
Ação: peça para um owner adicionar seu usuário em Administradores.
```

### Prevenção de erro humano

Implementar:

- Confirmação em ação destrutiva.
- Botão desabilitado durante envio.
- Proteção contra clique duplo.
- Aviso de alterações não salvas.
- Validação antes de enviar para Worker.
- Validação duplicada no Worker.
- Resumo antes de salvar agenda complexa.

### Feedback visual

Implementar consistentemente:

- Badges `ok`, `warn`, `err`, `pending`.
- Spinners apenas onde há operação real.
- Haptic feedback em sucesso/erro/seleção.
- MainButton apenas quando houver alteração pendente.
- BackButton sempre coerente.

### Acessibilidade mínima

- Botões devem ter texto visível.
- Ícones não devem ser a única informação.
- Inputs devem ter label.
- Estados desabilitados devem ser visualmente claros.
- Tamanho de toque mínimo adequado para celular.

## P3 — Segurança e RBAC

### Papéis

```text
owner
admin
member ou none
```

Regras:

- `owner`: tudo.
- `admin`: operação e configuração, mas não gerencia owners/admins críticos.
- `member/none`: sem acesso ao painel.

### Endpoints admin-only

Todos estes devem usar `requireAdmin`:

```text
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
/destinations
/ai-models
/health/deep
/bot-runtime
```

### Endpoints owner-only futuros

```text
/admins
/admins/:id
```

### Auditoria

Toda ação administrativa deve registrar:

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

Para alteração direta de settings/admins/destinos, registrar também:

```text
updated_by
updated_at
previous_value quando seguro
new_value quando seguro
```

Não registrar secrets.

## P4 — Worker e contratos de API

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

Todo endpoint deve retornar JSON consistente:

Sucesso:

```json
{ "ok": true }
```

Erro:

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
```

## P5 — Refatoração do `main.jsx`

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

1. `telegram.js`.
2. `api.js`.
3. `i18n.js`.
4. `constants.js` e `settings.js`.
5. `icons.jsx`.
6. Componentes simples.
7. Componentes complexos.
8. Screens.
9. `App.jsx`.
10. `main.jsx` como bootstrap.

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

## P6 — O que remover, migrar ou manter

### Remover

- Logs de produção em `saveSettings`.
- Qualquer fallback que libere painel sem admin confirmado.
- JSON bruto aberto por padrão.
- Duplicação permanente de modelos IA no front e Worker.
- Busca primária de packs na ArkhamDB quando Supabase local estiver populado.
- Menus misturados sem domínio claro.

### Migrar

- Agenda para menu próprio.
- Destinos para menu próprio.
- Admins para menu próprio owner-only.
- Modelos IA para `/ai-models`.
- Diagnóstico do bot Python para `/bot-runtime`.
- Status de sync para fonte confiável no banco.

### Manter

- Telegram theme variables.
- Safe area handling.
- Haptic feedback.
- Telegram MainButton.
- Telegram BackButton.
- Fallback ArkhamDB de packs.
- Worker como única camada entre Mini App e Supabase.

## P7 — Diagnóstico avançado futuro

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

## P8 — Checklist final de aceite profissional

### Build e runtime

```bash
python -m compileall -q .
python main.py healthcheck
cd miniapp && npm run build && npm run check
cd ../worker && npm run dry-run
```

### Regressão por busca

```bash
grep -R "setAuthState('ready')" -n miniapp/src || true
grep -R "\[saveSettings\]\|saveSettings.*console" -n miniapp/src || true
grep -R "pathname === '/status'" -n worker/src/index.js
grep -R "handleGetPacks" -n worker/src/index.js
grep -R "from \.supabase_client\|from \.config\|from \.local_storage\|from \.scheduler" -n src/arkham_bot/handlers/telegram_handlers.py || true
```

### Teste manual Telegram

```text
/status
/cotd
/search Roland
/faq 01001
```

### Teste manual Mini App

- Admin abre o app.
- Não admin é bloqueado.
- Worker fora não libera painel.
- Postagem busca carta.
- Postagem enfileira comando.
- Destino aparece corretamente.
- Agenda salva e recarrega.
- IA salva e recarrega.
- Banco carrega status.
- Fila lista comandos.
- Histórico pagina e filtra.
- Saúde mostra status real.
- Idioma alterna.
- BackButton funciona.
- MainButton aparece somente com alterações pendentes.
- Ação destrutiva exige confirmação.

## Ordem de execução recomendada

```text
P0 — Segurança e estabilidade imediata
P1 — Menus e UX profissional
P2 — Estados e prevenção de erro humano
P3 — RBAC e auditoria
P4 — Contratos do Worker
P5 — Refatoração do main.jsx
P6 — Remover/migrar/manter
P7 — Diagnóstico avançado futuro
P8 — Checklist final
```

## Formato de resposta obrigatório da IA executora

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
