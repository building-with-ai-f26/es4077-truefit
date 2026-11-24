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
    response = read(client, b"x" * (20 * 1024 * 1024 + 1))
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert "Embed fonts" in response.json()["error"]["message"]


def test_resume_with_embedded_fonts_over_5_mb_is_read(client):
    """The outside reviewer's text-only resume was refused as over 5 MB on Nov 24; embedded fonts are the
    likely cause. 8 MB of incompressible font data, like a real font file."""
    import os
    from tests.unit.test_docx_text import with_extra_part
    data = with_extra_part(docx_bytes(lambda d: [d.add_paragraph(line) for line in RESUME]),
                           "word/fonts/font1.odttf", os.urandom(8 * 1024 * 1024), stored=True)
    assert len(data) > 5 * 1024 * 1024
    response = read(client, data)
    assert response.status_code == 200
    assert response.json()["text"].startswith("Jane Doe")


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


def test_file_that_unpacks_huge_is_refused(client):
    """A small .docx can unpack into something huge (a "zip bomb"); it's refused before it's opened."""
    import io
    import zipfile
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", b"0" * (60 * 1024 * 1024))
    assert len(out.getvalue()) < 20 * 1024 * 1024  # small enough to pass the upload limit
    response = read(client, out.getvalue())
    assert response.status_code == 413 and response.json()["error"]["code"] == "file_too_large"
