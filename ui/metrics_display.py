"""Call metrics formatting and KPI rendering helpers."""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from call_metrics import (
    aggregate_call_metrics,
    appointment_count,
    breakdown_line_items,
    enrich_calls_dataframe,
    has_latency_metrics,
    latency_assistant_turns,
    latency_e2e_avg,
    latency_playback_avg,
    latency_transcription_avg,
    latency_user_turns,
    notification_email_count,
    notification_sms_count,
    pricing_mode,
    cost_per_second,
    cost_usd,
)
from ui.components import render_kpi_group

LATENCY_COST_RAW_COLUMNS = ("latency_metrics", "estimated_cost_usd", "cost_breakdown")


def format_seconds(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"{float(value):.2f} s"
    except (TypeError, ValueError):
        return "—"


def format_usd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return f"${float(value):.4f}"
    except (TypeError, ValueError):
        return "—"


def latency_cost_column_keys(t_fn) -> list[str]:
    return [
        t_fn("col_e2e_latency"),
        t_fn("col_transcription_delay"),
        t_fn("col_estimated_cost"),
        t_fn("col_pricing_mode"),
    ]


def strip_latency_cost_raw_columns(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [col for col in LATENCY_COST_RAW_COLUMNS if col in df.columns]
    if not drop_cols:
        return df
    return df.drop(columns=drop_cols)


def add_latency_cost_display_columns(df: pd.DataFrame, *, t_fn) -> pd.DataFrame:
    enriched = enrich_calls_dataframe(df)
    enriched[t_fn("col_e2e_latency")] = enriched["_primary_latency_avg"].map(format_seconds)
    enriched[t_fn("col_transcription_delay")] = enriched["_transcription_delay_avg"].map(
        format_seconds
    )
    enriched[t_fn("col_estimated_cost")] = enriched["_estimated_cost_usd"].map(format_usd)
    enriched[t_fn("col_pricing_mode")] = enriched["_pricing_mode"].fillna("—")
    return enriched


def render_global_cumulative_kpis(
    *,
    t_fn,
    total_appels: int,
    completes: int,
    rdv_reserves: int,
    duree_moyenne: float,
    appels_abandonnes: int,
    rdv_confirmes: int,
    rdv_annules: int,
) -> None:
    render_kpi_group(
        t_fn("kpi_group_volume"),
        [
            (t_fn("metric_total"), total_appels, None),
            (t_fn("metric_completed"), completes, None),
            (t_fn("metric_abandoned"), appels_abandonnes, None),
            (t_fn("metric_avg_duration"), f"{duree_moyenne} s", None),
        ],
    )
    render_kpi_group(
        t_fn("kpi_group_appointments"),
        [
            (t_fn("metric_appointments"), rdv_reserves, None),
            (t_fn("metric_confirmed"), rdv_confirmes, None),
            (t_fn("metric_cancelled"), rdv_annules, None),
        ],
    )


def render_client_stats_kpis(
    *,
    t_fn,
    total: int,
    completes: int,
    booked: int,
    confirmed: int,
    cancelled: int,
    duree_moy: float,
    pourcent_rdv: float,
    appels_abandonnes: int,
    taux_abandon: float,
    taux_confirmation: float,
    transferred: int,
    transferred_success: int,
    messages_pris: int,
    metrics_summary: dict | None,
    is_admin: bool,
) -> None:
    render_kpi_group(
        t_fn("kpi_group_volume"),
        [
            (t_fn("metric_total"), total, None),
            (t_fn("metric_completed"), completes, None),
            (
                t_fn("metric_abandoned"),
                appels_abandonnes,
                f"{taux_abandon:.1f}%",
            ),
            (t_fn("metric_avg_duration"), f"{duree_moy:.1f} s", None),
        ],
    )
    render_kpi_group(
        t_fn("kpi_group_appointments"),
        [
            (t_fn("metric_appointments"), booked, f"{pourcent_rdv:.1f}%"),
            (t_fn("metric_confirmed_short"), confirmed, None),
            (t_fn("metric_cancelled_short"), cancelled, None),
            (t_fn("metric_confirm_rate"), f"{taux_confirmation:.1f}%", None),
        ],
    )
    transfer_rate = (
        (transferred_success / transferred * 100) if transferred > 0 else 0.0
    )
    render_kpi_group(
        t_fn("kpi_group_operations"),
        [
            (t_fn("metric_transfers_tried"), transferred, None),
            (
                t_fn("metric_transfers_ok"),
                transferred_success,
                f"{transfer_rate:.1f}%",
            ),
            (t_fn("metric_messages"), messages_pris, None),
            (
                t_fn("metric_normal"),
                total - transferred - messages_pris,
                None,
            ),
        ],
    )

    if is_admin and metrics_summary is not None:
        render_kpi_group(
            t_fn("kpi_group_admin_latency"),
            [
                (
                    t_fn("metric_avg_e2e_latency"),
                    format_seconds(metrics_summary["avg_e2e_latency_s"]),
                    None,
                ),
                (
                    t_fn("metric_avg_transcription_delay"),
                    format_seconds(metrics_summary["avg_transcription_delay_s"]),
                    None,
                ),
                (
                    t_fn("metric_calls_with_latency"),
                    metrics_summary["calls_with_latency"],
                    None,
                ),
            ],
        )
        render_kpi_group(
            t_fn("kpi_group_admin_cost"),
            [
                (
                    t_fn("metric_avg_call_cost"),
                    format_usd(metrics_summary["avg_cost_usd"]),
                    None,
                ),
                (
                    t_fn("metric_total_call_cost"),
                    format_usd(metrics_summary["total_cost_usd"]),
                    None,
                ),
                (
                    t_fn("metric_calls_with_cost"),
                    metrics_summary["calls_with_cost"],
                    None,
                ),
            ],
        )


def render_call_recording(row: pd.Series, *, t_fn) -> None:
    st.subheader(t_fn("recording"))
    recording_url = row.get("recording_url")
    if recording_url and isinstance(recording_url, str) and recording_url.startswith("http"):
        try:
            account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
            auth_token = st.secrets["TWILIO_AUTH_TOKEN"]
            response = requests.get(
                recording_url, auth=(account_sid, auth_token), timeout=15
            )
            if response.status_code == 200:
                audio_bytes = response.content
                st.success(t_fn("recording_ok"))
                st.audio(audio_bytes, format="audio/wav")
                st.download_button(
                    label=t_fn("download_wav"),
                    data=audio_bytes,
                    file_name=(
                        f"appel_{row.get('caller_number', 'inconnu')}_"
                        f"{row.get('call_date', '')}.wav"
                    ),
                    mime="audio/wav",
                )
            else:
                st.error(t_fn("recording_denied", code=response.status_code))
        except Exception as e:
            st.error(t_fn("recording_error", error=str(e)))
    else:
        st.info(t_fn("no_recording"))


def _format_notification_count(value: int | None) -> str | int:
    return value if value is not None else "—"


def render_call_notifications_detail(row: pd.Series, *, t_fn) -> None:
    sms = notification_sms_count(row.get("cost_breakdown"))
    emails = notification_email_count(row.get("cost_breakdown"))
    appointments = appointment_count(row)

    st.subheader(t_fn("notifications_section"))
    col_n1, col_n2, col_n3 = st.columns(3)
    with col_n1:
        st.metric(t_fn("metric_sms_sent"), _format_notification_count(sms))
    with col_n2:
        st.metric(t_fn("metric_emails_sent"), _format_notification_count(emails))
    with col_n3:
        st.metric(t_fn("metric_appointments_booked"), appointments)


def render_call_metrics_detail(row: pd.Series, *, t_fn, is_admin: bool) -> None:
    render_call_notifications_detail(row, t_fn=t_fn)
    if not is_admin:
        return
    latency_raw = row.get("latency_metrics")
    e2e = latency_e2e_avg(latency_raw)
    playback = latency_playback_avg(latency_raw)
    transcription = latency_transcription_avg(latency_raw)
    user_turns = latency_user_turns(latency_raw)
    assistant_turns = latency_assistant_turns(latency_raw)

    st.subheader(t_fn("latency_section"))
    if not has_latency_metrics(latency_raw):
        st.info(t_fn("no_latency_data"))
    else:
        col_l1, col_l2, col_l3, col_l4 = st.columns(4)
        with col_l1:
            st.metric(t_fn("latency_e2e"), format_seconds(e2e))
        with col_l2:
            st.metric(t_fn("latency_playback"), format_seconds(playback))
        with col_l3:
            st.metric(t_fn("latency_transcription"), format_seconds(transcription))
        with col_l4:
            st.metric(
                t_fn("latency_user_turns"),
                user_turns if user_turns is not None else "—",
            )
        if assistant_turns is not None:
            st.caption(f"{t_fn('latency_assistant_turns')} : **{assistant_turns}**")
        if e2e is None and playback is not None:
            st.caption(t_fn("latency_playback_only_hint"))

    estimated = cost_usd(row.get("estimated_cost_usd"))
    mode = pricing_mode(row.get("cost_breakdown"))
    per_second = cost_per_second(row.get("cost_breakdown"))

    st.subheader(t_fn("cost_section"))
    if estimated is None:
        st.info(t_fn("no_cost_data"))
    else:
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.metric(t_fn("cost_total"), format_usd(estimated))
        with col_c2:
            st.metric(t_fn("cost_per_second"), format_usd(per_second))
        with col_c3:
            st.metric(t_fn("cost_mode"), mode or "—")

        items = breakdown_line_items(row.get("cost_breakdown"))
        if items:
            st.markdown(f"**{t_fn('cost_breakdown')}**")
            st.dataframe(
                pd.DataFrame(items),
                use_container_width=True,
                hide_index=True,
            )


__all__ = [
    "LATENCY_COST_RAW_COLUMNS",
    "add_latency_cost_display_columns",
    "aggregate_call_metrics",
    "latency_cost_column_keys",
    "render_call_notifications_detail",
    "render_call_metrics_detail",
    "render_call_recording",
    "render_client_stats_kpis",
    "render_global_cumulative_kpis",
    "strip_latency_cost_raw_columns",
]