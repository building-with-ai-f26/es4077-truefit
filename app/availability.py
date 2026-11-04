"""Parses what the student typed as their availability (FR-006a, FR-006b).

Availability is open-ended: the earliest the student can start. Any start on or after it fits.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.errors import ApiError

DEFAULT_START = date(2027, 6, 1)

ACCEPTED_FORMS_MESSAGE = (
    'Enter the month you can start (e.g., "June 2027"), or "ASAP" or "Flexible".'
)
RANGE_MESSAGE = (
    'Enter just the month you can start, e.g., "June 2027". '
    "Any start date in or after that month counts as in window."
)

MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
MONTHS["sept"] = 9

MONTH_RE = re.compile(r"^(?:starting |from )?([a-z]+)\.?\s+(\d{4})$")
ASAP_RE = re.compile(r"^(?:starting )?asap$")
LOOKS_LIKE_RANGE_RE = re.compile(r"\d{4}\s*(?:-|–|—|to|through|until)\s*[a-z]+")


@dataclass(frozen=True)
class Availability:
    mode: Literal["month", "asap", "flexible"]
    start: date | None  # first day of the start month, today for ASAP, None for flexible
    label: str

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "start": self.start.isoformat() if self.start else None,
            "label": self.label,
        }


def default_availability() -> Availability:
    return Availability("month", DEFAULT_START, _month_label(DEFAULT_START))


def parse_availability(text: str | None, today: date) -> Availability:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    if not cleaned:
        return default_availability()

    if cleaned == "flexible":
        return Availability("flexible", None, "Flexible")

    if ASAP_RE.match(cleaned):
        return Availability("asap", today, "ASAP")

    match = MONTH_RE.match(cleaned)
    if match and match.group(1) in MONTHS:
        start = date(int(match.group(2)), MONTHS[match.group(1)], 1)
        return Availability("month", start, _month_label(start))

    if LOOKS_LIKE_RANGE_RE.search(cleaned) or re.search(r"\basap\b", cleaned):
        raise ApiError(422, "availability_invalid", RANGE_MESSAGE)
    raise ApiError(422, "availability_invalid", ACCEPTED_FORMS_MESSAGE)


def _month_label(d: date) -> str:
    return f"Starting {calendar.month_name[d.month]} {d.year}"
