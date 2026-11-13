from i18n import TRANSLATIONS


def test_config_section_labels_exist_in_fr_and_en() -> None:
    keys = [
        "config_section_locale_company",
        "config_section_notifications",
        "config_section_agent",
        "config_section_transfer",
        "config_section_options",
        "config_section_telnek_demo",
        "config_section_google",
        "contacts_section_title",
        "contacts_section_title_none",
        "contacts_section_caption_none",
        "notifications_contacts_hint",
        "contacts_save",
        "contacts_save_ok_none",
        "transfer_numbers_legacy",
        "toggle_telnek_demo",
        "toggle_telnek_demo_help",
        "hours_by_day_caption",
        "day_closed",
        "hours_day_invalid",
        "weekday_0",
        "weekday_1",
        "weekday_2",
        "weekday_3",
        "weekday_4",
        "weekday_5",
        "weekday_6",
    ]
    for key in keys:
        assert key in TRANSLATIONS["fr"]
        assert key in TRANSLATIONS["en"]