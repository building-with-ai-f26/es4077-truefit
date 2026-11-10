from app.resume_lines import split_lines

RESUME = """JANE DOE
EDUCATION
NYU Stern School of Business | MBA | May 2027

Experience:
Associate, Acme Corp | New York, NY | Jun 2022 – Jul 2025
- Grew regional revenue 12% by repricing 40 SKUs
"""


def test_blank_lines_skipped_and_ids_in_order():
    lines = split_lines(RESUME)
    assert [line.id for line in lines] == ["L1", "L2", "L3", "L4", "L5", "L6"]
    assert lines[5].text == "- Grew regional revenue 12% by repricing 40 SKUs"


def test_section_is_nearest_heading_above():
    lines = split_lines(RESUME)
    assert lines[2].section == "Education"
    assert lines[5].section == "Experience"


def test_notes_become_n_lines_split_into_sentences():
    lines = split_lines(RESUME, "- At Acme I also trained 3 new analysts. I built the pricing model in Excel.\n\nVolunteer tutor.")
    notes = [line for line in lines if line.source == "notes"]
    assert [(n.id, n.text) for n in notes] == [
        ("N1", "At Acme I also trained 3 new analysts."),
        ("N2", "I built the pricing model in Excel."),
        ("N3", "Volunteer tutor."),
    ]
