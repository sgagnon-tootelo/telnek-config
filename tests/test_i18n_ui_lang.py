"""Tests for UI language session normalization."""


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


def test_normalize_ui_lang_resets_invalid_value() -> None:
    from i18n import normalize_ui_lang
    from ui.sidebar_state import UI_LANG_STORAGE_KEY

    session = _Session({"ui_lang": "sylvain@videotron.ca"})
    assert normalize_ui_lang(session) == "fr"
    assert session.get(UI_LANG_STORAGE_KEY) == "fr"


def test_normalize_ui_lang_keeps_valid_value() -> None:
    from i18n import normalize_ui_lang
    from ui.sidebar_state import UI_LANG_STORAGE_KEY

    session = _Session({UI_LANG_STORAGE_KEY: "en"})
    assert normalize_ui_lang(session) == "en"