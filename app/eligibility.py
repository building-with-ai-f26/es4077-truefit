"""Eligibility beyond the start date: degree, work authorization, and years of experience.

The model only finds and quotes what the posting states (in the same call as the start-date check).
Python confirms every quote is in the posting. Degree gets a verdict (the student is finishing an MBA);
work authorization and years of experience are information only: TrueFit reports what the posting says
and never asks the student about visas or their work history.
"""

import re
from dataclasses import dataclass

from app.quotes import quote_in

VERDICT_LABELS = {
    "meets": "Meets",
    "doesnt_meet": "Doesn't meet",
    "unclear": "Unclear",
    "not_stated": "Not stated",
    "info": "For your information",  # shown with a label naming what the posting says
}

REQUIREMENT_NAMES = {
    "degree": "Degree",
    "work_authorization": "Work authorization",
    "years_experience": "Years of experience",
}

DEGREE_LEVELS = {"bachelors", "masters_or_mba", "phd", "other", "not_stated"}
AUTH_STANCES = {"no_sponsorship", "sponsors", "must_be_authorized", "citizenship_required", "not_stated"}
YEARS_LEVELS = {"required", "preferred", "not_stated"}

NOTE_UNDERGRAD = ("This role looks aimed at undergraduates. TrueFit is built for MBA and graduate roles, "
                  "so check the posting before applying.")
NOTE_PHD = "This role requires a PhD."
NOTE_OTHER_DEGREE = "This role asks for a specific degree TrueFit doesn't check. Make sure yours counts."

STANCE_LABELS = {
    "no_sponsorship": "No sponsorship",
    "sponsors": "Sponsors visas",
    "must_be_authorized": "Authorization required",
    "citizenship_required": "Citizenship required",
}
STANCE_NOTES = {
    "no_sponsorship": "The employer won't sponsor a visa. If you'll need sponsorship, this role likely isn't open to you.",
    "sponsors": "The employer says visa sponsorship is available.",
    "must_be_authorized": ("The posting asks for work authorization but doesn't say whether it sponsors visas. "
                           "If you'll need sponsorship, ask the recruiter."),
    "citizenship_required": "This role requires citizenship (or similar), so check before applying.",
}
NOTE_YEARS_REQUIRED = "Required. Compare it with your own full-time experience before applying."
NOTE_YEARS_PREFERRED = "Preferred, not required."

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15}


@dataclass
class Requirement:
    key: str
    verdict: str
    quote: str | None = None
    note: str | None = None
    label: str | None = None  # overrides the verdict's label on information-only rows
    detail: str | None = None  # what an information-only row found, e.g. "no_sponsorship" or "required:5"

    def to_dict(self) -> dict:
        return {
            "requirement": self.key,
            "name": REQUIREMENT_NAMES[self.key],
            "verdict": self.verdict,
            "verdict_label": self.label or VERDICT_LABELS[self.verdict],
            "quote": self.quote,
            "note": self.note,
            "detail": self.detail,
        }


def _verified_quote(item, posting: str) -> str | None:
    quote = item.get("quote") if isinstance(item, dict) else None
    return quote.strip() if isinstance(quote, str) and quote.strip() and quote_in(posting, quote) else None


def _number_in(quote: str, n: int) -> bool:
    """The minimum the model reported must be written in the quote itself (digits or a word)."""
    if re.search(rf"(?<![\d.]){n}(?![\d])", quote):
        return True
    return any(NUMBER_WORDS[w] == n for w in re.findall(r"[a-z]+", quote.lower()) if w in NUMBER_WORDS)


def degree_requirement(raw, audience, posting: str) -> Requirement:
    # The undergraduate check (already in the start-date call) wins: it's a clearer signal than a degree line.
    if isinstance(audience, dict) and audience.get("level") == "undergraduate":
        quote = _verified_quote(audience, posting)
        if quote:
            return Requirement("degree", "unclear", quote, NOTE_UNDERGRAD)
    level = raw.get("level") if isinstance(raw, dict) else None
    quote = _verified_quote(raw, posting)
    if level not in DEGREE_LEVELS or level == "not_stated" or not quote:
        return Requirement("degree", "not_stated")
    if level in ("bachelors", "masters_or_mba"):
        return Requirement("degree", "meets", quote)  # an MBA meets a bachelor's, master's, or MBA requirement
    if level == "phd":
        return Requirement("degree", "doesnt_meet", quote, NOTE_PHD)
    return Requirement("degree", "unclear", quote, NOTE_OTHER_DEGREE)


def work_authorization_requirement(raw, posting: str) -> Requirement:
    """Information only: what the posting says about visas."""
    stance = raw.get("stance") if isinstance(raw, dict) else None
    quote = _verified_quote(raw, posting)
    if stance not in AUTH_STANCES or stance == "not_stated" or not quote:
        return Requirement("work_authorization", "not_stated")
    return Requirement("work_authorization", "info", quote, STANCE_NOTES[stance], STANCE_LABELS[stance], stance)


def years_requirement(raw, posting: str) -> Requirement:
    """Information only: the minimum years the posting asks for, and whether it's required or preferred."""
    level = raw.get("level") if isinstance(raw, dict) else None
    quote = _verified_quote(raw, posting)
    minimum = raw.get("min_years") if isinstance(raw, dict) else None
    if isinstance(minimum, float) and minimum.is_integer():
        minimum = int(minimum)
    if (level not in YEARS_LEVELS or level == "not_stated" or not quote
            or not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1
            or not _number_in(quote, minimum)):
        return Requirement("years_experience", "not_stated")
    note = NOTE_YEARS_REQUIRED if level == "required" else NOTE_YEARS_PREFERRED
    return Requirement("years_experience", "info", quote, note, f"{minimum}+ years {level}", f"{level}:{minimum}")


def check_requirements(reply: dict, posting: str) -> list[Requirement]:
    raw = reply.get("requirements") if isinstance(reply.get("requirements"), dict) else {}
    return [
        degree_requirement(raw.get("degree"), reply.get("audience"), posting),
        work_authorization_requirement(raw.get("work_authorization"), posting),
        years_requirement(raw.get("years_experience"), posting),
    ]
