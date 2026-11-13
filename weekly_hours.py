"""Per-day opening and closing hours for the client config form."""

from __future__ import annotations

import re
from dataclasses import dataclass

_DAY_INDEX = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
_DAY = (
    r"(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
)
_DAY_GROUP = (
    rf"(?:{_DAY}\s+(?:au|à|a|to|through|-)\s+{_DAY}"
    rf"|{_DAY}(?:\s*(?:,|et)\s*{_DAY})*)"
)
_TIME = (
    r"(?:"
    r"\d{1,2}:\d{2}\s*(?:a\.?\s*m\.?|p\.?\s*m\.?)?"
    r"|\d{1,2}\s*(?:a\.?\s*m\.?|p\.?\s*m\.?)"
    r"|\d{1,2}\s*heure(?:\s+\d{1,2})?"
    r"(?:\s+du\s+matin|\s+de\s+l['’]après-midi|\s+de\s+l['’]apres-midi|\s+du\s+soir)?"
    r"|\d{1,2}"
    r")"
)
_SEGMENT = re.compile(
    rf"\b(?P<days>{_DAY_GROUP})\b\s*,?\s*(?:de\s+|from\s+)?"
    rf"(?P<open>{_TIME})\s+(?:à|a|to|-)\s+(?P<close>{_TIME})\b",
    re.IGNORECASE,
)
_RANGE = re.compile(
    rf"^({_DAY})\s+(?:au|à|a|to|through|-)\s+({_DAY})$",
    re.IGNORECASE,
)
_WEEKDAYS = frozenset(range(5))
_NAMES = {
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
    "en": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
}


@dataclass(frozen=True)
class DayHours:
    open_hour: int
    open_minute: int
    close_hour: int
    close_minute: int
    closed: bool = False

    def as_minutes(self) -> tuple[int, int] | None:
        if self.closed:
            return None
        return (
            self.open_hour * 60 + self.open_minute,
            self.close_hour * 60 + self.close_minute,
        )


def week_from_client(
    company_hours: str,
    opening_hour: int = 9,
    closing_hour: int = 17,
) -> list[DayHours]:
    """Hours Amélie actually uses, one row per day starting Monday."""
    schedule = parse_weekly_hours(company_hours)
    if schedule is not None and _uses_daily_schedule(schedule):
        return _rows_from_schedule(schedule, opening_hour, closing_hour)
    return default_week(opening_hour, closing_hour)


def default_week(opening_hour: int, closing_hour: int) -> list[DayHours]:
    return [
        DayHours(int(opening_hour), 0, int(closing_hour), 0, closed=day >= 5)
        for day in range(7)
    ]


def format_company_hours(rows: list[DayHours], language: str) -> str:
    """Spoken hours sentence that the agent can parse back into the same days."""
    names = _NAMES["en" if str(language).lower().startswith("en") else "fr"]
    english = names is _NAMES["en"]
    groups: list[tuple[list[int], DayHours]] = []
    for index, row in enumerate(rows):
        if row.closed:
            continue
        if (
            groups
            and groups[-1][0][-1] == index - 1
            and groups[-1][1].as_minutes() == row.as_minutes()
        ):
            groups[-1][0].append(index)
            continue
        groups.append(([index], row))

    parts = []
    for days, row in groups:
        label = _day_label(days, names, english)
        if english:
            parts.append(
                f"{label} from {_clock_en(row.open_hour, row.open_minute)} "
                f"to {_clock_en(row.close_hour, row.close_minute)}"
            )
        else:
            parts.append(
                f"{label} de {_clock_fr(row.open_hour, row.open_minute, leading=True)} "
                f"à {_clock_fr(row.close_hour, row.close_minute, leading=False)}"
            )
    return ". ".join(parts)


def legacy_opening_closing(rows: list[DayHours]) -> tuple[int, int]:
    """Single pair kept for clients whose week does not change by day."""
    open_rows = [row for row in rows if not row.closed]
    if not open_rows:
        return 9, 17
    return (
        min(row.open_hour for row in open_rows),
        max(row.close_hour for row in open_rows),
    )


def invalid_day_indexes(rows: list[DayHours]) -> list[int]:
    bad = []
    for index, row in enumerate(rows):
        if row.closed:
            continue
        opening, closing = row.as_minutes() or (0, 0)
        if closing <= opening or row.open_hour > 23 or row.close_hour > 24:
            bad.append(index)
    return bad


