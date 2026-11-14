from datetime import datetime, timezone

import pandas as pd

from dashboard_data import format_call_moment, live_duration, period_start, summarize_calls


def test_period_today_starts_at_montreal_midnight() -> None:
    now = datetime(2026, 11, 14, 17, 45, tzinfo=timezone.utc)
    start = period_start("today", now)
    assert start == datetime(2026, 11, 14, 5, 0, tzinfo=timezone.utc)
    assert period_start("all", now) is None
    assert period_start("7d", now) == datetime(2026, 11, 7, 17, 45, tzinfo=timezone.utc)


def test_format_call_moment_uses_montreal_and_french_month() -> None:
    moment = datetime(2026, 11, 14, 17, 45, 3, tzinfo=timezone.utc)
    assert format_call_moment(moment, "fr") == "14 novembre 2026 à 12:45:03"
    assert format_call_moment(moment, "en") == "November 14, 2026 at 12:45:03"


def test_short_live_call_is_not_marked_long() -> None:
    started = datetime(2026, 11, 14, 17, 45, tzinfo=timezone.utc)
    now = datetime(2026, 11, 14, 17, 45, 40, tzinfo=timezone.utc)
    label, is_long = live_duration(started, now)
    assert label == "short"
    assert is_long is False


def test_live_call_past_one_minute_is_long() -> None:
    started = datetime(2026, 11, 14, 17, 40, tzinfo=timezone.utc)
    now = datetime(2026, 11, 14, 17, 45, tzinfo=timezone.utc)
    label, is_long = live_duration(started, now)
    assert label == "5"
    assert is_long is True


def test_average_duration_weights_calls_not_clients() -> None:
    rows = pd.DataFrame(
        [
            {"client_id": "small", "company_name": "Petit", "duration_seconds": 10, "status": "completed"},
            {"client_id": "eco", "company_name": "Écodentaire", "duration_seconds": 100, "status": "completed"},
            {"client_id": "eco", "company_name": "Écodentaire", "duration_seconds": 100, "status": "transferred", "transfer_attempted": True, "transfer_success": True},
            {"client_id": "eco", "company_name": "Écodentaire", "duration_seconds": 100, "status": "completed", "message_taken": True},
        ]
    )
    summary = summarize_calls(rows)
    assert summary["avg_duration_s"] == 77.5
    assert summary["transferred"] == 1
    assert summary["transferred_success"] == 1
    assert summary["messages"] == 1
    assert summary["completed"] == 3
    eco = summary["clients"].loc[summary["clients"]["client_id"] == "eco"].iloc[0]
    assert eco["avg_duration_s"] == 100.0
    assert eco["total"] == 3
    assert eco["messages"] == 1
