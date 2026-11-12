"""Splits the student's material into numbered lines that tailored bullets must cite (Constitution I).

Master resume lines are L1, L2, ...; sentences from the student's other writing (notes, past cover
letters, behavioral stories, essays) are N1, N2, ...
"""

import re
from dataclasses import dataclass

COMMON_HEADINGS = {
    "education", "experience", "work experience", "professional experience", "employment",
    "skills", "skills & interests", "skills and interests", "additional", "additional information",
    "leadership", "leadership experience", "activities", "projects", "certifications",
    "interests", "summary", "volunteer", "awards", "publications",
}
_BULLET_PREFIX = re.compile(r"^[\-\*•●▪◦·–—]\s*")
_SEPARATOR = re.compile(r"\s[|•·]\s|\t")
_DATE = re.compile(
    r"\b(?:19|20)\d{2}\s*[–—-]\s*(?:(?:19|20)\d{2}|present|current)\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(?:19|20)\d{2}\b",
    re.IGNORECASE)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


@dataclass(frozen=True)
class ResumeLine:
    id: str
    text: str
    section: str | None
    source: str  # "resume" or "notes"
    kind: str = "bullet"  # "heading", "header" (title, company, school, dates), or "bullet"

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "section": self.section, "source": self.source, "kind": self.kind}


def _is_heading(text: str) -> bool:
    bare = text.strip().rstrip(":").strip()
    if bare.lower() in COMMON_HEADINGS:
        return True
    letters = [c for c in bare if c.isalpha()]
    return 0 < len(bare) <= 40 and bool(letters) and all(c.isupper() for c in letters) and not any(c.isdigit() for c in bare)


def _line_kind(text: str, resume_uses_bullet_symbols: bool) -> str:
    """Tell job and school header lines (title, company, location, dates) apart from bullet lines."""
    if _is_heading(text):
        return "heading"
    if _BULLET_PREFIX.match(text):
        return "bullet"
    words = len(text.split())
    if words <= 16 and (resume_uses_bullet_symbols or _SEPARATOR.search(text) or _DATE.search(text)):
        return "header"
    return "header" if words <= 5 else "bullet"


def split_lines(master_resume: str, background_notes: str | None = None) -> list[ResumeLine]:
    """Number every non-blank resume line, then every note sentence. Section = nearest heading above."""
    lines: list[ResumeLine] = []
    section = None
    raw_lines = [raw.strip() for raw in master_resume.splitlines() if raw.strip()]
    uses_symbols = any(_BULLET_PREFIX.match(text) for text in raw_lines)
    for text in raw_lines:
        if _is_heading(text):
            section = text.rstrip(":").strip().title()
        lines.append(ResumeLine(f"L{len(lines) + 1}", text, section, "resume", _line_kind(text, uses_symbols)))

    count = 0
    for raw in (background_notes or "").splitlines():
        text = _BULLET_PREFIX.sub("", raw.strip())
        # Paragraphs are split into sentences so a bullet can cite the exact sentence it uses.
        for sentence in _SENTENCE_END.split(text):
            if sentence.strip():
                count += 1
                lines.append(ResumeLine(f"N{count}", sentence.strip(), "Your writing", "notes", "bullet"))
    return lines
