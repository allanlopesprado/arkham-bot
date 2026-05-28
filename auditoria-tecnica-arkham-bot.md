# Auditoria Técnica — Arkham Bot

Data da auditoria: 2026-05-28  
Repositório analisado: `allanlopesprado/arkham-bot`  
Escopo: análise estática da branch `main`, sem alteração de arquivos no repositório.

## 1. Sumário executivo

O projeto não está estruturalmente errado. A base é coerente para o objetivo proposto: bot Python para Telegram, Mini App administrativo em React/Vite, Cloudflare Worker como camada de API/autenticação, Supabase como banco/fila/configuração, CI no GitHub Actions e deploy automático para Oracle.

A avaliação geral é: **projeto funcional e bem encaminhado, mas ainda não plenamente robusto para produção sem ajustes**.

Os pontos mais preocupantes não são organização visual ou falta de arquivos, mas inconsistências de comportamento entre componentes, risco operacional em falhas, tratamento incompleto de múltiplos destinos, divergências de configuração de IA, mascaramento incompleto de secrets e cobertura de testes insuficiente para o tamanho do sistema.

Principais pontos que devem ser corrigidos antes de considerar o projeto maduro:

1. Inconsistência entre provedores de IA no bot, Worker, Mini App e `/status`.
2. Mascaramento incompleto de secrets em logs.
3. Scheduler marca postagem como consumida antes de confirmar sucesso real.
4. Histórico `/cotd` possui filtros temporais frágeis.
5. Multi-destino está implementado apenas parcialmente.
6. Deploy altera `.env` de produção automaticamente.
7. Worker usa `SUPABASE_SERVICE_ROLE_KEY`, o que exige controles mais rígidos.
8. `telegram_handlers.py` concentra responsabilidades demais.
9. Testes ainda são mínimos para o risco operacional do projeto.
10. Versionamento e documentação têm inconsistências.

---

## 2. Contexto arquitetural encontrado

O `README.md` descreve o sistema como composto por:

- Bot Python com `python-telegram-bot` e long polling.
- Cloudflare Worker em JavaScript.
- Mini App Admin em React 18 + Vite.
- Supabase PostgreSQL REST.
- Deploy do bot em Oracle Linux.

Evidência:

- `README.md`, linhas 7–15.
- `README.md`, linhas 16–23.
- `README.md`, linhas 29–49.

Essa arquitetura é adequada para o tipo de projeto. O bot fica responsável pela operação Telegram e lógica de postagem. O Worker atua como camada intermediária para autenticar o Mini App via `initData` do Telegram e conversar com o Supabase. O Mini App fica sem secrets e opera por API. O Supabase mantém estado, configurações, fila de comandos, histórico e dados das cartas.

A arquitetura, portanto, é válida. O problema está na maturidade de algumas integrações.

---

## 3. Pontos positivos encontrados

### 3.1 Separação geral de camadas

O projeto já separa:

- `src/arkham_bot/core`: configuração, logging, permissões, Supabase.
- `src/arkham_bot/clients`: ArkhamDB.
- `src/arkham_bot/repositories`: acesso às tabelas Supabase.
- `src/arkham_bot/services`: scheduler, daily card, heartbeat.
- `src/arkham_bot/handlers`: comandos Telegram e command worker.
- `worker`: API Cloudflare Worker.
- `miniapp`: painel React/Vite.
- `scripts`: healthcheck, sync ArkhamDB.
- `.github/workflows`: CI e deploy.

Isso é positivo porque evita que tudo fique em um único script. A existência de `pyproject.toml` também indica intenção de tratar o bot como pacote Python instalável.

Evidência:

- `README.md`, linhas 29–49.
- `pyproject.toml`, linhas 7–31.

### 3.2 CI cobre Python, Worker e Mini App

O workflow `test.yml` executa:

- checkout;
- setup Python;
- instalação de dependências;
- `compileall`;
- `pytest`;
- `python main.py --help`;
- healthcheck não estrito;
- validação do Worker;
- testes Node do Worker;
- dry-run do Worker;
- build do Mini App.

Evidência:

- `.github/workflows/test.yml`, linhas 12–33.
- `.github/workflows/test.yml`, linhas 35–71.

Isso é uma boa base. O projeto não depende somente de testes manuais.

### 3.3 Deploy automatizado com validação antes de reiniciar serviço

O workflow de deploy para Oracle valida o pacote antes de conectar no servidor e, no servidor, faz:

- `git fetch`;
- `git reset --hard origin/main`;
- instalação de dependências;
- `compileall`;
- `healthcheck --strict`;
- restart do `systemd`;
- verificação do status;
- coleta dos logs recentes.

Evidência:

- `.github/workflows/deploy-oracle.yml`, linhas 43–62.
- `.github/workflows/deploy-oracle.yml`, linhas 77–134.

Isso é positivo. O deploy não é apenas “copiar arquivo e torcer”.

### 3.4 Worker valida `initData` do Telegram

