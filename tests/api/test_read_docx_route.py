"""POST /api/read-docx: the text of a Word file the student chose (specs/2026-11-18-word-upload-design.md)."""

import logging

from docx import Document

from tests.unit.test_docx_text import docx_bytes

RESUME = ["Jane Doe", "EDUCATION", "NYU Stern | MBA | Aug 2025 – May 2027", "", "Built a model"]


def read(client, data):
    return client.post("/api/read-docx", content=data,
                       headers={"Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"})


def test_reads_a_resume(client):
    response = read(client, docx_bytes(lambda d: [d.add_paragraph(line) for line in RESUME]))
    assert response.status_code == 200
    body = response.json()
    assert body["text"].startswith("Jane Doe")
    assert body["lines"] == 4  # the empty line isn't counted


def test_too_large(client):
    response = read(client, b"x" * (5 * 1024 * 1024 + 1))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_renamed_pdf_is_rejected(client):
    response = read(client, b"%PDF-1.7 a pdf saved as resume.docx")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "not_docx"
    assert "paste the text" in response.json()["error"]["message"]


def test_empty_document(client):
    response = read(client, docx_bytes(lambda d: None))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "docx_empty"


def test_text_is_not_logged(client, caplog):
    caplog.set_level(logging.DEBUG)
    read(client, docx_bytes(lambda d: d.add_paragraph("SECRETLINE")))
    assert "SECRETLINE" not in caplog.text
