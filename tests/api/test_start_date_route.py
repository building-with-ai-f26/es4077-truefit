from app.errors import ModelUnavailable

POSTING = (
    "Associate, Strategy & Operations. Acme Corp is hiring MBA graduates for our New York office. "
    "Start date: July 13, 2027. Applications close March 1, 2027. Requirements: MBA, 3+ years of experience."
)


def reply(mentions, is_job_posting=True, is_english=True, **extra):
    return {"is_job_posting": is_job_posting, "is_english": is_english, "mentions": mentions, **extra}


def test_valid_mention_returns_contract_shape(client, fake_llm):
    fake_llm.queue(reply([{"quote": "Start date: July 13, 2027.", "kind": "exact_date",
                           "start": "2027-07-13", "end": None, "role_hint": None}]))
    r = client.post("/api/start-date", json={"posting": POSTING})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "in_window"
    assert body["verdict_label"] == "In window"
    assert body["availability"] == {"mode": "month", "start": "2027-06-01", "label": "Starting June 2027"}
    assert body["mentions"][0]["quote"] == "Start date: July 13, 2027."
    assert body["mentions"][0]["start"] == "2027-07-13"
    assert body["mentions"][0]["verdict"] == "in_window"
    assert "note" in body


def test_custom_availability_used(client, fake_llm):
    fake_llm.queue(reply([{"quote": "Start date: July 13, 2027.", "kind": "exact_date", "start": "2027-07-13"}]))
    r = client.post("/api/start-date", json={"posting": POSTING, "availability_text": "september 2027"})
    assert r.json()["verdict"] == "outside_window"
    assert r.json()["availability"]["label"] == "Starting September 2027"


def test_quote_not_in_posting_is_dropped(client, fake_llm):
    fake_llm.queue(reply([{"quote": "The role starts in July 2027", "kind": "month", "start": "2027-07"}]))
    body = client.post("/api/start-date", json={"posting": POSTING}).json()
    assert body["verdict"] == "likely_too_early"
    assert body["mentions"] == []


def test_model_supplied_verdict_is_ignored(client, fake_llm):
    fake_llm.queue(reply([{"quote": "Applications close March 1, 2027.", "kind": "exact_date",
                           "start": "2027-03-01", "verdict": "in_window"}], verdict="in_window"))
    body = client.post("/api/start-date", json={"posting": POSTING}).json()
    assert body["verdict"] == "outside_window"


def test_not_a_posting(client, fake_llm):
    fake_llm.queue(reply([], is_job_posting=False))
    r = client.post("/api/start-date", json={"posting": "x" * 150})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "not_a_posting"


def test_not_english(client, fake_llm):
    fake_llm.queue(reply([], is_english=False))
    r = client.post("/api/start-date", json={"posting": POSTING})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "not_english"


def test_posting_too_short_or_long(client, fake_llm):
    assert client.post("/api/start-date", json={"posting": "too short"}).json()["error"]["code"] == "posting_too_short"
    assert client.post("/api/start-date", json={"posting": "x" * 20001}).json()["error"]["code"] == "posting_too_long"
    assert fake_llm.calls == []


def test_invalid_availability_checked_before_model_call(client, fake_llm):
    r = client.post("/api/start-date", json={"posting": POSTING, "availability_text": "soonish"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "availability_invalid"
    assert fake_llm.calls == []


def test_missing_field_uses_error_format(client):
    r = client.post("/api/start-date", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_request"


def test_model_unavailable(client, fake_llm):
    fake_llm.queue(ModelUnavailable)
    r = client.post("/api/start-date", json={"posting": POSTING})
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "model_unavailable"


def test_malformed_mentions_field(client, fake_llm):
    fake_llm.queue({"is_job_posting": True, "is_english": True, "mentions": "July"})
    body = client.post("/api/start-date", json={"posting": POSTING}).json()
    assert body["verdict"] == "likely_too_early"


def test_missing_config_gives_plain_error(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.setattr("app.config._load_env_file", lambda *a, **k: None)
    r = client.post("/api/start-date", json={"posting": POSTING})
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "not_configured"


def test_account_problem_shown_with_reason(client, monkeypatch):
    from app.errors import ModelAccountProblem

    async def out_of_credit(system, user):
        raise ModelAccountProblem("model_out_of_credit", "TrueFit's AI account is out of credit.")

    monkeypatch.setattr("app.llm.call", out_of_credit)
    r = client.post("/api/start-date", json={"posting": POSTING})
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "model_out_of_credit"


GRAD_POSTING = (
    "Associate, Corporate Strategy. Acme Corp is hiring MBA candidates graduating between December 2026 "
    "and June 2027 for our New York office. Requirements: MBA, 3+ years of experience, strong Excel skills."
)


def test_graduation_window_gives_in_window(client, fake_llm):
    fake_llm.queue(reply([{"quote": "graduating between December 2026 and June 2027", "kind": "graduation",
                           "start": "2026-12", "end": "2027-06"}]))
    body = client.post("/api/start-date", json={"posting": GRAD_POSTING}).json()
    assert body["verdict"] == "in_window"
    assert body["mentions"][0]["quote"] == "graduating between December 2026 and June 2027"


UNDERGRAD_POSTING = (
    "Business Analyst, Class of 2027. Acme Corp is hiring students pursuing a Bachelor's degree in economics "
    "or business for our New York office. Start date: July 13, 2027. Requirements: strong Excel skills."
)


def test_undergrad_posting_gets_warning_with_quote(client, fake_llm):
    fake_llm.queue(reply([{"quote": "Start date: July 13, 2027.", "kind": "exact_date", "start": "2027-07-13"}],
                         audience={"level": "undergraduate", "quote": "pursuing a Bachelor's degree"}))
    body = client.post("/api/start-date", json={"posting": UNDERGRAD_POSTING}).json()
    assert body["verdict"] == "in_window"
    assert body["undergrad_warning"] == {"quote": "pursuing a Bachelor's degree"}


def test_undergrad_warning_dropped_when_quote_not_in_posting(client, fake_llm):
    fake_llm.queue(reply([], audience={"level": "undergraduate", "quote": "for college seniors only"}))
    body = client.post("/api/start-date", json={"posting": UNDERGRAD_POSTING}).json()
    assert body["undergrad_warning"] is None


def test_graduate_posting_has_no_warning(client, fake_llm):
    fake_llm.queue(reply([], audience={"level": "graduate", "quote": "MBA graduates"}))
    body = client.post("/api/start-date", json={"posting": POSTING}).json()
    assert body["undergrad_warning"] is None
