"""Sidebar selection state (explicit storage, no widget keys)."""

from __future__ import annotations

import streamlit as st

CLIENT_STORAGE_KEY = "telnek_selected_client_id"
UI_LANG_STORAGE_KEY = "telnek_ui_lang_code"
VALID_UI_LANGS = ("fr", "en")

# Legacy Streamlit widget keys that may hold corrupted values.
_WIDGET_KEYS_TO_PURGE = (
    "main_client_selector",
    "main_client_selector_v2",
    "telnek_client_selector",
    "ui_lang",
    "ui_lang_v2",
    "telnek_ui_lang",
)


def _delete_keys(session_state, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in session_state:
            try:
                del session_state[key]
            except TypeError:
                session_state.pop(key, None)


def purge_sidebar_widget_keys(session_state) -> None:
    _delete_keys(session_state, _WIDGET_KEYS_TO_PURGE)


def option_index(options: list[str], value: str | None, *, default: str) -> int:
    if value in options:
        return options.index(value)
    if default in options:
        return options.index(default)
    return 0


def resolve_stored_client(session_state, client_ids: list[str]) -> str | None:
    purge_sidebar_widget_keys(session_state)
    if not client_ids:
        _delete_keys(session_state, (CLIENT_STORAGE_KEY,))
        return None

    stored = session_state.get(CLIENT_STORAGE_KEY)
    if stored not in client_ids:
        stored = client_ids[0]
        setattr(session_state, CLIENT_STORAGE_KEY, stored)
    return str(stored)


def store_client_selection(session_state, client_id: str | None) -> None:
    if client_id:
        setattr(session_state, CLIENT_STORAGE_KEY, client_id)


def resolve_stored_ui_lang(session_state) -> str:
    purge_sidebar_widget_keys(session_state)
    stored = session_state.get(UI_LANG_STORAGE_KEY)
    if stored not in VALID_UI_LANGS:
        setattr(session_state, UI_LANG_STORAGE_KEY, "fr")
        return "fr"
    return str(stored)


def store_ui_lang(session_state, lang: str) -> None:
    if lang in VALID_UI_LANGS:
        setattr(session_state, UI_LANG_STORAGE_KEY, lang)


# Backward-compatible aliases used by i18n helpers.
UI_LANG_KEY = UI_LANG_STORAGE_KEY
CLIENT_SELECTOR_KEY = CLIENT_STORAGE_KEY


def prepare_ui_lang(session_state) -> str:
    return resolve_stored_ui_lang(session_state)


def prepare_client_selector(session_state, client_ids: list[str]) -> None:
    resolve_stored_client(session_state, client_ids)


def render_language_selector(
    session_state,
    t_fn,
    *,
    horizontal: bool = True,
    widget_key: str = "telnek_ui_lang_radio",
) -> None:
    """Radio buttons avoid Streamlit selectbox 'No results' on corrupted lang state."""
    lang_options = list(VALID_UI_LANGS)
    stored_lang = resolve_stored_ui_lang(session_state)
    chosen_lang = st.radio(
        t_fn("ui_language"),
        options=lang_options,
        index=option_index(lang_options, stored_lang, default="fr"),
        format_func=lambda code: "Français" if code == "fr" else "English",
        horizontal=horizontal,
        key=widget_key,
    )
    store_ui_lang(session_state, chosen_lang)