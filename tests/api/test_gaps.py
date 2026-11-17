"""Gap list (User Story 3, FR-016, FR-016a, FR-017): what the posting asks for that the student can't claim."""

from tests.api.test_tailor_route import MASTER, supported, tailored

POSTING = ("Senior Analyst, Finance. Requirements: CPA required. Strong Excel and financial modeling. "
           "You have 3+ years in FP&A. Bonus if you know Python. Ideally you've used Tableau. "
           "Start date: July 2027. Excellent communicator. MBA preferred.")


def req(text, quote, group="required", kind="tool_or_skill", supported=False, line_ids=(), related=()):
    return {"text": text, "quote": quote, "group": group, "kind": kind, "supported": supported,
            "line_ids": list(line_ids), "related_line_ids": list(related)}


def gaps_for(client, fake_llm, *requirements):
    fake_llm.gaps_reply = {"requirements": list(requirements)}
    fake_llm.queue(tailored({"text": "Built an Excel pricing model used by 3 regional teams", "source_line_ids": ["L6"]}),
                   supported("B1"))
    response = client.post("/api/tailor", json={"posting": POSTING, "master_resume": MASTER})
    assert response.status_code == 200
    return response.json()["gaps"]


def test_required_and_preferred_follow_the_posting_wording(client, fake_llm):
    gaps = gaps_for(client, fake_llm,
                    req("CPA", "CPA required", kind="credential"),
                    req("Python", "Bonus if you know Python", group="preferred"),
                    req("Tableau", "Ideally you've used Tableau", group="preferred"))
    assert [g["text"] for g in gaps["required"]] == ["CPA"]
    assert [g["text"] for g in gaps["preferred"]] == ["Python", "Tableau"]
    assert gaps["none_found"] is False
    assert len(fake_llm.gap_calls) == 1


def test_unlabeled_requirement_counts_as_required(client, fake_llm):
    gaps = gaps_for(client, fake_llm, req("FP&A experience", "You have 3+ years in FP&A", group="unlabeled", kind="experience"))
    assert [g["group"] for g in gaps["required"]] == ["required"]
    assert gaps["preferred"] == []


def test_supported_without_valid_lines_is_still_a_gap(client, fake_llm):
    gaps = gaps_for(client, fake_llm,
                    req("CPA", "CPA required", kind="credential", supported=True, line_ids=["L99"]),
                    req("Excel", "Strong Excel and financial modeling", supported=True, line_ids=["L6"]))
    assert [g["text"] for g in gaps["required"]] == ["CPA"]  # Excel is backed by L6, so it isn't a gap


def test_quote_not_in_posting_is_dropped(client, fake_llm):
    gaps = gaps_for(client, fake_llm, req("SQL", "SQL required"), req("CPA", "CPA required", kind="credential"))
    assert [g["text"] for g in gaps["required"]] == ["CPA"]


def test_all_supported_means_none_found(client, fake_llm):
    gaps = gaps_for(client, fake_llm, req("Excel", "Strong Excel and financial modeling", supported=True, line_ids=["L6"]))
    assert gaps == {"required": [], "preferred": [], "none_found": True}


def test_no_requirements_means_none_found(client, fake_llm):
    assert gaps_for(client, fake_llm)["none_found"] is True


def test_soft_skills_and_eligibility_items_are_not_gaps(client, fake_llm):
    # Eligibility (start date, degree, sponsorship, years) has its own exhibit; soft skills can't be traced to a line.
    gaps = gaps_for(client, fake_llm,
                    req("Communication", "Excellent communicator", kind="soft_skill"),
                    req("MBA", "MBA preferred", group="preferred", kind="eligibility"),
                    req("Start date", "Start date: July 2027", kind="eligibility"))
    assert gaps["none_found"] is True


def test_notes_say_how_serious_a_gap_is(client, fake_llm):
    gaps = gaps_for(client, fake_llm,
                    req("CPA", "CPA required", kind="credential"),
                    req("Python", "Bonus if you know Python", group="preferred"),
                    req("FP&A experience", "You have 3+ years in FP&A", kind="experience"),
                    req("Tableau", "Ideally you've used Tableau", group="preferred", kind="other"))
    required = {g["text"]: g["note"] for g in gaps["required"]}
    preferred = {g["text"]: g["note"] for g in gaps["preferred"]}
    assert "dealbreaker" in required["CPA"]
    assert "learn" in preferred["Python"]
    assert "master resume" in required["FP&A experience"]
    assert preferred["Tableau"] is None


def test_related_lines_must_exist_and_hold_experience(client, fake_llm):
    # L6 is a resume bullet; L1 is the EDUCATION heading; L99 doesn't exist.
    gaps = gaps_for(client, fake_llm, req("Python", "Bonus if you know Python", group="preferred", related=["L6", "L1", "L99"]))
    assert gaps["preferred"][0]["related_line_ids"] == ["L6"]


def test_same_gap_listed_once(client, fake_llm):
    gaps = gaps_for(client, fake_llm, req("CPA", "CPA required", kind="credential"), req("cpa", "CPA required", kind="credential"))
    assert len(gaps["required"]) == 1


def test_gap_call_sees_posting_and_numbered_lines(client, fake_llm):
    gaps_for(client, fake_llm)
    user = fake_llm.gap_calls[0]["user"]
    assert "CPA required" in user and "L6" in user
