"""Tests for sidebar session normalization."""

from ui.sidebar_state import normalize_client_selector


class _Session:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def __setattr__(self, key: str, value) -> None:
        if key == "_data":
            super().__setattr__(key, value)
        else:
            self._data[key] = value


def test_normalize_client_selector_resets_invalid_value() -> None:
    session = _Session({"main_client_selector": "sylvain@videotron.ca"})
    normalize_client_selector(session, ["electriciens", "telnekdev"])
    assert session.get("main_client_selector") == "electriciens"


def test_normalize_client_selector_keeps_valid_value() -> None:
    session = _Session({"main_client_selector": "telnekdev"})
    normalize_client_selector(session, ["electriciens", "telnekdev"])
    assert session.get("main_client_selector") == "telnekdev"