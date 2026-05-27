# Changelog

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
- Módulo `arkhamdb_oauth.py` (placeholder OAuth sem uso)
- Constantes `ARKHAMDB_OAUTH_CLIENT_ID/SECRET` do config e `.env`
- Variáveis mortas do `.env`: `SUPABASE_ANON_KEY`, `ALLOWED_ORIGINS`, `ARKHAMDB_SAMPLE_DECKLIST_ID`
- Funções mortas: `menu_command`, `random_command`, `_require_admin`, `_yes_no`, `_active_inactive`, `_send_long_or_private`
- `data/arkhamdb_samples/` (8 JSONs sem referência no código)
- `scripts/inspect_arkhamdb_api.py` (script de dev sem uso)
- `EXEMPLOS/` (imagens de referência não usadas pelo código)

### Corrigido
- 400 Bad Request no sync ArkhamDB: campo `name` ausente no upsert de packs e factions
- `start_command` chamava `menu_command` removido (NameError)
- Filtro de data com chave duplicada `created_at2` no `/cotd` (bug silencioso)
- Input de horário no miniapp cortando `HH:MM` (`5ch` → `6ch`)
