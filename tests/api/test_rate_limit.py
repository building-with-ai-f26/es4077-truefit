"""Rate limits for the live site (Build 3): the AI routes spend the owner's OpenRouter credit, so each visitor
and the whole site are capped. Short postings are used so no request reaches the model."""

import pytest

from app import rate_limit

SHORT = {"posting": "too short"}  # rejected by the length check, after the rate limit has counted it


@pytest.fixture
def clock(monkeypatch):
    now = [1_000_000.0]
    monkeypatch.setattr(rate_limit, "_now", lambda: now[0])
    return now


def ai_call(client, ip="203.0.113.7"):
    return client.post("/api/start-date", json=SHORT, headers={"X-Forwarded-For": ip})


def test_thirty_quick_calls_are_refused_after_ten(client, clock):
    """The course's proof that the live site is locked down: 30 calls in a row, calls 11-30 refused."""
    statuses = [ai_call(client).status_code for _ in range(30)]
    assert statuses[:10] == [422] * 10  # allowed through (then rejected as too short, no model call)
    assert statuses[10:] == [429] * 20
    body = ai_call(client).json()
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["message"] == "Too many requests. Try again in a minute."


def test_the_minute_limit_resets(client, clock):
    for _ in range(10):
        ai_call(client)
    assert ai_call(client).status_code == 429
    clock[0] += 61
    assert ai_call(client).status_code == 422


def test_daily_limit_per_visitor(client, clock):
    for _ in range(5):
        for _ in range(10):
            assert ai_call(client).status_code == 422
        clock[0] += 61
    refused = ai_call(client)
    assert refused.status_code == 429 and refused.json()["error"]["code"] == "daily_limit"
    clock[0] += 24 * 3600
    assert ai_call(client).status_code == 422


def test_site_wide_daily_cap_of_200(client, clock):
    for i in range(200):
        assert ai_call(client, ip=f"198.51.100.{i % 250}").status_code == 422 or i >= 200
        if i % 10 == 9:
            clock[0] += 61
    refused = ai_call(client, ip="192.0.2.99")
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "site_daily_limit"


def test_all_ai_routes_share_the_limit(client, clock):
    for _ in range(4):
        client.post("/api/start-date", json=SHORT, headers={"X-Forwarded-For": "203.0.113.9"})
        client.post("/api/tailor", json={"posting": "x", "master_resume": "y"}, headers={"X-Forwarded-For": "203.0.113.9"})
    assert client.post("/api/verify-bullet", json={}, headers={"X-Forwarded-For": "203.0.113.9"}).status_code != 429
    assert client.post("/api/verify-bullet", json={}, headers={"X-Forwarded-For": "203.0.113.9"}).status_code != 429
    assert client.post("/api/start-date", json=SHORT, headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 429


def test_other_routes_allow_thirty_a_minute(client, clock):
    statuses = [client.post("/api/posting-link", json={"url": "ftp://x"}, headers={"X-Forwarded-For": "203.0.113.8"}).status_code
                for _ in range(31)]
    assert statuses[:30] == [422] * 30 and statuses[30] == 429


def test_page_and_static_files_are_not_limited(client, clock):
    assert all(client.get("/").status_code == 200 for _ in range(40))


def test_visitor_is_the_address_the_host_added(client, clock):
    """Render appends the real address last; anything before it was sent by the visitor and can be faked."""
    for i in range(10):
        ai_call(client, ip=f"10.0.0.{i}, 203.0.113.50")
    assert ai_call(client, ip="10.0.0.99, 203.0.113.50").status_code == 429


def test_cloudflare_address_is_the_visitor(client, clock):
    """Live on Render (Nov 18), the last X-Forwarded-For entry was one of several relay servers, so 30 calls let
    25 through. Cloudflare, in front of Render, sets CF-Connecting-IP to the real visitor and visitors can't fake it."""
    for i in range(10):
        client.post("/api/start-date", json=SHORT,
                    headers={"CF-Connecting-IP": "203.0.113.70", "X-Forwarded-For": f"203.0.113.70, 10.0.0.{i}"})
    refused = client.post("/api/start-date", json=SHORT,
                          headers={"CF-Connecting-IP": "203.0.113.70", "X-Forwarded-For": "203.0.113.70, 10.0.0.99"})
    assert refused.status_code == 429
