import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.shared import Pt

from app.docx_resume import LAYOUTS, build_docx, file_name
from app.resume_lines import split_lines

MASTER = """Jordan Lee
jordan@example.com | (555) 010-0100 | New York, NY
EDUCATION
NYU Stern School of Business | MBA | Aug 2025 – May 2027
EXPERIENCE
Associate, Acme Corp | New York, NY | Jun 2022 – Jul 2025
Grew regional revenue 12% by repricing 40 SKUs, adding $1.2M in annual profit
Built Excel pricing model used by 3 regional teams
Presented quarterly pricing reviews to the VP of Sales"""

ACME_FIELDS = {"L6": {"title": "Associate", "organization": "Acme Corp", "location": "New York, NY", "dates": "Jun 2022 – Jul 2025"}}


def sections(*bullets, extra=()):
    return [
        {"heading": "Education", "entries": [{"header_line_ids": ["L4"], "bullets": []}]},
        {"heading": "Experience", "entries": [{"header_line_ids": ["L6"], "header_fields": ACME_FIELDS, "bullets": list(bullets)}, *extra]},
    ]


def bullet(text, included=True):
    return {"text": text, "included": included}


def open_docx(raw_sections, master=MASTER):
    content, layout = build_docx(raw_sections, split_lines(master, None))
    return Document(io.BytesIO(content)), layout


def texts(doc):
    return [p.text for p in doc.paragraphs]


def test_contents_in_order_with_only_kept_bullets():
    doc, _ = open_docx(sections(bullet("Repriced 40 SKUs, growing revenue 12%"), bullet("Removed bullet", included=False)))
    assert texts(doc) == [
        "Jordan Lee",
        "jordan@example.com | (555) 010-0100 | New York, NY",
        "Education",
        "NYU Stern School of Business | MBA | Aug 2025 – May 2027",
        "Experience",
        "Acme Corp\tNew York, NY",
        "Associate\tJun 2022 – Jul 2025",
        "Repriced 40 SKUs, growing revenue 12%",
    ]


def test_header_rows_keep_left_and_right_alignment():
    # Organization left / location right, then title left / dates right, with a right tab at the margin.
    doc, _ = open_docx(sections(bullet("Built an Excel pricing model")))
    section = doc.sections[0]
    text_width = section.page_width - section.left_margin - section.right_margin
    org, role = (p for p in doc.paragraphs if "\t" in p.text)
    for p in (org, role):
        stops = list(p.paragraph_format.tab_stops)
        assert [(s.alignment, s.position) for s in stops] == [(WD_TAB_ALIGNMENT.RIGHT, text_width)]
    assert org.runs[0].text == "Acme Corp" and org.runs[0].bold
    assert role.runs[0].text == "Associate" and not role.runs[0].bold


def test_ats_safe_structure():
    doc, _ = open_docx(sections(bullet("Built an Excel pricing model")))
    assert doc.tables == []
    assert all(not p.text for p in doc.sections[0].header.paragraphs)  # contact details live in the body
    assert all(not p.text for p in doc.sections[0].footer.paragraphs)
    assert doc.styles["Normal"].font.name == "Calibri"
    name = doc.paragraphs[0].runs[0]
    assert name.bold and name.font.size == Pt(16)
    assert doc.paragraphs[0].alignment == doc.paragraphs[1].alignment == WD_ALIGN_PARAGRAPH.CENTER  # name and contact
    assert all(p.alignment is None for p in doc.paragraphs[2:])  # everything else stays left
    heading = next(p for p in doc.paragraphs if p.text == "Experience").runs[0]
    assert heading.bold and heading.font.size == Pt(12)
    assert next(p for p in doc.paragraphs if p.text.startswith("Built")).style.name == "List Bullet"


def test_us_letter_and_first_layout_when_short():
    doc, layout = open_docx(sections(bullet("Built an Excel pricing model")))
    assert (doc.sections[0].page_width.inches, doc.sections[0].page_height.inches) == (8.5, 11)
    assert (layout.body_pt, layout.margin_in, layout.fits_one_page, layout.remove_bullets) == (*LAYOUTS[0], True, 0)


def test_longer_resume_steps_down_size_and_margins():
    many = [bullet(f"Led workstream {i} on pricing, forecasting, and market sizing for a consumer client portfolio") for i in range(30)]
    _, layout = open_docx(sections(*many))
    assert layout.fits_one_page and (layout.body_pt, layout.margin_in) != LAYOUTS[0]


def test_too_long_says_how_many_bullets_to_remove_and_keeps_them_all():
    many = [bullet(f"Led workstream {i} on pricing, forecasting, and market sizing for a consumer client portfolio") for i in range(60)]
    doc, layout = open_docx(sections(*many))
    assert not layout.fits_one_page and layout.remove_bullets > 0
    assert sum(1 for p in doc.paragraphs if p.text.startswith("Led workstream")) == 60  # nothing is cut


def test_header_parts_not_in_the_line_are_ignored():
    # Edited in the browser: a title the master resume doesn't have shows the line as written instead.
    tampered = {"L6": {**ACME_FIELDS["L6"], "title": "Vice President"}}
    raw = sections(bullet("Built an Excel pricing model"))
    raw[1]["entries"][0]["header_fields"] = tampered
    doc, _ = open_docx(raw)
    assert "Vice President" not in "\n".join(texts(doc))
    assert "Associate, Acme Corp | New York, NY | Jun 2022 – Jul 2025" in texts(doc)


def test_file_name_uses_the_name_line():
    lines = {line.id: line for line in split_lines(MASTER, None)}
    assert file_name(lines) == "Jordan Lee Resume.docx"
