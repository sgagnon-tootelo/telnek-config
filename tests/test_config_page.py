from i18n import TRANSLATIONS


def test_config_section_labels_exist_in_fr_and_en() -> None:
    keys = [
        "config_section_locale_company",
        "config_section_notifications",
        "config_section_agent",
        "config_section_transfer",
        "config_section_options",
        "config_section_google",
        "contacts_section_title",
        "contacts_save",
        "transfer_numbers_legacy",
    ]
    for key in keys:
        assert key in TRANSLATIONS["fr"]
        assert key in TRANSLATIONS["en"]