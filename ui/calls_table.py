"""Call history tables — badges, filters, and Streamlit column_config."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import pandas as pd
import streamlit as st

IssueType = str
TranslateFn = Callable[..., str]

ISSUE_APPOINTMENT = "appointment"
ISSUE_MESSAGE = "message"
ISSUE_TRANSFER = "transfer"
ISSUE_ABANDONED = "abandoned"
ISSUE_DONE = "done"

ISSUE_FILTER_OPTIONS = (
    "all",
    ISSUE_APPOINTMENT,
    ISSUE_MESSAGE,
    ISSUE_TRANSFER,
    ISSUE_ABANDONED,
    ISSUE_DONE,
)

PERIOD_FILTER_OPTIONS = ("all", "7", "30", "90")

STATUS_FILTER_OPTIONS = ("all", "completed", "abandoned", "transferred", "in_progress", "voicemail")

RECORDING_URL_COLUMNS = ("recording_url", "audio_url", "wav_url", "recording")

INTERNAL_DISPLAY_COLUMNS = (
    "_issue_type",
    "_issue_badge",
    "_status_badge",
    "_detail",
    "_has_audio",
    "_audio_label",
    "_transcript_preview",
)


def call_issue_type(row: pd.Series | dict) -> IssueType:
    if row.get("appointment_booked"):
        return ISSUE_APPOINTMENT
    if row.get("message_taken"):
        return ISSUE_MESSAGE
    if row.get("transfer_success"):
        return ISSUE_TRANSFER
    if row.get("status") == "abandoned":
        return ISSUE_ABANDONED
    return ISSUE_DONE


def issue_badge_label(issue_type: IssueType, t_fn: TranslateFn) -> str:
    return {
        ISSUE_APPOINTMENT: t_fn("badge_appointment"),
        ISSUE_MESSAGE: t_fn("badge_message"),
        ISSUE_TRANSFER: t_fn("badge_transfer"),
        ISSUE_ABANDONED: t_fn("badge_abandoned"),
        ISSUE_DONE: t_fn("badge_done"),
    }.get(issue_type, t_fn("badge_done"))


def status_badge_label(status: Any, t_fn: TranslateFn) -> str:
    mapping = {
        "in_progress": t_fn("status_badge_in_progress"),
        "completed": t_fn("status_badge_completed"),
        "abandoned": t_fn("status_badge_abandoned"),
        "transferred": t_fn("status_badge_transferred"),
        "voicemail": t_fn("status_badge_voicemail"),
    }
    if status in mapping:
        return mapping[status]
    if status:
        return t_fn("status_badge_other", status=str(status))
    return "—"


def has_recording(row: pd.Series | dict) -> bool:
    return any(
        pd.notna(row.get(col)) and str(row.get(col)).startswith("http")
        for col in RECORDING_URL_COLUMNS
    )


def call_detail_text(row: pd.Series | dict) -> str:
    if row.get("message_taken"):
        reason = str(row.get("message_reason") or "")
        return reason[:70] + "..." if len(reason) > 70 else reason or "—"
    if row.get("transfer_success"):
        dept = str(row.get("transfer_department") or "")
        number = str(row.get("transfer_to_number") or "")
        if dept and number:
            return f"{dept} ({number})"
        return dept or number or "—"
    return "—"


def prepare_calls_table_dataframe(
    df: pd.DataFrame,
    *,
    t_fn: TranslateFn,
    client_tz: Any | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    enriched = df.copy()
    for col in ("started_at", "appointment_start"):
        if col not in enriched.columns:
            continue
        enriched[col] = pd.to_datetime(enriched[col], errors="coerce")
        mask = enriched[col].notna()
        if not mask.any():
            continue
        if enriched.loc[mask, col].dt.tz is None:
            enriched.loc[mask, col] = enriched.loc[mask, col].dt.tz_localize("UTC")
        if client_tz is not None:
            enriched.loc[mask, col] = enriched.loc[mask, col].dt.tz_convert(client_tz)

    enriched["_issue_type"] = enriched.apply(call_issue_type, axis=1)
    enriched["_issue_badge"] = enriched["_issue_type"].map(
        lambda value: issue_badge_label(value, t_fn)
    )
    enriched["_status_badge"] = enriched.apply(
        lambda row: status_badge_label(row.get("status"), t_fn),
        axis=1,
    )
    enriched["_detail"] = enriched.apply(call_detail_text, axis=1)
    enriched["_has_audio"] = enriched.apply(has_recording, axis=1)
    enriched["_audio_label"] = enriched["_has_audio"].map(
        lambda yes: t_fn("audio_available") if yes else ""
    )
    if "transcript" in enriched.columns:
        enriched["_transcript_preview"] = (
            enriched["transcript"].fillna("").astype(str).apply(
                lambda text: (text[:85] + "...") if len(text) > 85 else text
            )
        )
    return enriched


def filter_calls_dataframe(
    df: pd.DataFrame,
    *,
    period_days: str,
    status_filter: str,
    issue_filter: str,
    now: datetime | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()
    if period_days != "all" and "started_at" in filtered.columns:
        days = int(period_days)
        started = pd.to_datetime(filtered["started_at"], errors="coerce", utc=True)
        if now is None:
            reference = pd.Timestamp.now(tz="UTC")
        else:
            reference = pd.Timestamp(now)
            reference = (
                reference.tz_localize("UTC")
                if reference.tzinfo is None
                else reference.tz_convert("UTC")
            )
        cutoff = reference - timedelta(days=days)
        filtered = filtered[started >= cutoff]

    if status_filter != "all" and "status" in filtered.columns:
        filtered = filtered[filtered["status"] == status_filter]

    if issue_filter != "all" and "_issue_type" in filtered.columns:
        filtered = filtered[filtered["_issue_type"] == issue_filter]

    return filtered.reset_index(drop=True)


def sort_calls_dataframe(
    df: pd.DataFrame,
    *,
    newest_first: bool,
) -> pd.DataFrame:
    if df.empty:
        return df
    if "started_at" in df.columns:
        return df.sort_values(by="started_at", ascending=not newest_first).reset_index(
            drop=True
        )
    if {"call_date", "call_time"}.issubset(df.columns):
        return df.sort_values(by=["call_date", "call_time"], ascending=not newest_first).reset_index(
            drop=True
        )
    return df


def build_calls_display_dataframe(
    df: pd.DataFrame,
    *,
    t_fn: TranslateFn,
    is_admin: bool,
    latency_column_keys: list[str],
    include_transcript_preview: bool = True,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    columns: list[tuple[str, str]] = [
        ("call_date", t_fn("col_date")),
        ("call_time", t_fn("col_time")),
        ("caller_number", t_fn("col_caller")),
        ("_audio_label", t_fn("col_audio")),
        ("_status_badge", t_fn("col_status")),
        ("_issue_badge", t_fn("result_action")),
        ("statut_rdv", t_fn("col_appointment_status")),
        ("_detail", t_fn("detail")),
        ("appointment_start", t_fn("col_appointment_start")),
        ("appointment_name", t_fn("col_appointment_name")),
        ("duration_formatted", t_fn("col_duration")),
    ]
    if is_admin:
        for key in latency_column_keys:
            if key in df.columns:
                columns.append((key, key))
    if include_transcript_preview and "_transcript_preview" in df.columns:
        columns.append(("_transcript_preview", t_fn("col_transcript_preview")))

    data: dict[str, Any] = {}
    for source, label in columns:
        if source in df.columns:
            data[label] = df[source]

    display = pd.DataFrame(data)
    appt_status_col = t_fn("col_appointment_status")
    if appt_status_col in display.columns:
        display[appt_status_col] = display[appt_status_col].fillna("—")
    if "appointment_start" in df.columns:
        appt_col = t_fn("col_appointment_start")
        if appt_col in display.columns:
            display[appt_col] = pd.to_datetime(
                display[appt_col], errors="coerce"
            ).dt.strftime("%Y-%m-%d %H:%M")
            display[appt_col] = display[appt_col].fillna("—")
    return display


def calls_table_column_config(
    df_display: pd.DataFrame,
    *,
    t_fn: TranslateFn,
) -> dict[str, st.column_config.Column]:
    config: dict[str, st.column_config.Column] = {}
    widths = {
        t_fn("col_date"): 110,
        t_fn("col_time"): 70,
        t_fn("col_caller"): 140,
        t_fn("col_audio"): 60,
        t_fn("col_status"): 120,
        t_fn("result_action"): 100,
        t_fn("col_appointment_status"): 120,
        t_fn("detail"): 220,
        t_fn("col_appointment_start"): 140,
        t_fn("col_appointment_name"): 140,
        t_fn("col_duration"): 90,
        t_fn("col_transcript_preview"): 260,
    }
    for column, width in widths.items():
        if column in df_display.columns:
            config[column] = st.column_config.TextColumn(column, width=width)
    return config


def strip_internal_call_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [col for col in INTERNAL_DISPLAY_COLUMNS if col in df.columns]
    if not drop_cols:
        return df
    return df.drop(columns=drop_cols)


def render_calls_filters(
    *,
    t_fn: TranslateFn,
    key_prefix: str,
) -> tuple[str, str, str]:
    col_period, col_status, col_issue = st.columns(3)
    with col_period:
        period = st.selectbox(
            t_fn("filter_period"),
            options=list(PERIOD_FILTER_OPTIONS),
            format_func=lambda value: t_fn(f"filter_period_{value}"),
            key=f"{key_prefix}_period",
        )
    with col_status:
        status = st.selectbox(
            t_fn("filter_status"),
            options=list(STATUS_FILTER_OPTIONS),
            format_func=lambda value: t_fn(f"filter_status_{value}"),
            key=f"{key_prefix}_status",
        )
    with col_issue:
        issue = st.selectbox(
            t_fn("filter_issue"),
            options=list(ISSUE_FILTER_OPTIONS),
            format_func=lambda value: t_fn(f"filter_issue_{value}"),
            key=f"{key_prefix}_issue",
        )
    return period, status, issue


def render_calls_dataframe(
    df_display: pd.DataFrame,
    *,
    t_fn: TranslateFn,
    selection_key: str,
    enable_selection: bool = True,
):
    if df_display.empty:
        st.info(t_fn("no_calls_match_filters"))
        return None

    kwargs: dict[str, Any] = {
        "use_container_width": True,
        "hide_index": True,
        "column_config": calls_table_column_config(df_display, t_fn=t_fn),
    }
    if enable_selection:
        kwargs.update(
            on_select="rerun",
            selection_mode="single-row",
            key=selection_key,
        )
    return st.dataframe(df_display, **kwargs)


def render_call_detail_panel(
    row: pd.Series,
    *,
    t_fn: TranslateFn,
    is_admin: bool,
    render_metrics: Callable[..., None] | None = None,
    render_recording: Callable[[pd.Series], None] | None = None,
) -> None:
    st.divider()
    st.subheader(
        t_fn(
            "call_detail",
            date=row.get("call_date"),
            time=row.get("call_time"),
            caller=row.get("caller_number"),
        )
    )
    st.markdown(
        f"**{t_fn('col_status')}** : {status_badge_label(row.get('status'), t_fn)}"
    )
    st.markdown(
        f"**{t_fn('result_action')}** : "
        f"{issue_badge_label(call_issue_type(row), t_fn)}"
    )
    st.markdown(
        f"**{t_fn('appointment_status')}** : {row.get('statut_rdv', '—')}"
    )
    st.markdown(f"**{t_fn('detail')}** : {call_detail_text(row)}")

    if render_metrics is not None:
        render_metrics(row, is_admin=is_admin)

    if render_recording is not None:
        render_recording(row)

    st.subheader(t_fn("transcript_full"))
    transcript = row.get("transcript", "")
    if transcript and str(transcript).strip():
        st.text_area(
            t_fn("transcript_full"),
            str(transcript),
            height=380,
            label_visibility="collapsed",
        )
    else:
        st.info(t_fn("no_transcript"))