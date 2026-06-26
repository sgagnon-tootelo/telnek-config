"""Account actions — email reset only (no password inputs in Streamlit)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from auth_password import request_password_reset

PASSWORD_RESET_BUTTON_KEY = "telnek_btn_password_reset"


def can_change_password(user_email: str | None) -> bool:
    return bool(user_email) and not user_email.endswith("@local.test")


def render_password_reset_request(
    *,
    supabase: Any,
    t_fn: Callable[..., str],
    user_email: str,
    redirect_to: str,
) -> None:
    st.caption(t_fn("password_reset_caption"))
    if st.button(
        t_fn("password_reset_send"),
        key=PASSWORD_RESET_BUTTON_KEY,
        type="primary",
        use_container_width=True,
    ):
        error_code, detail = request_password_reset(
            supabase,
            email=user_email,
            redirect_to=redirect_to,
        )
        if error_code:
            if detail:
                st.error(t_fn(error_code, error=detail))
            else:
                st.error(t_fn(error_code))
            return
        st.success(t_fn("password_reset_sent"))