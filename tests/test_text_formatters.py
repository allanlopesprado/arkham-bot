from arkham_bot.text_formatters import clean_and_format_text, format_factions_display, skill_test_display, format_card_caption


def test_clean_and_format_text_replaces_icons_and_strips_unwanted_html():
    text = clean_and_format_text("<p>[action] Gain [[Resource]].</p><script>bad</script>")
    assert "➡️" in text
    assert "<b>Resource</b>" in text
    assert "script" not in text.lower()


def test_format_factions_display_removes_neutral_when_multiclass():
    card = {"faction_name": "Neutral", "faction2_name": "Guardian"}
    rendered = format_factions_display(card)
    assert "Guardian" in rendered
    assert "Neutral" not in rendered


def test_skill_test_display():
    result = skill_test_display({"skill_willpower": 2, "skill_combat": 1})
    assert result.count("👤") == 2
    assert "✊🏻" in result


def test_format_card_caption_minimal_card():
    caption = format_card_caption({"code": "01001", "name": "Roland Banks", "type_name": "Investigator", "pack_name": "Core Set"})
    assert "Roland Banks" in caption
    assert "01001" in caption
