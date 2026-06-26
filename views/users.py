"""Admin user management page (profiles table)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app_context import AppContext
from profiles_store import fetch_profiles, profiles_to_editor_rows, save_profiles

EDITOR_COLUMNS = ["id", "email", "role", "client_id", "created_at"]


def _editor_column_config(t, *, client_ids: list[str]) -> dict[str, Any]:
    return {
        "id": st.column_config.TextColumn(
            t("users_col_id"),
            help=t("users_col_id_help"),
            width="medium",
        ),
        "email": st.column_config.TextColumn(
            t("users_col_email"),
            required=True,
            width="medium",
        ),
        "role": st.column_config.SelectboxColumn(
            t("users_col_role"),
            options=["admin", "client"],
            required=True,
            width="small",
        ),
        "client_id": st.column_config.SelectboxColumn(
            t("users_col_client"),
            options=[""] + client_ids,
            width="medium",
            help=t("users_col_client_help"),
        ),
        "created_at": st.column_config.TextColumn(
            t("users_col_created"),
            disabled=True,
            width="medium",
        ),
    }


def render_users_page(ctx: AppContext) -> None:
    t = ctx.t_fn
    if not ctx.is_admin:
        st.error(t("users_admin_only"))
        return

    st.subheader(t("users_title"))
    st.caption(t("users_caption"))

    client_ids = sorted(c.get("id", "") for c in ctx.get_clients() if c.get("id"))
    valid_client_ids = set(client_ids)

    try:
        profiles = fetch_profiles(ctx.supabase)
    except Exception as exc:
        st.error(t("users_load_error", error=exc))
        return

    rows = profiles_to_editor_rows(profiles)
    df = pd.DataFrame(rows, columns=EDITOR_COLUMNS) if rows else pd.DataFrame(columns=EDITOR_COLUMNS)

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=_editor_column_config(t, client_ids=client_ids),
        key="profiles_editor",
    )

    profile = st.session_state.get("profile") or {}
    current_user_id = str(profile.get("id") or "")

    if st.button(t("users_save"), type="primary", key="save_profiles"):
        try:
            editor_rows = edited_df.fillna("").to_dict(orient="records")
            existing_ids = {str(p.get("id")) for p in profiles if p.get("id")}
            kept_ids = {str(r.get("id")).strip() for r in editor_rows if str(r.get("id")).strip()}

            if current_user_id and current_user_id not in kept_ids:
                st.error(t("users_error_cannot_delete_self"))
                return

            for row in editor_rows:
                row_id = str(row.get("id")).strip()
                if row_id == current_user_id and str(row.get("role")).lower() != "admin":
                    st.error(t("users_error_cannot_demote_self"))
                    return

            count = save_profiles(
                ctx.supabase,
                editor_rows,
                existing_ids=existing_ids,
                valid_client_ids=valid_client_ids,
            )
            st.success(t("users_save_ok", count=count))
            st.rerun()
        except ValueError as exc:
            code = str(exc)
            error_key = {
                "id_invalid": "users_error_id_invalid",
                "email_required": "users_error_email_required",
                "role_invalid": "users_error_role_invalid",
                "client_id_required": "users_error_client_required",
                "client_id_invalid": "users_error_client_invalid",
            }.get(code, "users_error_generic")
            st.error(t(error_key, error=code))
        except Exception as exc:
            st.error(t("users_error_generic", error=exc))

    with st.expander(t("users_help_title"), expanded=False):
        st.markdown(t("users_help_body"))