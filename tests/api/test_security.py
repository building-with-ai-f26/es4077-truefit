"""Security audit fixes for the live site (SECURITY.md)."""


def test_api_documentation_pages_are_off(client):
    """FastAPI's automatic /docs and /openapi.json would list every route for anyone; the page doesn't need them."""
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_security_headers_on_every_response(client):
    for response in (client.get("/"), client.post("/api/start-date", json={"posting": "short"})):
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"  # can't be framed by another site (clickjacking)
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_oversized_request_refused_before_reading(client):
    response = client.post("/api/tailor", content=b"x", headers={"Content-Length": str(7 * 1024 * 1024),
                                                                   "Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