O Worker valida `initData`, compara HMAC, confere `auth_date` e rejeita dados com mais de 86400 segundos. Isso é correto para Mini App do Telegram.

Evidência:

- `worker/src/index.js`, linhas 87–108.

Além disso, há separação entre:

- `requireAuth`;
- `requireAdmin`;
- `requireOwner`.

Evidência:

- `worker/src/index.js`, linhas 119–184.
- `worker/src/index.js`, linhas 1220–1367.

### 3.5 Há preocupação com rate limit e filas

O bot possui rate limiter em memória para comandos públicos e uma fila de comandos no Supabase para ações administrativas vindas do Mini App.

Evidência:

- `src/arkham_bot/core/rate_limiter.py`, linhas 16–53.
- `src/arkham_bot/handlers/command_worker.py`, linhas 38–48.
- `src/arkham_bot/repositories/commands_repo.py`, linhas 8–154.

Isso é melhor do que executar tudo diretamente pelo Worker no momento do clique.

---

## 4. Problemas técnicos encontrados

## 4.1 Inconsistência na camada de IA

### O que encontrei

O projeto declara suporte a Gemini, OpenAI, Groq e Mistral.

Evidência:

- `README.md`, linhas 18–20.
- `src/arkham_bot/core/config.py`, linhas 90–97.
- `src/arkham_bot/ai/daily_card_selector.py`, linhas 28–39.

O seletor de IA realmente possui conjuntos de modelos para Gemini, OpenAI, Groq e Mistral, além de roteamento por provedor.

Evidência:

- `src/arkham_bot/ai/daily_card_selector.py`, linhas 28–49.
- `src/arkham_bot/ai/daily_card_selector.py`, linhas 137–148.

Porém, em outros pontos o código ainda assume OpenAI ou Gemini de forma fixa.

No `/status`, o campo `ai_daily_card_enabled` depende de `OPENAI_API_KEY`, e `ai_model` aparece como `"sem OPENAI_API_KEY"` se não houver chave OpenAI. Isso está errado se o usuário estiver usando Gemini, Groq ou Mistral.

Evidência:

- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 570–583 da leitura feita, especialmente os campos:
  - `ai_daily_card_enabled: bool(AI_DAILY_CARD_ENABLED and OPENAI_API_KEY)`
  - `ai_model: AI_MODEL if OPENAI_API_KEY else "sem OPENAI_API_KEY"`

Também existe log da postagem diária que registra `has_key` olhando somente `GEMINI_API_KEY`, mesmo que o modelo escolhido seja OpenAI, Groq ou Mistral.

Evidência:

- `src/arkham_bot/services/daily_card.py`, linhas 186–192.

### Por que isso é problema

Isso gera diagnóstico falso.

Exemplo: se o Mini App estiver configurado com `gemini-2.5-flash` e `GEMINI_API_KEY`, o `/status` pode dizer que IA está inativa por falta de `OPENAI_API_KEY`. O bot pode estar funcionando, mas a telemetria fica errada.

Também ocorre o inverso: se o usuário escolher OpenAI e houver `OPENAI_API_KEY`, o log de `has_key` olhando Gemini não representa o estado real.

Em produção, diagnóstico falso é grave porque leva a correções erradas. O operador pode mexer em `.env`, trocar modelo, recriar chave ou reiniciar serviço sem necessidade.

### Como eu resolveria

Criaria uma função única para resolver provedor e disponibilidade da chave.

Exemplo conceitual:

```python
def get_ai_provider_for_model(model: str) -> str:
    if model.startswith("gpt-"):
        return "openai"
    if model in GROQ_MODELS:
        return "groq"
    if model in MISTRAL_MODELS:
        return "mistral"
    return "gemini"


def get_ai_key_status(model: str) -> dict:
    provider = get_ai_provider_for_model(model)
    key_map = {
        "gemini": GEMINI_API_KEY,
        "openai": OPENAI_API_KEY,
        "groq": GROQ_API_KEY,
        "mistral": MISTRAL_API_KEY,
    }
    return {
        "provider": provider,
        "model": model,
        "has_key": bool(key_map.get(provider)),
    }
```

Depois usaria essa função em:

- `daily_card_selector.py`;
- `daily_card.py`;
- `/status`;
- healthcheck, se futuramente validar IA;
- logs.

Correção esperada:

- `/status` deve dizer algo como:
  - `IA: ativa`
  - `Provider: gemini`
  - `Model: gemini-2.5-flash`
  - `Key: configurada`
- Se a chave estiver ausente:
  - `IA: configurada, mas sem chave do provider gemini`.

---

## 4.2 Mascaramento incompleto de secrets

### O que encontrei

O README afirma que logs mascaram tokens e chaves automaticamente.

Evidência:

- `README.md`, linhas 110–116.

O `logging_config.py` mascara:

- `TELEGRAM_BOT_TOKEN`;
- `SUPABASE_SERVICE_ROLE_KEY`;
- `OPENAI_API_KEY`.

Evidência:

- `src/arkham_bot/core/logging_config.py`, linhas 22–36.

