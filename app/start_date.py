"""Start-date check (User Story 1).

The model only finds and quotes start-date text. Python checks the quote and decides the verdict.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app import llm
from app.availability import Availability, parse_availability
from app.errors import ApiError
from app.quotes import quote_in

VERDICT_LABELS = {
    "in_window": "In window",
    "outside_window": "Outside window",
    "partly_in_window": "Partly in window",
    "likely_in_window_vague": "Likely in window (vague)",
    "flexible_to_discuss": "Flexible / to discuss",
    "not_stated": "Not stated",
}

NOTE_VAGUE = "Exact date not specified"
NOTE_PASSED = "This date has already passed"
NOTE_TOO_EARLY = "The role starts before you're available"
NOTE_DIFFERENT = "Different start dates are listed (for example, for different roles or offices). See each one below."

# Season → (first month, last month). Winter runs Dec of the year before through Feb.
SEASONS = {"spring": (3, 5), "summer": (6, 8), "fall": (9, 11), "autumn": (9, 11), "winter": (12, 2), "year": (1, 12)}
KINDS = {"exact_date", "month", "range", "season", "immediate", "flexible"}


@dataclass
class Mention:
    quote: str
    kind: str
    start: date | None
    end: date | None
    role_hint: str | None = None
    is_vague: bool = False
    verdict: str | None = None
    note: str | None = None

    def to_dict(self) -> dict:
        return {
            "quote": self.quote,
            "kind": self.kind,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "role_hint": self.role_hint,
            "is_vague": self.is_vague,
            "verdict": self.verdict,
            "verdict_label": VERDICT_LABELS.get(self.verdict),
            "note": self.note,
        }


@dataclass
class StartDateResult:
    verdict: str
    availability: Availability
    mentions: list[Mention] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "verdict_label": VERDICT_LABELS[self.verdict],
            "availability": self.availability.to_dict(),
            "mentions": [m.to_dict() for m in self.mentions],
            "note": self.note,
        }


def today_ny() -> date:
    """'Today' for ASAP and passed-date checks, in New York time."""
    return datetime.now(ZoneInfo("America/New_York")).date()


# ---- Turning model output into date intervals ------------------------------

def _parse_day_or_month(value, *, as_end: bool) -> date | None:
    """Accept 'YYYY-MM-DD' or 'YYYY-MM'. A bare month means its first (or, for an end, last) day."""
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        if len(value) == 7:
            year, month = int(value[:4]), int(value[5:7])
            day = calendar.monthrange(year, month)[1] if as_end else 1
            return date(year, month, day)
    except ValueError:
        return None
    return None


def _month_bounds(d: date) -> tuple[date, date]:
    return date(d.year, d.month, 1), date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _season_bounds(season, year) -> tuple[date, date] | None:
    if not isinstance(season, str) or season.lower() not in SEASONS:
        return None
    try:
        year = int(year)
    except (TypeError, ValueError):
        return None
    first, last = SEASONS[season.lower()]
    start_year = year - 1 if first > last else year
    return date(start_year, first, 1), date(year, last, calendar.monthrange(year, last)[1])


def normalize_mention(raw: dict, today: date) -> Mention | None:
    """Build a Mention from one model-returned item, or None if it's unusable."""
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    quote = raw.get("quote")
    if kind not in KINDS or not isinstance(quote, str):
        return None
    role_hint = raw.get("role_hint") if isinstance(raw.get("role_hint"), str) else None
    start = end = None
    is_vague = False

    if kind == "exact_date":
        start = _parse_day_or_month(raw.get("start"), as_end=False)
        if start is None or len(raw["start"]) != 10:
            return None
        end = start
    elif kind == "month":
        first = _parse_day_or_month(raw.get("start"), as_end=False)
        if first is None:
            return None
        start, end = _month_bounds(first)
    elif kind == "range":
        start = _parse_day_or_month(raw.get("start"), as_end=False)
        end = _parse_day_or_month(raw.get("end"), as_end=True)
        if start is None or end is None or end < start:
            return None
    elif kind == "season":
        bounds = _season_bounds(raw.get("season"), raw.get("year"))
        if bounds is None:
            return None
        start, end = bounds
        is_vague = True
    elif kind == "immediate":
        start = end = today
    # "flexible" has no dates.

    return Mention(quote=quote.strip(), kind=kind, start=start, end=end, role_hint=role_hint, is_vague=is_vague)


