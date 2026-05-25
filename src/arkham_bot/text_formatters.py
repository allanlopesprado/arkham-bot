import html
import re


MAX_CAPTION_BYTES = 1024

SKILL_ICONS = {
    'skill_willpower': '👤', 'skill_intellect': '📖',
    'skill_combat': '✊', 'skill_agility': '🦶', 'skill_wild': '❓'
}

GLOBAL_ICON_REPLACEMENTS = {
    '[action]': '➡️ ', '[reaction]': '🔁 ', '[free]': '🆓 ',
    '[fast]': '💨 ', '[unique]': '⭐ ',
    '[combat]': '✊', '[intellect]': '📖', '[agility]': '🦶',
    '[willpower]': '👤', '[wild]': '❓',
    '[guardian]': '🔵', '[seeker]': '🟡', '[mystic]': '🟣',
    '[rogue]': '🟢', '[survivor]': '🔴',
    '[bless]': '✨', '[curse]': '💀',
    '[resource]': '💵', '[health]': '❤️', '[sanity]': '🧠',
    '[elder_sign]': '✨', '[skull]': '💀', '[cultist]': '👤',
    '[tablet]': '📜', '[elder_thing]': '🐙', '[auto_fail]': '🚫',
    '[elite]': '👑', '[peril]': '⚠️'
}

FACTION_ICONS_MAP = {
    'Guardian': '🔵', 'Seeker': '🟡', 'Rogue': '🟢',
    'Mystic': '🟣', 'Survivor': '🔴',
    'Neutral': '⚪', 'Mythos': '⚫'
}


def format_factions_display(card):
    """
    Constructs the display string for all factions on the card,
    checking primary, secondary, and tertiary faction fields.
    """
    factions = []

    f1_name = card.get('faction_name')
    if f1_name:
        factions.append(f1_name)

    f2_name = card.get('faction2_name')
    if f2_name and f2_name not in factions:
        factions.append(f2_name)

    f3_name = card.get('faction3_name')
    if f3_name and f3_name not in factions:
        factions.append(f3_name)

    unique_factions = [f for f in factions if f]

    if len(unique_factions) > 1:
        unique_factions = [f for f in unique_factions if f.lower() != 'neutral']

    unique_factions = list(dict.fromkeys(unique_factions))

    if not unique_factions:
        return ""

    display_parts = []
    for faction_name in unique_factions:
        icon = FACTION_ICONS_MAP.get(faction_name, '⚪')
        display_parts.append(f"{faction_name} {icon}")

    return " / ".join(display_parts)


def skill_test_display(card):
    """Returns the skill test display using 'Skill Test' in English."""
    test_icons = []
    for skill_key, icon in SKILL_ICONS.items():
        count = card.get(skill_key, 0)
        if count > 0:
            test_icons.extend([icon] * count)
    return f"Skill Test: {' '.join(test_icons)}" if test_icons else ""


