from unittest.mock import MagicMock, patch

from arkham_bot.repositories.faq_repo import get_faq_by_code, upsert_faq, get_cached_faq_codes


def _mock_client(rows):
    client = MagicMock()
    client.get.return_value = rows
    client.upsert.return_value = None
    return client


def test_get_faq_by_code_returns_list_when_found():
    rows = [{"raw": [{"html": "<p>Q: test</p>", "text": "Q: test"}], "updated_at": "2026-01-01T00:00:00+00:00"}]
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=_mock_client(rows)):
        result, updated_at = get_faq_by_code("01001")
    assert isinstance(result, list)
    assert result[0]["html"] == "<p>Q: test</p>"
    assert updated_at == "2026-01-01T00:00:00+00:00"


def test_get_faq_by_code_returns_none_when_not_found():
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=_mock_client([])):
        result, updated_at = get_faq_by_code("99999")
    assert result is None
    assert updated_at is None


def test_get_faq_by_code_returns_none_when_no_client():
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=None):
        result, updated_at = get_faq_by_code("01001")
    assert result is None
    assert updated_at is None


def test_get_faq_by_code_wraps_dict_in_list():
    rows = [{"raw": {"html": "<p>test</p>", "text": "test"}, "updated_at": "2026-01-01T00:00:00+00:00"}]
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=_mock_client(rows)):
        result, _ = get_faq_by_code("01001")
    assert isinstance(result, list)
    assert result[0]["html"] == "<p>test</p>"


def test_upsert_faq_calls_client():
    client = _mock_client([])
    payload = [{"html": "<p>Q: test</p>"}]
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=client):
        upsert_faq("01001", payload)
    client.upsert.assert_called_once()
    args = client.upsert.call_args
    assert args[0][0] == "arkham_faq"
    assert args[0][1]["card_code"] == "01001"


def test_upsert_faq_no_op_when_no_client():
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=None):
        upsert_faq("01001", [])  # should not raise


def test_get_cached_faq_codes_returns_codes():
    rows = [{"card_code": "01001"}, {"card_code": "01002"}]
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=_mock_client(rows)):
        codes = get_cached_faq_codes()
    assert "01001" in codes
    assert "01002" in codes


def test_get_cached_faq_codes_empty_when_no_client():
    with patch("arkham_bot.repositories.faq_repo.get_supabase_client", return_value=None):
        codes = get_cached_faq_codes()
    assert codes == []
