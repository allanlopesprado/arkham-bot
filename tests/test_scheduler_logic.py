from datetime import datetime
from zoneinfo import ZoneInfo

from arkham_bot.services.scheduler import _finish_attempt, _mark_attempting, _as_list, _is_due, _times_for_day, _slot_key


def test_as_list_handles_string_and_list():
    assert _as_list("08:00, 12:00", ["09:00"]) == ["08:00", "12:00"]
    assert _as_list(["mon", "tue"], ["sun"]) == ["mon", "tue"]
    assert _as_list(None, ["sun"]) == ["sun"]


def test_is_due_only_inside_window_and_once_per_time():
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 5, 24, 8, 5, tzinfo=tz)
    assert _is_due(now, "08:00", {}) is True
    state = {"posted_slots": ["2026-05-24_08:00"]}
    assert _is_due(now, "08:00", state) is False
    too_late = datetime(2026, 5, 24, 8, 30, tzinfo=tz)
    assert _is_due(too_late, "08:00", {}) is False


def test_times_for_day_prefers_day_config():
    default = ["08:00"]
    day_config = {"mon": {"times": ["10:30", "21:00"]}, "tue": {"times": []}}

    assert _times_for_day("mon", default, day_config) == ["10:30", "21:00"]
    assert _times_for_day("tue", default, day_config) == []
    assert _times_for_day("wed", default, day_config) == default


def test_slot_key_format():
    assert _slot_key("2026-05-28", "08:30") == "2026-05-28_08:30"


def test_slot_claimed_temporarily_prevents_refire():
    """An active attempt blocks immediate refire, but stale attempts can retry."""
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 5, 28, 8, 5, tzinfo=tz)
    state_before = {}
    assert _is_due(now, "08:00", state_before) is True
    state_after = _mark_attempting(state_before, "2026-05-28", "08:00", now)
    assert _is_due(now, "08:00", state_after) is False
    stale_now = datetime(2026, 5, 28, 8, 8, tzinfo=tz)
    assert _is_due(stale_now, "08:00", state_after) is True


def test_successful_attempt_marks_slot_posted():
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 5, 28, 8, 5, tzinfo=tz)
    state = _mark_attempting({}, "2026-05-28", "08:00", now)
    state = _finish_attempt(state, "2026-05-28", "08:00", success=True)
    assert state["posted_slots"] == [_slot_key("2026-05-28", "08:00")]
    assert state["attempting_slots"] == {}
    assert _is_due(now, "08:00", state) is False


def test_failed_attempt_does_not_mark_slot_posted():
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 5, 28, 8, 5, tzinfo=tz)
    state = _mark_attempting({}, "2026-05-28", "08:00", now)
    state = _finish_attempt(state, "2026-05-28", "08:00", success=False)
    assert state.get("posted_slots", []) == []
    assert state["attempting_slots"] == {}
    assert _is_due(now, "08:00", state) is True


def test_slot_only_blocks_same_day():
    """A slot from yesterday must not block today's post."""
    tz = ZoneInfo("America/Sao_Paulo")
    today = datetime(2026, 5, 28, 8, 5, tzinfo=tz)
    state = {"posted_slots": [_slot_key("2026-05-27", "08:00")]}
    assert _is_due(today, "08:00", state) is True


def test_before_seconds_shifts_trigger_window():
    """With before_seconds=300, an 08:30 post should be due at 08:25."""
    tz = ZoneInfo("America/Sao_Paulo")
    at_825 = datetime(2026, 5, 28, 8, 25, tzinfo=tz)
    at_836 = datetime(2026, 5, 28, 8, 36, tzinfo=tz)  # outside 10-min window from 08:25
    assert _is_due(at_825, "08:30", {}, before_seconds=300) is True
    assert _is_due(at_836, "08:30", {}, before_seconds=300) is False
