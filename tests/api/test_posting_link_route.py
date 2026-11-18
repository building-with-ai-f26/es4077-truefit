"""POST /api/posting-link: the text of a posting the student linked to."""

import logging

import httpx

from app import posting_link


def fake_web(monkeypatch, content="<p>Build models</p>"):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"title": "Analyst", "content": content})

    monkeypatch.setattr(posting_link, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(posting_link, "_public", lambda host: True)
    return seen


def test_route_returns_text(client, monkeypatch):
    fake_web(monkeypatch)
    response = client.post("/api/posting-link", json={"url": "https://boards.greenhouse.io/acme/jobs/1"})
    assert response.status_code == 200
    assert response.json() == {"text": "Analyst\n\nBuild models", "lines": 2, "site": "greenhouse",
                               "host": "boards.greenhouse.io"}


def test_route_blocked_site(client, monkeypatch):
    seen = fake_web(monkeypatch)
    response = client.post("/api/posting-link", json={"url": "https://www.linkedin.com/jobs/view/1"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "blocked_site"
    assert seen == []


def test_route_rejects_a_very_long_link(client, monkeypatch):
    fake_web(monkeypatch)
    response = client.post("/api/posting-link", json={"url": "https://example.com/" + "a" * 2000})
    assert response.json()["error"]["code"] == "bad_link"


def test_link_and_text_not_logged(client, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    fake_web(monkeypatch, content="<p>SECRETPOSTING</p>")
    client.post("/api/posting-link", json={"url": "https://boards.greenhouse.io/secret-slug/jobs/1"})
    assert "SECRETPOSTING" not in caplog.text and "secret-slug" not in caplog.text
