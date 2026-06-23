"""Reusable Streamlit UI components for Telnek dashboards."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from ui.theme import apply_brand_plotly, brand_color_sequence

KpiMetric = tuple[str, Any, str | None]


def app_header_html(*, subtitle: str, logo_data_uri: str) -> str:
    """Single-block app header markup (avoids Streamlit column layout overlap)."""
    safe_subtitle = escape(subtitle)
    return (
        f'<div class="telnek-app-header-shell">'
        f'<img class="telnek-app-header-logo" src="{logo_data_uri}" alt="Telnek" />'
        f'<div class="telnek-brand-subtitle telnek-brand-subtitle--app">'
        f"{safe_subtitle}</div></div>"
        f'<div class="telnek-app-header-rule"></div>'
    )


def render_kpi_group(title: str, metrics: list[KpiMetric]) -> None:
    """Render a bordered group of KPI metrics (label, value, optional delta)."""
    if not metrics:
        return
    with st.container(border=True):
        st.markdown(f"**{title}**")
        cols = st.columns(len(metrics))
        for col, (label, value, delta) in zip(cols, metrics, strict=True):
            with col:
                if delta is not None:
                    st.metric(label, value, delta=delta)
                else:
                    st.metric(label, value)


def render_branded_plotly_chart(fig) -> None:
    """Apply Telnek Plotly styling and render the figure."""
    apply_brand_plotly(fig)
    st.plotly_chart(fig, use_container_width=True)


def pie_chart_colors(count: int) -> list[str]:
    return brand_color_sequence(count)