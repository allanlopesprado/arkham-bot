# Changelog

## [1.4.0] — 2026-05-28

### Adicionado
- `pending_destinations` table e fluxo completo: bot detecta automaticamente quando adicionado a um grupo, Mini App exibe seção de confirmação com campo opcional de Thread ID
- Auto-resolução de nome do grupo ao digitar Chat ID (Worker `GET /destinations/resolve`)
- Lucide React substituiu ícones SVG manuais — biblioteca consistente com tree-shaking (+10KB apenas)
- 3 variáveis CSS semânticas: `--warn`, `--warn-bg`, `--toggle-knob`

### Alterado
- `telegram_chat_id` removido completamente — destinos vêm exclusivamente de `target_chats`
- Mini App: `telegram_handlers.py` (2349 linhas) dividido em 9 módulos especializados
- Filtro de cartas (spoilers) movido para dentro da aba Agenda
- Hierarquia de fontes padronizada: 19px / 14px / 13px / 12px / 11px em todos os componentes
- Paddings padronizados: `8px 14px` em todos os rows, inputs e containers
- Todos os `border-radius` padronizados: 8px para inputs/botões, 12px para cards
- Todos os `border-radius` com valores hardcoded migrados para CSS variables
- `SelectRow` inline unificado visualmente com `StackedSelectRow`
- Toggle reduzido de 50×28px para 40×22px
- Densidade visual reduzida ~15-20% em todo o app (min-height 50→44px, padding 10→8px)
- Flash "verificando" removido ao abrir configurações
- Ícones redistribuídos semanticamente — sem duplicatas, cada um condiz com a função

### Corrigido
- Descrição do bot (BotFather) não aparecia no header — Worker usava `getMe` em vez de `getMyDescription`
- `telegram_chat_id` ainda presente em `settings.js` causava rejeição de todos os PATCH de settings
- Import órfão `TELEGRAM_CHAT_ID` em `status_handler.py`

---

## [1.3.0] — 2026-05-28

### Adicionado
- Suporte completo a tópicos do Telegram: `target_chats` agora usa `UNIQUE(chat_id, message_thread_id)`, permitindo múltiplos tópicos por grupo; bot passa `message_thread_id` em todos os envios
- Cache in-memory de cartas (10 min TTL) com invalidação automática após sync ArkhamDB
- Cache-on-demand para FAQ (TTL 7 dias) e decklists (TTL 24h) em Supabase
- Alerta Telegram para admins quando postagem diária falha ou comando vai para `failed` (i18n PT/EN)
- Retry automático com backoff exponencial no Supabase client para erros transitórios (429, 5xx, timeout)
- Paginação em `/card`, `/sets` e `/taboo` (10 por página para cartas/packs, 5 para taboo)
- `/faq`: imagem como reply ao usuário, FAQ como reply à imagem, link ArkhamDB e data de atualização
- `/decklist`: imagem do investigador, cartas agrupadas por tipo com links clicáveis, cache Supabase
- `/status`: data/hora local formato BR, timezone, próximo post em PT-BR, link do último card
- Pre-warm automático de caches de cartas e packs no startup do bot
- Mini App: aba "Aplicativo" na Home com idioma + administradores; histórico abre no dia atual; paginação em /sets e /card
- Validação de número de carta no `/card` contra conjunto real de números do pack
- Migration `20260528_claim_bot_commands_rpc.sql`: RPC atômica `FOR UPDATE SKIP LOCKED` para command queue
- Payload whitelist por tipo de comando no Worker (`PAYLOAD_SCHEMA`)
- Headers de segurança no Worker: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
- Audit logs nos 4 endpoints faltantes: PATCH /settings, POST /bot-command, PATCH /commands/:id, PATCH /destinations/:id
- Split de `telegram_handlers.py` (2349 linhas) em 9 módulos especializados + shim de compatibilidade
- 54 testes automatizados (pytest) cobrindo scheduler, faq_repo, rate_limiter, status, formatters, etc.

### Corrigido
- Scheduler: slot gravado antes de `post_daily_card` para evitar double-post em restart durante delay da IA
- Mensagem de abertura da IA enviada duas vezes em caso de retry (`pre_message_sent` movido para fora do loop)
- `user_id` NameError em `search_card_selected` (introduzido durante refactoring de memória)
- Filtro de COTD sem limite superior de ano (`_cotd_fetch_months` sem `lt.{year+1}`)
- Deploy Oracle forçava `AI_DAILY_CARD_ENABLED=true` no `.env` automaticamente — removido
- Timeout hardcoded `10.0s` em `download_image_async` substituído por `REQUEST_TIMEOUT_SECONDS`
- Rate limiter: hit do usuário registrado antes de verificar chat — agora check before append
- `viewer` role aceito em `handleAddAdmin` mas não reconhecido por `ADMIN_ROLES` — adicionado `owner` na validação
- Mascaramento de logs: GEMINI_API_KEY, GROQ_API_KEY e MISTRAL_API_KEY adicionados + regex para `key=` em URLs
- `/status`: `ai_daily_card_enabled` verificava apenas `OPENAI_API_KEY`; agora verifica todos os provedores
- Timeout async e sync do Supabase client unificados via `_request_with_retry`
- RPC call usando GET em vez de POST — método `rpc()` adicionado ao `SupabaseRestClient`
- Chave duplicada `removeTime` em i18n PT e EN removida
- `--separator` CSS variável inexistente corrigida para `--sep`
- Cores hardcoded dos status dots substituídas por CSS variables

### Removido
- 4 wrappers Python mortos: `handlers/supabase_client.py`, `handlers/config.py`, `handlers/local_storage.py`, `handlers/scheduler.py`
- 4 funções mortas em `telegram_handlers.py`: `_format_list`, `_format_days`, `_bold`, `_format_day_config_lines`
- Chave duplicada `sets_no_sets` em i18n (Python silenciosamente usava a última definição)
- Bloco de alteração automática de `.env` no workflow de deploy Oracle

---

## [Não versionado] — 2026-05-27

### Adicionado
- Comando `/cotd`: histórico de cartas do dia navegável por ano e mês (somente postagens automáticas)
- `/faq`, `/taboo`, `/decklist` adicionados ao menu visível do Telegram
- `/sets`: navegação de cartas por set/expansão
- Prefixo `✸` para cartas únicas nas captions
- Labels em todas as stats das captions (`💰 Cost:`, `Slot:`, `Skills:`)
- Ícone `🕵️` para slot Ally, `🤲🏻` para Hand x2, `🪽` para agilidade, `📓` para intelecto
- Busca por códigos com sufixo de letra (ex: `09519a`)
- Suporte a múltiplos provedores de IA: Gemini (padrão), OpenAI, Groq, Mistral

### Alterado
- `/status` unificado: uma única view para todos os usuários (Online, Uptime, Cartas)
- Miniapp: rótulos em português, seção de horário acima dos dias no agendamento
- `.env.example` reorganizado em seções com comentários
- Workflow Oracle corrigido: `actions/checkout@v6` → `v4`, `setup-python@v6` → `v5`

### Removido
- Comandos `/menu` e `/random`
- Módulo `arkhamdb_oauth.py` e constantes relacionadas
- Funções mortas, scripts de dev, pastas de referência sem uso

### Corrigido
- 400 Bad Request no sync ArkhamDB: campo `name` ausente no upsert de packs e factions
- `start_command` chamava `menu_command` removido (NameError)
- Filtro de data com chave duplicada `created_at2` no `/cotd`
- Input de horário no miniapp cortando `HH:MM`
