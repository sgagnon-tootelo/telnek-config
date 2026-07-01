"""Tests for contacts editor helpers."""

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
    assert "notify_message" in columns


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