from app.errors import ModelUnavailable

POSTING = ("Strategy Associate, New York. We're hiring MBA graduates. Requirements: SQL required, "
           "strong Excel and financial modeling. Start date: July 13, 2027. Tableau a plus.")
MASTER = """EDUCATION
NYU Stern School of Business | MBA | Aug 2025 – May 2027
EXPERIENCE
Associate, Acme Corp | New York, NY | Jun 2022 – Jul 2025
Grew regional revenue 12% by repricing 40 SKUs, adding $1.2M in annual profit
Built Excel pricing model used by 3 regional teams
Presented quarterly pricing reviews to the VP of Sales"""
NOTES = "At Acme I also trained 2 new analysts on the pricing model."


def tailored(*bullets):
    return {"sections": [
        {"heading": "Education", "entries": [{"header_line_ids": ["L2"], "bullets": []}]},
        {"heading": "Experience", "entries": [{"header_line_ids": ["L4"], "bullets": list(bullets)}]},
    ]}


def supported(*ids, claims=None):
    claims = claims or {}
    return {"results": [{"bullet_id": i, "supported": i not in claims, "unsupported_claim": claims.get(i)} for i in ids]}


def post(client, **extra):
    return client.post("/api/tailor", json={"posting": POSTING, "master_resume": MASTER, **extra})


def test_traced_bullets_are_included_and_in_plain_text(client, fake_llm):
    fake_llm.queue(
        tailored({"text": "Repriced 40 SKUs, growing regional revenue 12% and adding $1.2M in profit", "source_line_ids": ["L5"]},
                 {"text": "Built an Excel pricing model adopted by 3 regional teams", "source_line_ids": ["L6"]}),
        supported("B1", "B2"))
    body = post(client).json()
    bullets = body["resume"]["sections"][1]["entries"][0]["bullets"]
    assert [(b["id"], b["status"], b["included"]) for b in bullets] == [("B1", "traced", True), ("B2", "traced", True)]
    assert body["resume_lines"][0] == {"id": "L1", "text": "EDUCATION", "section": "Education", "source": "resume"}
    assert body["resume"]["plain_text"].startswith("Education\nNYU Stern School of Business | MBA | Aug 2025 – May 2027\n\nExperience\n")
    assert "- Built an Excel pricing model adopted by 3 regional teams" in body["resume"]["plain_text"]


def test_invented_metric_and_skill_flagged_without_asking_model(client, fake_llm):
    fake_llm.queue(
        tailored({"text": "Grew regional revenue 20% by repricing 40 SKUs", "source_line_ids": ["L5"]},
                 {"text": "Used SQL to build a pricing model for 3 regional teams", "source_line_ids": ["L6"]},
                 {"text": "Built an Excel pricing model used by 3 regional teams", "source_line_ids": ["L6"]}),
        supported("B3"))
    body = post(client).json()
    bullets = body["resume"]["sections"][1]["entries"][0]["bullets"]
    assert [(b["status"], b["included"]) for b in bullets] == [("flagged", False), ("flagged", False), ("traced", True)]
    assert bullets[0]["flag_reason"] == '"20%" isn\'t in the cited lines'
    assert "sql" in bullets[1]["flag_reason"]
    assert '"bullets": [{"bullet_id": "B3"' in fake_llm.calls[1]["user"]  # only B3 reached the support check
    assert "20%" not in body["resume"]["plain_text"] and "SQL" not in body["resume"]["plain_text"]


def test_support_check_flags_overstated_bullet(client, fake_llm):
    fake_llm.queue(
        tailored({"text": "Led quarterly pricing reviews for the VP of Sales", "source_line_ids": ["L7"]}),
        supported("B1", claims={"B1": "Led the reviews"}))
    bullet = post(client).json()["resume"]["sections"][1]["entries"][0]["bullets"][0]
    assert (bullet["status"], bullet["flag_reason"], bullet["included"]) == ("flagged", "Led the reviews", False)


def test_missing_support_result_is_flagged(client, fake_llm):
    fake_llm.queue(tailored({"text": "Built an Excel pricing model", "source_line_ids": ["L6"]}), {"results": []})
    bullet = post(client).json()["resume"]["sections"][1]["entries"][0]["bullets"][0]
    assert bullet["status"] == "flagged"


def test_notes_can_back_a_bullet(client, fake_llm):
    fake_llm.queue(tailored({"text": "Trained 2 new analysts on the pricing model", "source_line_ids": ["N1"]}), supported("B1"))
    body = post(client, background_notes=NOTES).json()
    assert body["resume_lines"][-1]["id"] == "N1"
    assert body["resume"]["sections"][1]["entries"][0]["bullets"][0]["status"] == "traced"


def test_unusable_model_output_is_model_unavailable(client, fake_llm):
    fake_llm.queue({"sections": "nope"})
    r = post(client)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "model_unavailable"


def test_support_check_failure_is_model_unavailable(client, fake_llm):
    fake_llm.queue(tailored({"text": "Built an Excel pricing model", "source_line_ids": ["L6"]}), ModelUnavailable)
    assert post(client).status_code == 502


def test_short_resume_rejected_before_model_call(client, fake_llm):
    r = client.post("/api/tailor", json={"posting": POSTING, "master_resume": "Too short"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "master_resume_too_short"
    assert fake_llm.calls == []


def test_verify_bullet_flags_edit_adding_team_size(client, fake_llm):
    r = client.post("/api/verify-bullet", json={"bullet_text": "Led a team of 8 to reprice 40 SKUs",
                                                "source_line_ids": ["L5"], "posting": POSTING, "master_resume": MASTER})
    assert r.json() == {"status": "flagged", "source_line_ids": ["L5"], "flag_reason": '"8" isn\'t in the cited lines'}


def test_verify_bullet_traced_edit(client, fake_llm):
    fake_llm.queue(supported("B1"))
    r = client.post("/api/verify-bullet", json={"bullet_text": "Repriced 40 SKUs to grow regional revenue 12%",
                                                "source_line_ids": ["L5"], "posting": POSTING, "master_resume": MASTER})
    assert r.json()["status"] == "traced"


def test_long_writing_accepted_up_to_limit(client, fake_llm):
    fake_llm.queue(tailored({"text": "Built an Excel pricing model", "source_line_ids": ["L6"]}), supported("B1"))
    assert post(client, background_notes="I built things. " * 3000).status_code == 200  # ~48,000 chars
    r = post(client, background_notes="x" * 50_001)
    assert r.json()["error"]["code"] == "background_writing_too_long"


def test_year_and_employer_from_role_header_are_allowed(client, fake_llm):
    fake_llm.queue(tailored({"text": "At Acme Corp from 2022, built an Excel pricing model", "source_line_ids": ["L6"]}),
                   supported("B1"))
    body = post(client).json()
    assert body["resume"]["sections"][1]["entries"][0]["bullets"][0]["status"] == "traced"
    support_request = fake_llm.calls[1]["user"]
    assert '"role_context": ["Associate, Acme Corp | New York, NY | Jun 2022 – Jul 2025"]' in support_request


def test_verify_bullet_uses_header_context(client, fake_llm):
    fake_llm.queue(supported("B1"))
    r = client.post("/api/verify-bullet", json={"bullet_text": "In 2022, built an Excel pricing model", "source_line_ids": ["L6"],
                                                "header_line_ids": ["L4"], "posting": POSTING, "master_resume": MASTER})
    assert r.json()["status"] == "traced"
