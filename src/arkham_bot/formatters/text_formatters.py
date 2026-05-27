import html
import re
from ..i18n import get_strings


MAX_CAPTION_BYTES = 1024

SKILL_ICONS = {
    'skill_willpower': '👤', 'skill_intellect': '📓',
    'skill_combat': '✊🏻', 'skill_agility': '🪽', 'skill_wild': '❓'
}

GLOBAL_ICON_REPLACEMENTS = {
    '[action]': '➡️ ', '[reaction]': '🔁 ', '[free]': '🆓 ',
    '[fast]': '💨 ', '[unique]': '⭐ ',
    '[combat]': '✊🏻', '[intellect]': '📓', '[agility]': '🪽',
    '[willpower]': '👤', '[wild]': '❓',
    '[guardian]': '🔵', '[seeker]': '🟡', '[mystic]': '🟣',
    '[rogue]': '🟢', '[survivor]': '🔴',
    '[bless]': '🌟', '[curse]': '🖤',
    '[resource]': '💵', '[health]': '❤️', '[sanity]': '🧠',
    '[elder_sign]': '✨', '[skull]': '💀', '[cultist]': '🧟',
    '[tablet]': '📜', '[elder_thing]': '🐙', '[auto_fail]': '🚫',
    '[elite]': '👑', '[peril]': '⚠️',
    '[per_investigator]': '🔍', '[frost]': '❄️', '[token]': '🪙',
    '[void]': '⭕', '[damage]': '💢', '[horror]': '😨',
}

SLOT_ICONS_MAP = {
    'Hand': '🤚🏻',
    'Hand x2': '🤲🏻',
    'Arcane': '🔮',
    'Arcane x2': '🔮🔮',
    'Ally': '🕵️',
    'Body': '🧥',
    'Accessory': '💎',
    'Tarot': '🃏',
    'Head': '🪖',
    'Hand. Arcane': '🤚🏻🔮',
    'Hand x2. Arcane': '🤚🏻🤚🏻🔮',
    'Ally. Arcane': '🕵️🔮',
    'Body. Hand x2': '🧥🤚🏻🤚🏻',
    'Body. Arcane': '🧥🔮',
    'Arcane. Accessory': '🔮💎',
}

SLOT_TEXT_MAP = {
    'Hand': 'Hand', 'Hand x2': 'Hand x2',
    'Arcane': 'Arcane', 'Arcane x2': 'Arcane x2',
    'Ally': 'Ally', 'Body': 'Body',
    'Accessory': 'Accessory', 'Tarot': 'Tarot', 'Head': 'Head',
    'Hand. Arcane': 'Hand + Arcane',
    'Hand x2. Arcane': 'Hand x2 + Arcane',
    'Ally. Arcane': 'Ally + Arcane',
    'Body. Hand x2': 'Body + Hand x2',
    'Body. Arcane': 'Body + Arcane',
    'Arcane. Accessory': 'Arcane + Accessory',
}

SKILL_NAMES_STATS = {
    'skill_willpower': 'Will',
    'skill_intellect': 'Intellect',
    'skill_combat': 'Combat',
    'skill_agility': 'Agility',
    'skill_wild': 'Wild',
}

_ENCOUNTER_FACTION = {'mythos'}

FACTION_ICONS_MAP = {
    'Guardian': '🔵', 'Seeker': '🟡', 'Rogue': '🟢',
    'Mystic': '🟣', 'Survivor': '🔴',
    'Neutral': '⚪', 'Mythos': '⚫'
}


# Matches any tag that is NOT <b>, </b>, <i>, </i>
_STRIP_TAGS = re.compile(r"</?(?!b>|b |i>|i |/b>|/i>)[a-zA-Z][^>]*>", re.IGNORECASE)


def _e(text: str) -> str:
    """HTML-escape plain text for safe insertion into Telegram HTML messages."""
    return html.escape(str(text)) if text else ""


def _fmt_stat(value, fallback: str = '-') -> str:
    return str(value) if value is not None else fallback


def _exceptional_tag(card: dict) -> str:
    if card.get('exceptional') or card.get('is_exceptional'):
        return get_strings()['fmt_exceptional']
    return ''


