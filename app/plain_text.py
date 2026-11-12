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
    text = re.sub(r"\s*[•●▪◦·]\s*", " | ", text)  # "Coho Consulting • Los Angeles" keeps a separator
    text = _DATE_RANGE.sub(lambda m: f"{m.group(1)} \x00 {m.group(2)}", text)  # protect date-range dashes
    text = text.replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")  # é → e
    text = "".join(c for c in text if c.isprintable() or c == "\x00")
    return re.sub(r" {2,}", " ", text.replace("\x00", "–")).strip()


def contact_rows(lines_by_id: dict[str, ResumeLine]) -> list[str]:
    """The name on its own line, then all other contact details together on one line."""
    contact = [normalize_chars(line.text) for line in lines_by_id.values() if line.kind == "contact"]
    if len(contact) <= 1:
        return contact
    details = " | ".join(part.strip(" |") for part in contact[1:])
    return [contact[0], details]


def header_rows(entry: dict, lines_by_id: dict[str, ResumeLine]) -> list[list[str]]:
    """An entry's header as [left, right] rows: organization | location, then title | dates for each role.

    Lines without verified parts show as written. app.js builds the same rows for the page.
    """
    fields = entry.get("header_fields") or {}
    rows, org_row = [], None
    for line_id in entry.get("header_line_ids", []):
        if line_id not in lines_by_id:
            continue
        parts = fields.get(line_id)
        if not parts:
            rows.append([lines_by_id[line_id].text, ""])
            continue
        if parts.get("organization") or parts.get("location"):
            if org_row is None:
                org_row = [parts.get("organization", ""), parts.get("location", "")]
                rows.append(org_row)
            else:
                org_row[0] = org_row[0] or parts.get("organization", "")
                org_row[1] = org_row[1] or parts.get("location", "")
        if parts.get("title"):
            rows.append([parts["title"], parts.get("dates", "")])
        elif parts.get("dates"):
            if rows and rows[-1] is not org_row and not rows[-1][1]:
                rows[-1][1] = parts["dates"]
            else:
                rows.append(["", parts["dates"]])
    return rows


def render_plain_text(sections: list[dict], lines_by_id: dict[str, ResumeLine]) -> str:
    """Render included bullets only. Entries with nothing to show are skipped."""
    blocks = ["\n".join(contact_rows(lines_by_id))] if contact_rows(lines_by_id) else []
    for section in sections:
        rows = []
        for entry in section.get("entries", []):
            headers = [" | ".join(normalize_chars(part) for part in row if part) for row in header_rows(entry, lines_by_id)]
            bullets = [f"- {normalize_chars(b['text'])}" for b in entry.get("bullets", []) if b.get("included")]
            rows.extend(headers + bullets)
        if rows:
            blocks.append("\n".join([normalize_chars(section["heading"]).title(), *rows]))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
