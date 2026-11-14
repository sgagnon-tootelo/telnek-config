"""Global admin dashboard page."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from app_context import AppContext
from call_metrics import aggregate_call_metrics
from dashboard_data import format_call_moment, live_duration, period_start, summarize_calls
from i18n import get_ui_lang
from ui.metrics_display import render_client_stats_kpis

_CALL_COLUMNS = (
    "client_id, company_name, status, duration_seconds, "
    "appointment_booked, appointment_confirmed, appointment_cancelled, "
    "transfer_attempted, transfer_success, message_taken, "
    "estimated_cost_usd, latency_metrics, started_at"
)


def render_dashboard_page(ctx: AppContext) -> None:
    t = ctx.t_fn
    st.subheader(t("global_dashboard"))

    auto_refresh = st.toggle(t("auto_refresh"), value=True, key="global_refresh_top")
    if auto_refresh:
        _render_live_calls_auto(ctx)
    else:
        _render_live_calls(ctx)

    st.divider()
    period = st.radio(
        t("period_label"),
        options=["today", "7d", "all"],
        index=2,
        format_func=lambda key: t(f"period_{key}"),
        horizontal=True,
        key="global_period",
    )
    start = period_start(period, datetime.now(timezone.utc))
    _render_last_call(ctx, start)
    st.divider()
    st.subheader(t("cumulative_stats"))
    _render_period_stats(ctx, start)


@st.fragment(run_every=timedelta(seconds=5))
def _render_live_calls_auto(ctx: AppContext) -> None:
    _render_live_calls(ctx)


def _render_live_calls(ctx: AppContext) -> None:
    t = ctx.t_fn
    response = (
        ctx.supabase.table("vw_appels_clients")
        .select(
            "client_id, company_name, call_date, call_time, caller_number, started_at"
        )
        .eq("status", "in_progress")
        .gte("started_at", (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat())
        .order("started_at", desc=True)
        .execute()
    )
    rows = response.data or []
    st.metric(t("live_calls_total"), len(rows))
    if not rows:
        st.info(t("live_calls_none"))
        return

    now = datetime.now(timezone.utc)
    frame = pd.DataFrame(rows)
    started = pd.to_datetime(frame["started_at"], utc=True)
    labels = [
        live_duration(value.to_pydatetime(), now) for value in started
    ]
    frame[t("col_duration")] = [
        t("less_than_minute") if kind == "short" else t("duration_live", duration=kind)
        for kind, _long in labels
    ]
    frame["_long"] = [is_long for _kind, is_long in labels]
    display = frame.rename(
        columns={
            "company_name": t("col_client"),
            "call_date": t("col_date"),
            "call_time": t("col_time"),
            "caller_number": t("col_caller"),
        }
    )[
        [
            t("col_client"),
            t("col_date"),
            t("col_time"),
            t("col_caller"),
            t("col_duration"),
            "_long",
        ]
    ].reset_index(drop=True)
    flags = display["_long"].tolist()
    visible = display.drop(columns=["_long"])

    def _paint(row: pd.Series) -> list[str]:
        color = "background-color: #d4edda" if flags[row.name] else ""
        return [color] * len(row)

    st.dataframe(
        visible.style.apply(_paint, axis=1),
        use_container_width=True,
        hide_index=True,
    )


def _render_last_call(ctx: AppContext, start: datetime | None) -> None:
    t = ctx.t_fn
    st.subheader(t("last_call_global"))
    query = (
        ctx.supabase.table("vw_appels_clients")
        .select("started_at, company_name, caller_number, status_label")
        .order("started_at", desc=True)
        .limit(1)
    )
    if start is not None:
        query = query.gte("started_at", start.isoformat())
    response = query.execute()
    if not response.data:
        st.info(t("no_calls_yet"))
        return
    last = response.data[0]
    moment = pd.to_datetime(last["started_at"], utc=True).to_pydatetime()
    lang = get_ui_lang(st.session_state)
    st.metric(
        label=t("last_call_metric"),
        value=format_call_moment(moment, lang),
        delta=f"{last.get('company_name') or '—'} • {last.get('caller_number') or '—'}",
    )
    st.caption(f"**{t('status')} :** {last.get('status_label') or '—'}")


def _fetch_period_calls(ctx: AppContext, start: datetime | None) -> list[dict]:
    """Page through the view so totals are not cut at the API row limit."""
    page_size = 1000
    offset = 0
    rows: list[dict] = []
    while True:
        query = (
            ctx.supabase.table("vw_appels_clients")
            .select(_CALL_COLUMNS)
            .order("started_at")
        )
        if start is not None:
            query = query.gte("started_at", start.isoformat())
        batch = query.range(offset, offset + page_size - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        offset += page_size


def _render_period_stats(ctx: AppContext, start: datetime | None) -> None:
    t = ctx.t_fn
    frame = pd.DataFrame(_fetch_period_calls(ctx, start))
    summary = summarize_calls(frame)
    if summary["total"] == 0:
        st.info(t("no_stats"))
        return

    total = summary["total"]
    booked = summary["booked"]
    confirmed = summary["confirmed"]
    cancelled = summary["cancelled"]
    abandoned = summary["abandoned"]
    transferred = summary["transferred"]
    pourcent_rdv = (booked / total * 100) if total else 0.0
    taux_abandon = (abandoned / total * 100) if total else 0.0
    taux_confirmation = (
        confirmed / (confirmed + cancelled) * 100 if (confirmed + cancelled) else 0.0
    )
    metrics_summary = aggregate_call_metrics(frame) if ctx.is_admin else None
    render_client_stats_kpis(
        t_fn=t,
        total=total,
        completes=summary["completed"],
        booked=booked,
        confirmed=confirmed,
        cancelled=cancelled,
        duree_moy=summary["avg_duration_s"],
        pourcent_rdv=pourcent_rdv,
        appels_abandonnes=abandoned,
        taux_abandon=taux_abandon,
        taux_confirmation=taux_confirmation,
        transferred=transferred,
        transferred_success=summary["transferred_success"],
        messages_pris=summary["messages"],
        metrics_summary=metrics_summary,
        is_admin=ctx.is_admin,
    )

    clients = summary["clients"].rename(
        columns={
            "company_name": t("col_client"),
            "total": t("col_total"),
            "completed": t("col_completed"),
            "abandoned": t("col_abandoned"),
            "booked": t("col_appointments"),
            "transferred": t("col_transfers"),
            "messages": t("col_messages"),
            "avg_duration_s": t("col_avg_sec"),
        }
    )
    show = [
        t("col_client"),
        t("col_total"),
        t("col_completed"),
        t("col_abandoned"),
        t("col_appointments"),
        t("col_transfers"),
        t("col_messages"),
        t("col_avg_sec"),
    ]
    table = clients[show].copy()
    table.loc[len(table)] = [
        t("col_total_row"),
        total,
        summary["completed"],
        abandoned,
        booked,
        transferred,
        summary["messages"],
        summary["avg_duration_s"],
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)
