import html
import re


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
        return '⚡ Exceptional'
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
    parts = []
    for key, (icon, name) in _SKILL_ICONS_SKILLS.items():
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
            parts = []
            for key, (icon, short) in _SKILL_ICONS_STATS.items():
                v = card.get(key)
                if v is not None:
                    parts.append(f'{icon} <b>{short}:</b> {v}')
            if parts:
                lines.append('. '.join(parts) + '.')
            lines.append(
                f"❤️ <b>Health:</b> {_fmt_stat(card.get('health'))}. "
                f"🧠 <b>Sanity:</b> {_fmt_stat(card.get('sanity'))}."
            )
        xp = card.get('xp')
        if xp:
            lines.append(f"⭐️ <b>XP:</b> {xp}.")

    elif tc in ('asset', 'event', 'skill'):
        cost = _fmt_cost_stat(card)
        xp = card.get('xp')
        meta_flags = []
        if card.get('permanent'):
            meta_flags.append('Permanent.')
        if card.get('myriad'):
            meta_flags.append('Myriad.')
        if card.get('exile'):
            meta_flags.append('Exile.')

        cost_parts = []
        if cost is not None:
            cost_parts.append(f"💰 <b>Cost:</b> {cost}.")
        if xp:
            cost_parts.append(f"⭐️ <b>XP:</b> {xp}.")
        if meta_flags:
            cost_parts.append(' '.join(meta_flags))
        if cost_parts:
            lines.append(' '.join(cost_parts))

        slot_icon, slot_name = _fmt_slot_text(card)
        if slot_name:
            slot_prefix = f"{slot_icon} " if slot_icon else ""
            lines.append(f"{slot_prefix}<b>Slot:</b> {slot_name}.")

        health = card.get('health')
        sanity = card.get('sanity')
        if health is not None or sanity is not None:
            lines.append(
                f"❤️ <b>Health:</b> {_fmt_stat(health, '0')}. "
                f"🧠 <b>Sanity:</b> {_fmt_stat(sanity, '0')}."
            )

        skills = _fmt_skills_text(card)
        if skills:
            lines.append(f"🎯 <b>Skills:</b> {skills}")

        dl = card.get('deck_limit')
        if dl is not None and dl != 2:
            lines.append(f"<b>Deck:</b> {dl}.")

        bonded = card.get('bonded_to')
        if bonded:
            lines.append(f"🔗 <b>Bonded:</b> {_e(bonded)}.")

    elif tc in ('enemy', 'enemy_location'):
        hp_suffix = ' (x inv.)' if card.get('health_per_investigator') else ''
        lines.append(
            f"✊🏻 <b>Fight:</b> {_fmt_stat(card.get('enemy_fight'))}. "
            f"❤️ <b>Health:</b> {_fmt_stat(card.get('health'))}{hp_suffix}. "
            f"🪽 <b>Evade:</b> {_fmt_stat(card.get('enemy_evade'))}."
        )
        lines.append(
            f"💢 <b>Damage:</b> {_fmt_stat(card.get('enemy_damage'))}. "
            f"😨 <b>Horror:</b> {_fmt_stat(card.get('enemy_horror'))}."
        )
        if tc == 'enemy_location':
            cl_suf = '' if card.get('clues_fixed') else ' (x inv.)'
            lines.append(
                f"🌑 <b>Shroud:</b> {_fmt_stat(card.get('shroud'))}. "
                f"🔍 <b>Clues:</b> {_fmt_stat(card.get('clues'))}{cl_suf}."
            )

    elif tc == 'location':
        cl_suf = '' if card.get('clues_fixed') else ' (x inv.)'
        lines.append(
            f"🌑 <b>Shroud:</b> {_fmt_stat(card.get('shroud'))}. "
            f"🔍 <b>Clues:</b> {_fmt_stat(card.get('clues'))}{cl_suf}."
        )

    elif tc == 'act':
        parts = []
        if card.get('stage') is not None:
            parts.append(f"<b>Stage:</b> {card['stage']}.")
        if card.get('clues') is not None:
            parts.append(f"🔍 <b>Clues:</b> {card['clues']}.")
        if parts:
            lines.append(' '.join(parts))

    elif tc == 'agenda':
        parts = []
        if card.get('stage') is not None:
            parts.append(f"<b>Stage:</b> {card['stage']}.")
        if card.get('doom') is not None:
            parts.append(f"💀 <b>Doom:</b> {card['doom']}.")
        if parts:
            lines.append(' '.join(parts))

    elif tc == 'key':
        linked = card.get('linked_to_name') or card.get('linked_to_code')
        if linked:
            lines.append(f"🔑 <b>Linked to:</b> {_e(linked)}.")

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
    artist = card.get('illustrator', '')
    pack_name = card.get('pack_name', '')
    position = card.get('position', '')
    encounter_name = card.get('encounter_name', '')

    end_lines = []
    if artist:
        end_lines.append(f"Art: {_e(artist)}")
    if encounter_name:
        end_lines.append(f"Encounter: {_e(encounter_name)}")
    elif pack_name and position:
        end_lines.append(f"Pack: {_e(pack_name)} #{position}")

    if end_lines:
        lines.append("\n" + "\n".join(f"<i>{l}</i>" for l in end_lines))

    lines.append(f"🔗 <a href='https://arkhamdb.com/card/{code}'>View on ArkhamDB</a>")


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
    link_tag = f"🔗 <a href='https://arkhamdb.com/card/{code}'>View on ArkhamDB</a>"
    caption = "\n".join(line for line in lines if line or line == "")
    return _truncate_caption(caption, link_tag)