def clean_and_format_text(text_raw, is_flavor=False):
    """
    Centralizes text cleaning, HTML unescape, icon replacement,
    and character normalization.
    """
    if not text_raw:
        return ""

    text = re.sub(r'[\u200B-\u200F\u202A-\u202E\ufeff]', '', text_raw)
    text = html.unescape(text)

    if is_flavor:
        text = re.sub(r'<[^>]+>', '', text, flags=re.IGNORECASE)
    else:
        text = text.replace('<br/>', '\n').replace('<br>', '\n')
        text = text.replace('<p>', '\n\n').replace('</p>', '')
        text = re.sub(r'</?(?!b\b|i\b)[a-z]+[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<a[^>]+?>.*?</a>', '', text, flags=re.IGNORECASE | re.DOTALL)

    if not is_flavor:
        for tag, icon in GLOBAL_ICON_REPLACEMENTS.items():
            text = text.replace(tag, icon)

        text = re.sub(r'\[\[(.*?)\]\]', r'<b>\1</b>', text)

        all_icons = list(SKILL_ICONS.values())
        icons_regex_group = '[' + ''.join(re.escape(icon) for icon in all_icons) + ']'
        text = re.sub(rf'({icons_regex_group})\.', r'\1', text)

    text = (
        text.replace("“", "\"").replace("”", "\"")
        .replace("‘", "'").replace("’", "'")
        .replace("—", "-").replace("–", "-")
        .replace("…", "...")
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


def format_card_caption(card, is_interactive=False):
    name = _card_name(card)
    type_name = card.get('type_name', '')
    subname = card.get('subname', '')
    cost = card.get('cost')
    xp = card.get('xp')
    text = _card_text(card)
    flavor = card.get('flavor', '')
    artist = card.get('illustrator', '')
    code = card.get('code')
    traits = _card_traits(card)
    pack_name = card.get('pack_name', '')
    position = card.get('position', '')
    card_type_code = card.get('type_code', 'unknown')

    text_formatted = clean_and_format_text(text, is_flavor=False)
    flavor_formatted = clean_and_format_text(flavor, is_flavor=True)

    lines = []

    prefix = ""
    if not is_interactive:
        prefix = "[COTD] "

    title_suffix = " - Front" if card_type_code in ['investigator', 'act', 'agenda'] else ""
    lines.append(f"<b>{prefix}Card: {name}{title_suffix}</b>")

    lines.append(f"<i>{type_name}{' • ' + subname if subname else ''}</i>")

    if traits.strip():
        lines.append(f"<i>{traits.strip()}</i>")

    lines.append("")

    faction_display = format_factions_display(card)
    if faction_display:
        lines.append(faction_display)

    is_mini_investigator = (card_type_code == 'investigator' and
                            card.get('faction_code', '').lower() == 'neutral' and
                            card.get('skill_willpower') is None)

    if card_type_code == 'investigator':
        if not is_mini_investigator:
            lines.append(f"Stats: 👤 {card.get('skill_willpower', 0)} | 📖 {card.get('skill_intellect', 0)} | ✊ {card.get('skill_combat', 0)} | 🦶 {card.get('skill_agility', 0)}")
            lines.append(f"Health: ❤️ {card.get('health', 0)} | Sanity: 🧠 {card.get('sanity', 0)}")

        meta_parts = []
        if cost is not None and cost > 0:
            meta_parts.append(f"💰 Cost: {cost}")
        if xp is not None and xp > 0:
            meta_parts.append(f"⭐️ XP: {xp}")
        if meta_parts:
            lines.append(" | ".join(meta_parts))

    elif card_type_code == 'enemy':
        lines.append(f"Fight: ✊ {card.get('enemy_fight', 0)} | Health: ❤️ {card.get('health', 0)} | Evade: 🦶{card.get('enemy_evade', 0)}")
        lines.append(f"Damage: ❤️ {card.get('enemy_damage', 0)} | Horror: 🧠 {card.get('enemy_horror', 0)}")

    elif card_type_code == 'asset':
        lines.append(f"💰 Cost: {card.get('cost', 0)} | ⭐️ XP: {card.get('xp', 0)} | {skill_test_display(card)}")

        if card.get('health') is not None or card.get('sanity') is not None:
            if card.get('health', 0) > 0 or card.get('sanity', 0) > 0:
                lines.append(f"Health: ❤️ {card.get('health', 0)} | Sanity: 🧠 {card.get('sanity', 0)}")

    elif card_type_code in ['event', 'skill']:
        lines.append(f"💰 Cost: {card.get('cost', 0)} | ⭐️ XP: {card.get('xp', 0)} | {skill_test_display(card)}")

    elif card_type_code == 'location':
        lines.append(f"Shroud: 🌑 {card.get('shroud', 0)} | Clues: 📖 {card.get('clues', 0)}")

    if text_formatted:
        lines.append(f"\n{text_formatted}")

    if flavor_formatted:
        lines.append(f"\n<i>{flavor_formatted}</i>")

    end_lines = []
    if artist:
        end_lines.append(f"Art: {artist}")
    if pack_name and position:
        end_lines.append(f"Pack: {pack_name} #{position}")

    if end_lines:
        lines.append("\n" + "\n".join([f"<i>{line}</i>" for line in end_lines]))

    link_tag = f"🔗 <a href='https://arkhamdb.com/card/{code}'>View on ArkhamDB</a>"
    lines.append(link_tag)

    caption = "\n".join([line for line in lines if line or line == ""])

    if len(caption.encode('utf-8')) > MAX_CAPTION_BYTES:
        link_tag_bytes = len(link_tag.encode('utf-8'))
        safe_char_cut_point = MAX_CAPTION_BYTES - link_tag_bytes - 25

        if safe_char_cut_point > 0:
            body_caption_raw = caption[:safe_char_cut_point]
            body_caption = body_caption_raw.strip()

            if body_caption.count("<i>") > body_caption.count("</i>"):
                body_caption += "</i>"
            if body_caption.count("<b>") > body_caption.count("</b>"):
                body_caption += "</b>"

            caption = body_caption + "...\n\n" + link_tag

        else:
            caption = caption.encode('utf-8')[:MAX_CAPTION_BYTES - 4].decode('utf-8', 'ignore').strip() + "..."

    return caption


def format_card_back_caption(card, back_text_raw, is_interactive=False):
    name = _card_name(card)
    back_name = card.get('back_name') or name
    code = card.get('code')
    back_flavor = card.get('back_flavor', '')

    back_text_formatted = clean_and_format_text(back_text_raw, is_flavor=False)
    back_flavor_formatted = clean_and_format_text(back_flavor, is_flavor=True)

    lines = []

    prefix = "" if is_interactive else "[COTD] "
    lines.append(f"<b>{prefix}Card Back: {back_name}</b>")
    lines.append("")

    if back_text_formatted:
        lines.append(f"{back_text_formatted}")

    if back_flavor_formatted:
        lines.append(f"\n<i>{back_flavor_formatted}</i>")

    link_tag = f"🔗 <a href='https://arkhamdb.com/card/{code}'>View on ArkhamDB</a>"
    lines.append(link_tag)

    caption = "\n".join([line for line in lines if line or line == ""])

    if len(caption.encode('utf-8')) > MAX_CAPTION_BYTES:
        link_tag_bytes = len(link_tag.encode('utf-8'))
        safe_char_cut_point = MAX_CAPTION_BYTES - link_tag_bytes - 25

        if safe_char_cut_point > 0:
            body_caption_raw = caption[:safe_char_cut_point]
            body_caption = body_caption_raw.strip()

            if body_caption.count("<i>") > body_caption.count("</i>"):
                body_caption += "</i>"
            if body_caption.count("<b>") > body_caption.count("</b>"):
                body_caption += "</b>"

            caption = body_caption + "...\n\n" + link_tag
        else:
            caption = caption.encode('utf-8')[:MAX_CAPTION_BYTES - 4].decode('utf-8', 'ignore').strip() + "..."

    return caption
