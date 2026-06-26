"""Tests for sidebar session normalization."""

from ui.sidebar_state import (
    CLIENT_SELECTOR_KEY,
    UI_LANG_KEY,
    prepare_client_selector,
    prepare_ui_lang,
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


def test_prepare_client_selector_resets_invalid_value() -> None:
    session = _Session(
        {
            "main_client_selector": "sylvain@videotron.ca",
            CLIENT_SELECTOR_KEY: "sylvain@videotron.ca",
        }
    )
    prepare_client_selector(session, ["electriciens", "telnekdev"])
    assert session.get("main_client_selector") is None
    assert session.get(CLIENT_SELECTOR_KEY) == "electriciens"


def test_prepare_client_selector_keeps_valid_value() -> None:
    session = _Session({CLIENT_SELECTOR_KEY: "telnekdev"})
    prepare_client_selector(session, ["electriciens", "telnekdev"])
    assert session.get(CLIENT_SELECTOR_KEY) == "telnekdev"


def test_prepare_ui_lang_resets_invalid_value() -> None:
    session = _Session({"ui_lang": "sylvain@videotron.ca", UI_LANG_KEY: "bad"})
    assert prepare_ui_lang(session) == "fr"
    assert session.get("ui_lang") is None
    assert session.get(UI_LANG_KEY) == "fr"