_SKILL_ICONS_STATS = {
    'skill_willpower': ('👤', 'Will'),
    'skill_intellect': ('📓', 'Int'),
    'skill_combat':    ('✊🏻', 'Combat'),
    'skill_agility':   ('🪽', 'Agi'),
    'skill_wild':      ('❓', 'Wild'),
}

_SKILL_ICONS_SKILLS = {
    'skill_willpower': ('👤', 'Will'),
    'skill_intellect': ('📓', 'Intellect'),
    'skill_combat':    ('✊🏻', 'Combat'),
    'skill_agility':   ('🪽', 'Agility'),
    'skill_wild':      ('❓', 'Wild'),
}


def _fmt_faction_stats(card: dict) -> str:
    """Faction line with icons. Empty for mythos/encounter cards."""
    factions = []
    for key in ('faction_name', 'faction2_name', 'faction3_name'):
        f = card.get(key)
        if f and f not in factions:
            factions.append(f)
    if len(factions) > 1:
        factions = [f for f in factions if f.lower() != 'neutral']
    factions = list(dict.fromkeys(factions))
    if not factions or all(f.lower() in _ENCOUNTER_FACTION for f in factions):
        return ''
    return '. '.join(f"{FACTION_ICONS_MAP.get(f, '⚪')} {f}" for f in factions) + '.'


def _fmt_skills_text(card: dict) -> str:
    """Returns '📓 Intellect x2. 🪽 Agility x1.' or empty string."""
    s = get_strings()
    skill_names = {
        'skill_willpower': (SKILL_ICONS['skill_willpower'], s['skill_will']),
        'skill_intellect': (SKILL_ICONS['skill_intellect'], s['skill_intellect']),
        'skill_combat':    (SKILL_ICONS['skill_combat'],    s['skill_combat']),
        'skill_agility':   (SKILL_ICONS['skill_agility'],   s['skill_agility']),
        'skill_wild':      (SKILL_ICONS['skill_wild'],      s['skill_wild']),
    }
    parts = []
    for key, (icon, name) in skill_names.items():
        v = card.get(key)
        if v and v > 0:
            parts.append(f'{icon} {name} x{v}')
    return '. '.join(parts) + '.' if parts else ''


def _fmt_slot_text(card: dict) -> tuple[str, str]:
    """Returns (icon, name) for the slot field."""
    slot_raw = card.get('slot', '') or ''
    icon = SLOT_ICONS_MAP.get(slot_raw, '')
    name = SLOT_TEXT_MAP.get(slot_raw, slot_raw)
    return icon, name


def _fmt_cost_stat(card: dict) -> str | None:
    """Returns cost string or None if cost is absent (permanent/bonded)."""
    cost = card.get('cost')
    if cost is None:
        return None
    if cost == -2:
        return 'X'
    return str(cost)


