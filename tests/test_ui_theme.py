from ui.theme import BRAND_PRIMARY, inject_brand_css


def test_inject_brand_css_emits_brand_tokens(monkeypatch) -> None:
    captured: list[str] = []

    def fake_markdown(html: str, **_kwargs) -> None:
        captured.append(html)

    monkeypatch.setattr("streamlit.markdown", fake_markdown)
    inject_brand_css()

    assert len(captured) == 1
    css = captured[0]
    assert BRAND_PRIMARY in css
    assert "telnek-footer" in css
    assert "telnek-login-title" in css
    assert "telnek-brand-subtitle" in css
    assert '#MainMenu {visibility: hidden;}' in css