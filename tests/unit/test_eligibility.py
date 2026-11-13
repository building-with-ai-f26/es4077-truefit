import pytest

from app.eligibility import check_requirements, degree_requirement, work_authorization_requirement, years_requirement

POSTING = (
    "Senior Associate, Pricing. Requirements: MBA required. 5+ years of experience in pricing or strategy. "
    "Candidates must be authorized to work in the U.S. without sponsorship now or in the future. "
    "SQL a plus. Two years of Tableau experience preferred."
)


# ---- Degree --------------------------------------------------------------

def test_mba_required_meets():
    r = degree_requirement({"level": "masters_or_mba", "quote": "MBA required."}, None, POSTING)
    assert (r.verdict, r.quote) == ("meets", "MBA required.")


def test_bachelors_minimum_meets_for_mba_student():
    posting = "Analyst. Bachelor's degree required, 4+ years of experience."
    assert degree_requirement({"level": "bachelors", "quote": "Bachelor's degree required"}, None, posting).verdict == "meets"


def test_phd_doesnt_meet():
    posting = "Research Scientist. PhD in economics required."
    assert degree_requirement({"level": "phd", "quote": "PhD in economics required."}, None, posting).verdict == "doesnt_meet"


def test_undergraduate_audience_is_unclear_with_its_quote():
    posting = "Analyst Program for students pursuing a Bachelor's degree. Bachelor's degree required."
    audience = {"level": "undergraduate", "quote": "students pursuing a Bachelor's degree"}
    r = degree_requirement({"level": "bachelors", "quote": "Bachelor's degree required."}, audience, posting)
    assert (r.verdict, r.quote) == ("unclear", "students pursuing a Bachelor's degree")


def test_degree_quote_not_in_posting_is_not_stated():
    r = degree_requirement({"level": "phd", "quote": "PhD required"}, None, POSTING)
    assert (r.verdict, r.quote) == ("not_stated", None)


# ---- Work authorization (information only) ---------------------------------

AUTH_QUOTE = "Candidates must be authorized to work in the U.S. without sponsorship now or in the future."


def test_no_sponsorship_is_reported_not_judged():
    r = work_authorization_requirement({"stance": "no_sponsorship", "quote": AUTH_QUOTE}, POSTING).to_dict()
    assert (r["verdict"], r["verdict_label"], r["detail"]) == ("info", "No sponsorship", "no_sponsorship")
    assert r["quote"] == AUTH_QUOTE


@pytest.mark.parametrize("stance, label", [
    ("sponsors", "Sponsors visas"),
    ("must_be_authorized", "Authorization required"),
    ("citizenship_required", "Citizenship required"),
])
def test_each_stance_has_a_label(stance, label):
    posting = "Associate. The quoted line."
    r = work_authorization_requirement({"stance": stance, "quote": "The quoted line."}, posting).to_dict()
    assert (r["verdict"], r["verdict_label"]) == ("info", label)


def test_auth_without_quote_is_not_stated():
    assert work_authorization_requirement({"stance": "no_sponsorship", "quote": None}, POSTING).verdict == "not_stated"


def test_unknown_stance_is_not_stated():
    assert work_authorization_requirement({"stance": "maybe", "quote": AUTH_QUOTE}, POSTING).verdict == "not_stated"


# ---- Years of experience (information only) ---------------------------------

YEARS = {"min_years": 5, "level": "required", "quote": "5+ years of experience in pricing or strategy."}


def test_required_years_are_reported_not_judged():
    r = years_requirement(YEARS, POSTING).to_dict()
    assert (r["verdict"], r["verdict_label"], r["detail"]) == ("info", "5+ years required", "required:5")


def test_preferred_years():
    raw = {"min_years": 2, "level": "preferred", "quote": "Two years of Tableau experience preferred."}
    r = years_requirement(raw, POSTING).to_dict()
    assert (r["verdict_label"], r["detail"]) == ("2+ years preferred", "preferred:2")


def test_years_number_must_be_in_the_quote():
    raw = {"min_years": 3, "level": "required", "quote": "5+ years of experience in pricing or strategy."}
    assert years_requirement(raw, POSTING).verdict == "not_stated"


@pytest.mark.parametrize("minimum", [0, -2, "5", True, None])
def test_bad_minimum_is_not_stated(minimum):
    assert years_requirement({**YEARS, "min_years": minimum}, POSTING).verdict == "not_stated"


# ---- All three -----------------------------------------------------------

def test_missing_requirements_block_is_all_not_stated():
    rows = check_requirements({"mentions": []}, POSTING)
    assert [r.key for r in rows] == ["degree", "work_authorization", "years_experience"]
    assert {r.verdict for r in rows} == {"not_stated"}


def test_model_verdicts_are_ignored():
    reply = {"requirements": {"degree": {"level": "masters_or_mba", "quote": "MBA required.", "verdict": "doesnt_meet"}}}
    assert check_requirements(reply, POSTING)[0].verdict == "meets"