def parse_weekly_hours(company_hours: str) -> dict[int, tuple[int, int]] | None:
    text = _normalize(company_hours)
    if not text:
        return None
    schedule: dict[int, tuple[int, int]] = {}
    for match in _SEGMENT.finditer(text):
        days = _expand_days(match.group("days"))
        opening = _parse_clock(match.group("open"))
        closing = _parse_clock(match.group("close"))
        if not days or opening is None or closing is None or closing <= opening:
            continue
        for day in days:
            schedule[day] = (opening, closing)
    return schedule or None


def _rows_from_schedule(
    schedule: dict[int, tuple[int, int]],
    opening_hour: int,
    closing_hour: int,
) -> list[DayHours]:
    rows = []
    for day in range(7):
        window = schedule.get(day)
        if window is None:
            rows.append(
                DayHours(int(opening_hour), 0, int(closing_hour), 0, closed=True)
            )
            continue
        opening, closing = window
        rows.append(
            DayHours(
                opening // 60,
                opening % 60,
                closing // 60,
                closing % 60,
                closed=False,
            )
        )
    return rows


def _uses_daily_schedule(schedule: dict[int, tuple[int, int]]) -> bool:
    windows = set(schedule.values())
    if len(windows) > 1:
        return True
    if any(day >= 5 for day in schedule):
        return True
    if any(opening % 60 or closing % 60 for opening, closing in schedule.values()):
        return True
    return set(schedule) != _WEEKDAYS


def _day_label(days: list[int], names: list[str], english: bool) -> str:
    contiguous = days == list(range(days[0], days[-1] + 1))
    if len(days) >= 3 and contiguous:
        joiner = " to " if english else " au "
        return f"{names[days[0]]}{joiner}{names[days[-1]]}"
    if len(days) == 2:
        joiner = ", " if english else ", "
        return f"{names[days[0]]}{joiner}{names[days[1]]}"
    return names[days[0]]


def _clock_fr(hour: int, minute: int, *, leading: bool) -> str:
    if minute:
        return f"{hour} heure {minute:02d}"
    if leading:
        return str(hour)
    return f"{hour} heure"


def _clock_en(hour: int, minute: int) -> str:
    if minute:
        return f"{hour}:{minute:02d}"
    return str(hour)


def _normalize(company_hours: str) -> str:
    text = (company_hours or "").lower().replace("’", "'")
    text = text.replace("heures", "heure")
    text = re.sub(r"\b(le|les|the)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _expand_days(chunk: str) -> list[int]:
    chunk = chunk.strip().lower()
    span = _RANGE.fullmatch(chunk)
    if span:
        start = _DAY_INDEX[span.group(1)]
        end = _DAY_INDEX[span.group(2)]
        if end < start:
            return []
        return list(range(start, end + 1))
    days: list[int] = []
    for part in re.split(r"\s*,\s*|\s+et\s+", chunk):
        name = part.strip()
        if name in _DAY_INDEX:
            days.append(_DAY_INDEX[name])
    return days


def _parse_clock(raw: str) -> int | None:
    text = raw.strip().lower().replace("’", "'")
    clock = re.fullmatch(r"(\d{1,2}):(\d{2})\s*(a\.?\s*m\.?|p\.?\s*m\.?)?", text)
    if clock:
        return _to_minutes(int(clock.group(1)), int(clock.group(2)), clock.group(3) or "")
    ampm = re.fullmatch(r"(\d{1,2})\s*(a\.?\s*m\.?|p\.?\s*m\.?)", text)
    if ampm:
        return _to_minutes(int(ampm.group(1)), 0, ampm.group(2))
    spoken = re.fullmatch(
        r"(\d{1,2})(?:\s*heure)?(?:\s+(\d{1,2}))?"
        r"(?:\s+(du matin|de l'après-midi|de l'apres-midi|du soir))?",
        text,
    )
    if not spoken:
        return None
    return _to_minutes(int(spoken.group(1)), int(spoken.group(2) or 0), spoken.group(3) or "")


def _to_minutes(hour: int, minute: int, period: str) -> int | None:
    if minute > 59 or hour > 24 or (hour == 24 and minute != 0):
        return None
    marker = period.lower().replace(" ", "").replace(".", "")
    if marker in {"pm", "del'après-midi", "del'apres-midi", "dusoir"} and hour < 12:
        hour += 12
    elif marker in {"am", "dumatin"} and hour == 12:
        hour = 0
    if hour > 24 or (hour == 24 and minute != 0):
        return None
    return hour * 60 + minute
