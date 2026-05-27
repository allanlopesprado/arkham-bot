import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from src.arkham_bot.card_provider import get_card

samples = {
    'Asset simples':           '01059',
    'Asset XP+Slot+Skill':     '60233',
    'Asset multi-faction ally':'08099',
    'Asset permanent':         '02110',
    'Asset exile':             '02115',
    'Asset myriad+arcane2':    '06328',
    'Asset bonded':            '06113',
    'Event simples':           '01010',
    'Event cost X + myriad':   '06034',
    'Investigator':            '01001',
    'Enemy vengeance':         '04078',
    'Enemy health_per_inv VP': '01116',
    'Enemy-Location':          '10533b',
    'Location per_inv':        '01111',
    'Location fixed':          '10556',
    'Treachery weakness':      '01007',
    'Enemy basicweakness':     '01103',
    'Act':                     '10657',
    'Agenda':                  '03278',
    'Key':                     '09768a',
    'Story':                   '10675',
    'Customizable':            '09042',
}

SKILL_NAMES = {
    'skill_willpower': 'Will',
    'skill_intellect': 'Intellect',
    'skill_combat': 'Combat',
    'skill_agility': 'Agility',
    'skill_wild': 'Wild',
}

SLOT_TEXT = {
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

def fmt_skills(card):
    parts = []
    for key, name in SKILL_NAMES.items():
        v = card.get(key) or 0
        if v > 0:
            parts.append(f'{name} x{v}')
    return '. '.join(parts) + '.' if parts else ''

def fmt_cost(card):
    c = card.get('cost')
    if c == -2: return 'X'
    if c is None: return '-'
    return str(c)

def fmt_factions(card):
    factions = [f for f in [card.get('faction_name'), card.get('faction2_name'), card.get('faction3_name')] if f]
    if len(factions) > 1:
        factions = [f for f in factions if f.lower() != 'neutral']
    return ' / '.join(dict.fromkeys(factions))

for label, code in samples.items():
    card, _ = get_card(code)
    if not card:
        print(f'{label}: NOT FOUND\n')
        continue
    tc = card.get('type_code', '')
    lines = []

    faction_str = fmt_factions(card)
    if faction_str:
        lines.append(faction_str)

    if tc == 'investigator':
        lines.append(f"Will: {card.get('skill_willpower', '-')}. Int: {card.get('skill_intellect', '-')}. Combat: {card.get('skill_combat', '-')}. Agi: {card.get('skill_agility', '-')}.")
        lines.append(f"Health: {card.get('health', '-')}. Sanity: {card.get('sanity', '-')}.")

    elif tc in ('asset', 'event', 'skill'):
        cost_str = fmt_cost(card)
        xp = card.get('xp')
        cost_line = f'Cost: {cost_str}.'
        if xp:
            cost_line += f' XP: {xp}.'
        meta = []
        if card.get('permanent'): meta.append('Permanent.')
        if card.get('myriad'): meta.append('Myriad.')
        if card.get('exile'): meta.append('Exile.')
        if meta:
            cost_line += ' ' + ' '.join(meta)
        lines.append(cost_line)

        slot = SLOT_TEXT.get(card.get('slot', ''), card.get('slot', ''))
        if slot:
            lines.append(f'Slot: {slot}.')

        h, s = card.get('health'), card.get('sanity')
        if h is not None or s is not None:
            lines.append(f'Health: {h or 0}. Sanity: {s or 0}.')

        skills = fmt_skills(card)
        if skills:
            lines.append(f'Skills: {skills}')

        dl = card.get('deck_limit')
        if dl is not None and dl != 2:
            lines.append(f'Deck: {dl}.')

        bonded = card.get('bonded_to')
        if bonded:
            lines.append(f'Bonded: {bonded}.')

    elif tc == 'enemy':
        hp_suffix = ' (x inv.)' if card.get('health_per_investigator') else ''
        lines.append(f"Fight: {card.get('enemy_fight', '-')}. Health: {card.get('health', '-')}{hp_suffix}. Evade: {card.get('enemy_evade', '-')}.")
        lines.append(f"Damage: {card.get('enemy_damage', '-')}. Horror: {card.get('enemy_horror', '-')}.")
        if card.get('victory') is not None:
            lines.append(f"VP: {card['victory']}.")
        if card.get('vengeance') is not None:
            lines.append(f"Vengeance: {card['vengeance']}.")

    elif tc == 'enemy_location':
        hp_suffix = ' (x inv.)' if card.get('health_per_investigator') else ''
        lines.append(f"Fight: {card.get('enemy_fight', '-')}. Health: {card.get('health', '-')}{hp_suffix}. Evade: {card.get('enemy_evade', '-')}.")
        lines.append(f"Damage: {card.get('enemy_damage', '-')}. Horror: {card.get('enemy_horror', '-')}.")
        cl_suf = '' if card.get('clues_fixed') else ' (x inv.)'
        lines.append(f"Shroud: {card.get('shroud', '-')}. Clues: {card.get('clues', '-')}{cl_suf}.")

    elif tc == 'location':
        cl_suf = '' if card.get('clues_fixed') else ' (x inv.)'
        lines.append(f"Shroud: {card.get('shroud', '-')}. Clues: {card.get('clues', '-')}{cl_suf}.")

    elif tc == 'act':
        parts = []
        if card.get('stage') is not None: parts.append(f"Stage: {card['stage']}.")
        if card.get('clues') is not None: parts.append(f"Clues: {card['clues']}.")
        if parts: lines.append(' '.join(parts))

    elif tc == 'agenda':
        parts = []
        if card.get('stage') is not None: parts.append(f"Stage: {card['stage']}.")
        if card.get('doom') is not None: parts.append(f"Doom: {card['doom']}.")
        if parts: lines.append(' '.join(parts))

    elif tc == 'key':
        linked = card.get('linked_to_name') or card.get('linked_to_code')
        if linked: lines.append(f'Linked to: {linked}.')

    print(f'--- {label} ({code}) ---')
    for l in lines:
        print(f'  {l}')
    print()
