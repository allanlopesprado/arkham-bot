from datetime import datetime
from zoneinfo import ZoneInfo

from arkham_bot.services.scheduler import _as_list, _is_due, _times_for_day


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
