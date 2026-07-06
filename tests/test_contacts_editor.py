"""Tests for contacts editor helpers."""

from pathlib import Path

from views.contacts_editor import (
    count_notification_contacts,
    editor_columns_for_mode,
)


def test_editor_columns_for_none_mode_hides_transfer_fields() -> None:
    columns = editor_columns_for_mode("none")
    assert "slug" not in columns
    assert "can_transfer" not in columns
    assert "keywords" not in columns
    assert "notify_transfer_fail" not in columns
    assert "notify_message" in columns
    assert "notify_rdv" in columns
    assert "email_enabled" in columns
    assert "phone_e164" in columns


def test_editor_columns_for_blind_mode_includes_transfer_fields() -> None:
    columns = editor_columns_for_mode("blind")
    assert "slug" in columns
    assert "can_transfer" in columns
    assert "phone_ext" in columns
    assert "notify_message" in columns


def test_editor_columns_for_none_mode_hides_phone_ext() -> None:
    columns = editor_columns_for_mode("none")
    assert "phone_ext" not in columns


def test_contacts_editor_allows_client_editing() -> None:
    source = Path("views/contacts_editor.py").read_text(encoding="utf-8")
    assert "st.data_editor" in source
    assert "contacts_readonly_hint" not in source
    assert "if not ctx.is_admin" not in source


def test_count_notification_contacts() -> None:
    rows = [
        {
            "active": True,
            "phone_e164": "+15141111111",
            "notify_message": True,
            "notify_rdv": False,
        },
        {
            "active": True,
            "phone_e164": "+15142222222",
            "notify_message": False,
            "notify_rdv": True,
        },
        {
            "active": True,
            "phone_e164": "+15143333333",
            "notify_message": False,
            "notify_rdv": False,
        },
    ]
    assert count_notification_contacts(rows) == 2