"""Account page — session info and password change."""

from __future__ import annotations

import streamlit as st

from app_context import AppContext
from ui.session_panel import can_change_password, render_password_change_form


def render_account_page(ctx: AppContext) -> None:
    t = ctx.t_fn
    user_email = st.session_state.get("user_email", "—")
    role = st.session_state.get("user_role", "—")
    role_emoji = "🛡️" if role == "admin" else "👤"

    st.markdown(f"## {t('account_title')}")
    st.caption(t("account_caption"))

    st.markdown(f"**{user_email}**")
    st.markdown(f"{t('role')} : {role_emoji} **{role}**")
    if st.session_state.get("user_client_id"):
        st.caption(f"{t('restricted_client')} : `{st.session_state['user_client_id']}`")

    st.divider()
    st.markdown(f"### {t('password_change_title')}")

    if not can_change_password(user_email):
        st.info(t("password_change_dev_unavailable"))
        return

    render_password_change_form(
        supabase=ctx.supabase,
        t_fn=t,
        user_email=user_email,
    )