Mas o projeto também usa:

- `GEMINI_API_KEY`;
- `GROQ_API_KEY`;
- `MISTRAL_API_KEY`.

Evidência:

- `src/arkham_bot/core/config.py`, linhas 91–94.
- `src/arkham_bot/ai/daily_card_selector.py`, linhas 11–12.

Essas chaves não aparecem no mascaramento explícito.

### Por que isso é problema

Se alguma exceção, print, corpo de resposta ou debug vazar uma URL contendo chave Gemini, ou se algum trecho logar variáveis de ambiente, essas chaves podem ir para:

- `bot_execution.log`;
- `bot_errors.log`;
- `journalctl`;
- logs do GitHub Actions;
- logs de deploy.

No caso do Gemini, o código chama a API com a chave na query string:

```python
https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}
```

Evidência:

- `src/arkham_bot/ai/daily_card_selector.py`, linhas 99–103.

Mesmo que hoje o código não logue a URL inteira em caso de erro, é uma superfície de risco.

### Como eu resolveria

Alteraria `logging_config.py` para importar e mascarar todas as chaves sensíveis:

```python
from .config import (
    TELEGRAM_BOT_TOKEN,
    SUPABASE_SERVICE_ROLE_KEY,
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    MISTRAL_API_KEY,
)
```

E substituiria:

```python
for secret in (TELEGRAM_BOT_TOKEN, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY):
```

por:

```python
for secret in (
    TELEGRAM_BOT_TOKEN,
    SUPABASE_SERVICE_ROLE_KEY,
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    MISTRAL_API_KEY,
):
```

Também atualizaria `SECRET_NAME_RE` para incluir:

- `GEMINI_API_KEY`;
- `GROQ_API_KEY`;
- `MISTRAL_API_KEY`.

Além disso, eu evitaria passar chave Gemini como query string em logs internos. Quando possível, manteria logs sem URL completa ou mascararia parâmetros `key=`.

---

## 4.3 Scheduler marca slot como usado antes de sucesso real

### O que encontrei

No scheduler, quando chega o horário configurado, o código adiciona o slot em `posted_slots` antes de executar `post_daily_card`.

Evidência:

- `src/arkham_bot/services/scheduler.py`, linhas 149–161.

Depois a postagem é executada e o estado final é atualizado com sucesso ou falha.

Evidência:

- `src/arkham_bot/services/scheduler.py`, linhas 161–175.

O comentário explica a intenção: evitar repost se houver restart durante o delay da IA.

Evidência:

- `src/arkham_bot/services/scheduler.py`, linhas 155–156.

### Por que isso é problema

A intenção é válida, mas a consequência operacional é ruim.

Se a postagem falhar por:

- instabilidade do Telegram;
- erro temporário no ArkhamDB;
- erro ao baixar imagem;
- indisponibilidade do Supabase;
- timeout;
- reinício no meio do fluxo;
- erro transitório da IA;

o slot já fica marcado como consumido. O bot não tentará novamente naquele horário dentro da janela de 10 minutos.

Isso transforma falhas transitórias em perda definitiva da postagem do dia/horário.

### Como eu resolveria

Separaria dois conceitos:

- `claimed_slots`: slot em execução;
- `posted_slots`: slot concluído com sucesso.

Fluxo recomendado:

1. Quando o horário vence:
   - se `posted_slots` contém o slot, não faz nada;
   - se `claimed_slots` contém o slot recente, não duplica;
   - se não contém, adiciona em `claimed_slots`.
2. Executa `post_daily_card`.
3. Se sucesso:
   - move de `claimed_slots` para `posted_slots`.
4. Se falha:
   - remove de `claimed_slots`;
   - mantém `posted_slots` sem o slot;
   - registra `last_daily_post_status=failed`;
   - permite nova tentativa dentro da janela ou agenda retry com backoff.
5. Se processo morrer:
   - na próxima execução, `claimed_slots` antigo com timestamp expirado é liberado.

Exemplo conceitual de estado:

```json
{
  "claimed_slots": {
    "2026-05-28_08:00": "2026-05-28T08:00:05-03:00"
  },
  "posted_slots": [
    "2026-05-28_08:00"
  ]
}
```

Também colocaria um limite de retry por slot:

- máximo 3 tentativas;
- backoff de 60s, 180s, 300s;
- após isso, marca falha final e notifica admin.

---

## 4.4 Multi-destino implementado parcialmente

### O que encontrei

O bot busca destinos em `target_chats`, e se houver mais de um, usa o primeiro como principal e os demais como extras.

Evidência:

- `src/arkham_bot/services/daily_card.py`, linhas 117–134.
- `src/arkham_bot/services/daily_card.py`, linhas 150–152.

A carta frontal é postada no destino principal, salva histórico e depois é replicada para destinos extras.

Evidência:

- `src/arkham_bot/services/daily_card.py`, linhas 87–108 da segunda leitura, correspondentes à postagem principal.
- `src/arkham_bot/services/daily_card.py`, linhas 181–207.

