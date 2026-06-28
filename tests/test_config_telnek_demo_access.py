"""Telnek demo config is admin-only in the config page source."""

from pathlib import Path


def test_telnek_demo_section_gated_by_admin() -> None:
    source = Path("views/config.py").read_text(encoding="utf-8")
    assert "if ctx.is_admin:" in source
    assert 'with st.expander(t("config_section_telnek_demo")' in source
    assert source.index("if ctx.is_admin:") < source.index(
        'with st.expander(t("config_section_telnek_demo")'
    )


def test_telnek_demo_save_gated_by_admin() -> None:
    source = Path("views/config.py").read_text(encoding="utf-8")
    assert 'updated_data["telnek_demo_enabled"] = telnek_demo_enabled' in source
    assert (
        source.index('if ctx.is_admin:')
        < source.index('updated_data["telnek_demo_enabled"]')
    )