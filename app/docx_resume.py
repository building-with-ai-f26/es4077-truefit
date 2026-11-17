"""One-page Word download (Build 3): the same kept bullets and header rows as the copy-ready text.

Layout follows ATS-safe rules (adapted from the resume-formatter skill, Paramchoudhary/ResumeSkills, MIT):
one column, a standard font, no tables, text boxes, or Word header/footer, contact details in the body,
name 16 pt, headings 12 pt, body 10-11 pt. Each job header keeps the page's layout: organization left and
location right, then title left and dates right, using a right-aligned tab stop (not a table) so ATS
parsers read it as plain lines.

To fit one page TrueFit tries smaller sizes and margins from a length estimate. If it still won't fit, it
says roughly how many bullets to remove; it never cuts the student's content itself.
"""

import io
import math
from dataclasses import dataclass

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from app.plain_text import contact_rows, header_rows, normalize_chars
from app.resume_lines import ResumeLine
from app.tailor import verified_fields

FONT = "Calibri"
NAME_PT = 16
HEADING_PT = 12
PAGE_WIDTH_IN, PAGE_HEIGHT_IN = 8.5, 11  # US Letter
BULLET_INDENT_IN = 0.25
# Tried in order until the estimate fits one page: (body font pt, margin inches).
LAYOUTS = [(11, 0.75), (10.5, 0.6), (10, 0.5)]
AVG_CHAR_EM = 0.5  # average Calibri character width as a share of the font size; rounded up to stay safe


@dataclass
class Layout:
    body_pt: float
    margin_in: float
    fits_one_page: bool
    remove_bullets: int  # about how many bullets to remove if it doesn't fit; 0 if it does


def build_docx(raw_sections, lines: list[ResumeLine]) -> tuple[bytes, Layout]:
    """raw_sections come from the browser (with the student's edits), so header lines are re-checked
    against the master resume and only kept bullets are used."""
    lines_by_id = {line.id: line for line in lines}
    blocks = _blocks(clean_sections(raw_sections, lines), lines_by_id)
    layout = choose_layout(blocks)
    return _render(blocks, layout), layout


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


def choose_layout(blocks: list[tuple]) -> Layout:
    for body_pt, margin_in in LAYOUTS:
        if _estimated_height(blocks, body_pt, margin_in) <= _page_lines(body_pt, margin_in):
            return Layout(body_pt, margin_in, True, 0)
    body_pt, margin_in = LAYOUTS[-1]
    over = _estimated_height(blocks, body_pt, margin_in) - _page_lines(body_pt, margin_in)
    bullets = [_lines(b[1], body_pt, margin_in, BULLET_INDENT_IN) for b in blocks if b[0] == "bullet"]
    per_bullet = sum(bullets) / len(bullets) if bullets else 1
    return Layout(body_pt, margin_in, False, max(1, math.ceil(over / per_bullet)))


def _page_lines(body_pt: float, margin_in: float) -> float:
    return (PAGE_HEIGHT_IN - 2 * margin_in) * 72 / (body_pt * 1.2)


def _lines(text: str, body_pt: float, margin_in: float, indent_in: float = 0, size_pt: float | None = None) -> int:
    width_pt = (PAGE_WIDTH_IN - 2 * margin_in - indent_in) * 72
    per_line = max(1, int(width_pt / ((size_pt or body_pt) * AVG_CHAR_EM)))
    return max(1, math.ceil(len(text) / per_line))


def _estimated_height(blocks: list[tuple], body_pt: float, margin_in: float) -> float:
    """Height in body-text lines, counting wrapped bullets, larger name and heading text, and spacing."""
    height = 0.0
    for block in blocks:
        kind = block[0]
        if kind == "name":
            height += NAME_PT / body_pt
        elif kind == "heading":
            height += HEADING_PT / body_pt + 0.9  # space above plus the rule under it
        elif kind == "header":
            height += _lines(block[1] + "    " + block[2], body_pt, margin_in) + (0.4 if block[3] else 0)
        elif kind == "bullet":
            height += _lines(block[1], body_pt, margin_in, BULLET_INDENT_IN)
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

    for block in blocks:
        kind = block[0]
        if kind == "name":
            run = doc.add_paragraph().add_run(block[1])
            run.bold, run.font.size = True, Pt(NAME_PT)
        elif kind == "details":
            doc.add_paragraph(block[1])
        elif kind == "heading":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            run = p.add_run(block[1])
            run.bold, run.font.size = True, Pt(HEADING_PT)
            _bottom_rule(p)
        elif kind == "header":
            _, left, right, first = block
            p = doc.add_paragraph()
            if first:
                p.paragraph_format.space_before = Pt(5)
            p.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
            left_run = p.add_run(left)
            left_run.bold = first  # organization line in bold, as on the page
            if right:
                p.add_run("\t" + right)
        elif kind == "bullet":
            p = doc.add_paragraph(block[1], style="List Bullet")
            p.paragraph_format.left_indent = Inches(BULLET_INDENT_IN)
            p.paragraph_format.first_line_indent = Inches(-BULLET_INDENT_IN)

    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


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
