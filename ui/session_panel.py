"""Sidebar session panel (password change + account info)."""

from __future__ import annotations

import streamlit as st

from auth_password import change_password, validate_password_fields


def render_password_change_form(*, supabase, t_fn, user_email: str) -> None:
    if not user_email or user_email.endswith("@local.test"):
        st.caption(t_fn("password_change_dev_unavailable"))
        return

    with st.expander(t_fn("password_change_title"), expanded=False):
        with st.form("change_password_form", clear_on_submit=True):
            current_password = st.text_input(
                t_fn("password_current"),
                type="password",
                autocomplete="current-password",
            )
            new_password = st.text_input(
                t_fn("password_new"),
                type="password",
                autocomplete="new-password",
            )
            confirm_password = st.text_input(
                t_fn("password_confirm"),
                type="password",
                autocomplete="new-password",
            )
            submitted = st.form_submit_button(
                t_fn("password_change_submit"),
                use_container_width=True,
            )

        if not submitted:
            return

        error_code = validate_password_fields(
            current_password=current_password,
            new_password=new_password,
            confirm_password=confirm_password,
        )
        if error_code:
            st.error(t_fn(error_code))
            return

        error_code, detail = change_password(
            supabase,
            email=user_email,
            current_password=current_password,
            new_password=new_password,
        )
        if error_code:
            if error_code == "password_update_failed" and detail:
                st.error(t_fn(error_code, error=detail))
            else:
                st.error(t_fn(error_code))
            return

        st.success(t_fn("password_change_ok"))