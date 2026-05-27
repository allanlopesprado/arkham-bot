class ArkhamDBPayloadError(ValueError):
    """Raised when ArkhamDB returns an unexpected payload shape."""


class ArkhamDBHTTPError(RuntimeError):
    """Raised when ArkhamDB HTTP or JSON parsing fails."""


def ensure_dict(value: object, context: str) -> dict:
    if not isinstance(value, dict):
        raise ArkhamDBPayloadError(f"{context} payload must be an object.")
    return value


def ensure_list(value: object, context: str) -> list:
    if not isinstance(value, list):
        raise ArkhamDBPayloadError(f"{context} payload must be a list.")
    return value


def _validate_optional_string(payload: dict, key: str, context: str) -> None:
    value = payload.get(key)
    if value is not None and not isinstance(value, str):
        raise ArkhamDBPayloadError(f"{context}.{key} must be a string or null.")


def _validate_optional_number(payload: dict, key: str, context: str) -> None:
    value = payload.get(key)
    if value is not None and not isinstance(value, (int, float)):
        raise ArkhamDBPayloadError(f"{context}.{key} must be numeric or null.")


def _validate_optional_bool(payload: dict, key: str, context: str) -> None:
    value = payload.get(key)
    if value is not None and not isinstance(value, (bool, int)):
        raise ArkhamDBPayloadError(f"{context}.{key} must be boolean, integer flag, or null.")


def _require_string(payload: dict, key: str, context: str) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ArkhamDBPayloadError(f"{context}.{key} is required and must be a non-empty string.")


def _validate_optional_dict(payload: dict, key: str, context: str) -> None:
    value = payload.get(key)
    if value is not None and not isinstance(value, dict):
        raise ArkhamDBPayloadError(f"{context}.{key} must be an object or null.")


def validate_card_payload(payload: object, context: str = "card") -> dict:
    card = ensure_dict(payload, context)

    _require_string(card, "code", context)
    _require_string(card, "type_code", context)
    _require_string(card, "pack_code", context)

    if not card.get("name") and not card.get("real_name"):
        raise ArkhamDBPayloadError(f"{context} must include name or real_name.")

    string_fields = [
        "code", "name", "real_name", "type_code", "type_name", "faction_code",
        "faction_name", "pack_code", "pack_name", "text", "real_text", "traits",
        "real_traits", "slot", "imagesrc", "backimagesrc", "back_text", "back_name", "back_flavor",
    ]
    number_fields = [
        "position", "xp", "cost", "health", "sanity", "skill_willpower",
        "skill_intellect", "skill_combat", "skill_agility", "skill_wild",
    ]
    bool_fields = ["is_unique", "permanent", "exceptional", "hidden", "spoiler", "double_sided"]

    for key in string_fields:
        _validate_optional_string(card, key, context)
    for key in number_fields:
        _validate_optional_number(card, key, context)
    for key in bool_fields:
        _validate_optional_bool(card, key, context)

    return card


def validate_cards_payload(payload: object, context: str = "cards") -> list[dict]:
    cards = ensure_list(payload, context)
    return [validate_card_payload(card, f"{context}[{index}]") for index, card in enumerate(cards)]


def validate_pack_payload(payload: object, context: str = "pack") -> dict:
    pack = ensure_dict(payload, context)
    _require_string(pack, "code", context)
    _require_string(pack, "name", context)
    return pack


def validate_packs_payload(payload: object, context: str = "packs") -> list[dict]:
    packs = ensure_list(payload, context)
    return [validate_pack_payload(pack, f"{context}[{index}]") for index, pack in enumerate(packs)]


def validate_faction_payload(payload: object, context: str = "faction") -> dict:
    faction = ensure_dict(payload, context)
    _require_string(faction, "code", context)
    _require_string(faction, "name", context)
    return faction


def validate_factions_payload(payload: object, context: str = "factions") -> list[dict]:
    factions = ensure_list(payload, context)
    return [validate_faction_payload(faction, f"{context}[{index}]") for index, faction in enumerate(factions)]


def validate_decklist_payload(payload: object, context: str = "decklist") -> dict:
    decklist = ensure_dict(payload, context)
    decklist_id = decklist.get("id")
    if decklist_id is not None and not isinstance(decklist_id, (str, int)):
        raise ArkhamDBPayloadError(f"{context}.id must be a string, integer, or null.")
    _validate_optional_string(decklist, "name", context)
    _validate_optional_dict(decklist, "slots", context)
    return decklist


def validate_faq_payload(payload: object, context: str = "faq") -> dict | list | None:
    """FAQ may be empty or have variable public API structure."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        for index, item in enumerate(payload):
            ensure_dict(item, f"{context}[{index}]")
        return payload
    raise ArkhamDBPayloadError(f"{context} payload must be an object, list, or null.")


def validate_taboo_payload(payload: object, context: str = "taboo") -> dict:
    return ensure_dict(payload, context)


def validate_taboos_payload(payload: object, context: str = "taboos") -> list[dict] | dict:
    """Taboo may be an object aggregator or a list of taboo objects."""
    if isinstance(payload, dict):
        return payload
    taboos = ensure_list(payload, context)
    return [validate_taboo_payload(taboo, f"{context}[{index}]") for index, taboo in enumerate(taboos)]


def get_card_required_string(card: dict, key: str, fallback: str | None = None) -> str:
    value = card.get(key)
    if isinstance(value, str) and value:
        return value
    if fallback is not None:
        return fallback
    raise ArkhamDBPayloadError(f"card.{key} is required.")


def get_card_optional_string(card: dict, key: str, default: str = "") -> str:
    value = card.get(key)
    return value if isinstance(value, str) else default
