import io

from pypdf import PdfReader

from app.docx_resume import LAYOUTS, resume_blocks
from app.pdf_resume import build_pdf
from app.resume_lines import split_lines
from tests.unit.test_docx_resume import MASTER, bullet, sections


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
    margin, page_width = 0.75 * 72, 8.5 * 72
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
    reader, layout = pdf_for(sections(*workstreams(60)))
    assert not layout.fits_one_page and layout.remove_bullets > 0
    assert "Led workstream 59" in "".join(page.extract_text() for page in reader.pages)  # nothing is cut
    fewer, _ = pdf_for(sections(*workstreams(60 - layout.remove_bullets)))
    assert len(fewer.pages) == 1  # removing that many does make it fit
    one_less, _ = pdf_for(sections(*workstreams(60 - layout.remove_bullets + 1)))
    assert len(one_less.pages) == 2  # and that many is the fewest
