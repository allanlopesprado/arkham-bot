import pytest

from arkham_bot.clients.arkhamdb_models import validate_card_payload, validate_pack_payload, validate_faction_payload, validate_decklist_payload


def test_validate_card_payload_minimal_ok():
    payload = {"code": "01001", "name": "Roland Banks", "type_code": "investigator", "pack_code": "core"}
    assert validate_card_payload(payload)["code"] == "01001"


def test_validate_card_payload_requires_code():
    with pytest.raises(ValueError):
        validate_card_payload({"name": "No code", "type_code": "asset", "pack_code": "core"})


def test_validate_pack_payload_requires_code_name():
    assert validate_pack_payload({"code": "core", "name": "Core Set"})["code"] == "core"
    with pytest.raises(ValueError):
        validate_pack_payload({"code": "core"})


def test_validate_faction_payload_requires_code_name():
    assert validate_faction_payload({"code": "guardian", "name": "Guardian"})["code"] == "guardian"
    with pytest.raises(ValueError):
        validate_faction_payload({"name": "Guardian"})


def test_validate_decklist_payload_rejects_primitives():
    with pytest.raises(ValueError):
        validate_decklist_payload("<html>bad</html>")