Porém:

- o pin/unpin ocorre só no destino principal;
- o verso da carta é tratado dentro do fluxo principal;
- a mensagem de IA pré-card é enviada só no destino principal;
- a pergunta pós-card é enviada só no destino principal;
- falha em destino extra só gera log, mas o resultado final continua sucesso.

Evidência:

- `src/arkham_bot/services/daily_card.py`, linhas 75–85.
- `src/arkham_bot/services/daily_card.py`, linhas 125–180.
- `src/arkham_bot/services/daily_card.py`, linhas 183–225.

### Por que isso é problema

Se a funcionalidade de múltiplos destinos existe no Mini App, o operador tende a esperar comportamento completo.

Exemplo: se o bot está configurado para postar em dois grupos, um grupo pode receber:

- mensagem de IA;
- carta;
- verso;
- pin;
- pergunta final.

E outro grupo pode receber apenas:

- carta frontal.

Isso é inconsistente.

Também há problema de confiabilidade: se o destino principal funcionar e os extras falharem, o `DailyPostResult` retorna sucesso. Isso mascara falha parcial.

### Como eu resolveria

Criaria uma função única para postar em um destino:

```python
async def post_card_to_destination(bot, destination, card, caption, ai_pre_message, ai_post_question, is_scheduled):
    # envia pre-message
    # envia frente
    # envia verso se houver
    # fixa mensagem se configurado
    # registra histórico daquele destino
    # retorna resultado por destino
```

Depois `post_daily_card` faria:

```python
results = []
for destination in destinations:
    result = await post_card_to_destination(...)
    results.append(result)
```

O resultado final deveria distinguir:

- sucesso total;
- sucesso parcial;
- falha total.

Exemplo:

```python
DailyPostResult(
    success=any(r.success for r in results),
    partial_failure=any(not r.success for r in results),
    destination_results=results
)
```

E o histórico deveria registrar:

- `target_chat_id`;
- `message_thread_id`;
- `status`;
- `error`;
- `telegram_message_id`;
- `source`.

---

## 4.5 Histórico `/cotd` com filtro temporal incorreto ou frágil

### O que encontrei

A função `_cotd_fetch_months(year)` filtra por:

```python
created_at >= {year}-01-01T00:00:00Z
```

mas não filtra:

```python
created_at < {year + 1}-01-01T00:00:00Z
```

Evidência:

- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 267–280 da leitura específica do COTD.

Isso significa que, ao consultar meses de 2025, registros de 2026 também podem entrar, dependendo da base.

Já `_cotd_fetch_cards(year, month)` usa início e fim em UTC, depois converte para `America/Sao_Paulo`.

Evidência:

- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 3–27 da leitura específica do COTD.

### Por que isso é problema

O histórico por ano/mês pode mostrar dados errados.

Dois problemas:

1. Sem limite superior no ano, meses futuros entram na lista de anos anteriores.
2. Filtro mensal em UTC pode deslocar postagem perto da meia-noite para outro dia/mês local.

Exemplo: uma postagem em `2026-06-01T02:30:00Z` equivale a `2026-05-31 23:30` em São Paulo. Dependendo da intenção do usuário, ela deveria aparecer no histórico local de maio, não de junho.

### Como eu resolveria

Em `_cotd_fetch_months`, adicionar limite superior:

```python
'created_at': f'gte.{year}-01-01T00:00:00Z',
'created_at': f'lt.{year + 1}-01-01T00:00:00Z',
```

Mas como dicionário Python não permite duas chaves iguais, o client atual teria dificuldade com múltiplos filtros no mesmo campo. Isso revela outro problema: o client `SupabaseRestClient.get` aceita `params` como `dict`, mas alguns trechos ainda passam lista de tuplas.

Evidência:

- `src/arkham_bot/core/supabase_client.py`, linhas 32–35.
- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 13–19 da leitura COTD cards.

O `httpx` aceita lista de tuplas como params, então funciona, mas a tipagem do client declara `dict | None`. Eu padronizaria isso.

Correção recomendada:

```python
def get(self, table: str, params: dict | list[tuple[str, str]] | None = None) -> list[dict]:
    ...
```

E usaria lista de tuplas quando precisar repetir filtros:

```python
rows = client.get("bot_posting_history", [
    ("select", "created_at"),
    ("source", "eq.scheduled"),
    ("created_at", f"gte.{year}-01-01T00:00:00Z"),
    ("created_at", f"lt.{year + 1}-01-01T00:00:00Z"),
    ("order", "created_at.asc"),
    ("limit", "5000"),
])
```

Para histórico local por mês, eu criaria função que converte período local para UTC:

```python
def local_month_range_to_utc(year, month, tz_name):
    tz = ZoneInfo(tz_name)
    start_local = datetime(year, month, 1, 0, 0, tzinfo=tz)
    if month == 12:
        end_local = datetime(year + 1, 1, 1, 0, 0, tzinfo=tz)
    else:
        end_local = datetime(year, month + 1, 1, 0, 0, tzinfo=tz)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)
```

