"""Copy-ready, ATS-safe plain text (research.md §R10, Constitution III).

Headings on their own line with a blank line before, header lines copied from the source, bullets as "- ".
Only printable ASCII and newlines, plus "–" in date ranges. app.js mirrors these rules after edits.
"""

import re
import unicodedata

from app.resume_lines import ResumeLine

_LEADING_BULLET = re.compile(r"^[\-\*•●▪◦·]\s*")
_DATE_RANGE = re.compile(
    r"(\d{4})\s*[–—-]\s*((?:[A-Z][a-z]{2,8}\.?\s+)?\d{4}|Present|present|Current|current)")
_REPLACEMENTS = {"‘": "'", "’": "'", "“": '"', "”": '"', "…": "...", " ": " "}


def normalize_chars(text: str) -> str:
    """Straight quotes, plain hyphens (except "–" in date ranges), no bullet symbols or non-ASCII characters."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    text = _LEADING_BULLET.sub("", text.strip())
    text = _DATE_RANGE.sub(lambda m: f"{m.group(1)} \x00 {m.group(2)}", text)  # protect date-range dashes
    text = text.replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")  # é → e
    text = "".join(c for c in text if c.isprintable() or c == "\x00")
    return re.sub(r" {2,}", " ", text.replace("\x00", "–")).strip()


def render_plain_text(sections: list[dict], lines_by_id: dict[str, ResumeLine]) -> str:
    """Render included bullets only. Entries with nothing to show are skipped."""
    blocks = []
    for section in sections:
        rows = []
        for entry in section.get("entries", []):
            headers = [normalize_chars(lines_by_id[i].text) for i in entry.get("header_line_ids", []) if i in lines_by_id]
            bullets = [f"- {normalize_chars(b['text'])}" for b in entry.get("bullets", []) if b.get("included")]
            rows.extend(headers + bullets)
        if rows:
            blocks.append("\n".join([normalize_chars(section["heading"]).title(), *rows]))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
