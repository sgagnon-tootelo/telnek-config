"""Tests for sidebar session normalization."""

from ui.sidebar_state import (
    CLIENT_STORAGE_KEY,
    UI_LANG_STORAGE_KEY,
    option_index,
    resolve_stored_client,
    resolve_stored_ui_lang,
)


class _Session:
    def __init__(self, data: dict):
        self._data = dict(data)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __setattr__(self, key: str, value) -> None:
        if key == "_data":
            super().__setattr__(key, value)
        else:
            self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]


def test_option_index_falls_back_to_default() -> None:
    assert option_index(["a", "b"], "invalid", default="b") == 1


def test_resolve_stored_client_resets_invalid_value() -> None:
    session = _Session(
        {
            "main_client_selector": "sylvain@videotron.ca",
            CLIENT_STORAGE_KEY: "sylvain@videotron.ca",
        }
    )
    assert resolve_stored_client(session, ["electriciens", "telnekdev"]) == "electriciens"
    assert session.get("main_client_selector") is None
    assert session.get(CLIENT_STORAGE_KEY) == "electriciens"


def test_resolve_stored_ui_lang_resets_invalid_value() -> None:
    session = _Session({"ui_lang": "sylvain@videotron.ca"})
    assert resolve_stored_ui_lang(session) == "fr"
    assert session.get(UI_LANG_STORAGE_KEY) == "fr"