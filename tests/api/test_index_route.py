def test_index_fills_posthog_settings(client, monkeypatch):
    monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", "phc_test")
    monkeypatch.setenv("POSTHOG_HOST", "https://us.i.posthog.com")
    page = client.get("/").text
    assert '<meta name="posthog-token" content="phc_test" />' in page
    assert '<meta name="posthog-host" content="https://us.i.posthog.com" />' in page


def test_index_leaves_posthog_empty_when_unset(client, monkeypatch):
    monkeypatch.delenv("POSTHOG_PROJECT_TOKEN", raising=False)
    monkeypatch.delenv("POSTHOG_HOST", raising=False)
    page = client.get("/").text
    assert '<meta name="posthog-token" content="" />' in page
    assert "{{" not in page