def format_card_caption(card, is_interactive=False):
    name = _card_name(card)
    type_name = card.get('type_name', '')
    subname = card.get('subname', '')
    traits = _card_traits(card)
    code = card.get('code')
    tc = card.get('type_code', 'unknown')
    prefix = "" if is_interactive else "[COTD] "

    double_sided_types = {'investigator', 'act', 'agenda', 'scenario'}
    title_suffix = " - Front" if tc in double_sided_types else ""
    unique_prefix = "✸ " if card.get('is_unique') else ""
    lines = [f"<b>{prefix}{unique_prefix}{_e(name)}{title_suffix}</b>"]

    type_line = _e(type_name)
    if subname:
        type_line += f" • {_e(subname)}"
    if tc in ('weakness', 'basicweakness') or card.get('subtype_code') in ('weakness', 'basicweakness'):
        type_line += ' ⚠️'
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
        meta.append(f"🏆 {card['victory']} VP")
    if card.get('vengeance') is not None:
        meta.append(f"⚔️ {card['vengeance']} Vengeance")
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
            lines.append('\n<b>Customizations:</b>\n' + '\n'.join(cust_lines))

    # --- Text, flavor, footer ---
    _append_text_flavor(lines, card)
    _append_footer(lines, card, code)

    return _build_caption(lines, code)


def format_card_back_caption(card, back_text_raw, is_interactive=False):
    name = _card_name(card)
    back_name = card.get('back_name') or name
    code = card.get('code')
    back_flavor = card.get('back_flavor', '')
    tc = card.get('type_code', 'unknown')
    prefix = "" if is_interactive else "[COTD] "

    unique_prefix = "✸ " if card.get('is_unique') else ""
    lines = [f"<b>{prefix}{unique_prefix}{_e(back_name)} - Back</b>", ""]

    # Back-side stats for act/agenda
    if tc == 'act':
        clues = card.get('clues')
        if clues is not None:
            lines.append(f"🔍 Clues: {clues}")
    elif tc == 'agenda':
        doom = card.get('doom')
        if doom is not None:
            lines.append(f"💀 Doom: {doom}")

    back_text_formatted = clean_and_format_text(back_text_raw)
    back_flavor_formatted = clean_and_format_text(back_flavor, is_flavor=True)

    if back_text_formatted:
        lines.append(back_text_formatted)
    if back_flavor_formatted:
        lines.append(f"\n<i>{back_flavor_formatted}</i>")

    link_tag = f"🔗 <a href='https://arkhamdb.com/card/{code}'>View on ArkhamDB</a>"
    lines.append(link_tag)

    caption = "\n".join(line for line in lines if line or line == "")
    return _truncate_caption(caption, link_tag)
