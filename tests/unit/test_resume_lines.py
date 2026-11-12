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


def test_line_kinds_with_bullet_symbols():
    kinds = [line.kind for line in split_lines(RESUME)]
    assert kinds == ["contact", "heading", "header", "heading", "header", "bullet"]


def test_line_kinds_without_bullet_symbols():
    resume = """EXPERIENCE
Acme Corp
Senior Analyst
New York, NY | Jun 2022 – Jul 2025
Grew regional revenue 12% in 2024 by repricing 40 SKUs
Built Excel pricing model used by 3 regional teams"""
    kinds = [line.kind for line in split_lines(resume)]
    assert kinds == ["heading", "header", "header", "header", "bullet", "bullet"]


# A made-up resume pasted from a PDF: line breaks were lost, so headers are glued onto bullets.
GLUED = """Pat Lee 1 Main St, New York, NY | 555-0100 | pat@example.com EDUCATION STATE UNIVERSITY, School of Business New York, NY Master of Business Administration Aug. 2025 - Present Concentrations: Strategy, Finance
●Leadership: VP, Tech Club; Career Mentor (advising 10first-year students)RIVER COLLEGE Boston, MA Bachelor of Arts in Economics Aug. 2012 - May 2016 EXPERIENCE NORTHWIND Seattle, WA Product Intern June 2026 - Aug. 2026
●Built the team's first planning model, finding 30 gaps across 16 campaigns and better outputsCONTOSO New York, NY Marketing Manager June 2022 - Aug. 2025
●Drove 20% subscriber growth through 30 paid campaigns for top programming prioritiesMarketing Assistant May 2017 - June 2022
●Managed a $10M budget with Operations andFinance teams
FABRIKAM STUDIOS
New York, NY
Executive Assistant 2016 - 2017
●Coordinated 18 press screening eventsADDITIONAL
●Tools: Airtable, GitHub Copilot CLI, SQL"""


def test_restores_line_breaks_from_pdf_paste():
    lines = split_lines(GLUED)
    got = [(line.kind, line.section, line.text) for line in lines]
    assert got == [
        ("contact", None, "Pat Lee 1 Main St, New York, NY | 555-0100 | pat@example.com"),
        ("heading", "Education", "EDUCATION"),
        ("header", "Education", "STATE UNIVERSITY, School of Business New York, NY Master of Business Administration Aug. 2025 - Present"),
        ("header", "Education", "Concentrations: Strategy, Finance"),
        ("bullet", "Education", "● Leadership: VP, Tech Club; Career Mentor (advising 10first-year students)"),
        ("header", "Education", "RIVER COLLEGE Boston, MA Bachelor of Arts in Economics Aug. 2012 - May 2016"),
        ("heading", "Experience", "EXPERIENCE"),
        ("header", "Experience", "NORTHWIND Seattle, WA Product Intern June 2026 - Aug. 2026"),
        ("bullet", "Experience", "● Built the team's first planning model, finding 30 gaps across 16 campaigns and better outputs"),
        ("header", "Experience", "CONTOSO New York, NY Marketing Manager June 2022 - Aug. 2025"),
        ("bullet", "Experience", "● Drove 20% subscriber growth through 30 paid campaigns for top programming priorities"),
        ("header", "Experience", "Marketing Assistant May 2017 - June 2022"),
        ("bullet", "Experience", "● Managed a $10M budget with Operations andFinance teams"),
        ("header", "Experience", "FABRIKAM STUDIOS"),
        ("header", "Experience", "New York, NY"),
        ("header", "Experience", "Executive Assistant 2016 - 2017"),
        ("bullet", "Experience", "● Coordinated 18 press screening events"),
        ("heading", "Additional", "ADDITIONAL"),
        ("bullet", "Additional", "● Tools: Airtable, GitHub Copilot CLI, SQL"),
    ]
