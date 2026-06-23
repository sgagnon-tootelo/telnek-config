"""Global admin dashboard page."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytz
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app_context import AppContext
from ui.metrics_display import render_global_cumulative_kpis


def render_dashboard_page(ctx: AppContext) -> None:
    t = ctx.t_fn

    st.subheader(t("global_dashboard"))

    auto_refresh = st.toggle(t("auto_refresh"), value=True, key="global_refresh_top")
    if auto_refresh:
        st_autorefresh(interval=5000, limit=300, key="global_auto_top_level")

    live_response = (
        ctx.supabase.table("vw_appels_clients")
        .select(
            "client_id, company_name, call_date, call_time, caller_number, "
            "room_name, status_label, started_at"
        )
        .eq("status", "in_progress")
        .gte("started_at", (datetime.now(pytz.utc) - timedelta(minutes=90)).isoformat())
        .order("started_at", desc=True)
        .execute()
    )

    if live_response.data:
        df_global = pd.DataFrame(live_response.data)
        tz_montreal = pytz.timezone("America/Montreal")
        now = datetime.now(tz_montreal)

        df_global["started_at"] = pd.to_datetime(df_global["started_at"])
        if df_global["started_at"].dt.tz is None:
            df_global["started_at"] = df_global["started_at"].dt.tz_localize("UTC")
        df_global["started_at"] = df_global["started_at"].dt.tz_convert(tz_montreal)

        df_global["Durée en cours"] = df_global["started_at"].apply(
            lambda x: t("duration_live", duration=str(now - x).split(".")[0])
            if (now - x).total_seconds() > 60
            else t("less_than_minute")
        )

        display_cols = [
            "company_name",
            "call_date",
            "call_time",
            "caller_number",
            "Durée en cours",
            "room_name",
        ]
        styled = df_global[display_cols].style.apply(
            lambda row: ["background-color: #d4edda"] * len(row)
            if "min" in str(row["Durée en cours"])
            else [""] * len(row),
            axis=1,
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.metric(t("live_calls_total"), len(df_global))
    else:
        st.success(t("live_calls_none"))

    st.divider()
    st.subheader(t("last_call_global"))

    latest_response = (
        ctx.supabase.table("vw_appels_clients")
        .select("started_at, company_name, caller_number, status_label")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    if latest_response.data:
        last = latest_response.data[0]
        tz_montreal = pytz.timezone("America/Montreal")
        last_time = pd.to_datetime(last["started_at"])
        if last_time.tz is None:
            last_time = last_time.tz_localize("UTC")
        last_time = last_time.tz_convert(tz_montreal)
        formatted_time = last_time.strftime("%d %B %Y à %H:%M:%S")
        st.metric(
            label=t("last_call_metric"),
            value=formatted_time,
            delta=f"{last.get('company_name', 'Inconnu')} • {last.get('caller_number', 'N/A')}",
        )
        st.caption(f"**{t('status')} :** {last.get('status_label', '—')}")
    else:
        st.info(t("no_calls_yet"))

    st.divider()
    st.subheader(t("cumulative_stats"))

    stats_response = ctx.supabase.table("vw_stats_appels_clients").select("*").execute()
    if stats_response.data:
        df_stats = pd.DataFrame(stats_response.data)
        clients_list = ctx.get_clients()
        client_map = {c["id"]: c.get("company_name", c["id"]) for c in clients_list}
        df_stats["company_name"] = df_stats["client_id"].map(client_map).fillna("Inconnu")

        total_appels = int(df_stats["total_appels"].sum())
        completes = int(df_stats["appels_completes"].sum())
        rdv_reserves = int(df_stats["rdv_reserves"].sum())
        duree_moyenne = round(df_stats["duree_moyenne_sec"].mean(), 1) if not df_stats.empty else 0

        abandoned_resp = (
            ctx.supabase.table("vw_appels_clients")
            .select("*", count="exact")
            .eq("status", "abandoned")
            .execute()
        )
        confirmed_resp = (
            ctx.supabase.table("vw_appels_clients")
            .select("*", count="exact")
            .eq("appointment_confirmed", True)
            .execute()
        )
        cancelled_resp = (
            ctx.supabase.table("vw_appels_clients")
            .select("*", count="exact")
            .eq("appointment_cancelled", True)
            .execute()
        )

        render_global_cumulative_kpis(
            t_fn=t,
            total_appels=total_appels,
            completes=completes,
            rdv_reserves=rdv_reserves,
            duree_moyenne=duree_moyenne,
            appels_abandonnes=abandoned_resp.count or 0,
            rdv_confirmes=confirmed_resp.count or 0,
            rdv_annules=cancelled_resp.count or 0,
        )

        df_stats_display = df_stats[
            ["company_name", "total_appels", "appels_completes", "rdv_reserves", "duree_moyenne_sec"]
        ].copy()
        df_stats_display = df_stats_display.rename(
            columns={
                "company_name": t("col_client"),
                "total_appels": t("col_total"),
                "appels_completes": t("col_completed"),
                "rdv_reserves": t("col_appointments"),
                "duree_moyenne_sec": t("col_avg_sec"),
            }
        )
        df_stats_display.loc[len(df_stats_display)] = [
            t("col_total_row"),
            total_appels,
            completes,
            rdv_reserves,
            duree_moyenne,
        ]
        st.dataframe(
            df_stats_display.style.set_properties(subset=[t("col_client")], **{"font-weight": "bold"}),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(t("no_stats"))