"""One-page PDF download: the same blocks as the Word file, drawn with reportlab.

Same layout as the .docx: name and contact centered, headings with a thin rule, each job's organization
left and location right, then title left and dates right. The text is real text (not an image), so ATS
parsers can read it. Helvetica stands in for Calibri, which can't be bundled.

Unlike the Word file, the PDF's page count can be measured exactly, so TrueFit renders each layout and keeps
the first that fits one page. If none does, it measures how many bullets would need to go and cuts nothing.
"""

import io

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, HRFlowable, PageTemplate, Paragraph, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from app.docx_resume import BULLET_INDENT_IN, HEADING_PT, LAYOUTS, NAME_PT, Layout

FONT, BOLD = "Helvetica", "Helvetica-Bold"
RIGHT_SHARE = 0.4  # the right column (location, dates) gets up to 40% of the line


def build_pdf(blocks: list[tuple]) -> tuple[bytes, Layout]:
    for body_pt, margin_in in LAYOUTS:
        content, pages = _render(blocks, body_pt, margin_in)
        if pages == 1:
            return content, Layout(body_pt, margin_in, True, 0)
    return content, Layout(body_pt, margin_in, False, _bullets_to_remove(blocks, body_pt, margin_in))


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


def _render(blocks: list[tuple], body_pt: float, margin_in: float) -> tuple[bytes, int]:
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
        "name": ParagraphStyle("name", parent=body, fontName=BOLD, fontSize=NAME_PT, leading=NAME_PT * 1.2, alignment=TA_CENTER),
        "details": ParagraphStyle("details", parent=body, alignment=TA_CENTER),
        "heading": ParagraphStyle("heading", parent=body, fontName=BOLD, fontSize=HEADING_PT, leading=HEADING_PT * 1.2, spaceBefore=10),
        "left": body,
        "left_bold": ParagraphStyle("left_bold", parent=body, fontName=BOLD),
        "right": ParagraphStyle("right", parent=body, alignment=TA_RIGHT),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=BULLET_INDENT_IN * inch, bulletIndent=0.08 * inch),
    }

    story = []
    for block in blocks:
        kind, text = block[0], escape(block[1])
        if kind in ("name", "details"):
            story.append(Paragraph(text, styles[kind]))
        elif kind == "heading":
            story.append(Paragraph(text, styles["heading"]))
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#808080"), spaceBefore=1, spaceAfter=3))
        elif kind == "header":
            _, left, right, first = block
            if first:
                story.append(Spacer(1, 5))
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