---

## 4.6 Deploy altera `.env` de produção

### O que encontrei

Durante o deploy na Oracle, o workflow entra no servidor e força `AI_DAILY_CARD_ENABLED=true` no `.env`.

Evidência:

- `.github/workflows/deploy-oracle.yml`, linhas 107–118.

### Por que isso é problema

Deploy não deve reescrever decisão operacional local.

Se o operador desativar IA por custo, instabilidade, manutenção, chave inválida ou teste, o próximo deploy religará automaticamente.

Isso viola separação entre:

- código;
- configuração;
- operação.

Também pode gerar incidentes: uma alteração de código aparentemente simples pode religar IA em produção sem o operador perceber.

### Como eu resolveria

Remover esse bloco do workflow:

```bash
if [ -f .env ]; then
  if grep -q '^AI_DAILY_CARD_ENABLED=' .env; then
    sed -i 's/^AI_DAILY_CARD_ENABLED=.*/AI_DAILY_CARD_ENABLED=true/' .env
  else
    printf '\nAI_DAILY_CARD_ENABLED=true\n' >> .env
  fi
fi
```

Substituir por validação somente leitura:

```bash
echo "== Environment validation =="
python main.py healthcheck --strict
```

Se quiser garantir variável obrigatória, o healthcheck deve reportar erro, não alterar `.env`.

---

## 4.7 Worker usando `SUPABASE_SERVICE_ROLE_KEY`

### O que encontrei

O Worker usa `SUPABASE_SERVICE_ROLE_KEY` diretamente para acessar Supabase.

Evidência:

- `worker/src/index.js`, linhas 121–130.
- `worker/src/index.js`, linhas 194–204.
- `worker/src/index.js`, linhas 215–224.

O Worker valida `initData`, admin e owner antes de rotas sensíveis, o que é positivo.

Evidência:

- `worker/src/index.js`, linhas 119–184.
- `worker/src/index.js`, linhas 1220–1367.

### Por que isso é problema

`service_role` normalmente ignora RLS no Supabase. Isso significa que qualquer bug de validação, rota exposta indevidamente ou manipulação de payload pode ter impacto total no banco.

A arquitetura pode usar service role em backend, mas isso exige rigor maior:

- payloads estritamente validados;
- rotas pequenas;
- auditoria;
- logs seguros;
- menor superfície possível;
- nunca expor essa chave ao frontend.

O projeto já não expõe a chave ao Mini App, o que é correto. O risco está no Worker como ponto único de alto privilégio.

### Como eu resolveria

Curto prazo:

- manter service role apenas no Worker;
- validar payload por tipo de comando;
- bloquear campos inesperados em `payload`;
- registrar auditoria para toda ação mutável;
- adicionar testes de autorização e payload inválido;
- garantir CORS estrito em produção.

Médio prazo:

- mover operações sensíveis para funções SQL/RPC específicas;
- dar ao Worker uma chave com acesso menor quando possível;
- usar RLS com policies explícitas;
- separar operações de leitura e escrita.

Exemplo: em vez do Worker escrever diretamente em `bot_settings`, criar RPC:

```sql
select admin_update_setting(actor_user_id, key, value);
```

E a função no banco valida o ator e a chave permitida.

---

## 4.8 `telegram_handlers.py` concentra responsabilidades demais

### O que encontrei

O arquivo `telegram_handlers.py` contém:

- caches globais;
- busca de cartas;
- busca FAQ;
- formatação de uptime/status;
- comandos `/status`, `/start`, `/card`, `/search`, `/sets`, `/cotd`;
- callbacks;
- HTML conversion;
- envio de imagem;
- lógica de spoiler;
- paginação;
- registro dos handlers.

Evidência:

- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 46–107.
- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 198–319 da leitura de status.
- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 570–900 da leitura de comandos card.
- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 1900–2290 da leitura de search/sets/cotd.
- `src/arkham_bot/handlers/telegram_handlers.py`, linhas 103–167 da leitura final de registro dos handlers.

### Por que isso é problema

Um arquivo grande com muitas responsabilidades aumenta risco de regressão.

Exemplo: uma alteração em busca pode afetar callbacks de sets; uma alteração em formatação pode quebrar FAQ; uma alteração em estado de conversa pode impactar `/card`.

Também dificulta teste unitário, porque funções ficam acopladas a muitos imports e estado global.

### Como eu resolveria

Separaria em módulos:

```text
src/arkham_bot/handlers/
  __init__.py
  registry.py
  common.py
  status_handler.py
  card_handler.py
  search_handler.py
  sets_handler.py
  taboo_handler.py
  faq_handler.py
  decklist_handler.py
  cotd_handler.py
```

Moveria utilidades comuns para:

```text
src/arkham_bot/services/card_rendering.py
src/arkham_bot/services/card_search.py
src/arkham_bot/services/cotd_history.py
src/arkham_bot/services/telegram_media.py
```

