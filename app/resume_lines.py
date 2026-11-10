"""Splits the student's material into numbered lines that tailored bullets must cite (Constitution I).

Master resume lines are L1, L2, ...; background-note sentences are N1, N2, ...
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
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")


@dataclass(frozen=True)
class ResumeLine:
    id: str
    text: str
    section: str | None
    source: str  # "resume" or "notes"

    def to_dict(self) -> dict:
        return {"id": self.id, "text": self.text, "section": self.section, "source": self.source}


def _is_heading(text: str) -> bool:
    bare = text.strip().rstrip(":").strip()
    if bare.lower() in COMMON_HEADINGS:
        return True
    letters = [c for c in bare if c.isalpha()]
    return 0 < len(bare) <= 40 and bool(letters) and all(c.isupper() for c in letters) and not any(c.isdigit() for c in bare)


def split_lines(master_resume: str, background_notes: str | None = None) -> list[ResumeLine]:
    """Number every non-blank resume line, then every note sentence. Section = nearest heading above."""
    lines: list[ResumeLine] = []
    section = None
    for raw in master_resume.splitlines():
        text = raw.strip()
        if not text:
            continue
        if _is_heading(text):
            section = text.rstrip(":").strip().title()
        lines.append(ResumeLine(f"L{len(lines) + 1}", text, section, "resume"))

    count = 0
    for raw in (background_notes or "").splitlines():
        text = _BULLET_PREFIX.sub("", raw.strip())
        # Paragraphs are split into sentences so a bullet can cite the exact sentence it uses.
        for sentence in _SENTENCE_END.split(text):
            if sentence.strip():
                count += 1
                lines.append(ResumeLine(f"N{count}", sentence.strip(), "Background notes", "notes"))
    return lines
