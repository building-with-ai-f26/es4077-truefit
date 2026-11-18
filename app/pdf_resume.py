"""One-page PDF download: the same blocks as the Word file, drawn with reportlab.

Same layout as the .docx: name and contact centered, headings with a thin rule, each job's organization
left and location right, then title left and dates right. The text is real text (not an image), so ATS
parsers can read it. Helvetica stands in for Calibri, which can't be bundled.

Unlike the Word file, the PDF's page count can be measured exactly, so TrueFit renders each layout and keeps
the first that fits one page (1-inch margins first; see LAYOUTS), then fills the page by measuring the most space
it can add between sections and entries, then bullets. If none fits, it measures how many bullets would need to
go and cuts nothing.
"""

import io

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, HRFlowable, PageTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from app.docx_resume import (BULLET_GAP_MAX_PT, BULLET_INDENT_IN, ENTRY_GAP_PT, FIRST_ENTRY_GAP_PT, LAYOUTS, SECTION_GAP_PT, Layout, gap_kinds,
                              heading_pt, name_pt)

FONT, BOLD = "Helvetica", "Helvetica-Bold"
RIGHT_SHARE = 0.4  # the right column (location, dates) gets up to 40% of the line


FILL_ROUNDS = 8  # binary search steps for the extra space; about 0.05 pt at 11 pt text


def build_pdf(blocks: list[tuple]) -> tuple[bytes, Layout]:
    for body_pt, margin_in in LAYOUTS:
        content, pages = _render(blocks, body_pt, margin_in)
        if pages == 1:
            extra, bullet_extra, content = _fill_page(blocks, body_pt, margin_in, content)
            return content, Layout(body_pt, margin_in, True, 0, extra, bullet_extra)
    return content, Layout(body_pt, margin_in, False, _bullets_to_remove(blocks, body_pt, margin_in))


def _fill_page(blocks: list[tuple], body_pt: float, margin_in: float, content: bytes) -> tuple[float, float, bytes]:
    """The most extra space per gap (up to one line) that still fits one page, so the resume reaches the bottom;
    if every gap reaches its cap, then the most space between bullets (up to BULLET_GAP_MAX_PT)."""
    cap = body_pt * 1.2
    capped, pages = _render(blocks, body_pt, margin_in, cap)
    if pages != 1:
        extra, content = _most_that_fits(lambda x: _render(blocks, body_pt, margin_in, x), cap, content)
        return extra, 0, content
    if not any(block[0] == "bullet" for block in blocks):
        return cap, 0, capped
    bullet_extra, content = _most_that_fits(lambda x: _render(blocks, body_pt, margin_in, cap, x), BULLET_GAP_MAX_PT, capped)
    return cap, bullet_extra, content


def _most_that_fits(render, high: float, fallback: bytes) -> tuple[float, bytes]:
    """Binary search for the largest value in [0, high] whose render is one page."""
    low, best = 0.0, fallback
    trial, pages = render(high)
    if pages == 1:
        return high, trial
    for _ in range(FILL_ROUNDS):
        middle = (low + high) / 2
        trial, pages = render(middle)
        if pages == 1:
            low, best = middle, trial
        else:
            high = middle
    return low, best


def _bullets_to_remove(blocks: list[tuple], body_pt: float, margin_in: float) -> int:
    """The fewest bullets whose removal makes it fit, measured on trial copies (the student's file keeps all)."""
    positions = [i for i, block in enumerate(blocks) if block[0] == "bullet"]
    low, high = 1, len(positions)
    while low < high:
        k = (low + high) // 2
        trial = [b for i, b in enumerate(blocks) if i not in set(positions[-k:])]
        if _render(trial, body_pt, margin_in)[1] == 1:
            high = k
        else:
            low = k + 1
    return max(1, low)


def _render(blocks: list[tuple], body_pt: float, margin_in: float, extra_pt: float = 0,
            bullet_extra_pt: float = 0) -> tuple[bytes, int]:
    out = io.BytesIO()
    margin = margin_in * inch
    width, height = LETTER[0] - 2 * margin, LETTER[1] - 2 * margin
    # No frame padding, so headings, bullets, and job headers all start exactly at the margin.
    frame = Frame(margin, margin, width, height, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    pages = []
    doc = BaseDocTemplate(out, pagesize=LETTER, title="Resume",
                          pageTemplates=[PageTemplate(frames=[frame], onPage=lambda c, d: pages.append(1))])
    lead = body_pt * 1.2
    body = ParagraphStyle("body", fontName=FONT, fontSize=body_pt, leading=lead)
    styles = {
        "name": ParagraphStyle("name", parent=body, fontName=BOLD, fontSize=name_pt(body_pt), leading=name_pt(body_pt) * 1.2,
                               alignment=TA_CENTER),
        "details": ParagraphStyle("details", parent=body, alignment=TA_CENTER),
        "heading": ParagraphStyle("heading", parent=body, fontName=BOLD, fontSize=heading_pt(body_pt),
                                  leading=heading_pt(body_pt) * 1.2),
        "left": body,
        "left_bold": ParagraphStyle("left_bold", parent=body, fontName=BOLD),
        "right": ParagraphStyle("right", parent=body, alignment=TA_RIGHT),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=BULLET_INDENT_IN * inch, bulletIndent=0.08 * inch,
                                 spaceBefore=bullet_extra_pt),
    }

    gaps = {"section": SECTION_GAP_PT + extra_pt, "entry": ENTRY_GAP_PT + extra_pt, "one_line_entry": ENTRY_GAP_PT,
            "first_entry": FIRST_ENTRY_GAP_PT}
    story = []
    for block, gap in zip(blocks, gap_kinds(blocks)):
        kind, text = block[0], escape(block[1])
        if gap:
            story.append(Spacer(1, gaps[gap]))
        if kind in ("name", "details"):
            story.append(Paragraph(text, styles[kind]))
        elif kind == "heading":
            story.append(Paragraph(text, styles["heading"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#808080"), spaceBefore=1, spaceAfter=3))
        elif kind == "header":
            _, left, right, first = block
            left_par = Paragraph(escape(left), styles["left_bold" if first else "left"])
            if not right:
                story.append(left_par)
                continue
            right_w = min(width * RIGHT_SHARE, len(right) * body_pt * 0.55 + 4)
            row = Table([[left_par, Paragraph(escape(right), styles["right"])]], colWidths=[width - right_w, right_w], hAlign="LEFT")
            row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                     ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            story.append(row)
        elif kind == "bullet":
            story.append(Paragraph(text, styles["bullet"], bulletText="•"))

    doc.build(story)
    return out.getvalue(), len(pages)
