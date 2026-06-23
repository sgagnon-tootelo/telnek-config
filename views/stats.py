"""Client statistics page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_context import AppContext
from call_metrics import aggregate_call_metrics
from ui.calls_table import (
    build_calls_display_dataframe,
    filter_calls_dataframe,
    prepare_calls_table_dataframe,
    render_calls_dataframe,
    render_calls_filters,
    sort_calls_dataframe,
    strip_internal_call_columns,
)
from ui.components import pie_chart_colors, render_branded_plotly_chart
from ui.metrics_display import (
    add_latency_cost_display_columns,
    latency_cost_column_keys,
    render_client_stats_kpis,
    strip_latency_cost_raw_columns,
)


def render_stats_page(ctx: AppContext) -> None:
    t = ctx.t_fn
    client_id = ctx.selected_client_id

    st.subheader(t("stats_for", client_id=client_id))

    stats_response = (
        ctx.supabase.table("vw_stats_appels_clients")
        .select("*")
        .eq("client_id", client_id)
        .execute()
    )

    if not stats_response.data:
        st.info(t("no_stats_client"))
        return

    stats_df = pd.DataFrame(stats_response.data).iloc[0]
    total = int(stats_df["total_appels"])
    completes = int(stats_df["appels_completes"])
    booked = int(stats_df["rdv_reserves"])
    confirmed = int(stats_df.get("rdv_confirmes", 0))
    cancelled = int(stats_df.get("rdv_annules", 0))
    duree_moy = float(stats_df["duree_moyenne_sec"])
    pourcent_rdv = float(stats_df["pourcentage_rdv"])

    taux_confirmation = (
        (confirmed / (confirmed + cancelled) * 100) if (confirmed + cancelled) > 0 else 0
    )
    appels_abandonnes = total - completes
    taux_abandon = (appels_abandonnes / total * 100) if total > 0 else 0

    appels_response = (
        ctx.supabase.table("vw_appels_clients")
        .select("*")
        .eq("client_id", client_id)
        .execute()
    )

    transferred = 0
    transferred_success = 0
    messages_pris = 0

    if appels_response.data:
        df_detail = pd.DataFrame(appels_response.data)
        if ctx.is_admin:
            df_detail = add_latency_cost_display_columns(df_detail, t_fn=t)
        transferred = len(df_detail[df_detail["transfer_attempted"] == True])
        transferred_success = len(df_detail[df_detail["transfer_success"] == True])
        messages_pris = len(df_detail[df_detail["message_taken"] == True])
    else:
        df_detail = pd.DataFrame()

    metrics_summary = aggregate_call_metrics(df_detail) if ctx.is_admin else None

    render_client_stats_kpis(
        t_fn=t,
        total=total,
        completes=completes,
        booked=booked,
        confirmed=confirmed,
        cancelled=cancelled,
        duree_moy=duree_moy,
        pourcent_rdv=pourcent_rdv,
        appels_abandonnes=appels_abandonnes,
        taux_abandon=taux_abandon,
        taux_confirmation=taux_confirmation,
        transferred=transferred,
        transferred_success=transferred_success,
        messages_pris=messages_pris,
        metrics_summary=metrics_summary,
        is_admin=ctx.is_admin,
    )

    st.caption(
        t(
            "funnel",
            total=total,
            booked=booked,
            confirmed=confirmed,
            transferred=transferred,
            messages=messages_pris,
        )
    )

    st.divider()
    st.subheader(t("charts"))

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        repartition = pd.DataFrame(
            {
                "Type": [
                    t("chart_pie_normal"),
                    t("chart_pie_transfer"),
                    t("chart_pie_message"),
                ],
                "Nombre": [
                    total - transferred - messages_pris,
                    transferred,
                    messages_pris,
                ],
            }
        )
        fig_pie = px.pie(
            repartition,
            values="Nombre",
            names="Type",
            title=t("chart_pie_title"),
            color_discrete_sequence=pie_chart_colors(3),
        )
        render_branded_plotly_chart(fig_pie)

    with col_g2:
        if appels_response.data and "appointment_reason" in df_detail.columns:
            booked_reasons = df_detail[df_detail["appointment_booked"] == True][
                "appointment_reason"
            ].dropna()
            reasons = booked_reasons.value_counts().head(8)
            if len(reasons) > 0:
                fig_bar = px.bar(
                    x=reasons.index.tolist(),
                    y=reasons.values.tolist(),
                    labels={"x": t("chart_bar_x"), "y": t("chart_bar_y")},
                    title=t("chart_bar_title"),
                    color_discrete_sequence=pie_chart_colors(1),
                )
                render_branded_plotly_chart(fig_bar)
            else:
                st.info(t("no_reasons"))
        else:
            st.info(t("no_reasons_client"))

    if (
        ctx.is_admin
        and metrics_summary is not None
        and not df_detail.empty
        and metrics_summary["calls_with_latency"] > 0
    ):
        recent = df_detail.dropna(subset=["_primary_latency_avg"]).head(30).copy()
        if not recent.empty and "call_date" in recent.columns:
            fig_latency = px.bar(
                recent,
                x="call_date",
                y="_primary_latency_avg",
                labels={
                    "call_date": t("sort_calls"),
                    "_primary_latency_avg": t("latency_primary"),
                },
                title=t("chart_latency_title"),
                color_discrete_sequence=pie_chart_colors(1),
            )
            render_branded_plotly_chart(fig_latency)

    if (
        ctx.is_admin
        and metrics_summary is not None
        and not df_detail.empty
        and metrics_summary["calls_with_cost"] > 0
    ):
        recent_cost = df_detail.dropna(subset=["_estimated_cost_usd"]).head(30).copy()
        if not recent_cost.empty and "call_date" in recent_cost.columns:
            fig_cost = px.bar(
                recent_cost,
                x="call_date",
                y="_estimated_cost_usd",
                labels={
                    "call_date": t("sort_calls"),
                    "_estimated_cost_usd": t("cost_total"),
                },
                title=t("chart_cost_title"),
                color_discrete_sequence=pie_chart_colors(1),
            )
            render_branded_plotly_chart(fig_cost)

    st.divider()
    st.subheader(t("detail_table"))

    df_detail_enriched = prepare_calls_table_dataframe(
        df_detail.copy(),
        t_fn=t,
        client_tz=ctx.client_tz,
    )
    period, status_filter, issue_filter = render_calls_filters(
        t_fn=t,
        key_prefix=f"stats_{client_id}",
    )
    df_detail_enriched = filter_calls_dataframe(
        df_detail_enriched,
        period_days=period,
        status_filter=status_filter,
        issue_filter=issue_filter,
    )

    sort_col, _ = st.columns([1, 3])
    with sort_col:
        sort_option = st.selectbox(
            t("sort_calls"),
            options=[t("sort_newest"), t("sort_oldest")],
            index=0,
            key=f"stats_sort_{client_id}",
        )
    df_sorted = sort_calls_dataframe(
        df_detail_enriched,
        newest_first=sort_option == t("sort_newest"),
    )
    df_display = build_calls_display_dataframe(
        df_sorted,
        t_fn=t,
        is_admin=ctx.is_admin,
        latency_column_keys=latency_cost_column_keys(t),
        include_transcript_preview=False,
    )
    render_calls_dataframe(
        df_display,
        t_fn=t,
        selection_key=f"stats_table_{client_id}",
        enable_selection=False,
    )

    csv_df = strip_internal_call_columns(df_sorted)
    csv_df = strip_latency_cost_raw_columns(csv_df) if not ctx.is_admin else csv_df
    csv = csv_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        t("download_all_csv"),
        csv,
        f"stats_detaillees_{client_id}.csv",
        "text/csv",
    )