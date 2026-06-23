from ui.components import app_header_html


def test_app_header_html_is_single_block() -> None:
    html = app_header_html(subtitle="Réceptionniste IA", logo_data_uri="data:image/png;base64,abc")

    assert html.count("telnek-app-header-shell") == 1
    assert "telnek-app-header-logo" in html
    assert "telnek-brand-subtitle--app" in html
    assert "Réceptionniste IA" in html
    assert "data:image/png;base64,abc" in html
    assert html.index("telnek-app-header-shell") < html.index("telnek-app-header-rule")