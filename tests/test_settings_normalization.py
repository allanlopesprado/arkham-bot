"""Unit tests for settings normalization and text formatting logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.arkham_bot.formatters.text_formatters import clean_and_format_text, _fmt_stat, _fmt_cost_stat


# ── clean_and_format_text ────────────────────────────────────────────────────

def test_clean_and_format_text_empty():
    assert clean_and_format_text('') == ''
    assert clean_and_format_text(None) == ''


def test_clean_and_format_text_icon_replacements():
    result = clean_and_format_text('[action] [combat]')
    assert '➡️' in result
    assert '✊🏻' in result


def test_clean_and_format_text_strips_unknown_tags():
    result = clean_and_format_text('<span class="foo">hello</span>')
    assert '<span' not in result
    assert 'hello' in result


def test_clean_and_format_text_keeps_bold_italic():
    result = clean_and_format_text('<b>Bold</b> and <i>italic</i>')
    assert '<b>' in result
    assert '<i>' in result


def test_clean_and_format_text_flavor_strips_all_tags():
    result = clean_and_format_text('<b>Flavor</b> text', is_flavor=True)
    assert '<b>' not in result
    assert 'Flavor' in result


def test_clean_and_format_text_curly_quotes():
    result = clean_and_format_text('“Hello”')
    assert '"Hello"' in result


# ── _fmt_stat ─────────────────────────────────────────────────────────────────

def test_fmt_stat_value():
    assert _fmt_stat(3) == '3'
    assert _fmt_stat(0) == '0'


def test_fmt_stat_none_returns_fallback():
    assert _fmt_stat(None) == '-'
    assert _fmt_stat(None, 'X') == 'X'


# ── _fmt_cost_stat ────────────────────────────────────────────────────────────

def test_fmt_cost_stat_normal():
    assert _fmt_cost_stat({'cost': 3}) == '3'
    assert _fmt_cost_stat({'cost': 0}) == '0'


def test_fmt_cost_stat_x():
    assert _fmt_cost_stat({'cost': -2}) == 'X'


def test_fmt_cost_stat_none():
    assert _fmt_cost_stat({}) is None
    assert _fmt_cost_stat({'cost': None}) is None
