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


def test_static_files_are_revalidated(client):
    r = client.get("/static/app.js")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-cache"


def test_replays_never_record_words(client):
    # The page shows students' resumes and postings; replays must mask all text, not only the boxes.
    js = client.get("/static/posthog.js").text
    assert "maskTextSelector: '*'" in js
    assert "maskAllInputs: true" in js
    assert "mask_all_text: true" in js
