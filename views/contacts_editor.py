"""Streamlit editor for client_contacts (phase 2)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app_context import AppContext
from client_contacts_store import (
    build_transfer_numbers,
    contacts_to_editor_rows,
    fetch_client_contacts,
    save_client_contacts,
)

EDITOR_COLUMNS = [
    "id",
    "display_name",
    "slug",
    "contact_type",
    "phone_e164",
    "email",
    "can_transfer",
    "notify_message",
    "notify_rdv",
    "notify_transfer_fail",
    "keywords",
    "priority",
    "active",
]


def _editor_column_config(t) -> dict[str, Any]:
    return {
        "id": st.column_config.TextColumn(t("contacts_col_id"), disabled=True, width="small"),
        "display_name": st.column_config.TextColumn(t("contacts_col_name"), required=True, width="medium"),
        "slug": st.column_config.TextColumn(t("contacts_col_slug"), help=t("contacts_col_slug_help"), width="medium"),
        "contact_type": st.column_config.SelectboxColumn(
            t("contacts_col_type"),
            options=["department", "person"],
            width="small",
        ),
        "phone_e164": st.column_config.TextColumn(
            t("contacts_col_phone"),
            help=t("contacts_col_phone_help"),
            width="medium",
        ),
        "email": st.column_config.TextColumn(t("contacts_col_email"), width="medium"),
        "can_transfer": st.column_config.CheckboxColumn(t("contacts_col_can_transfer"), default=True),
        "notify_message": st.column_config.CheckboxColumn(t("contacts_col_notify_message"), default=False),
        "notify_rdv": st.column_config.CheckboxColumn(t("contacts_col_notify_rdv"), default=False),
        "notify_transfer_fail": st.column_config.CheckboxColumn(
            t("contacts_col_notify_transfer_fail"),
            default=True,
        ),
        "keywords": st.column_config.TextColumn(t("contacts_col_keywords"), width="medium"),
        "priority": st.column_config.NumberColumn(t("contacts_col_priority"), min_value=0, max_value=9999, step=1),
        "active": st.column_config.CheckboxColumn(t("contacts_col_active"), default=True),
    }


def render_contacts_editor(ctx: AppContext, *, transfer_mode: str) -> None:
    t = ctx.t_fn
    client_id = ctx.selected_client_id

    if transfer_mode == "none":
        st.caption(t("contacts_disabled_none"))
        return

    contacts = fetch_client_contacts(ctx.supabase, client_id)
    rows = contacts_to_editor_rows(contacts)
    df = pd.DataFrame(rows, columns=EDITOR_COLUMNS) if rows else pd.DataFrame(columns=EDITOR_COLUMNS)

    st.markdown(f"**{t('contacts_section_title')}**")
    st.caption(t("contacts_section_caption"))

    if df.empty and not ctx.is_admin:
        st.info(t("contacts_empty_readonly"))
        return

    if not ctx.is_admin:
        if df.empty:
            st.info(t("contacts_empty_readonly"))
            return
        st.dataframe(
            df.drop(columns=["id"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(t("contacts_readonly_hint"))
        return

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=_editor_column_config(t),
        key=f"contacts_editor_{client_id}",
    )

    if st.button(t("contacts_save"), type="secondary", key=f"save_contacts_{client_id}"):
        try:
            existing_ids = {str(c.get("id")) for c in contacts if c.get("id")}
            editor_rows = edited_df.fillna("").to_dict(orient="records")
            transfer_map = save_client_contacts(
                ctx.supabase,
                client_id,
                editor_rows,
                existing_ids=existing_ids,
            )
            st.success(t("contacts_save_ok", count=len(transfer_map)))
            st.rerun()
        except ValueError as exc:
            code = str(exc)
            if code == "display_name_required":
                st.error(t("contacts_error_name_required"))
            elif code == "phone_required_for_transfer":
                st.error(t("contacts_error_phone_required"))
            else:
                st.error(t("contacts_error_generic", error=code))
        except Exception as exc:
            st.error(t("contacts_error_generic", error=exc))

    with st.expander(t("contacts_legacy_json"), expanded=False):
        st.caption(t("contacts_legacy_json_hint"))
        transfer_map = build_transfer_numbers(contacts)
        st.json(transfer_map)