O `registry.py` ficaria responsável só por registrar handlers:

```python
def register_handlers(application):
    register_status(application)
    register_card(application)
    register_search(application)
    register_sets(application)
    register_cotd(application)
    ...
```

---

## 4.9 Supabase client sem retry/backoff

### O que encontrei

O `SupabaseRestClient` usa `httpx.Client` persistente com timeout e pool de conexões.

Evidência:

- `src/arkham_bot/core/supabase_client.py`, linhas 8–21.

Mas os métodos `get`, `post`, `upsert`, `patch` e `delete` fazem request direto e `raise_for_status()` sem retry.

Evidência:

- `src/arkham_bot/core/supabase_client.py`, linhas 32–76.

### Por que isso é problema

Supabase REST pode falhar temporariamente por:

- timeout;
- 502/503/504;
- erro de rede;
- rate limit;
- reset de conexão.

Sem retry, uma falha breve pode quebrar:

- postagem do dia;
- fila de comandos;
- sync;
- status;
- histórico;
- Mini App.

O ArkhamDB client já possui retry com `tenacity`, mas o Supabase client não.

Evidência:

- `src/arkham_bot/clients/arkhamdb_client.py`, linhas 48–56.
- `src/arkham_bot/clients/arkhamdb_client.py`, linhas 107–144.

### Como eu resolveria

Adicionar retry no Supabase client para erros transitórios:

- `httpx.TimeoutException`;
- `httpx.NetworkError`;
- HTTP 429;
- HTTP 500;
- HTTP 502;
- HTTP 503;
- HTTP 504.

Exemplo conceitual:

```python
def _request(self, method, table, **kwargs):
    for attempt in range(1, 4):
        try:
            response = self._client.request(method, self.table_url(table), **kwargs)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise TransientSupabaseError(response.status_code)
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.NetworkError, TransientSupabaseError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
```

Melhor ainda: usar `tenacity`, como no ArkhamDB client.

---

## 4.10 Fila de comandos com concorrência frágil

### O que encontrei

O command worker busca comandos pendentes/retrying, marca como `processing` e executa.

Evidência:

- `src/arkham_bot/handlers/command_worker.py`, linhas 139–184.
- `src/arkham_bot/repositories/commands_repo.py`, linhas 32–63.

### Por que isso é problema

Funciona se houver apenas uma instância do bot/worker. Mas se por erro existirem duas instâncias, pode ocorrer condição de corrida:

1. Worker A busca comando pendente.
2. Worker B busca o mesmo comando pendente.
3. Ambos marcam como processing.
4. Ambos executam.

O `main.py` usa lock local para evitar duas instâncias na mesma máquina.

Evidência:

- `main.py`, linhas 138–146.

Mas esse lock é local ao filesystem. Ele não impede duplicidade se houver outro ambiente, outro servidor ou execução manual paralela fora do mesmo lock.

### Como eu resolveria

Ideal: claim atômico no banco.

Exemplo de RPC:

```sql
claim_next_bot_commands(batch_size integer)
```

A função faria algo como:

```sql
update bot_commands
set status = 'processing',
    attempt_count = attempt_count + 1,
    updated_at = now()
where id in (
  select id
  from bot_commands
  where status in ('pending', 'retrying')
  order by created_at asc
  for update skip locked
  limit batch_size
)
returning *;
```

Assim dois workers não pegam o mesmo comando.

---

## 4.11 Dependências com pin parcial

### O que encontrei

`requirements.txt` define ranges, não versões exatas:

```text
python-telegram-bot>=22.0,<23.0
requests>=2.31,<3.0
python-dotenv>=1.0
pillow>=10.0
filelock>=3.12
httpx>=0.24,<1.0
tenacity>=8.2,<10.0
tzdata>=2023.3
```

Evidência:

- `requirements.txt`, linhas 3–10.

`requirements-dev.txt` contém apenas:

```text
-r requirements.txt
pytest
```

Evidência:

- `requirements-dev.txt`, linhas 3–4.

### Por que isso é problema

Ranges são melhores do que nada, mas ainda permitem mudanças automáticas entre deploys.

Exemplo: `httpx>=0.24,<1.0` permite muita variação. Uma atualização minor pode alterar comportamento de timeout, headers, exceptions ou compatibilidade.

Em produção, é preferível ter lockfile ou pins exatos para deploy reprodutível.

### Como eu resolveria

Manter `requirements.in` com ranges humanos e gerar `requirements.txt` pinado com `pip-tools`.

Exemplo:

```text
# requirements.in
python-telegram-bot>=22.0,<23.0
requests>=2.31,<3.0
...
```

Gerar:

```bash
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
```

No CI/deploy, instalar somente o lock gerado.

Também adicionaria dependências de qualidade:

- `ruff`;
- `mypy` ou `pyright`;
- `pytest-cov`;
- `pip-audit` ou equivalente.

---

## 4.12 Versionamento inconsistente entre Worker e pacotes

### O que encontrei

O Worker define:

```js
const APP_VERSION = '1.3.0';
```

