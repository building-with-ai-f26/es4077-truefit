import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.shared import Pt

from app.docx_resume import LAYOUTS, MIN_BODY_PT, MIN_NAME_PT, build_docx, file_name, heading_pt, name_pt
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
    many = [bullet(f"Led workstream {i} on pricing, forecasting, and market sizing for a consumer client portfolio") for i in range(45)]
    _, layout = open_docx(sections(*many))
    assert layout.fits_one_page and (layout.body_pt, layout.margin_in) != LAYOUTS[0]


def workstreams(n):
    return [bullet(f"Led workstream {i} on pricing, forecasting, and market sizing for a consumer client portfolio") for i in range(n)]


def test_all_text_shrinks_together_down_to_the_floors():
    # Long enough to need the smallest layout: body 8 pt, name 11 pt, headings 9 pt, and nothing under 8 pt.
    doc, layout = open_docx(sections(*workstreams(70)))
    assert (layout.body_pt, layout.margin_in) == LAYOUTS[-1] == (MIN_BODY_PT, 0.5)
    assert doc.styles["Normal"].font.size == Pt(8)
    assert doc.paragraphs[0].runs[0].font.size == Pt(MIN_NAME_PT)
    assert next(p for p in doc.paragraphs if p.text == "Experience").runs[0].font.size == Pt(9)
    sizes = [run.font.size or doc.styles["Normal"].font.size for p in doc.paragraphs for run in p.runs]
    assert min(sizes) == Pt(8)


def test_sizes_step_down_together():
    assert [(body, name_pt(body), heading_pt(body)) for body in dict.fromkeys(body for body, _ in LAYOUTS)] == [
        (11, 16, 12), (10.5, 15, 11.5), (10, 14.5, 11), (9.5, 13.5, 10.5), (9, 12.5, 10), (8.5, 12, 9.5), (8, 11, 9)]


def test_too_long_says_how_many_bullets_to_remove_and_keeps_them_all():
    doc, layout = open_docx(sections(*workstreams(80)))
    assert not layout.fits_one_page and layout.remove_bullets > 0 and layout.body_pt == MIN_BODY_PT
    assert sum(1 for p in doc.paragraphs if p.text.startswith("Led workstream")) == 80  # nothing is cut


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


# ---- Spacing and filling the page (specs/2026-11-18-fill-page-design.md) ----

from app.docx_resume import ENTRY_GAP_PT, _estimated_height, _page_lines, gap_kinds, resume_blocks  # noqa: E402

LONG_SCHOOL = "University of Michigan College of Literature, Science, and the Arts, Department of Economics Honors Program"


def two_school_sections(*bullets):
    return [
        {"heading": "Education", "entries": [{"header_line_ids": ["L4"], "bullets": []},
                                             {"header_line_ids": ["L5"], "bullets": []}]},
        {"heading": "Experience", "entries": [{"header_line_ids": ["L7"], "header_fields": {"L7": ACME_FIELDS["L6"]},
                                               "bullets": list(bullets)}]},
    ]


def two_school_master(school="University of Michigan"):
    return MASTER.replace("NYU Stern School of Business | MBA | Aug 2025 – May 2027",
                          f"NYU Stern School of Business | MBA | Aug 2025 – May 2027\n{school} | BA, Economics | Sep 2014 – May 2018")


def test_word_short_resume_uses_one_inch_margins():
    doc, layout = open_docx(sections(bullet("Built an Excel pricing model")))
    assert layout.margin_in == 1.0 and doc.sections[0].left_margin.inches == doc.sections[0].bottom_margin.inches == 1.0


def test_word_schools_have_space_between():
    doc, layout = open_docx(two_school_sections(bullet("Built an Excel pricing model")), two_school_master())
    michigan = next(p for p in doc.paragraphs if p.text.startswith("University of Michigan"))
    assert michigan.paragraph_format.space_before >= Pt(ENTRY_GAP_PT + layout.extra_pt) >= Pt(ENTRY_GAP_PT)


def test_word_extra_space_fills_estimate():
    raw = two_school_sections(*workstreams(33))  # fits at 11 pt, 1 inch, with spare space under the cap
    _, layout = open_docx(raw, two_school_master())
    blocks = resume_blocks(raw, split_lines(two_school_master(), None))
    lead = layout.body_pt * 1.22
    gaps = sum(kind in ("section", "entry") for kind in gap_kinds(blocks))  # Education, Experience, Michigan
    used = _estimated_height(blocks, layout.body_pt, layout.margin_in) * lead + gaps * layout.extra_pt
    assert 0 < layout.extra_pt < layout.body_pt * 1.2
    assert used <= _page_lines(layout.body_pt, layout.margin_in) * lead


def test_word_extra_space_counts_wrapped_headers():
    raw = two_school_sections(*workstreams(33))  # fits at 11 pt, 1 inch, with spare space under the cap
    _, short_name = open_docx(raw, two_school_master())
    _, long_name = open_docx(raw, two_school_master(LONG_SCHOOL))
    # the wrapped name takes room: less extra space, or a smaller layout
    assert long_name.extra_pt < short_name.extra_pt or LAYOUTS.index((long_name.body_pt, long_name.margin_in)) > LAYOUTS.index((short_name.body_pt, short_name.margin_in))


def test_word_full_page_gets_no_extra_space():
    _, layout = open_docx(sections(*workstreams(80)))
    assert layout.extra_pt == 0 and not layout.fits_one_page


def test_word_wrapping_matches_real_word():
    """Checked against Microsoft Word on Nov 18: this bullet takes 2 lines at 11 pt with 1-inch margins and
    1 line at 10 pt with 0.7-inch margins (it used to be estimated at 2 for both, leaving the page a third empty)."""
    from app.docx_resume import BULLET_INDENT_IN, _lines
    text = "Led pricing and market sizing workstream 0 for a consumer portfolio, growing revenue 12% across 3 regions"
    assert _lines(text, 11, 1.0, BULLET_INDENT_IN) == 2
    assert _lines(text, 10, 0.7, BULLET_INDENT_IN) == 1
    assert _lines(text, 10.5, 1.0, BULLET_INDENT_IN) == 2


def test_word_bullet_lines_are_taller():
    """Measured in Word on Nov 18: bulleted lines are 1.26-1.28 times the font size apart (the bullet symbol is taller),
    plain lines 1.22. Counting bullets at 1.22 let 40-bullet resumes spill onto a second page."""
    one_bullet = _estimated_height([("bullet", "Built a model")], 10, 1.0)
    one_line = _estimated_height([("details", "Built a model")], 10, 1.0)
    assert one_bullet / one_line >= 1.28 / 1.22


def test_word_space_between_bullets_only_after_gaps_are_full():
    doc, layout = open_docx(two_school_sections(*workstreams(20)), two_school_master())  # gaps at the cap, room left
    assert layout.extra_pt == layout.body_pt * 1.2 and 0 < layout.bullet_extra_pt <= 2
    bullets = [p for p in doc.paragraphs if p.text.startswith("Led workstream")]
    assert all(p.paragraph_format.space_before == Pt(layout.bullet_extra_pt) for p in bullets)
    _, filled = open_docx(two_school_sections(*workstreams(33)), two_school_master())  # gaps not full
    assert filled.bullet_extra_pt == 0
