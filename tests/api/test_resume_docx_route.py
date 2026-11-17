import io

from docx import Document

from tests.unit.test_docx_resume import MASTER, bullet, sections


def test_download_returns_a_word_file(client):
    response = client.post("/api/resume-docx", json={"master_resume": MASTER, "sections": sections(bullet("Built an Excel pricing model"))})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert response.headers["content-disposition"] == 'attachment; filename="Jordan Lee Resume.docx"'
    assert (response.headers["x-fits-one-page"], response.headers["x-remove-bullets"]) == ("true", "0")
    assert "Built an Excel pricing model" in [p.text for p in Document(io.BytesIO(response.content)).paragraphs]


def test_download_checks_resume_length(client):
    response = client.post("/api/resume-docx", json={"master_resume": "too short", "sections": []})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "master_resume_too_short"


def test_malformed_sections_are_skipped(client):
    response = client.post("/api/resume-docx", json={"master_resume": MASTER, "sections": ["junk", {"heading": 3}, {"heading": "Experience", "entries": ["x"]}]})
    assert response.status_code == 200
