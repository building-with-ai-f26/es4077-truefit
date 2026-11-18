"""One-page Word download (Build 3): the same kept bullets and header rows as the copy-ready text.

Layout follows ATS-safe rules (adapted from the resume-formatter skill, Paramchoudhary/ResumeSkills, MIT):
one column, a standard font, no tables, text boxes, or Word header/footer, contact details centered in the body,
name 16 pt, headings 12 pt, body 11 pt at full size. Each job header keeps the page's layout: organization left and
location right, then title left and dates right, using a right-aligned tab stop (not a table) so ATS
parsers read it as plain lines.

To fit one page TrueFit keeps 1-inch margins while the text is 10 pt or larger, then narrows the margins (to
0.5 in), then shrinks all the text together (body to 8 pt at the smallest, name to 11 pt), from a length estimate
that uses Calibri's real character widths and line heights measured in Word. A resume that fits fills the page:
spare space goes between sections and entries, then between bullets. If it still won't fit, it says roughly how
many bullets to remove; it never cuts the student's content itself.
"""

import io
import math
import re
from dataclasses import dataclass

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from app.plain_text import contact_rows, header_rows, normalize_chars
from app import calibri_widths
from app.resume_lines import ResumeLine
from app.tailor import verified_fields

FONT = "Calibri"
NAME_PT = 16  # at full size; see name_pt()
HEADING_PT = 12  # at full size; see heading_pt()
MIN_BODY_PT, MIN_NAME_PT = 8, 11  # the student's floors: no text below 8 pt, the name no smaller than 11 pt
PAGE_WIDTH_IN, PAGE_HEIGHT_IN = 8.5, 11  # US Letter
BULLET_INDENT_IN = 0.25
# Tried in order until it fits one page: (body font pt, margin inches). Word's standard 1-inch margins while the
# text is 10 pt or larger; a longer resume narrows the margins before the text goes below 10 pt.
LAYOUTS = [(11, 1.0), (10.5, 1.0), (10, 1.0), (10, 0.9), (10, 0.8), (10, 0.7), (10, 0.6), (10, 0.5),
           (9.5, 0.5), (9, 0.5), (8.5, 0.5), (8, 0.5)]  # small margin steps keep margins as close to 1 inch as fits
# Space above each section heading, each school or job after the first in its section, and the first one (pt).
# Spare space on the page is shared out as extra_pt, the same for every section and entry gap, up to one line.
SECTION_GAP_PT, ENTRY_GAP_PT, FIRST_ENTRY_GAP_PT = 12, 8, 4
HEADING_SPACE_AFTER_PT = 3  # between a heading's rule and its first entry
BULLET_GAP_MAX_PT = 2  # once every gap is at its cap, up to this much space between bullets fills the rest
HEADING_RULE_PT = 2  # Word adds the rule's own space (1 pt) and width under each heading
RESERVE_LINES = 1  # Word's layout can only be estimated (checked against real Word, Nov 18), so one line stays free
WORD_LEADING = 1.22  # Word's single line spacing for Calibri, as a multiple of the font size
WRAP_ROOM = 0.99  # a line within 1% of the text width counts as wrapping: Word's rounding can differ slightly
BULLET_LEADING = 1.28  # bulleted lines are taller: the bullet symbol's font (measured in Word, Nov 18)


def name_pt(body_pt: float) -> float:
    """The name shrinks with the body text: 16 pt at 11 pt body, down to 11 pt at the 8 pt floor (half points)."""
    share = (body_pt - MIN_BODY_PT) / (LAYOUTS[0][0] - MIN_BODY_PT)
    return round((MIN_NAME_PT + share * (NAME_PT - MIN_NAME_PT)) * 2) / 2


def heading_pt(body_pt: float) -> float:
    """Headings stay 1 pt larger than the body text so they still stand out."""
    return body_pt + 1


@dataclass
class Layout:
    body_pt: float
    margin_in: float
    fits_one_page: bool
    remove_bullets: int  # about how many bullets to remove if it doesn't fit; 0 if it does
    extra_pt: float = 0  # added to every section and entry gap so the resume reaches the bottom margin
    bullet_extra_pt: float = 0  # space above each bullet, used only once extra_pt is at its cap


_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def gap_kinds(blocks: list[tuple]) -> list[str | None]:
    """For each block, the space above it: "section" (a heading), "entry" (a school or job after the first in its
    section), "one_line_entry" (a one-line item with nothing on the right, like "Skills: ..."), "first_entry",
    or None. Only "section" and "entry" gaps grow to fill the page."""
    kinds, seen_entry = [], False
    for i, block in enumerate(blocks):
        if block[0] == "heading":
            kinds.append("section")
            seen_entry = False
        elif block[0] == "header" and block[3]:
            following = blocks[i + 1] if i + 1 < len(blocks) else None
            # Nothing under it, nothing on the right, and no year in it: a line like "Skills: Excel, SQL",
            # not a school or job ("University of Michigan | BA | Sep 2014 – May 2018")
            one_line = not block[2] and not _YEAR.search(block[1]) and (
                following is None or following[0] == "heading" or (following[0] == "header" and following[3]))
            kinds.append("first_entry" if not seen_entry else "one_line_entry" if one_line else "entry")
            seen_entry = True
        else:
            kinds.append(None)
    return kinds


