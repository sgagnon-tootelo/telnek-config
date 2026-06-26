"""Sidebar widget session-state normalization."""

from __future__ import annotations

CLIENT_SELECTOR_KEY = "telnek_client_selector"
UI_LANG_KEY = "telnek_ui_lang"
VALID_UI_LANGS = ("fr", "en")

_LEGACY_CLIENT_KEYS = ("main_client_selector", "main_client_selector_v2")
_LEGACY_LANG_KEYS = ("ui_lang", "ui_lang_v2")


def _delete_keys(session_state, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in session_state:
            try:
                del session_state[key]
            except TypeError:
                session_state.pop(key, None)


def prepare_client_selector(session_state, client_ids: list[str]) -> None:
    """Reset corrupted Streamlit selectbox state for the client picker."""
    _delete_keys(session_state, _LEGACY_CLIENT_KEYS)

    if not client_ids:
        _delete_keys(session_state, (CLIENT_SELECTOR_KEY,))
        return

    current = session_state.get(CLIENT_SELECTOR_KEY)
    if current not in client_ids:
        _delete_keys(session_state, (CLIENT_SELECTOR_KEY,))
        setattr(session_state, CLIENT_SELECTOR_KEY, client_ids[0])


def prepare_ui_lang(session_state) -> str:
    """Reset corrupted Streamlit selectbox state for UI language."""
    _delete_keys(session_state, _LEGACY_LANG_KEYS)

    current = session_state.get(UI_LANG_KEY)
    if current not in VALID_UI_LANGS:
        _delete_keys(session_state, (UI_LANG_KEY,))
        setattr(session_state, UI_LANG_KEY, "fr")
        return "fr"
    return str(current)