# ---- Verdict rules (data-model.md §Verdict rules) --------------------------

def _mention_verdict(m: Mention, a: Availability, today: date) -> tuple[str, str | None]:
    vague_note = NOTE_VAGUE if m.is_vague else None

    if m.kind == "flexible":
        return "flexible_to_discuss", None
    if m.end < today:
        return "outside_window", NOTE_PASSED
    if m.kind == "immediate":
        available_now = a.mode == "flexible" or a.start <= today
        return ("in_window", None) if available_now else ("outside_window", NOTE_TOO_EARLY)
    if a.mode == "flexible":
        return "in_window", vague_note

    # Availability is open-ended: anything starting on or after the student's start month fits.
    if m.start >= a.start:
        return ("likely_in_window_vague", vague_note) if m.is_vague else ("in_window", None)
    if m.end >= a.start:
        return "partly_in_window", vague_note
    return "outside_window", None


def compute_verdict(mentions: list[Mention], availability: Availability, today: date) -> StartDateResult:
    if not mentions:
        return StartDateResult("not_stated", availability, [], None)

    for m in mentions:
        m.verdict, m.note = _mention_verdict(m, availability, today)

    verdicts = {m.verdict for m in mentions}
    if len(verdicts) == 1:
        notes = {m.note for m in mentions}
        return StartDateResult(mentions[0].verdict, availability, mentions, notes.pop() if len(notes) == 1 else None)
    return StartDateResult("partly_in_window", availability, mentions, NOTE_DIFFERENT)


# ---- Model extraction ------------------------------------------------------

EXTRACTION_PROMPT = """You read job postings and find when the job STARTS. Reply with one JSON object only.

Shape:
{"is_job_posting": true|false, "is_english": true|false,
 "mentions": [{"quote": "...", "kind": "...", "start": "...", "end": "...", "season": "...", "year": 2027, "role_hint": "..."}]}

Rules:
- Only the date the job itself starts. Ignore application deadlines, interview dates, event dates, posting dates, and end dates.
- "quote" MUST be copied character for character from the posting: the shortest phrase or sentence that states the start date. Do not paraphrase, fix typos, or change capitalization.
- Never invent or guess a date. If the posting doesn't say when the job starts, return "mentions": [].
- If no year is written, use a year only if the posting states it elsewhere (e.g., "MBA Class of 2027"). Otherwise set start to null.
- kind and fields:
  - "exact_date": a specific day. start = "YYYY-MM-DD".
  - "month": one month. start = "YYYY-MM".
  - "range": between two days or months. start and end = "YYYY-MM" or "YYYY-MM-DD".
  - "season": a season or only a year. season = "spring" | "summer" | "fall" | "winter" | "year"; year = the year as a number.
  - "immediate": "immediately", "ASAP", "as soon as possible", "immediate start".
  - "flexible": "flexible start date", "rolling start", "start date to be discussed".
  Use null for fields that don't apply.
- If different roles, offices, or programs start at different times, return one mention for each and name it in "role_hint". Otherwise role_hint is null.
- is_job_posting is false if the text is not a job or internship posting. is_english is false if the posting is not in English."""


async def check_start_date(posting: str, availability_text: str | None) -> StartDateResult:
    today = today_ny()
    availability = parse_availability(availability_text, today)  # fail fast, before paying for a model call

    reply = await llm.call(EXTRACTION_PROMPT, f"Today's date: {today.isoformat()}\n\nJob posting:\n<<<\n{posting}\n>>>")

    if reply.get("is_job_posting") is False:
        raise ApiError(422, "not_a_posting", "That doesn't look like a job posting. Paste the full posting text.")
    if reply.get("is_english") is False:
        raise ApiError(422, "not_english", "TrueFit only supports postings in English for now.")

    raw_mentions = reply.get("mentions")
    mentions = []
    for raw in raw_mentions if isinstance(raw_mentions, list) else []:
        if not isinstance(raw, dict) or not quote_in(posting, raw.get("quote") or ""):
            continue  # Show the Source: a quote we can't find in the posting is never shown
        mention = normalize_mention(raw, today)
        if mention is not None:
            mentions.append(mention)

    return compute_verdict(mentions, availability, today)