def build_docx(raw_sections, lines: list[ResumeLine]) -> tuple[bytes, Layout]:
    """raw_sections come from the browser (with the student's edits), so header lines are re-checked
    against the master resume and only kept bullets are used."""
    blocks = resume_blocks(raw_sections, lines)
    layout = choose_layout(blocks)
    return _render(blocks, layout), layout


def resume_blocks(raw_sections, lines: list[ResumeLine]) -> list[tuple]:
    """The checked resume as ordered blocks; the PDF download uses the same ones."""
    return _blocks(clean_sections(raw_sections, lines), {line.id: line for line in lines})


def clean_sections(raw_sections, lines: list[ResumeLine]) -> list[dict]:
    header_ok = {line.id for line in lines if line.kind == "header"}
    sections = []
    for raw in raw_sections if isinstance(raw_sections, list) else []:
        if not isinstance(raw, dict) or not isinstance(raw.get("heading"), str):
            continue
        entries = []
        for entry in raw.get("entries") or []:
            if not isinstance(entry, dict):
                continue
            headers = [i for i in entry.get("header_line_ids") or [] if i in header_ok]
            bullets = [{"text": b["text"], "included": True} for b in entry.get("bullets") or []
                       if isinstance(b, dict) and b.get("included") is True and isinstance(b.get("text"), str) and b["text"].strip()]
            entries.append({"header_line_ids": headers, "header_fields": verified_fields(entry.get("header_fields"), headers, lines),
                            "bullets": bullets})
        sections.append({"heading": raw["heading"], "entries": entries})
    return sections


def _blocks(sections: list[dict], lines_by_id: dict[str, ResumeLine]) -> list[tuple]:
    """The resume as (kind, ...) blocks, in order: name, details, heading, header row, bullet."""
    blocks = []
    contact = contact_rows(lines_by_id)
    if contact:
        blocks.append(("name", contact[0]))
    if len(contact) > 1:
        blocks.append(("details", contact[1]))
    for section in sections:
        rows = []
        for entry in section.get("entries", []):
            headers = [("header", normalize_chars(left), normalize_chars(right), i == 0)
                       for i, (left, right) in enumerate(header_rows(entry, lines_by_id))]
            bullets = [("bullet", normalize_chars(b["text"])) for b in entry.get("bullets", []) if b.get("included")]
            rows.extend(headers + bullets)
        if rows:
            blocks.append(("heading", normalize_chars(section["heading"]).title()))
            blocks.extend(rows)
    return blocks


FILL_SAFETY = 0.95  # Word's layout can only be estimated, so 5% of the spare space is left unused


def choose_layout(blocks: list[tuple]) -> Layout:
    for body_pt, margin_in in LAYOUTS:
        spare = _page_lines(body_pt, margin_in) - RESERVE_LINES - _estimated_height(blocks, body_pt, margin_in)
        if spare >= 0:
            return Layout(body_pt, margin_in, True, 0, *_extra_space(blocks, body_pt, spare))
    body_pt, margin_in = LAYOUTS[-1]
    over = _estimated_height(blocks, body_pt, margin_in) + RESERVE_LINES - _page_lines(body_pt, margin_in)
    bullets = [_lines(b[1], body_pt, margin_in, BULLET_INDENT_IN) * BULLET_LEADING / WORD_LEADING for b in blocks if b[0] == "bullet"]
    per_bullet = sum(bullets) / len(bullets) if bullets else 1
    return Layout(body_pt, margin_in, False, max(1, math.ceil(over / per_bullet)))


def _extra_space(blocks: list[tuple], body_pt: float, spare_lines: float) -> tuple[float, float]:
    """The spare space shared out over the section and entry gaps (at most one line each), then whatever is left
    over the bullets (at most BULLET_GAP_MAX_PT each)."""
    spare_pt = FILL_SAFETY * spare_lines * body_pt * WORD_LEADING
    gaps = sum(kind in ("section", "entry") for kind in gap_kinds(blocks))
    extra = min(body_pt * 1.2, spare_pt / gaps) if gaps else 0
    if gaps and extra < body_pt * 1.2:
        return extra, 0
    bullets = sum(block[0] == "bullet" for block in blocks)
    return extra, min(BULLET_GAP_MAX_PT, (spare_pt - gaps * extra) / bullets) if bullets else 0


def _page_lines(body_pt: float, margin_in: float) -> float:
    return (PAGE_HEIGHT_IN - 2 * margin_in) * 72 / (body_pt * WORD_LEADING)


