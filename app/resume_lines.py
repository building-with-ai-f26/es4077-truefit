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

# Text copied from a PDF often loses its line breaks, gluing a job's header onto the previous bullet
# ("...better outputsPARAMOUNT New York, NY Marketing Manager June 2022 - Aug. 2025").
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE_RANGE = re.compile(
    rf"\b(?:{_MONTH}\s+)?(?:19|20)\d{{2}}\s*[–—-]\s*(?:(?:{_MONTH}\s+)?(?:19|20)\d{{2}}|present|current)\b",
    re.IGNORECASE)
_INLINE_BULLET = re.compile(r"\s*([●▪◦]|(?<=\S)•|•(?=\S))\s*")
_INLINE_HEADING = re.compile(
    r"(?<![A-Za-z&])(" + "|".join(sorted((re.escape(h.upper()) for h in COMMON_HEADINGS), key=len, reverse=True))
    + r")(?![A-Za-z&])")
_GLUE = re.compile(r"(?<=[a-z0-9).,;%])(?=[A-Z])")
_CAPS_START = re.compile(r"^[A-Z][A-Z&.'-]{2,}\b")


@dataclass(frozen=True)
class ResumeLine:
    id: str
    text: str
    section: str | None
    source: str  # "resume" or "notes"
    kind: str = "bullet"  # "contact", "heading", "header" (title, company, school, dates), or "bullet"

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "section": self.section, "source": self.source, "kind": self.kind}


def _is_heading(text: str, standard_only: bool = False) -> bool:
    bare = text.strip().rstrip(":").strip()
    if bare.lower() in COMMON_HEADINGS:
        return True
    if standard_only:
        return False  # the resume has standard headings, so an all-caps line is a company or school
    letters = [c for c in bare if c.isalpha()]
    return 0 < len(bare) <= 40 and bool(letters) and all(c.isupper() for c in letters) and not any(c.isdigit() for c in bare)


def _line_kind(text: str, resume_uses_bullet_symbols: bool, standard_headings: bool = False) -> str:
    """Tell job and school header lines (title, company, location, dates) apart from bullet lines."""
    if _is_heading(text, standard_headings):
        return "heading"
    if _BULLET_PREFIX.match(text):
        return "bullet"
    words = len(text.split())
    if words <= 25 and _DATE.search(text):
        return "header"
    if words <= 16 and (resume_uses_bullet_symbols or _SEPARATOR.search(text)):
        return "header"
    return "header" if words <= 5 else "bullet"


def _looks_like_header(text: str) -> bool:
    words = len(text.split())
    return bool(_CAPS_START.match(text) and words <= 25) or bool(_DATE_RANGE.search(text) and words <= 12)


def _split_glued(line: str) -> list[str]:
    """Split where a header was glued onto the end of a bullet with no space or line break."""
    for match in _GLUE.finditer(line):
        before, after = line[:match.start()].strip(), line[match.start():].strip()
        if len(before.split()) >= 3 and _looks_like_header(after):
            return [before, *_split_glued(after)]
    return [line]


def _split_after_dates(line: str) -> list[str]:
    """A header line followed by more text ("...Aug. 2025 - Present Specializations: ...") ends at its dates."""
    if _BULLET_PREFIX.match(line):
        return [line]
    match = _DATE_RANGE.search(line)
    if match and len(line[match.end():].split()) >= 3 and len(line[:match.start()].split()) <= 20:
        return [line[:match.end()].strip(), line[match.end():].strip()]
    return [line]


def restore_line_breaks(master_resume: str) -> list[str]:
    """Put bullets, headings, and job headers back on their own lines."""
    text = _INLINE_BULLET.sub(lambda m: f"\n{m.group(1)} ", master_resume)
    text = _INLINE_HEADING.sub(lambda m: f"\n{m.group(1)}\n", text)
    lines = []
    for raw in text.splitlines():
        for part in _split_glued(raw.strip()):
            lines.extend(_split_after_dates(part))
    return [line.strip() for line in lines if line.strip()]


def split_lines(master_resume: str, background_notes: str | None = None) -> list[ResumeLine]:
    """Number every non-blank resume line, then every note sentence. Section = nearest heading above."""
    lines: list[ResumeLine] = []
    section = None
    raw_lines = restore_line_breaks(master_resume)
    uses_symbols = any(_BULLET_PREFIX.match(text) for text in raw_lines)
    # Lines above the first standard heading (name, email, phone, links) are the contact block.
    first_section = next((i for i, t in enumerate(raw_lines) if t.rstrip(":").strip().lower() in COMMON_HEADINGS), None)
    for i, text in enumerate(raw_lines):
        if first_section is not None and i < first_section:
            kind = "contact"
        else:
            kind = _line_kind(text, uses_symbols, standard_headings=first_section is not None)
            if kind == "heading":
                section = text.rstrip(":").strip().title()
        lines.append(ResumeLine(f"L{len(lines) + 1}", text, section, "resume", kind))

    count = 0
    for raw in (background_notes or "").splitlines():
        text = _BULLET_PREFIX.sub("", raw.strip())
        # Paragraphs are split into sentences so a bullet can cite the exact sentence it uses.
        for sentence in _SENTENCE_END.split(text):
            if sentence.strip():
                count += 1
                lines.append(ResumeLine(f"N{count}", sentence.strip(), "Your writing", "notes", "bullet"))
    return lines