def _build_stats_lines(card: dict) -> list[str]:
    """Returns stat lines for the stats block of a card caption."""
    s = get_strings()
    lines = []
    tc = card.get('type_code', '')

    faction = _fmt_faction_stats(card)
    if faction:
        exceptional = _exceptional_tag(card)
        faction_line = faction
        if exceptional:
            faction_line += f' | {exceptional}'
        lines.append(faction_line)

    if tc == 'investigator':
        is_mini = (
            card.get('faction_code', '').lower() == 'neutral' and
            card.get('skill_willpower') is None
        )
        if not is_mini:
            skill_icons_stats = [
                ('skill_willpower', '👤', s['stat_will']),
                ('skill_intellect', '📓', s['stat_int']),
                ('skill_combat',    '✊🏻', s['stat_combat']),
                ('skill_agility',   '🪽', s['stat_agi']),
            ]
            parts = []
            for key, icon, short in skill_icons_stats:
                v = card.get(key)
                if v is not None:
                    parts.append(f'{icon} <b>{short}:</b> {v}')
            if parts:
                lines.append('. '.join(parts) + '.')
            lines.append(
                f"❤️ <b>{s['stat_health']}:</b> {_fmt_stat(card.get('health'))}. "
                f"🧠 <b>{s['stat_sanity']}:</b> {_fmt_stat(card.get('sanity'))}."
            )
        xp = card.get('xp')
        if xp:
            lines.append(f"⭐️ <b>{s['stat_xp']}:</b> {xp}.")

    elif tc in ('asset', 'event', 'skill'):
        cost = _fmt_cost_stat(card)
        xp = card.get('xp')
        meta_flags = []
        if card.get('permanent'):
            meta_flags.append(s['fmt_permanent'])
        if card.get('myriad'):
            meta_flags.append(s['fmt_myriad'])
        if card.get('exile'):
            meta_flags.append(s['fmt_exile'])

        cost_parts = []
        if cost is not None:
            cost_parts.append(f"💰 <b>{s['stat_cost']}:</b> {cost}.")
        if xp:
            cost_parts.append(f"⭐️ <b>{s['stat_xp']}:</b> {xp}.")
        if meta_flags:
            cost_parts.append(' '.join(meta_flags))
        if cost_parts:
            lines.append(' '.join(cost_parts))

        slot_icon, slot_name = _fmt_slot_text(card)
        if slot_name:
            slot_prefix = f"{slot_icon} " if slot_icon else ""
            lines.append(f"{slot_prefix}<b>{s['stat_slot']}:</b> {slot_name}.")

        health = card.get('health')
        sanity = card.get('sanity')
        if health is not None or sanity is not None:
            lines.append(
                f"❤️ <b>{s['stat_health']}:</b> {_fmt_stat(health, '0')}. "
                f"🧠 <b>{s['stat_sanity']}:</b> {_fmt_stat(sanity, '0')}."
            )

        skills = _fmt_skills_text(card)
        if skills:
            lines.append(f"🎯 <b>{s['stat_skills']}:</b> {skills}")

        dl = card.get('deck_limit')
        if dl is not None and dl != 2:
            lines.append(f"<b>{s['stat_deck']}:</b> {dl}.")

        bonded = card.get('bonded_to')
        if bonded:
            lines.append(f"🔗 <b>{s['stat_bonded']}:</b> {_e(bonded)}.")

    elif tc in ('enemy', 'enemy_location'):
        hp_suffix = s['stat_per_inv'] if card.get('health_per_investigator') else ''
        lines.append(
            f"✊🏻 <b>{s['stat_fight']}:</b> {_fmt_stat(card.get('enemy_fight'))}. "
            f"❤️ <b>{s['stat_health']}:</b> {_fmt_stat(card.get('health'))}{hp_suffix}. "
            f"🪽 <b>{s['stat_evade']}:</b> {_fmt_stat(card.get('enemy_evade'))}."
        )
        lines.append(
            f"💢 <b>{s['stat_damage']}:</b> {_fmt_stat(card.get('enemy_damage'))}. "
            f"😨 <b>{s['stat_horror']}:</b> {_fmt_stat(card.get('enemy_horror'))}."
        )
        if tc == 'enemy_location':
            cl_suf = '' if card.get('clues_fixed') else s['stat_per_inv']
            lines.append(
                f"🌑 <b>{s['stat_shroud']}:</b> {_fmt_stat(card.get('shroud'))}. "
                f"🔍 <b>{s['stat_clues']}:</b> {_fmt_stat(card.get('clues'))}{cl_suf}."
            )

    elif tc == 'location':
        cl_suf = '' if card.get('clues_fixed') else s['stat_per_inv']
        lines.append(
            f"🌑 <b>{s['stat_shroud']}:</b> {_fmt_stat(card.get('shroud'))}. "
            f"🔍 <b>{s['stat_clues']}:</b> {_fmt_stat(card.get('clues'))}{cl_suf}."
        )

    elif tc == 'act':
        parts = []
        if card.get('stage') is not None:
            parts.append(f"<b>{s['stat_stage']}:</b> {card['stage']}.")
        if card.get('clues') is not None:
            parts.append(f"🔍 <b>{s['stat_clues']}:</b> {card['clues']}.")
        if parts:
            lines.append(' '.join(parts))

    elif tc == 'agenda':
        parts = []
        if card.get('stage') is not None:
            parts.append(f"<b>{s['stat_stage']}:</b> {card['stage']}.")
        if card.get('doom') is not None:
            parts.append(f"💀 <b>{s['stat_doom']}:</b> {card['doom']}.")
        if parts:
            lines.append(' '.join(parts))

    elif tc == 'key':
        linked = card.get('linked_to_name') or card.get('linked_to_code')
        if linked:
            lines.append(f"🔑 <b>{s['stat_linked_to']}:</b> {_e(linked)}.")

    elif tc in ('scenario', 'story'):
        encounter_name = card.get('encounter_name', '')
        if encounter_name:
            lines.append(f"📖 {_e(encounter_name)}")

    return lines

