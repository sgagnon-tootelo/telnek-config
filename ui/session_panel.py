"""Account password change form (rendered in main content, not sidebar)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from auth_password import change_password, validate_password_fields

PASSWORD_FORM_KEY = "telnek_change_password_form"


def can_change_password(user_email: str | None) -> bool:
    return bool(user_email) and not user_email.endswith("@local.test")


def render_password_change_form(
    *, supabase: Any, t_fn: Callable[..., str], user_email: str
) -> None:
    with st.form(PASSWORD_FORM_KEY, clear_on_submit=True):
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