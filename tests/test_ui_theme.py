from ui.theme import BRAND_PRIMARY, brand_color_sequence, inject_brand_css


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
    assert "telnek-brand-subtitle--app" in css
    assert "telnek-brand-subtitle--login" in css
    assert "telnek-app-header-shell" in css
    assert "telnek-config-save-bar" in css
    assert "telnek-app-header-logo" in css
    assert '#MainMenu {visibility: hidden;}' in css
    assert len(brand_color_sequence(3)) == 3