strings: dict = {
    # Startup
    "bot_started": "Bot iniciado e aguardando mensagens...",

    # /start / help
    "help_title": "🃏 <b>Arkham Bot</b>\nSeu companheiro para Arkham Horror: The Card Game.",
    "help_cards_section": "🔍 <b>Cartas</b>",
    "help_card_cmd": "  <code>/card</code> — busca guiada por ciclo e pacote",
    "help_sets_cmd": "  <code>/sets</code> — navega todas as cartas organizadas por set",
    "help_search_cmd": "  <code>/search &lt;nome&gt;</code> — busca livre por nome ou texto",
    "help_rules_section": "📖 <b>Regras e referências</b>",
    "help_faq_cmd": "  <code>/faq &lt;código&gt;</code> — perguntas e respostas oficiais de uma carta",
    "help_taboo_cmd": "  <code>/taboo</code> — lista taboo atual com restrições e erratas",
    "help_decklist_cmd": "  <code>/decklist &lt;id&gt;</code> — visualiza um deck público do ArkhamDB",
    "help_history_section": "📅 <b>Histórico</b>",
    "help_cotd_cmd": "  <code>/cotd</code> — cartas do dia postadas por mês",
    "help_bot_section": "⚙️ <b>Bot</b>",
    "help_status_cmd": "  <code>/status</code> — status operacional e próximo post agendado",

    # /status
    "status_title": "🤖 <b>Arkham Bot — Online</b>",
    "status_date": "📅 {date} · {hour}",
    "status_timezone": "🌎 {timezone}",
    "status_uptime": "⏱ Online há {uptime}",
    "status_cards_line": "📚 Cartas: <code>{count}</code>",
    "status_packs_line": "📦 Pacotes: <code>{count}</code>",
    "status_taboos_line": "🔖 Taboos: <code>{count}</code>",
    "status_next_post": "⏰ Próximo post: {next_post}",
    "status_last_post": "🃏 Último card do dia: {card}",
    "status_no_last_post": "📭 Nenhum card postado nesta sessão",
    "status_post_disabled": "⏸ Postagem automática desativada",
    "status_pending_commands": "🗂 Fila: <code>{count}</code> pendente(s)",
    "status_supabase": "🗄 Supabase: {status}",

    # /card
    "card_choose_pack": "Escolha um pacote para buscar a carta:",
    "card_btn_close": "Fechar",
    "card_canceled": "Operação cancelada. Digite /card para começar de novo.",
    "card_pack_selected": "Pacote **{pack_name}** {card_info} selecionado!\n👉🏻 Agora **digite o número da carta** que deseja buscar ({example_hint}):",
    "card_example_fallback": "Ex: 1, 10, 50",
    "card_invalid_input": "Entrada inválida. Digite o código ou número da carta (Ex: 1, 150, L01).",
    "card_input_too_long": "Entrada inválida. O código parece muito longo. Digite o número da carta (Ex: 1, 150, L01).",
    "card_no_pack": "⚠️ Pacote não selecionado. Comece de novo com /card.",
    "card_searching": "⏳ Buscando carta **{full_card_id}**...",
    "card_not_found": "⚠️ Carta `{full_card_id}` não encontrada. Verifique o código e tente novamente.",
    "card_number_not_in_pack": "⚠️ O número *{number}* não existe neste pacote.\nNúmeros válidos: {samples}\n\nDigite outro número:",
    "faq_last_updated": "Atualizado em",
    "card_error": "🚨 Erro ao buscar a carta `{full_card_id}`. Tente novamente mais tarde.",

    # cancel
    "cancel_closed": "✖️ Fechado.",
    "cancel_text": "Operação cancelada.",

    # /faq
    "faq_usage": "Uso: /faq <card_code>",
    "faq_not_found": "Nenhum FAQ encontrado para <code>{card_code}</code>.",
    "faq_title": "📖 <b>FAQ — {card_code}</b>",
    "faq_error": "Não foi possível carregar o FAQ agora.",

    # /taboo
    "taboo_no_lists": "Nenhuma lista taboo encontrada.",
    "taboo_not_found_for": "Nenhuma restrição taboo encontrada para «{query}».",
    "taboo_results_title": "<b>Resultados taboo para «{query}»:</b>",
    "taboo_error": "Não foi possível carregar a lista taboo agora.",
    "taboo_list_not_found": "Lista não encontrada.",
    "taboo_session_expired": "Sessão expirada. Use /taboo novamente.",
    "taboo_card_not_found": "Carta não encontrada na lista taboo.",
    "taboo_card_searching": "⏳ Buscando carta <code>{code}</code>...",
    "taboo_lists_title": "<b>Listas Taboo</b>",
    "taboo_lists_subtitle": "Selecione uma lista para explorar:\n",
    "taboo_list_current_prefix": "[atual] ",
    "taboo_btn_close": "Fechar",
    "taboo_btn_lists": "Listas",
    "taboo_btn_back": "Voltar",
    "taboo_btn_previous": "Anterior",
    "taboo_btn_next": "Próximo",
    "taboo_detail_title": "<b>Taboo — {date}</b>",
    "taboo_detail_affected": "{total} carta(s) afetada(s)\n",
    "taboo_category_page": "<b>{label}</b> — {total} carta(s) — página {page}/{total_pages}:",

    # taboo restriction labels
    "taboo_label_banned": "Banida",
    "taboo_label_limit": "Limite {n}/deck",
    "taboo_label_exceptional": "Exceptional",
    "taboo_label_errata": "Errata",
    "taboo_label_restricted": "Restrita",

    # taboo category labels
    "taboo_cat_forbidden": "Banidas",
    "taboo_cat_xp_up": "+XP (mais cara)",
    "taboo_cat_xp_down": "−XP (mais barata)",
    "taboo_cat_exceptional": "Exceptional",
    "taboo_cat_errata": "Errata de texto",
    "taboo_cat_other": "Outras restrições",

    # /decklist
    "decklist_usage": "Uso: /decklist <decklist_id>",
    "decklist_invalid_id": "ID de decklist inválido.",
    "decklist_text": "Decklist: {name}\nInvestigador: {investigator}\nCartas: {slots}\nhttps://arkhamdb.com/decklist/view/{decklist_id}",
    "decklist_error": "Não foi possível carregar a decklist agora.",
    "decklist_untitled": "Decklist sem título",
    "decklist_unknown_investigator": "Investigador desconhecido",

    # /search
    "search_prompt": "🔍 Digite o nome ou código da carta:",
    "search_btn_cancel": "Cancelar",
    "search_empty_query": "Digite algo para buscar.",
    "search_searching": "🔍 Pesquisando…",
    "search_not_found": "Nenhuma carta encontrada. Tente outro termo.",
    "search_error": "Erro ao buscar cartas.",
    "search_results": "🔍 <b>{total} resultado(s)</b> para «{query}» — página {page}/{total_pages}:",
    "search_session_expired": "Sessão expirada. Use /search novamente.",
    "search_btn_previous": "Anterior",
    "search_btn_next": "Próximo",
    "search_btn_cancel_nav": "Cancelar",
    "search_card_not_found": "Carta não encontrada.",
    "search_card_load_error": "Erro ao carregar a carta.",
    "search_card_not_found_code": "Carta <code>{code}</code> não encontrada.",
    "search_spoiler_warning": "⚠️ <b>Atenção: esta carta contém spoiler!</b>",

    # /sets
    "sets_no_sets": "Nenhum set disponível.",
    "sets_choose": "📦 Escolha um set para ver as cartas:",
    "sets_error": "Erro ao carregar sets.",
    "sets_no_cards": "Nenhuma carta encontrada neste set.",
    "sets_pack_title": "📦 <b>{pack_name}</b> — {count} carta(s):",
    "sets_pack_error": "Erro ao carregar cartas do set.",
    "sets_btn_back": "Voltar aos sets",
    "sets_btn_prev": "Anterior",
    "sets_btn_next": "Próxima",
    "sets_no_sets": "Nenhum set encontrado.",

    # /cotd
    "cotd_no_cards": "Nenhuma carta do dia encontrada.",
    "cotd_select_year": "Selecione o ano:",
    "cotd_no_year": "Nenhuma carta encontrada para este ano.",
    "cotd_select_month": "Selecione o mês ({year}):",
    "cotd_no_month": "Nenhuma carta encontrada para este mês.",
    "cotd_month_title": "<b>Cartas do Dia - {month_name}/{year}</b>",
    "cotd_btn_back": "« Voltar",

    # daily_card.py
    "daily_cycle_reset": (
        "🔄 <b>Ciclo concluído!</b>\n"
        "Todas as cartas da seleção atual já foram postadas.\n"
        "O ciclo foi reiniciado automaticamente."
    ),

    # text_formatters.py
    "fmt_exceptional": "⚡ Exceptional",
    "fmt_permanent": "Permanent.",
    "fmt_myriad": "Myriad.",
    "fmt_exile": "Exile.",
    "fmt_front_suffix": " - Front",
    "fmt_back_suffix": " - Back",
    "fmt_cotd_prefix": "[COTD] ",
    "fmt_weakness_tag": " ⚠️",
    "fmt_vp": "🏆 {n} VP",
    "fmt_vengeance": "⚔️ {n} Vengeance",
    "fmt_customizations": "<b>Personalizações:</b>",
    "fmt_art": "Arte: {artist}",
    "fmt_encounter": "Encontro: {name}",
    "fmt_pack": "Pacote: {name} #{position}",
    "fmt_view_arkhamdb": "🔗 <a href='https://arkhamdb.com/card/{code}'>Ver no ArkhamDB</a>",
    "fmt_taboo_label": "<b>Taboo:</b> {restriction}",

    # card stat labels (kept in English — game terms)
    "stat_will": "Will",
    "stat_int": "Int",
    "stat_combat": "Combat",
    "stat_agi": "Agi",
    "stat_health": "Health",
    "stat_sanity": "Sanity",
    "stat_cost": "Cost",
    "stat_xp": "XP",
    "stat_slot": "Slot",
    "stat_skills": "Skills",
    "stat_deck": "🃏 Deck",
    "stat_bonded": "Bonded",
    "stat_fight": "Fight",
    "stat_evade": "Evade",
    "stat_damage": "Damage",
    "stat_horror": "Horror",
    "stat_shroud": "Shroud",
    "stat_clues": "Clues",
    "stat_stage": "Stage",
    "stat_doom": "Doom",
    "stat_linked_to": "Linked to",
    "stat_per_inv": " (x inv.)",

    # skill names (kept in English — game terms)
    "skill_will": "Will",
    "skill_intellect": "Intellect",
    "skill_combat": "Combat",
    "skill_agility": "Agility",
    "skill_wild": "Wild",

    # month names
    "months": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"],

    # day labels
    "day_mon": "Seg", "day_tue": "Ter", "day_wed": "Qua", "day_thu": "Qui",
    "day_fri": "Sex", "day_sat": "Sab", "day_sun": "Dom", "day_all": "Todos",
}