def clean_and_format_text(text_raw, is_flavor=False):
    if not text_raw:
        return ""

    text = re.sub(r'[​-‏‪-‮﻿]', '', text_raw)
    text = html.unescape(text)

    if is_flavor:
        text = re.sub(r'<[^>]+>', '', text, flags=re.IGNORECASE)
    else:
        text = text.replace('<br/>', '\n').replace('<br>', '\n')
        text = text.replace('<p>', '\n\n').replace('</p>', '')
        text = _STRIP_TAGS.sub('', text)
        text = re.sub(r'<a[^>]+?>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)

    if not is_flavor:
        for tag, icon in GLOBAL_ICON_REPLACEMENTS.items():
            text = text.replace(tag, icon)

        text = re.sub(r'\[\[(.*?)\]\]', r'<b>\1</b>', text)

        all_icons = list(SKILL_ICONS.values())
        icons_regex_group = '[' + ''.join(re.escape(icon) for icon in all_icons) + ']'
        text = re.sub(rf'({icons_regex_group})\.', r'\1', text)

    text = (
        text.replace('“', '"').replace('”', '"')
        .replace('‘', "'").replace('’', "'")
        .replace('—', '-').replace('–', '-')
        .replace('…', '...')
    )

    if text.count("<i>") > text.count("</i>"):
        text += "</i>"
    if text.count("<b>") > text.count("</b>"):
        text += "</b>"

    return text.strip()


def _card_name(card: dict) -> str:
    return card.get('name') or card.get('real_name') or 'Unknown Card'


def _card_text(card: dict) -> str:
    return card.get('text') or card.get('real_text') or ''


def _card_traits(card: dict) -> str:
    return card.get('traits') or card.get('real_traits') or ''


def _append_text_flavor(lines: list, card: dict, text: str = '', flavor: str = ''):
    text_formatted = clean_and_format_text(text or _card_text(card))
    flavor_formatted = clean_and_format_text(flavor or card.get('flavor', ''), is_flavor=True)
    if text_formatted:
        lines.append(f"\n{text_formatted}")
    if flavor_formatted:
        lines.append(f"\n<i>{flavor_formatted}</i>")


def _append_footer(lines: list, card: dict, code: str):
    s = get_strings()
    artist = card.get('illustrator', '')
    pack_name = card.get('pack_name', '')
    position = card.get('position', '')
    encounter_name = card.get('encounter_name', '')

    end_lines = []
    if artist:
        end_lines.append(s['fmt_art'].format(artist=_e(artist)))
    if encounter_name:
        end_lines.append(s['fmt_encounter'].format(name=_e(encounter_name)))
    elif pack_name and position:
        end_lines.append(s['fmt_pack'].format(name=_e(pack_name), position=position))

    if end_lines:
        lines.append("\n" + "\n".join(f"<i>{l}</i>" for l in end_lines))

    lines.append(s['fmt_view_arkhamdb'].format(code=code))


def _truncate_caption(caption: str, link_tag: str) -> str:
    if len(caption.encode('utf-8')) <= MAX_CAPTION_BYTES:
        return caption

    link_tag_bytes = len(link_tag.encode('utf-8'))
    cut = MAX_CAPTION_BYTES - link_tag_bytes - 25

    if cut > 0:
        body = caption[:cut].strip()
        if body.count("<i>") > body.count("</i>"):
            body += "</i>"
        if body.count("<b>") > body.count("</b>"):
            body += "</b>"
        return body + "...\n\n" + link_tag

    return caption.encode('utf-8')[:MAX_CAPTION_BYTES - 4].decode('utf-8', 'ignore').strip() + "..."


def _build_caption(lines: list, code: str) -> str:
    link_tag = get_strings()['fmt_view_arkhamdb'].format(code=code)
    caption = "\n".join(line for line in lines if line or line == "")
    return _truncate_caption(caption, link_tag)


def format_card_caption(card, is_interactive=False):
    s = get_strings()
    name = _card_name(card)
    type_name = card.get('type_name', '')
    subname = card.get('subname', '')
    traits = _card_traits(card)
    code = card.get('code')
    tc = card.get('type_code', 'unknown')
    prefix = "" if is_interactive else s['fmt_cotd_prefix']

    double_sided_types = {'investigator', 'act', 'agenda', 'scenario'}
    title_suffix = s['fmt_front_suffix'] if tc in double_sided_types else ""
    unique_prefix = "✸ " if card.get('is_unique') else ""
    lines = [f"<b>{prefix}{unique_prefix}{_e(name)}{title_suffix}</b>"]

    type_line = _e(type_name)
    if subname:
        type_line += f" • {_e(subname)}"
    if tc in ('weakness', 'basicweakness') or card.get('subtype_code') in ('weakness', 'basicweakness'):
        type_line += s['fmt_weakness_tag']
    lines.append(f"<i>{type_line}</i>")

    if traits.strip():
        lines.append(f"<i>{_e(traits.strip())}</i>")

    lines.append("")

    # --- Stats per type ---
    stats = _build_stats_lines(card)
    if stats:
        lines.extend(stats)

    # --- Shared card attributes ---
    meta = []
    if card.get('victory') is not None:
        meta.append(s['fmt_vp'].format(n=card['victory']))
    if card.get('vengeance') is not None:
        meta.append(s['fmt_vengeance'].format(n=card['vengeance']))
    if meta:
        lines.append(' | '.join(meta))

    # --- Customization options ---
    cust_opts = card.get('customization_options')
    if cust_opts:
        cust_lines = []
        for opt in cust_opts:
            xp = opt.get('xp', 0)
            text = clean_and_format_text(opt.get('text', ''))
            if text:
                cust_lines.append(f"{'⭐️' * xp} {text}" if xp else text)
        if cust_lines:
            lines.append('\n' + s['fmt_customizations'] + '\n' + '\n'.join(cust_lines))

    # --- Text, flavor, footer ---
    _append_text_flavor(lines, card)
    _append_footer(lines, card, code)

    return _build_caption(lines, code)


def format_card_back_caption(card, back_text_raw, is_interactive=False):
    s = get_strings()
    name = _card_name(card)
    back_name = card.get('back_name') or name
    code = card.get('code')
    back_flavor = card.get('back_flavor', '')
    tc = card.get('type_code', 'unknown')
    prefix = "" if is_interactive else s['fmt_cotd_prefix']

    unique_prefix = "✸ " if card.get('is_unique') else ""
    lines = [f"<b>{prefix}{unique_prefix}{_e(back_name)}{s['fmt_back_suffix']}</b>", ""]

    # Back-side stats for act/agenda
    if tc == 'act':
        clues = card.get('clues')
        if clues is not None:
            lines.append(f"🔍 {s['stat_clues']}: {clues}")
    elif tc == 'agenda':
        doom = card.get('doom')
        if doom is not None:
            lines.append(f"💀 {s['stat_doom']}: {doom}")

    back_text_formatted = clean_and_format_text(back_text_raw)
    back_flavor_formatted = clean_and_format_text(back_flavor, is_flavor=True)

    if back_text_formatted:
        lines.append(back_text_formatted)
    if back_flavor_formatted:
        lines.append(f"\n<i>{back_flavor_formatted}</i>")

    link_tag = s['fmt_view_arkhamdb'].format(code=code)
    lines.append(link_tag)

    caption = "\n".join(line for line in lines if line or line == "")
    return _truncate_caption(caption, link_tag)