Evidência:

- `worker/src/index.js`, linha 3.

Mas `worker/package.json` está em `1.1.0`.

Evidência:

- `worker/package.json`, linhas 16–19.

O Mini App também está em `1.1.0`.

Evidência:

- `miniapp/package.json`, linhas 3–6.

### Por que isso é problema

Não quebra execução, mas atrapalha diagnóstico.

Se o `/status`, `/bot-info` ou logs mostram `1.3.0`, mas o pacote diz `1.1.0`, fica difícil saber o que realmente está em produção.

### Como eu resolveria

Escolher uma fonte única de versão.

Opções:

1. Usar `package.json` e importar/gerar versão no build.
2. Ter `VERSION` na raiz e injetar em Worker/Mini App.
3. Usar commit SHA do GitHub Actions como versão operacional.

Para produção, eu usaria:

- `APP_VERSION`;
- `GIT_SHA`;
- `BUILD_TIME`.

Exemplo de retorno em `/status`:

```json
{
  "version": "1.3.0",
  "git_sha": "06e25ab",
  "build_time": "2026-05-28T17:42:44Z"
}
```

---

## 4.13 Mini App: bom avanço, mas componente principal grande demais

### O que encontrei

`App.jsx` concentra grande parte do estado e das operações:

- autenticação;
- tabs;
- settings;
- comandos;
- histórico;
- admin;
- destinos;
- health;
- carregamento de packs;
- save settings;
- enfileiramento de comandos.

Evidência:

- `miniapp/src/App.jsx`, linhas 18–97.
- `miniapp/src/App.jsx`, linhas 220–283.
- `miniapp/src/App.jsx`, linhas 285–407.

### Por que isso é problema

Mesmo que funcione, o arquivo tende a ficar difícil de manter. Qualquer nova tela ou ajuste de UX aumenta o risco de quebrar comportamento existente.

### Como eu resolveria

Separaria por hooks e páginas:

```text
miniapp/src/
  App.jsx
  api.js
  telegram.js
  hooks/
    useAuth.js
    useSettings.js
    useCommands.js
    useOverview.js
    useHistory.js
    useAdmins.js
    useDestinations.js
  pages/
    HomePage.jsx
    SettingsPage.jsx
    AiPage.jsx
    SchedulePage.jsx
    HistoryPage.jsx
    AdminsPage.jsx
    DestinationsPage.jsx
    HealthPage.jsx
  components/
    ...
```

A meta seria deixar `App.jsx` como roteador de telas e estado mínimo.

---

## 4.14 Mini App e Worker duplicam configuração de modelos IA

### O que encontrei

O Worker declara provedores/modelos de IA.

Evidência:

- `worker/src/index.js`, linhas 5–28.

O Mini App também declara provedores/modelos.

Evidência:

- `miniapp/src/settings.js`, linhas 19–65.

### Por que isso é problema

Quando um modelo mudar, for removido ou for adicionado, é necessário alterar em dois lugares. Isso gera divergência.

Exemplo: o Worker pode aceitar um modelo que o Mini App não mostra, ou o Mini App pode mostrar um modelo que o Worker rejeita.

### Como eu resolveria

O Worker já tem rota `/ai-models`.

Evidência:

- `worker/src/index.js`, linhas 89–93 da leitura final de rotas.

O Mini App deveria carregar a lista dessa rota e usar a lista local apenas como fallback.

Fluxo:

1. Mini App inicia.
2. Chama `/ai-models`.
3. Usa resposta do Worker.
4. Se falhar, usa fallback local mínimo.

Assim, o Worker vira fonte de verdade.

---

## 4.15 Documentação contradiz a decisão de documentação canônica

### O que encontrei

O README aponta para:

- `docs/technical.md`;
- `docs/operations.md`.

Evidência:

- `README.md`, linhas 24–28.

Mas a diretriz atual do projeto é tratar somente o `README.md` como documentação técnica canônica.

### Por que isso é problema

Documentação paralela tende a ficar desatualizada. Alguém novo no projeto pode ler um `.md` antigo e executar instruções erradas.

### Como eu resolveria

No README:

- remover referências a docs paralelos, se esses arquivos não forem mais canônicos;
- criar seções completas dentro do próprio README:
  - arquitetura;
  - variáveis de ambiente;
  - deploy;
  - comandos;
  - Supabase;
  - Worker;
  - Mini App;
  - troubleshooting;
  - decisões técnicas;
  - limitações conhecidas.

Se quiser manter arquivos antigos por histórico, mover para:

```text
docs/archive/
```

e marcar claramente:

```md
> Documento arquivado. Não usar como fonte operacional.
```

---

## 5. Plano de correção recomendado

## Fase 1 — Correções críticas de consistência e segurança

### 1.1 Corrigir status/IA

Arquivos afetados:

- `src/arkham_bot/ai/daily_card_selector.py`
- `src/arkham_bot/services/daily_card.py`
- `src/arkham_bot/handlers/telegram_handlers.py`
- possivelmente `src/arkham_bot/core/config.py`

