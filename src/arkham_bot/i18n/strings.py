"""
All user-facing strings for the Arkham Bot.
Keys are shared between EN and PT. Default language is English.
"""

EN: dict[str, str] = {
    # ── Startup ──────────────────────────────────────────────────────────────
    "bot_started": "Bot started and listening for messages...",

    # ── /start / help ─────────────────────────────────────────────────────────
    "help_title": "<b>Arkham Bot</b>",
    "help_cards_section": "<b>Cards</b>",
    "help_card_cmd": "- <code>/card</code> - guided search by cycle/pack",
    "help_sets_cmd": "- <code>/sets</code> - browse cards by set/expansion",
    "help_search_cmd": "- <code>/search &lt;text&gt;</code> - search by name/text",
    "help_rules_section": "<b>Rules &amp; references</b>",
    "help_faq_cmd": "- <code>/faq &lt;card_code&gt;</code> - card FAQ",
    "help_taboo_cmd": "- <code>/taboo</code> - taboo list",
    "help_decklist_cmd": "- <code>/decklist &lt;id&gt;</code> - ArkhamDB decklist",
    "help_history_section": "<b>History</b>",
    "help_cotd_cmd": "- <code>/cotd</code> - cards of the day by month",
    "help_bot_section": "<b>Bot</b>",
    "help_status_cmd": "- <code>/status</code> - operational status",

    # ── /status ───────────────────────────────────────────────────────────────
    "status_title": "<b>Arkham Bot - Online</b>",
    "status_uptime": "Uptime: {uptime}",
    "status_cards": "Cards: {cards_count}",

    # ── /card ─────────────────────────────────────────────────────────────────
    "card_choose_pack": "Choose a pack to search for the card:",
    "card_btn_close": "Close",
    "card_canceled": "Operation canceled. Type /card to start again.",
    "card_pack_selected": "Pack **{pack_name}** {card_info} selected!\n👉🏻 Please **now enter the card number** you want to search for ({example_hint}):",
    "card_example_fallback": "Ex: 1, 10, 50",
    "card_invalid_input": "Invalid input. Please enter the card code or number (Ex: 1, 150, L01).",
    "card_input_too_long": "Invalid input. The card code seems too long. Please enter the card number (Ex: 1, 150, L01).",
    "card_no_pack": "⚠️ Pack not selected. Please start again with /card.",
    "card_searching": "⏳ Searching for card **{full_card_id}**...",
    "card_not_found": "⚠️ Card `{full_card_id}` not found. Check the code and try again.",
    "card_error": "🚨 Error fetching card `{full_card_id}`. Please try again later.",

    # ── cancel ────────────────────────────────────────────────────────────────
    "cancel_closed": "✖️ Closed.",
    "cancel_text": "Operation canceled.",

    # ── /faq ──────────────────────────────────────────────────────────────────
    "faq_usage": "Usage: /faq <card_code>",
    "faq_not_found": "No FAQ found for <code>{card_code}</code>.",
    "faq_title": "📖 <b>FAQ — {card_code}</b>",
    "faq_error": "Could not fetch FAQ right now.",

    # ── /taboo ────────────────────────────────────────────────────────────────
    "taboo_no_lists": "No taboo lists found.",
    "taboo_not_found_for": "No taboo restriction found for «{query}».",
    "taboo_results_title": "<b>Taboo results for «{query}»:</b>",
    "taboo_error": "Could not load the taboo list right now.",
    "taboo_list_not_found": "List not found.",
    "taboo_session_expired": "Session expired. Use /taboo again.",
    "taboo_card_not_found": "Card not found in taboo list.",
    "taboo_card_searching": "⏳ Searching card <code>{code}</code>...",
    "taboo_lists_title": "<b>Taboo Lists</b>",
    "taboo_lists_subtitle": "Select a list to explore:\n",
    "taboo_list_current_prefix": "[current] ",
    "taboo_btn_close": "Close",
    "taboo_btn_lists": "Lists",
    "taboo_btn_back": "Back",
    "taboo_btn_previous": "Previous",
    "taboo_btn_next": "Next",
    "taboo_detail_title": "<b>Taboo — {date}</b>",
    "taboo_detail_affected": "{total} card(s) affected\n",
    "taboo_category_page": "<b>{label}</b> — {total} card(s) — page {page}/{total_pages}:",

    # ── taboo restriction labels ──────────────────────────────────────────────
    "taboo_label_banned": "Banned",
    "taboo_label_limit": "Limit {n}/deck",
    "taboo_label_exceptional": "Exceptional",
    "taboo_label_errata": "Errata",
    "taboo_label_restricted": "Restricted",

    # ── taboo category labels ─────────────────────────────────────────────────
    "taboo_cat_forbidden": "Banned",
    "taboo_cat_xp_up": "+XP (more expensive)",
    "taboo_cat_xp_down": "−XP (cheaper)",
    "taboo_cat_exceptional": "Exceptional",
    "taboo_cat_errata": "Text errata",
    "taboo_cat_other": "Other restrictions",

    # ── /decklist ─────────────────────────────────────────────────────────────
    "decklist_usage": "Usage: /decklist <decklist_id>",
    "decklist_invalid_id": "Invalid decklist id.",
    "decklist_text": "Decklist: {name}\nInvestigator: {investigator}\nCards in slots: {slots}\nhttps://arkhamdb.com/decklist/view/{decklist_id}",
    "decklist_error": "Could not fetch decklist right now.",
    "decklist_untitled": "Untitled decklist",
    "decklist_unknown_investigator": "Unknown investigator",

    # ── /search ───────────────────────────────────────────────────────────────
    "search_prompt": "🔍 Enter card name or code:",
    "search_btn_cancel": "❌ Cancel",
    "search_empty_query": "Type something to search.",
    "search_searching": "🔍 Searching…",
    "search_not_found": "No cards found. Try a different term.",
    "search_error": "Error fetching cards.",
    "search_results": "🔍 <b>{total} result(s)</b> for «{query}» — page {page}/{total_pages}:",
    "search_session_expired": "Session expired. Use /search again.",
    "search_btn_previous": "⬅️ Previous",
    "search_btn_next": "➡️ Next",
    "search_btn_cancel_nav": "❌ Cancel",
    "search_card_not_found": "Card not found.",
    "search_card_load_error": "Error loading card.",
    "search_card_not_found_code": "Card <code>{code}</code> not found.",
    "search_spoiler_warning": "⚠️ <b>Warning: this card contains a spoiler!</b>",

    # ── /sets ─────────────────────────────────────────────────────────────────
    "sets_no_sets": "No sets available.",
    "sets_choose": "📦 Choose a set to browse its cards:",
    "sets_error": "Error loading sets.",
    "sets_no_cards": "No cards found in this set.",
    "sets_pack_title": "📦 <b>{pack_name}</b> — {count} card(s):",
    "sets_pack_error": "Error loading cards from set.",
    "sets_btn_back": "« Back to sets",

    # ── /cotd ─────────────────────────────────────────────────────────────────
    "cotd_no_cards": "No card of the day found.",
    "cotd_select_year": "Select year:",
    "cotd_no_year": "No cards found for this year.",
    "cotd_select_month": "Select month ({year}):",
    "cotd_no_month": "No cards found for this month.",
    "cotd_month_title": "<b>Cards of the Day - {month_name}/{year}</b>",
    "cotd_btn_back": "« Back",

    # ── daily_card.py ─────────────────────────────────────────────────────────
    "daily_cycle_reset": (
        "🔄 <b>Cycle complete!</b>\n"
        "All cards in the current selection have been posted.\n"
        "The cycle has been reset automatically."
    ),

    # ── text_formatters.py ────────────────────────────────────────────────────
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
    "fmt_customizations": "<b>Customizations:</b>",
    "fmt_art": "Art: {artist}",
    "fmt_encounter": "Encounter: {name}",
    "fmt_pack": "Pack: {name} #{position}",
    "fmt_view_arkhamdb": "🔗 <a href='https://arkhamdb.com/card/{code}'>View on ArkhamDB</a>",
    "fmt_taboo_label": "<b>Taboo:</b> {restriction}",

    # card stat labels
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
    "stat_deck": "Deck",
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

    # skill names (used in Skills line)
    "skill_will": "Will",
    "skill_intellect": "Intellect",
    "skill_combat": "Combat",
    "skill_agility": "Agility",
    "skill_wild": "Wild",

    # month names
    "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],

    # day labels (short, for status display)
    "day_mon": "Mon", "day_tue": "Tue", "day_wed": "Wed", "day_thu": "Thu",
    "day_fri": "Fri", "day_sat": "Sat", "day_sun": "Sun", "day_all": "All",
}


