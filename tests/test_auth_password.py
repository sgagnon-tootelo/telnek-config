"""Tests for auth_password helpers."""

from auth_password import change_password, request_password_reset, validate_password_fields


def test_validate_password_fields_requires_current() -> None:
    assert (
        validate_password_fields(
            current_password="",
            new_password="newpassword1",
            confirm_password="newpassword1",
        )
        == "password_current_required"
    )


def test_validate_password_fields_detects_mismatch() -> None:
    assert (
        validate_password_fields(
            current_password="oldpass1",
            new_password="newpassword1",
            confirm_password="different1",
        )
        == "password_mismatch"
    )


def test_validate_password_fields_rejects_same_password() -> None:
    assert (
        validate_password_fields(
            current_password="samepass1",
            new_password="samepass1",
            confirm_password="samepass1",
        )
        == "password_same_as_current"
    )


def test_validate_password_fields_accepts_valid_input() -> None:
    assert (
        validate_password_fields(
            current_password="oldpass1",
            new_password="newpassword1",
            confirm_password="newpassword1",
        )
        is None
    )


class _FakeAuth:
    def __init__(self, *, current_ok: bool = True, update_ok: bool = True):
        self.current_ok = current_ok
        self.update_ok = update_ok
        self.update_called = False

    def sign_in_with_password(self, _credentials: dict):
        if not self.current_ok:
            raise RuntimeError("invalid credentials")
        return type("R", (), {"user": object()})()

    def update_user(self, _payload: dict):
        self.update_called = True
        if not self.update_ok:
            raise RuntimeError("update failed")
        return type("R", (), {"user": object()})()


class _FakeSupabase:
    def __init__(self, auth: _FakeAuth):
        self.auth = auth


def test_change_password_success() -> None:
    auth = _FakeAuth()
    client = _FakeSupabase(auth)
    error, detail = change_password(
        client,
        email="user@example.com",
        current_password="oldpass1",
        new_password="newpassword1",
    )
    assert error is None
    assert detail is None
    assert auth.update_called


def test_change_password_invalid_current() -> None:
    auth = _FakeAuth(current_ok=False)
    client = _FakeSupabase(auth)
    error, _detail = change_password(
        client,
        email="user@example.com",
        current_password="wrong",
        new_password="newpassword1",
    )
    assert error == "password_current_invalid"
    assert not auth.update_called


class _FakeAuthReset:
    def __init__(self, *, ok: bool = True):
        self.ok = ok
        self.called_with: tuple[str, dict] | None = None

    def reset_password_for_email(self, email: str, options: dict):
        self.called_with = (email, options)
        if not self.ok:
            raise RuntimeError("smtp error")


def test_request_password_reset_success() -> None:
    auth = _FakeAuthReset()
    client = type("C", (), {"auth": auth})()
    error, detail = request_password_reset(
        client,
        email="User@Example.com",
        redirect_to="https://telnek-config.streamlit.app",
    )
    assert error is None
    assert detail is None
    assert auth.called_with == (
        "user@example.com",
        {"redirect_to": "https://telnek-config.streamlit.app"},
    )


def test_request_password_reset_failure() -> None:
    auth = _FakeAuthReset(ok=False)
    client = type("C", (), {"auth": auth})()
    error, _detail = request_password_reset(
        client,
        email="user@example.com",
        redirect_to="https://example.com",
    )
    assert error == "password_reset_failed"