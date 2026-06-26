"""Password helpers — email reset avoids password widgets in Streamlit (sidebar corruption)."""

from __future__ import annotations

from typing import Any

MIN_PASSWORD_LENGTH = 8


def validate_password_fields(
    *,
    current_password: str,
    new_password: str,
    confirm_password: str,
    min_length: int = MIN_PASSWORD_LENGTH,
) -> str | None:
    if not current_password.strip():
        return "password_current_required"
    if len(new_password) < min_length:
        return "password_too_short"
    if new_password != confirm_password:
        return "password_mismatch"
    if new_password == current_password:
        return "password_same_as_current"
    return None


def change_password(
    supabase: Any,
    *,
    email: str,
    current_password: str,
    new_password: str,
) -> tuple[str | None, str | None]:
    """Return (error_code, technical_detail). Both None on success."""
    try:
        supabase.auth.sign_in_with_password(
            {"email": email.strip().lower(), "password": current_password}
        )
    except Exception as exc:
        return "password_current_invalid", str(exc)

    try:
        response = supabase.auth.update_user({"password": new_password})
        if not response or not getattr(response, "user", None):
            return "password_update_failed", None
    except Exception as exc:
        return "password_update_failed", str(exc)

    return None, None


def request_password_reset(
    supabase: Any,
    *,
    email: str,
    redirect_to: str,
) -> tuple[str | None, str | None]:
    """Send Supabase password-reset email. Return (error_code, technical_detail)."""
    try:
        supabase.auth.reset_password_for_email(
            email.strip().lower(),
            {"redirect_to": redirect_to},
        )
    except Exception as exc:
        return "password_reset_failed", str(exc)
    return None, None