PT: dict[str, str] = {
    # ── Startup ──────────────────────────────────────────────────────────────
    "bot_started": "Bot iniciado e aguardando mensagens...",

    # ── /start / help ─────────────────────────────────────────────────────────
    "help_title": "<b>Arkham Bot</b>",
    "help_cards_section": "<b>Cartas</b>",
    "help_card_cmd": "- <code>/card</code> - busca guiada por ciclo/pacote",
    "help_sets_cmd": "- <code>/sets</code> - navega cartas por set/expansão",
    "help_search_cmd": "- <code>/search &lt;texto&gt;</code> - busca por nome/texto",
    "help_rules_section": "<b>Regras e referências</b>",
    "help_faq_cmd": "- <code>/faq &lt;card_code&gt;</code> - FAQ da carta",
    "help_taboo_cmd": "- <code>/taboo</code> - lista taboo",
    "help_decklist_cmd": "- <code>/decklist &lt;id&gt;</code> - decklist do ArkhamDB",
    "help_history_section": "<b>Histórico</b>",
    "help_cotd_cmd": "- <code>/cotd</code> - cartas do dia por mês",
    "help_bot_section": "<b>Bot</b>",
    "help_status_cmd": "- <code>/status</code> - status operacional",

    # ── /status ───────────────────────────────────────────────────────────────
    "status_title": "<b>Arkham Bot - Online</b>",
    "status_uptime": "Uptime: {uptime}",
    "status_cards": "Cartas: {cards_count}",

    # ── /card ─────────────────────────────────────────────────────────────────
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
    "card_error": "🚨 Erro ao buscar a carta `{full_card_id}`. Tente novamente mais tarde.",

    # ── cancel ────────────────────────────────────────────────────────────────
    "cancel_closed": "✖️ Fechado.",
    "cancel_text": "Operação cancelada.",

    # ── /faq ──────────────────────────────────────────────────────────────────
    "faq_usage": "Uso: /faq <card_code>",
    "faq_not_found": "Nenhum FAQ encontrado para <code>{card_code}</code>.",
    "faq_title": "📖 <b>FAQ — {card_code}</b>",
    "faq_error": "Não foi possível carregar o FAQ agora.",

    # ── /taboo ────────────────────────────────────────────────────────────────
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

    # ── taboo restriction labels ──────────────────────────────────────────────
    "taboo_label_banned": "Banida",
    "taboo_label_limit": "Limite {n}/deck",
    "taboo_label_exceptional": "Exceptional",
    "taboo_label_errata": "Errata",
    "taboo_label_restricted": "Restrita",

    # ── taboo category labels ─────────────────────────────────────────────────
    "taboo_cat_forbidden": "Banidas",
    "taboo_cat_xp_up": "+XP (mais cara)",
    "taboo_cat_xp_down": "−XP (mais barata)",
    "taboo_cat_exceptional": "Exceptional",
    "taboo_cat_errata": "Errata de texto",
    "taboo_cat_other": "Outras restrições",

    # ── /decklist ─────────────────────────────────────────────────────────────
    "decklist_usage": "Uso: /decklist <decklist_id>",
    "decklist_invalid_id": "ID de decklist inválido.",
    "decklist_text": "Decklist: {name}\nInvestigador: {investigator}\nCartas: {slots}\nhttps://arkhamdb.com/decklist/view/{decklist_id}",
    "decklist_error": "Não foi possível carregar a decklist agora.",
    "decklist_untitled": "Decklist sem título",
    "decklist_unknown_investigator": "Investigador desconhecido",

    # ── /search ───────────────────────────────────────────────────────────────
    "search_prompt": "🔍 Digite o nome ou código da carta:",
    "search_btn_cancel": "❌ Cancelar",
    "search_empty_query": "Digite algo para buscar.",
    "search_searching": "🔍 Pesquisando…",
    "search_not_found": "Nenhuma carta encontrada. Tente outro termo.",
    "search_error": "Erro ao buscar cartas.",
    "search_results": "🔍 <b>{total} resultado(s)</b> para «{query}» — página {page}/{total_pages}:",
    "search_session_expired": "Sessão expirada. Use /search novamente.",
    "search_btn_previous": "⬅️ Anterior",
    "search_btn_next": "➡️ Próximo",
    "search_btn_cancel_nav": "❌ Cancelar",
    "search_card_not_found": "Carta não encontrada.",
    "search_card_load_error": "Erro ao carregar a carta.",
    "search_card_not_found_code": "Carta <code>{code}</code> não encontrada.",
    "search_spoiler_warning": "⚠️ <b>Atenção: esta carta contém spoiler!</b>",

    # ── /sets ─────────────────────────────────────────────────────────────────
    "sets_no_sets": "Nenhum set disponível.",
    "sets_choose": "📦 Escolha um set para ver as cartas:",
    "sets_error": "Erro ao carregar sets.",
    "sets_no_cards": "Nenhuma carta encontrada neste set.",
    "sets_pack_title": "📦 <b>{pack_name}</b> — {count} carta(s):",
    "sets_pack_error": "Erro ao carregar cartas do set.",
    "sets_btn_back": "« Voltar aos sets",

    # ── /cotd ─────────────────────────────────────────────────────────────────
    "cotd_no_cards": "Nenhuma carta do dia encontrada.",
    "cotd_select_year": "Selecione o ano:",
    "cotd_no_year": "Nenhuma carta encontrada para este ano.",
    "cotd_select_month": "Selecione o mês ({year}):",
    "cotd_no_month": "Nenhuma carta encontrada para este mês.",
    "cotd_month_title": "<b>Cartas do Dia - {month_name}/{year}</b>",
    "cotd_btn_back": "« Voltar",

    # ── daily_card.py ─────────────────────────────────────────────────────────
    "daily_cycle_reset": (
        "🔄 <b>Ciclo concluído!</b>\n"
        "Todas as cartas da seleção atual já foram postadas.\n"
        "O ciclo foi reiniciado automaticamente."
    ),

    # ── text_formatters.py ────────────────────────────────────────────────────
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

    # card stat labels (kept in English — these are game terms)
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
    "stat_deck": "Deck",
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
