from arkham_bot.services.daily_card import _telegram_html_text


def test_telegram_html_text_escapes_ai_content():
    assert _telegram_html_text("Investigue <b>isso</b> & avance") == "Investigue &lt;b&gt;isso&lt;/b&gt; &amp; avance"


def test_telegram_html_text_returns_none_for_blank_content():
    assert _telegram_html_text("") is None
    assert _telegram_html_text(None) is None
