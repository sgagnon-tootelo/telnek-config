"""Streamlit editor for client_contacts (transfers + SMS notifications)."""

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
    "phone_ext",
    "email",
    "email_enabled",
    "can_transfer",
    "notify_message",
    "notify_rdv",
    "notify_transfer_fail",
    "keywords",
    "priority",
    "active",
]

TRANSFER_ONLY_COLUMNS = frozenset(
    {"slug", "keywords", "can_transfer", "notify_transfer_fail", "phone_ext"}
)


def editor_columns_for_mode(transfer_mode: str) -> list[str]:
    if transfer_mode == "none":
        return [c for c in EDITOR_COLUMNS if c not in TRANSFER_ONLY_COLUMNS]
    return list(EDITOR_COLUMNS)


def count_notification_contacts(rows: list[dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if row.get("active", True)
        and row.get("phone_e164")
        and (row.get("notify_message") or row.get("notify_rdv"))
    )


def _editor_column_config(t, *, transfer_mode: str) -> dict[str, Any]:
    slug_help = (
        t("contacts_col_slug_help")
        if transfer_mode != "none"
        else t("contacts_col_slug_help_none")
    )
    return {
        "id": st.column_config.TextColumn(t("contacts_col_id"), disabled=True, width="small"),
        "display_name": st.column_config.TextColumn(
            t("contacts_col_name"), required=True, width="medium"
        ),
        "slug": st.column_config.TextColumn(
            t("contacts_col_slug"),
            help=slug_help,
            width="medium",
            disabled=transfer_mode == "none",
        ),
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
        "phone_ext": st.column_config.TextColumn(
            t("contacts_col_phone_ext"),
            help=t("contacts_col_phone_ext_help"),
            width="small",
            disabled=transfer_mode == "none",
        ),
        "email": st.column_config.TextColumn(
            t("contacts_col_email"),
            help=t("contacts_col_email_help"),
            width="medium",
        ),
        "email_enabled": st.column_config.CheckboxColumn(
            t("contacts_col_email_enabled"),
            default=False,
            help=t("contacts_col_email_enabled_help"),
        ),
        "can_transfer": st.column_config.CheckboxColumn(
            t("contacts_col_can_transfer"),
            default=True,
            disabled=transfer_mode == "none",
        ),
        "notify_message": st.column_config.CheckboxColumn(
            t("contacts_col_notify_message"),
            default=False,
            help=t("contacts_col_notify_message_help"),
        ),
        "notify_rdv": st.column_config.CheckboxColumn(
            t("contacts_col_notify_rdv"),
            default=False,
            help=t("contacts_col_notify_rdv_help"),
        ),
        "notify_transfer_fail": st.column_config.CheckboxColumn(
            t("contacts_col_notify_transfer_fail"),
            default=True,
            disabled=transfer_mode == "none",
        ),
        "keywords": st.column_config.TextColumn(
            t("contacts_col_keywords"),
            width="medium",
            disabled=transfer_mode == "none",
        ),
        "priority": st.column_config.NumberColumn(
            t("contacts_col_priority"), min_value=0, max_value=9999, step=1
        ),
        "active": st.column_config.CheckboxColumn(t("contacts_col_active"), default=True),
    }


def render_contacts_editor(ctx: AppContext, *, transfer_mode: str) -> None:
    t = ctx.t_fn
    client_id = ctx.selected_client_id
    notification_mode = transfer_mode == "none"
    visible_columns = editor_columns_for_mode(transfer_mode)

    contacts = fetch_client_contacts(ctx.supabase, client_id)
    rows = contacts_to_editor_rows(contacts)
    df = pd.DataFrame(rows, columns=EDITOR_COLUMNS) if rows else pd.DataFrame(columns=EDITOR_COLUMNS)
    if notification_mode and not df.empty:
        df = df.copy()
        df["can_transfer"] = False

    section_title = (
        t("contacts_section_title_none")
        if notification_mode
        else t("contacts_section_title")
    )
    section_caption = (
        t("contacts_section_caption_none")
        if notification_mode
        else t("contacts_section_caption")
    )

    st.markdown(f"**{section_title}**")
    st.caption(section_caption)

    if df.empty:
        st.info(t("contacts_empty_editable"))

    column_config = _editor_column_config(t, transfer_mode=transfer_mode)
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=visible_columns,
        column_config=column_config,
        key=f"contacts_editor_{client_id}_{transfer_mode}",
    )

    if st.button(t("contacts_save"), type="secondary", key=f"save_contacts_{client_id}"):
        try:
            existing_ids = {str(c.get("id")) for c in contacts if c.get("id")}
            editor_rows = edited_df.fillna("").to_dict(orient="records")
            if notification_mode:
                for row in editor_rows:
                    row["can_transfer"] = False
                    row["notify_transfer_fail"] = False
            transfer_map = save_client_contacts(
                ctx.supabase,
                client_id,
                editor_rows,
                existing_ids=existing_ids,
            )
            if notification_mode:
                notify_count = count_notification_contacts(editor_rows)
                st.success(t("contacts_save_ok_none", count=notify_count))
            else:
                st.success(t("contacts_save_ok", count=len(transfer_map)))
            st.rerun()
        except ValueError as exc:
            code = str(exc)
            if code == "display_name_required":
                st.error(t("contacts_error_name_required"))
            elif code == "phone_required_for_transfer":
                st.error(t("contacts_error_phone_required"))
            elif code == "phone_required_for_notify":
                st.error(t("contacts_error_phone_notify"))
            elif code == "email_required_for_notify":
                st.error(t("contacts_error_email_notify"))
            else:
                st.error(t("contacts_error_generic", error=code))
        except Exception as exc:
            st.error(t("contacts_error_generic", error=exc))

    if not notification_mode:
        with st.expander(t("contacts_legacy_json"), expanded=False):
            st.caption(t("contacts_legacy_json_hint"))
            transfer_map = build_transfer_numbers(contacts)
            st.json(transfer_map)