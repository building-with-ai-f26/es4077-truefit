"""Parses what the student typed as their availability (FR-006a, FR-006b)."""

import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.errors import ApiError

DEFAULT_START = date(2027, 6, 1)
DEFAULT_END = date(2027, 10, 31)

ACCEPTED_FORMS_MESSAGE = (
    'Enter your availability as a month range (e.g., "June 2027 – October 2027"), '
    '"Immediate", "ASAP", or "Flexible". You can add an end month after Immediate or ASAP, '
    'e.g., "ASAP through August 2027".'
)

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
MONTHS["sept"] = 9

_MONTH_YEAR = r"([a-z]+)\.?\s+(\d{4})"
_DASH = r"(?:-|–|—|to)"
RANGE_RE = re.compile(rf"^{_MONTH_YEAR}\s*{_DASH}\s*{_MONTH_YEAR}$")
IMMEDIATE_RE = re.compile(rf"^(immediate|immediately|asap)(?:\s*(?:through|until|-|–|—|to)\s*{_MONTH_YEAR})?$")


@dataclass(frozen=True)
class Availability:
    mode: Literal["range", "immediate", "flexible"]
    start: date | None
    end: date | None
    label: str

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "label": self.label,
        }


def default_availability() -> Availability:
    return Availability("range", DEFAULT_START, DEFAULT_END, _range_label(DEFAULT_START, DEFAULT_END))


def parse_availability(text: str | None, today: date) -> Availability:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not cleaned:
        return default_availability()

    if cleaned == "flexible":
        return Availability("flexible", None, None, "Flexible")

    match = IMMEDIATE_RE.match(cleaned)
    if match:
        word, end_month, end_year = match.groups()
        label = "ASAP" if word == "asap" else "Immediate"
        if end_month is None:
            return Availability("immediate", today, None, label)
        end = _month_end(end_month, end_year)
        if end < today:
            raise ApiError(422, "availability_end_before_start",
                           "Your availability ends before today. Choose an end month in the future.")
        return Availability("immediate", today, end, f"{label} through {_month_label(end)}")

    match = RANGE_RE.match(cleaned)
    if match:
        start = _month_start(match.group(1), match.group(2))
        end = _month_end(match.group(3), match.group(4))
        if end < start:
            raise ApiError(422, "availability_end_before_start",
                           "Your availability ends before it starts. Check the order of the two months.")
        return Availability("range", start, end, _range_label(start, end))

    raise ApiError(422, "availability_invalid", ACCEPTED_FORMS_MESSAGE)


def _month_number(name: str) -> int:
    if name not in MONTHS:
        raise ApiError(422, "availability_invalid", ACCEPTED_FORMS_MESSAGE)
    return MONTHS[name]


def _month_start(name: str, year: str) -> date:
    return date(int(year), _month_number(name), 1)


def _month_end(name: str, year: str) -> date:
    month = _month_number(name)
    return date(int(year), month, calendar.monthrange(int(year), month)[1])


def _month_label(d: date) -> str:
    return f"{calendar.month_name[d.month]} {d.year}"


def _range_label(start: date, end: date) -> str:
    return f"{_month_label(start)} – {_month_label(end)}"
