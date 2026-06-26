"""Tests for session panel helpers."""

from ui.session_panel import can_change_password


def test_can_change_password_rejects_empty() -> None:
    assert can_change_password(None) is False
    assert can_change_password("") is False


def test_can_change_password_rejects_dev_bypass() -> None:
    assert can_change_password("dev-admin@local.test") is False


def test_can_change_password_accepts_real_user() -> None:
    assert can_change_password("user@example.com") is True