def _lines(text: str, body_pt: float, margin_in: float, indent_in: float = 0, size_pt: float | None = None,
           bold: bool = False) -> int:
    """Lines the text takes in Word: wrapped word by word using Calibri's real character widths."""
    width_pt = (PAGE_WIDTH_IN - 2 * margin_in - indent_in) * 72 * WRAP_ROOM
    widths = calibri_widths.BOLD if bold else calibri_widths.REGULAR
    size = size_pt or body_pt
    measure = lambda s: sum(widths.get(c, 1000) for c in s) * size / 1000
    space = measure(" ")
    lines, used = 1, 0.0
    for word in text.split():
        w = measure(word)
        if used and used + space + w > width_pt:
            lines, used = lines + 1, 0.0
        used += (space if used else 0) + w
        while used > width_pt:  # a word longer than the line breaks across lines
            lines, used = lines + 1, used - width_pt
    return lines


def _estimated_height(blocks: list[tuple], body_pt: float, margin_in: float) -> float:
    """Height in body-text lines, counting wrapped bullets, larger name and heading text, and spacing
    (gaps at their base size; extra_pt is worked out from what's left)."""
    lead = body_pt * WORD_LEADING
    base = {"section": SECTION_GAP_PT, "entry": ENTRY_GAP_PT, "one_line_entry": ENTRY_GAP_PT,
            "first_entry": FIRST_ENTRY_GAP_PT}
    height = 0.0
    for block, gap in zip(blocks, gap_kinds(blocks)):
        kind = block[0]
        if gap:
            height += base[gap] / lead
        if kind == "name":
            height += name_pt(body_pt) / body_pt
        elif kind == "heading":
            height += heading_pt(body_pt) / body_pt + (HEADING_SPACE_AFTER_PT + HEADING_RULE_PT) / lead
        elif kind == "header":
            height += _lines(block[1] + "    " + block[2], body_pt, margin_in, bold=block[3])
        elif kind == "bullet":
            height += _lines(block[1], body_pt, margin_in, BULLET_INDENT_IN) * BULLET_LEADING / WORD_LEADING
        else:
            height += _lines(block[1], body_pt, margin_in)
    return height


def _render(blocks: list[tuple], layout: Layout) -> bytes:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(PAGE_WIDTH_IN), Inches(PAGE_HEIGHT_IN)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(layout.margin_in))
    text_width = section.page_width - section.left_margin - section.right_margin

    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    normal.font.size = Pt(layout.body_pt)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.line_spacing = 1.0

    for block, gap in zip(blocks, gap_kinds(blocks)):
        kind = block[0]
        if kind == "name":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(block[1])
            run.bold, run.font.size = True, Pt(name_pt(layout.body_pt))
        elif kind == "details":
            doc.add_paragraph(block[1]).alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif kind == "heading":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(SECTION_GAP_PT + layout.extra_pt)
            p.paragraph_format.space_after = Pt(HEADING_SPACE_AFTER_PT)
            run = p.add_run(block[1])
            run.bold, run.font.size = True, Pt(heading_pt(layout.body_pt))
            _bottom_rule(p)
        elif kind == "header":
            _, left, right, first = block
            p = doc.add_paragraph()
            if gap == "entry":
                p.paragraph_format.space_before = Pt(ENTRY_GAP_PT + layout.extra_pt)
            elif gap == "one_line_entry":
                p.paragraph_format.space_before = Pt(ENTRY_GAP_PT)
            elif gap == "first_entry":
                p.paragraph_format.space_before = Pt(FIRST_ENTRY_GAP_PT)
            p.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
            left_run = p.add_run(left)
            left_run.bold = first  # organization line in bold, as on the page
            if right:
                p.add_run("\t" + right)
        elif kind == "bullet":
            p = doc.add_paragraph(block[1], style="List Bullet")
            if layout.bullet_extra_pt:
                p.paragraph_format.space_before = Pt(layout.bullet_extra_pt)
                _no_contextual_spacing(p)
            p.paragraph_format.left_indent = Inches(BULLET_INDENT_IN)
            p.paragraph_format.first_line_indent = Inches(-BULLET_INDENT_IN)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def _no_contextual_spacing(paragraph) -> None:
    """Word's List Bullet style ignores space between bullets ("contextual spacing"); turn that off here."""
    off = OxmlElement("w:contextualSpacing")
    off.set(qn("w:val"), "0")
    paragraph._p.get_or_add_pPr().append(off)


def _bottom_rule(paragraph) -> None:
    """A thin line under a section heading: a paragraph border, not a table or drawing."""
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for key, value in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "808080")):
        bottom.set(qn(key), value)
    borders.append(bottom)
    paragraph._p.get_or_add_pPr().append(borders)


def file_name(lines_by_id: dict[str, ResumeLine]) -> str:
    contact = contact_rows(lines_by_id)
    name = "".join(c for c in (contact[0] if contact else "") if c.isalnum() or c == " ").strip()
    return f"{name} Resume.docx" if name and len(name) <= 60 else "Resume.docx"
