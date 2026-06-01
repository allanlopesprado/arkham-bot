# Changelog

## [1.5.1] — 2026-05-29

Segunda passada de refinamento de UI/UX no Mini App — hierarquia visual, acessibilidade, estados de interação e consistência de componentes. Sem mudança de comportamento de negócio, auth ou schema.

### Acessibilidade (Mini App)
- Foco de teclado (`:focus-visible`) visível em **todos** os controles interativos: toggles (o checkbox oculto não exibia indicador de foco), pills de filtro do histórico, botões de atualizar/limpar, botão de configurar dia, botão de info e o `<summary>` do diagnóstico
- Feedback de ação anunciado por leitores de tela: `role="status"`/`aria-live="polite"` para sucesso e `role="alert"`/`aria-live="assertive"` para erro
- `aria-busy` nos botões em estado de carregamento (`MenuRow`, `DangerRow`)
- `prefers-reduced-motion`: transições desativadas e spinner desacelerado para quem prefere menos movimento

### UX / UI (Mini App)
- **Hierarquia de seções**: títulos viraram rótulos em maiúsculas com tracking (estilo lista agrupada do Telegram/iOS), distinguindo-se de legendas e textos de apoio
- **Ações primárias** destacadas com a cor de acento do Telegram (`--accent`): "Postar agora", "Adicionar destino", "Adicionar administrador"
- **Alertas semânticos**: `Notice` de aviso (âmbar) e de erro (vermelho) ganharam fundo tonalizado e borda lateral de acento — antes era uma caixa neutra em que só o erro tinha cor
- **Feedback colorido**: linhas de sucesso (verde) / erro (vermelho) com ícone + texto — o significado não depende só da cor
- **Alvos de toque** padronizados em 36px (antes 32/34/22px inconsistentes): botões de ícone, configurar dia e a barra do histórico
- Proteção contra overflow horizontal em `SelectRow` com rótulos longos em telas estreitas

### Componentes / Limpeza (Mini App)
- Novo `ResultRow`: consolida 11 blocos quase idênticos de feedback de sucesso/erro espalhados pelas abas
- Novo `LoadingRow`: substitui linhas de carregamento com estilos inline
- Novos tokens CSS: `--ok`, `--err`, `--focus-ring`

---

## [1.5.0] — 2026-05-28

Foco em UX, acessibilidade e limpeza — concentrado no Mini App, com correções de qualidade no bot.

### Acessibilidade (Mini App)
- Campos de formulário (`InputRow`, `StackedInputRow`, `StackedSelectRow`, `ChatIdInputRow`) agora usam `<label>` associando rótulo ao campo
- Títulos de seção viraram headings semânticos (`<h2>`) — navegação por heading em leitores de tela
- Ao trocar de aba, o foco move para o título da nova tela (consciência de mudança para leitores de tela), sem outline azul visível
- `InfoTooltip` com `aria-expanded` / `aria-describedby` / `role="tooltip"` e rótulo localizável
- `aria-label` localizado no botão de configurar dia (`DayScheduleRow`) e nome acessível no toggle do dia
- `aria-label` no campo de busca de carta; `Notice` com `role="alert"`/`status`

### UX / UI (Mini App)
- Mensagens de erro amigáveis (destinos, administradores, histórico, adicionar destino/admin) via `resolveError` — sem códigos crus como `network_error`
- Remover administrador agora pede confirmação e usa estilo destrutivo (consistente com remover destino)
- Feedback de "testar/remover destino" aparece inline na própria linha do destino (antes surgia no rodapé do formulário)
- Banner visível de "alterações não salvas" nas abas de configuração
- Seleção de idioma virou um único seletor (`SelectRow`) em vez de dois toggles
- Stats do painel (status e cartas) agora são clicáveis → Saúde e Banco
- Busca de carta dispara no Enter; seleção é limpa após postar/repostar/pular
- Mensagem de sucesso sem ID técnico; badges redundantes "ok/err" removidos das linhas de resultado
- Hint explicando "Padrão global" × "Por dia da semana"; presets rápidos "Dias úteis" / "Fim de semana"
- Estado de carregamento no histórico; estado vazio na lista de administradores
- Validação inline (destaque vermelho) para Telegram User ID e Thread ID inválidos
- `max-width: 520px` no desktop — evita linhas largas demais no Telegram Desktop/Web
- Botões destrutivos de ícone (`.icon-btn.danger`) agora ficam vermelhos; botões de destinos pendentes ganharam classes próprias (antes usavam classe inexistente)

### Comando /taboo
- `/taboo` (sem argumento) volta a abrir o menu de listas; ao escolher uma data mostra apenas **título + total de cartas afetadas** (categorias como botões)
- Datas das listas alinhadas no menu
- Removida linha em branco extra na descrição do detalhe

### Corrigido (bot)
- `searchNotFound` ausente no i18n do Mini App fazia a busca vazia exibir "nenhuma postagem recente" — adicionada string correta
- Troca de idioma marcava "alterações não salvas" falsamente (baseline `savedSettings` não era sincronizado)
- Download da imagem do **verso** da carta não tentava o caminho do bundle e repetia a mesma URL — agora espelha a lógica da frente
- Docstring de `bot_started_message` dizia que enviava mensagem ao grupo (apenas faz pré-aquecimento de cache)
- `daily_card.py`: comparação `== True` trocada por checagem de verdade; variável ambígua `l` renomeada em `text_formatters.py`
- Rate limiter em memória vazava memória: a limpeza de buckets ficava depois do `append` (inalcançável), então `_user_hits`/`_chat_hits` cresciam sem limite ao longo da execução; agora um sweep periódico descarta buckets com a janela expirada
- `settings_repo.get_all_settings` passou a devolver uma cópia rasa do cache, evitando que um chamador corrompa o cache compartilhado

### Corrigido (Worker)
- `/packs` agora normaliza a barra final de `SUPABASE_URL` (como os demais endpoints), evitando caminho com `//` que o PostgREST pode rejeitar

### Testes
- Testes do Worker para a conversão de data→UTC em `/history` cobrindo UTC, `America/Sao_Paulo` (−3) e `Asia/Tokyo` (+9) — 3 novos (10 no total no Worker)

### Removido / Limpeza
- Funções Python mortas: `get_card_required_string`, `get_card_optional_string` (`arkhamdb_models`), `_code`, `_day_labels` (`common.py`)
- Chaves i18n órfãs do bot: `bot_started`, `faq_title`, `fmt_taboo_label`, `day_mon`…`day_all`
- ~50 chaves i18n mortas e captions redundantes no Mini App
- Imports não usados em vários handlers; f-strings sem placeholder
- CSS morto (`.time-add-btn`), ternário sem efeito em `formatDelay`, estilos inline migrados para classes (`.manage-row`, `.pending-action-btn`, `.preset-row`)
- `ruff` configurado para ignorar `E402` intencional nos entrypoints (`main.py`, `scripts/`)
- `pass` morto antes de `_execute_command` (`command_worker.py`) e bloco de eviction inalcançável no rate limiter

---

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
- Migration `202605280001_claim_bot_commands_rpc.sql`: RPC atômica `FOR UPDATE SKIP LOCKED` para command queue
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
