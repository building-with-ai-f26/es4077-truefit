from app.resume_lines import split_lines
from app.trace_check import deterministic_check, extract_numbers, posting_only_terms

MASTER = """Experience
Associate, Acme Corp | New York, NY | Jun 2022 – Jul 2025
Grew regional revenue 12% by repricing 40 SKUs, adding $1.2M in annual profit
Built Excel pricing model used by 3 regional teams"""
POSTING = "Strategy Associate. Requirements: SQL and Tableau required, strong Excel, financial modeling. MBA preferred."
LINES = {line.id: line for line in split_lines(MASTER)}
ONLY = posting_only_terms(POSTING, MASTER)


def check(text, cited=("L3",)):
    return deterministic_check(text, list(cited), LINES, ONLY)


def test_extract_numbers_units():
    assert extract_numbers("$1.2M, 12%, 3x, 1,200 and 40") == {("1.2", "$m"), ("12", "%"), ("3", "x"), ("1200", ""), ("40", "")}


def test_reworded_bullet_with_exact_numbers_passes():
    assert check("Repriced 40 SKUs, growing regional revenue 12% and adding $1.2M in annual profit") is None


def test_changed_metric_is_flagged():
    assert check("Grew regional revenue 15% by repricing 40 SKUs") == '"15%" isn\'t in the cited lines'


def test_number_from_another_line_is_flagged():
    assert check("Built a pricing model used by 3 teams", cited=("L3",)) is not None
    assert check("Built a pricing model used by 3 teams", cited=("L4",)) is None


def test_posting_only_skill_is_flagged():
    assert check("Used SQL to reprice 40 SKUs") == '"sql" is from the posting, not your resume or notes'


def test_generic_posting_words_are_fine():
    assert check("Drove strategy work that grew regional revenue 12%") is None


def test_missing_or_unknown_citation_is_flagged():
    assert check("Grew revenue 12%", cited=()) is not None
    assert check("Grew revenue 12%", cited=("L99",)) is not None


def test_notes_count_as_student_material():
    lines = split_lines(MASTER, "I used Tableau dashboards to report weekly results.")
    only = posting_only_terms(POSTING, " ".join(line.text for line in lines))
    by_id = {line.id: line for line in lines}
    assert deterministic_check("Reported weekly results with Tableau dashboards", ["N1"], by_id, only) is None
