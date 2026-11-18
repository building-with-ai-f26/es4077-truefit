import io

from pypdf import PdfReader

from app.docx_resume import ENTRY_GAP_PT, LAYOUTS, resume_blocks
from app.pdf_resume import build_pdf
from app.resume_lines import split_lines
from tests.unit.test_docx_resume import ACME_FIELDS, MASTER, bullet, sections


def pdf_for(raw_sections):
    content, layout = build_pdf(resume_blocks(raw_sections, split_lines(MASTER, None)))
    return PdfReader(io.BytesIO(content)), layout


def placed_text(page):
    """Each text run with its x position from the page's left edge, so alignment can be checked."""
    runs = []
    page.extract_text(visitor_text=lambda text, cm, tm, font, size: text.strip() and runs.append((text.strip(), round(cm[4] + tm[4], 1))))
    return runs


def test_text_based_one_page_with_only_kept_bullets():
    reader, layout = pdf_for(sections(bullet("Repriced 40 SKUs, growing revenue 12%"), bullet("Removed bullet", included=False)))
    assert len(reader.pages) == 1 and layout.fits_one_page and (layout.body_pt, layout.margin_in) == LAYOUTS[0]
    text = reader.pages[0].extract_text()
    for expected in ("Jordan Lee", "Education", "Acme Corp", "New York, NY", "Associate", "Jun 2022 – Jul 2025",
                     "Repriced 40 SKUs, growing revenue 12%"):
        assert expected in text
    assert "Removed bullet" not in text


def test_name_centered_and_location_and_dates_on_the_right():
    reader, _ = pdf_for(sections(bullet("Built an Excel pricing model")))
    runs = dict(placed_text(reader.pages[0]))
    margin, page_width = 1.0 * 72, 8.5 * 72
    assert runs["Acme Corp"] == runs["Associate"] == runs["Education"] == margin  # left-aligned at the margin
    assert abs(runs["Jordan Lee"] - (page_width - 97) / 2) < 6  # centered ("Jordan Lee" at 16 pt bold is about 97 pt wide)
    assert runs["jordan@example.com | (555) 010-0100 | New York, NY"] > margin + 40  # centered too
    assert runs["New York, NY"] > page_width / 2 and runs["Jun 2022 – Jul 2025"] > page_width / 2  # on the right


def workstreams(n):
    return [bullet(f"Led workstream {i} on pricing, forecasting, and market sizing for a consumer client portfolio") for i in range(n)]


def test_longer_resume_steps_down_size_and_margins():
    reader, layout = pdf_for(sections(*workstreams(45)))
    assert len(reader.pages) == 1 and layout.fits_one_page and (layout.body_pt, layout.margin_in) != LAYOUTS[0]


def test_too_long_measures_exactly_how_many_to_remove_and_cuts_nothing():
    reader, layout = pdf_for(sections(*workstreams(80)))
    assert not layout.fits_one_page and layout.remove_bullets > 0 and layout.body_pt == 8
    assert "Led workstream 79" in "".join(page.extract_text() for page in reader.pages)  # nothing is cut
    fewer, _ = pdf_for(sections(*workstreams(80 - layout.remove_bullets)))
    assert len(fewer.pages) == 1  # removing that many does make it fit
    one_less, _ = pdf_for(sections(*workstreams(80 - layout.remove_bullets + 1)))
    assert len(one_less.pages) == 2  # and that many is the fewest


# ---- Spacing and filling the page (specs/2026-11-18-fill-page-design.md) ----

TWO_SCHOOLS = MASTER.replace("NYU Stern School of Business | MBA | Aug 2025 – May 2027",
                             "NYU Stern School of Business | MBA | Aug 2025 – May 2027\n"
                             "University of Michigan | BA, Economics | Sep 2014 – May 2018")


def two_schools(*bullets):
    content, layout = build_pdf(resume_blocks([
        {"heading": "Education", "entries": [{"header_line_ids": ["L4"], "bullets": []},
                                             {"header_line_ids": ["L5"], "bullets": []}]},
        {"heading": "Experience", "entries": [{"header_line_ids": ["L7"], "header_fields": {"L7": ACME_FIELDS["L6"]},
                                               "bullets": list(bullets)}]},
    ], split_lines(TWO_SCHOOLS, None)))
    return PdfReader(io.BytesIO(content)), layout


def baselines(page):
    """Each text run with its height above the bottom of the page."""
    runs = []
    page.extract_text(visitor_text=lambda text, cm, tm, font, size: text.strip() and runs.append((text.strip(), round(cm[5] + tm[5], 1))))
    return runs


def test_layouts_start_at_one_inch():
    assert LAYOUTS[:3] == [(11, 1.0), (10.5, 1.0), (10, 1.0)] and LAYOUTS[-1] == (8, 0.5)


def test_schools_have_space_between():
    reader, layout = two_schools(bullet("Built an Excel pricing model"))
    y = dict(baselines(reader.pages[0]))
    nyu = next(v for k, v in y.items() if k.startswith("NYU Stern"))
    michigan = next(v for k, v in y.items() if k.startswith("University of Michigan"))
    assert nyu - michigan >= layout.body_pt * 1.2 + ENTRY_GAP_PT


def test_short_resume_gaps_are_capped():
    reader, layout = two_schools(bullet("Built an Excel pricing model"))
    assert layout.extra_pt == layout.body_pt * 1.2  # each gap grows by at most one line
    assert min(y for _, y in baselines(reader.pages[0])) > 72 + 100  # so space stays at the bottom


def test_pdf_fills_the_page():
    filled = 0
    for n in range(10, 40):
        reader, layout = two_schools(*workstreams(n))
        if (layout.body_pt, layout.margin_in) == LAYOUTS[0] and layout.extra_pt < layout.body_pt * 1.2:
            assert len(reader.pages) == 1
            assert min(y for _, y in baselines(reader.pages[0])) <= 72 + layout.body_pt * 1.2 * 1.5  # ends at the margin
            filled += 1
    assert filled  # at least one length was filled by spreading, not capped


def test_full_page_gets_no_extra_space():
    _, layout = pdf_for(sections(*workstreams(80)))
    assert layout.extra_pt == 0 and not layout.fits_one_page


def test_no_entry_gaps():
    content, layout = build_pdf([("name", "Jordan Lee"), ("details", "jordan@example.com"), ("heading", "Education"),
                                 ("header", "NYU Stern", "2027", True)])
    assert len(PdfReader(io.BytesIO(content)).pages) == 1 and layout.fits_one_page


def test_space_between_bullets_only_after_gaps_are_full():
    _, short = two_schools(bullet("Built an Excel pricing model"))
    assert short.extra_pt == short.body_pt * 1.2 and 0 < short.bullet_extra_pt <= 2  # gaps full, so bullets spread a little
    for n in range(10, 40):
        _, layout = two_schools(*workstreams(n))
        if layout.extra_pt < layout.body_pt * 1.2:
            assert layout.bullet_extra_pt == 0  # gaps not full yet: bullets stay together