Ação:

- Criar helper único para resolver provider, modelo e chave.
- Usar esse helper no `/status`.
- Usar esse helper nos logs de postagem.
- Garantir que Gemini/OpenAI/Groq/Mistral sejam tratados igualmente.

Resultado esperado:

- `/status` mostra o provedor correto.
- Logs indicam chave correta por provider.
- Não aparece erro “sem OPENAI_API_KEY” quando o modelo é Gemini.

### 1.2 Corrigir mascaramento de secrets

Arquivo afetado:

- `src/arkham_bot/core/logging_config.py`

Ação:

- Adicionar `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY` ao mascaramento.
- Adicionar os nomes ao regex `SECRET_NAME_RE`.
- Mascarar query param `key=` caso apareça em URL.

Resultado esperado:

- Nenhuma chave de IA aparece em logs.

### 1.3 Remover alteração automática de `.env` no deploy

Arquivo afetado:

- `.github/workflows/deploy-oracle.yml`

Ação:

- Remover bloco que altera `AI_DAILY_CARD_ENABLED=true`.
- Deixar deploy apenas validar ambiente.

Resultado esperado:

- Deploy não muda comportamento operacional sem permissão explícita.

---

## Fase 2 — Confiabilidade operacional

### 2.1 Corrigir scheduler

Arquivo afetado:

- `src/arkham_bot/services/scheduler.py`

Ação:

- Separar `claimed_slots` e `posted_slots`.
- Permitir retry se a postagem falhar.
- Marcar `posted_slots` só após sucesso real.
- Criar expiração para claims antigos.

Resultado esperado:

- Falha transitória não faz perder postagem do dia.
- Restart não duplica postagem em andamento.

### 2.2 Corrigir COTD

Arquivo afetado:

- `src/arkham_bot/handlers/telegram_handlers.py`
- idealmente novo service: `src/arkham_bot/services/cotd_history.py`

Ação:

- Adicionar limite superior no filtro por ano.
- Calcular intervalo local e converter para UTC.
- Padronizar client Supabase para aceitar lista de tuplas em params.

Resultado esperado:

- Histórico por ano/mês correto em timezone local.

### 2.3 Corrigir multi-destino

Arquivo afetado:

- `src/arkham_bot/services/daily_card.py`

Ação:

- Criar função de postagem por destino.
- Registrar resultado por destino.
- Decidir regra de pin/IA/verso para extras.
- Retornar sucesso parcial quando aplicável.

Resultado esperado:

- Todos os destinos têm comportamento previsível.
- Falha parcial aparece no histórico/status.

---

## Fase 3 — Qualidade de código e testes

### 3.1 Dividir `telegram_handlers.py`

Arquivos afetados:

- `src/arkham_bot/handlers/telegram_handlers.py`
- novos módulos em `src/arkham_bot/handlers/`

Ação:

- Separar comandos por domínio.
- Manter `register_handlers` como composição.

Resultado esperado:

- Código mais testável.
- Menor risco de regressão.

### 3.2 Adicionar testes

Áreas mínimas:

- scheduler;
- COTD;
- provider de IA;
- mascaramento de logs;
- command worker;
- Worker auth/admin/owner;
- Worker settings validation;
- multi-destino;
- Supabase client retry.

Ferramentas recomendadas:

- `pytest`;
- `pytest-cov`;
- `ruff`;
- `mypy` ou `pyright`;
- `node --test` já existe para Worker.

Resultado esperado:

- CI deixa de ser apenas smoke test e passa a validar comportamento real.

---

## 6. Priorização final

Ordem recomendada de execução:

1. Corrigir inconsistência de IA/status.
2. Corrigir mascaramento de secrets.
3. Remover alteração automática de `.env` no deploy.
4. Corrigir scheduler para não consumir slot em falha.
5. Corrigir COTD.
6. Definir e corrigir multi-destino.
7. Adicionar retry/backoff no Supabase client.
8. Adicionar testes para os pontos acima.
9. Refatorar `telegram_handlers.py`.
10. Unificar fonte de modelos IA entre Worker e Mini App.
11. Sincronizar versionamento.
12. Consolidar documentação no README.

---

## 7. Conclusão

O Arkham Bot está em uma fase intermediária entre projeto funcional e produto robusto.

A base está correta. Há boas decisões: pacote Python, CI, Worker autenticado, Mini App sem secrets, Supabase como fila/configuração e deploy automatizado.

O que impede a classificação como produção madura são inconsistências e falhas de borda:

- diagnóstico de IA incorreto;
- secrets não totalmente mascarados;
- scheduler com risco de perder postagem após falha;
- COTD com filtro temporal incompleto;
- multi-destino incompleto;
- deploy mexendo em `.env`;
- testes insuficientes;
- componentes grandes demais.

Minha avaliação técnica: **não precisa recomeçar o projeto**. Precisa de hardening direcionado. O caminho correto é corrigir os pontos críticos mantendo a arquitetura atual.
