from app.plain_text import normalize_chars, render_plain_text
from app.resume_lines import split_lines

LINES = {line.id: line for line in split_lines("""EDUCATION
NYU Stern | MBA | Aug 2025 – May 2027
EXPERIENCE
Associate, Café Corp | New York, NY | Jun 2022—Present""")}


def test_normalize_keeps_date_range_dash_only():
    assert normalize_chars("• “Led” work — fast | Jun 2022—Present") == '"Led" work - fast | Jun 2022 – Present'
    assert normalize_chars("Café") == "Cafe"
    assert normalize_chars("Senior Associate — Coho Consulting • Los Angeles") == "Senior Associate - Coho Consulting | Los Angeles"


def test_render_includes_only_included_bullets_and_is_ascii():
    sections = [
        {"heading": "EDUCATION", "entries": [{"header_line_ids": ["L2"], "bullets": []}]},
        {"heading": "Experience", "entries": [{"header_line_ids": ["L4"], "bullets": [
            {"text": "Grew revenue 12%", "included": True},
            {"text": "Led a team of 8", "included": False},
        ]}]},
    ]
    text = render_plain_text(sections, LINES)
    assert text == ("Education\nNYU Stern | MBA | Aug 2025 – May 2027\n\n"
                    "Experience\nAssociate, Cafe Corp | New York, NY | Jun 2022 – Present\n- Grew revenue 12%\n")
    assert all(c.isascii() or c == "–" for c in text)


def test_empty_sections_are_skipped():
    assert render_plain_text([{"heading": "Skills", "entries": [{"header_line_ids": [], "bullets": [
        {"text": "x", "included": False}]}]}], LINES) == ""
