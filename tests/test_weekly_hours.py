from weekly_hours import (
    format_company_hours,
    legacy_opening_closing,
    parse_weekly_hours,
    week_from_client,
)

ECODENTAIRE = (
    "lundi, mardi de 8 à 20 heure. mercredi, jeudi de 9 à 19 heure. "
    "vendredi de 9 à 17 heure. et le samedi de 9 à 13 heure."
)


def test_ecodentaire_grid_follows_each_day() -> None:
    week = week_from_client(ECODENTAIRE, opening_hour=9, closing_hour=17)
    assert [(row.open_hour, row.close_hour, row.closed) for row in week] == [
        (8, 20, False),
        (8, 20, False),
        (9, 19, False),
        (9, 19, False),
        (9, 17, False),
        (9, 13, False),
        (9, 17, True),
    ]
    assert legacy_opening_closing(week) == (8, 20)


def test_simple_weekday_client_keeps_numeric_hours() -> None:
    text = "lundi au vendredi de 9 heure du matin à 5 heure de l'après-midi"
    week = week_from_client(text, opening_hour=8, closing_hour=17)
    assert [(row.open_hour, row.close_hour, row.closed) for row in week[:5]] == [
        (8, 17, False)
    ] * 5
    assert all(row.closed for row in week[5:])


def test_formatted_ecodentaire_hours_roundtrip() -> None:
    week = week_from_client(ECODENTAIRE, opening_hour=9, closing_hour=17)
    spoken = format_company_hours(week, "fr-CA")
    parsed = parse_weekly_hours(spoken)
    assert parsed == {
        0: (8 * 60, 20 * 60),
        1: (8 * 60, 20 * 60),
        2: (9 * 60, 19 * 60),
        3: (9 * 60, 19 * 60),
        4: (9 * 60, 17 * 60),
        5: (9 * 60, 13 * 60),
    }
    assert "dimanche" not in spoken
