"""Parse latency and cost fields from Supabase call rows."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def _parse_json(value: Any) -> dict[str, Any] | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _summary(metrics: Any) -> dict[str, Any]:
    parsed = _parse_json(metrics)
    if not parsed:
        return {}
    summary = parsed.get("summary")
    if isinstance(summary, dict):
        return summary
    return parsed


def _stat_avg(block: Any) -> float | None:
    if not isinstance(block, dict):
        return None
    avg = block.get("avg")
    try:
        return round(float(avg), 3) if avg is not None else None
    except (TypeError, ValueError):
        return None


def latency_e2e_avg(metrics: Any) -> float | None:
    return _stat_avg(_summary(metrics).get("e2e_latency"))


def latency_transcription_avg(metrics: Any) -> float | None:
    return _stat_avg(_summary(metrics).get("transcription_delay"))


def latency_user_turns(metrics: Any) -> int | None:
    summary = _summary(metrics)
    if "user_turns" in summary:
        try:
            return int(summary["user_turns"])
        except (TypeError, ValueError):
            return None
    return None


def latency_assistant_turns(metrics: Any) -> int | None:
    summary = _summary(metrics)
    if "assistant_turns" in summary:
        try:
            return int(summary["assistant_turns"])
        except (TypeError, ValueError):
            return None
    return None


def latency_playback_avg(metrics: Any) -> float | None:
    parsed = _parse_json(metrics)
    if not parsed:
        return None
    values: list[float] = []
    for turn in parsed.get("turns", []):
        if not isinstance(turn, dict):
            continue
        value = turn.get("playback_latency")
        if value is None:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def latency_primary_avg(metrics: Any) -> float | None:
    """Prefer end-to-end latency; fall back to playback for realtime-only calls."""
    return latency_e2e_avg(metrics) or latency_playback_avg(metrics)


def has_latency_metrics(metrics: Any) -> bool:
    parsed = _parse_json(metrics)
    if not parsed:
        return False
    if parsed.get("turns"):
        return True
    summary = _summary(metrics)
    return any(
        summary.get(key) is not None
        for key in (
            "e2e_latency",
            "transcription_delay",
            "user_turns",
            "assistant_turns",
        )
    )


def cost_usd(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def pricing_mode(breakdown: Any) -> str | None:
    parsed = _parse_json(breakdown)
    if not parsed:
        return None
    mode = parsed.get("pricing_mode")
    return str(mode) if mode else None


def cost_per_second(breakdown: Any) -> float | None:
    parsed = _parse_json(breakdown)
    if not parsed:
        return None
    value = parsed.get("cost_per_second_usd")
    try:
        return round(float(value), 6) if value is not None else None
    except (TypeError, ValueError):
        return None


def breakdown_line_items(breakdown: Any) -> list[dict[str, Any]]:
    parsed = _parse_json(breakdown)
    if not parsed:
        return []
    items = parsed.get("breakdown")
    if not isinstance(items, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key, item in items.items():
        if not isinstance(item, dict) or item.get("usd") is None:
            continue
        rows.append(
            {
                "key": key,
                "usd": round(float(item["usd"]), 4),
                "characters": item.get("characters"),
            }
        )
    return rows


def enrich_calls_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized latency/cost columns for display and aggregation."""
    if df.empty:
        return df

    out = df.copy()
    if "latency_metrics" in out.columns:
        out["_e2e_latency_avg"] = out["latency_metrics"].map(latency_e2e_avg)
        out["_playback_latency_avg"] = out["latency_metrics"].map(latency_playback_avg)
        out["_primary_latency_avg"] = out["latency_metrics"].map(latency_primary_avg)
        out["_transcription_delay_avg"] = out["latency_metrics"].map(
            latency_transcription_avg
        )
        out["_user_turns"] = out["latency_metrics"].map(latency_user_turns)
        out["_assistant_turns"] = out["latency_metrics"].map(latency_assistant_turns)
        out["_has_latency"] = out["latency_metrics"].map(has_latency_metrics)
    else:
        out["_e2e_latency_avg"] = None
        out["_playback_latency_avg"] = None
        out["_primary_latency_avg"] = None
        out["_transcription_delay_avg"] = None
        out["_user_turns"] = None
        out["_assistant_turns"] = None
        out["_has_latency"] = False

    if "estimated_cost_usd" in out.columns:
        out["_estimated_cost_usd"] = out["estimated_cost_usd"].map(cost_usd)
    else:
        out["_estimated_cost_usd"] = None

    if "cost_breakdown" in out.columns:
        out["_pricing_mode"] = out["cost_breakdown"].map(pricing_mode)
        out["_cost_per_second_usd"] = out["cost_breakdown"].map(cost_per_second)
    else:
        out["_pricing_mode"] = None
        out["_cost_per_second_usd"] = None

    return out


def aggregate_call_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Return summary stats for latency and cost across calls."""
    if df.empty:
        return {
            "calls_with_latency": 0,
            "calls_with_cost": 0,
            "avg_e2e_latency_s": None,
            "avg_transcription_delay_s": None,
            "avg_cost_usd": None,
            "total_cost_usd": None,
        }

    enriched = enrich_calls_dataframe(df)
    with_latency = enriched[enriched["_has_latency"] == True]  # noqa: E712
    e2e = enriched["_e2e_latency_avg"].dropna()
    primary = enriched["_primary_latency_avg"].dropna()
    transcription = enriched["_transcription_delay_avg"].dropna()
    costs = enriched["_estimated_cost_usd"].dropna()

    return {
        "calls_with_latency": int(with_latency.shape[0]),
        "calls_with_cost": int(costs.count()),
        "avg_e2e_latency_s": round(float(e2e.mean()), 3) if not e2e.empty else None,
        "avg_primary_latency_s": round(float(primary.mean()), 3)
        if not primary.empty
        else None,
        "avg_transcription_delay_s": round(float(transcription.mean()), 3)
        if not transcription.empty
        else None,
        "avg_cost_usd": round(float(costs.mean()), 4) if not costs.empty else None,
        "total_cost_usd": round(float(costs.sum()), 4) if not costs.empty else None,
    }