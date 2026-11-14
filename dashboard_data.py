"""Pure helpers for the global dashboard: period, live rows, and call totals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

MONTREAL = ZoneInfo("America/Montreal")

_MONTHS = {
    "fr": (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ),
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}


def period_start(period: str, now: datetime) -> datetime | None:
    """UTC instant where the selected dashboard period begins. None means all time."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if period == "all":
        return None
    if period == "today":
        local = now.astimezone(MONTREAL)
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.astimezone(timezone.utc)
    if period == "7d":
        return now - timedelta(days=7)
    raise ValueError(f"unknown period: {period}")


def format_call_moment(moment: datetime, lang: str) -> str:
    """Local Montreal timestamp with an explicit month name."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    local = moment.astimezone(MONTREAL)
    months = _MONTHS["en"] if lang.startswith("en") else _MONTHS["fr"]
    month = months[local.month - 1]
    clock = local.strftime("%H:%M:%S")
    if lang.startswith("en"):
        return f"{month} {local.day}, {local.year} at {clock}"
    return f"{local.day} {month} {local.year} à {clock}"


def live_duration(started_at: datetime, now: datetime) -> tuple[str, bool]:
    """Return a short label and whether the call has already passed one minute.

    The long flag is independent of the label text, so a French phrase that
    contains "min" does not mark a short call as long.
    """
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    seconds = max((now - started_at).total_seconds(), 0)
    if seconds <= 60:
        return "short", False
    return str(int(seconds // 60)), True


def _flag(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return df[column].fillna(False).astype(bool)


def _duration(df: pd.DataFrame) -> pd.Series:
    if "duration_seconds" not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df["duration_seconds"], errors="coerce")


def _average_seconds(duration: pd.Series) -> float:
    valid = duration.dropna()
    if valid.empty:
        return 0.0
    return round(float(valid.mean()), 1)


def summarize_calls(df: pd.DataFrame, *, unknown_label: str = "Inconnu") -> dict:
    """Totals plus one row per client. Duration is the mean of calls, not of clients."""
    empty = {
        "total": 0,
        "completed": 0,
        "abandoned": 0,
        "booked": 0,
        "confirmed": 0,
        "cancelled": 0,
        "avg_duration_s": 0.0,
        "transferred": 0,
        "transferred_success": 0,
        "messages": 0,
        "clients": pd.DataFrame(),
    }
    if df is None or df.empty:
        return empty

    work = df.copy()
    names = work.get("company_name")
    if names is None:
        work["company_name"] = unknown_label
    else:
        work["company_name"] = names.fillna(unknown_label).replace("", unknown_label)
    if "client_id" not in work.columns:
        work["client_id"] = work["company_name"]
    status = work["status"] if "status" in work.columns else pd.Series("", index=work.index)
    work["_completed"] = status.eq("completed")
    work["_abandoned"] = status.eq("abandoned")
    work["_booked"] = _flag(work, "appointment_booked")
    work["_confirmed"] = _flag(work, "appointment_confirmed")
    work["_cancelled"] = _flag(work, "appointment_cancelled")
    work["_transferred"] = _flag(work, "transfer_attempted")
    work["_transferred_ok"] = _flag(work, "transfer_success")
    work["_messages"] = _flag(work, "message_taken")
    work["_duration"] = _duration(work)

    def _row(group: pd.DataFrame) -> dict:
        return {
            "client_id": group["client_id"].iloc[0],
            "company_name": group["company_name"].iloc[0],
            "total": int(len(group)),
            "completed": int(group["_completed"].sum()),
            "abandoned": int(group["_abandoned"].sum()),
            "booked": int(group["_booked"].sum()),
            "transferred": int(group["_transferred"].sum()),
            "messages": int(group["_messages"].sum()),
            "avg_duration_s": _average_seconds(group["_duration"]),
        }

    clients = pd.DataFrame([_row(group) for _, group in work.groupby("client_id", sort=False)])
    clients = clients.sort_values(["total", "company_name"], ascending=[False, True])
    return {
        "total": int(len(work)),
        "completed": int(work["_completed"].sum()),
        "abandoned": int(work["_abandoned"].sum()),
        "booked": int(work["_booked"].sum()),
        "confirmed": int(work["_confirmed"].sum()),
        "cancelled": int(work["_cancelled"].sum()),
        "avg_duration_s": _average_seconds(work["_duration"]),
        "transferred": int(work["_transferred"].sum()),
        "transferred_success": int(work["_transferred_ok"].sum()),
        "messages": int(work["_messages"].sum()),
        "clients": clients.reset_index(drop=True),
    }
