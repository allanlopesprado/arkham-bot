from arkham_bot.formatters.text_formatters import clean_and_format_text, format_card_caption


def test_clean_and_format_text_replaces_icons_and_strips_unwanted_html():
    text = clean_and_format_text("<p>[action] Gain [[Resource]].</p><script>bad</script>")
    assert "➡️" in text
    assert "<b>Resource</b>" in text
    assert "script" not in text.lower()


def test_format_card_caption_multiclass_excludes_neutral():
    card = {
        "code": "01001", "name": "Test Card", "type_code": "asset",
        "type_name": "Asset", "faction_code": "neutral", "faction_name": "Neutral",
        "faction2_name": "Guardian", "pack_name": "Core Set",
    }
    caption = format_card_caption(card, is_interactive=True)
    assert "Guardian" in caption
    assert "Neutral" not in caption


def test_format_card_caption_skills_display():
    card = {
        "code": "01001", "name": "Test Card", "type_code": "skill",
        "type_name": "Skill", "faction_name": "Guardian", "faction_code": "guardian",
        "skill_willpower": 2, "skill_combat": 1, "pack_name": "Core Set",
    }
    caption = format_card_caption(card, is_interactive=True)
    assert "👤" in caption
    assert "✊🏻" in caption


def test_format_card_caption_minimal_card():
    caption = format_card_caption({"code": "01001", "name": "Roland Banks", "type_name": "Investigator", "pack_name": "Core Set"})
    assert "Roland Banks" in caption
    assert "01001" in caption
