"""Call history page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app_context import AppContext
from ui.calls_table import (
    build_calls_display_dataframe,
    filter_calls_dataframe,
    prepare_calls_table_dataframe,
    render_call_detail_panel,
    render_calls_dataframe,
    render_calls_filters,
    strip_internal_call_columns,
)
from ui.metrics_display import (
    add_latency_cost_display_columns,
    latency_cost_column_keys,
    render_call_metrics_detail,
    render_call_recording,
    strip_latency_cost_raw_columns,
)


def render_calls_page(ctx: AppContext) -> None:
    t = ctx.t_fn
    client_id = ctx.selected_client_id

    st.subheader(t("calls_history", client_id=client_id))

    appels_response = (
        ctx.supabase.table("vw_appels_clients")
        .select("*")
        .eq("client_id", client_id)
        .order("started_at", desc=True)
        .limit(500)
        .execute()
    )

    if not appels_response.data:
        st.info(t("no_calls_yet"))
        return

    df = pd.DataFrame(appels_response.data)
    if ctx.is_admin:
        df = add_latency_cost_display_columns(df, t_fn=t)
    df = prepare_calls_table_dataframe(df, t_fn=t, client_tz=ctx.client_tz)

    period, status_filter, issue_filter = render_calls_filters(
        t_fn=t,
        key_prefix=f"calls_{client_id}",
    )
    df = filter_calls_dataframe(
        df,
        period_days=period,
        status_filter=status_filter,
        issue_filter=issue_filter,
    )

    st.caption(t("calls_click_hint"))
    df_display = build_calls_display_dataframe(
        df,
        t_fn=t,
        is_admin=ctx.is_admin,
        latency_column_keys=latency_cost_column_keys(t),
        include_transcript_preview=True,
    )
    event = render_calls_dataframe(
        df_display,
        t_fn=t,
        selection_key=f"call_table_{client_id}",
    )

    csv_df = strip_internal_call_columns(df)
    csv_df = strip_latency_cost_raw_columns(csv_df) if not ctx.is_admin else csv_df
    csv = csv_df.to_csv(index=False).encode("utf-8")
    st.download_button(t("download_csv"), csv, f"appels_{client_id}.csv", "text/csv")

    if event is not None and event.selection.rows:
        row = df.iloc[event.selection.rows[0]]
        render_call_detail_panel(
            row,
            t_fn=t,
            is_admin=ctx.is_admin,
            render_metrics=lambda r, is_admin: render_call_metrics_detail(
                r, t_fn=t, is_admin=is_admin
            ),
            render_recording=lambda r: render_call_recording(r, t_fn=t),
        )
    elif not df_display.empty:
        st.info(t("select_row"))