"""Reading the text out of an uploaded Word file (specs/2026-11-18-word-upload-design.md)."""

from io import BytesIO

import pytest
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from app.docx_text import NotDocx, read_docx_text

WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def docx_bytes(build) -> bytes:
    document = Document()
    build(document)
    out = BytesIO()
    document.save(out)
    return out.getvalue()


def test_paragraphs_in_order():
    data = docx_bytes(lambda d: (d.add_paragraph("EDUCATION"), d.add_paragraph("NYU Stern")))
    assert read_docx_text(data) == "EDUCATION\nNYU Stern"


def test_bullet_list_items_become_bullets():
    data = docx_bytes(lambda d: d.add_paragraph("Built a model", style="List Bullet"))
    assert read_docx_text(data) == "- Built a model"


def test_numbered_list_items_become_bullets():
    data = docx_bytes(lambda d: d.add_paragraph("Ran 15 interviews", style="List Number"))
    assert read_docx_text(data) == "- Ran 15 interviews"


def test_table_row_is_one_line_in_order():
    def build(d):
        row = d.add_table(rows=1, cols=2).rows[0]
        row.cells[0].text = "Alpine Logistics | Chicago"
        row.cells[1].text = "Jul 2018 – Jul 2025"
        d.add_paragraph("Managed a team of 14")
    assert read_docx_text(docx_bytes(build)) == "Alpine Logistics | Chicago Jul 2018 – Jul 2025\nManaged a team of 14"


def test_header_text_comes_first():
    def build(d):
        d.sections[0].header.paragraphs[0].text = "Jane Doe"
        d.add_paragraph("EDUCATION")
    assert read_docx_text(docx_bytes(build)).startswith("Jane Doe\nEDUCATION")


def test_text_box_text_is_read():
    def build(d):
        holder = d.add_paragraph("CERTIFICATIONS")
        holder._p.append(parse_xml(
            f'<w:r {nsdecls("w")} xmlns:wps="{WPS}" xmlns:mc="{MC}"><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing>'
            f'<wps:txbx><w:txbxContent><w:p><w:r><w:t>Lean Six Sigma</w:t></w:r></w:p></w:txbxContent></wps:txbx>'
            f'</w:drawing></mc:Choice></mc:AlternateContent></w:r>'))
    assert read_docx_text(docx_bytes(build)) == "CERTIFICATIONS\nLean Six Sigma"


def test_tabs_are_kept_for_the_existing_rule():
    data = docx_bytes(lambda d: d.add_paragraph("Analyst\tJun 2018"))
    assert read_docx_text(data) == "Analyst\tJun 2018"


def test_empty_paragraphs_keep_line_breaks():
    data = docx_bytes(lambda d: (d.add_paragraph("A"), d.add_paragraph(""), d.add_paragraph("B")))
    assert read_docx_text(data) == "A\n\nB"


@pytest.mark.parametrize("data", [b"%PDF-1.7 not a word file", b""])
def test_not_a_docx_raises(data):
    with pytest.raises(NotDocx):
        read_docx_text(data)


def test_text_box_fallback_copy_is_not_read_twice():
    """Word saves each text box twice: the shape, and an older-Word copy under mc:Fallback."""
    box = '<w:txbxContent><w:p><w:r><w:t>Lean Six Sigma</w:t></w:r></w:p></w:txbxContent>'
    def build(d):
        d.add_paragraph("CERTIFICATIONS")._p.append(parse_xml(
            f'<w:r {nsdecls("w")} xmlns:wps="{WPS}" xmlns:mc="{MC}" xmlns:v="urn:schemas-microsoft-com:vml">'
            f'<mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wps:txbx>{box}</wps:txbx></w:drawing></mc:Choice>'
            f'<mc:Fallback><w:pict><v:textbox>{box}</v:textbox></w:pict></mc:Fallback></mc:AlternateContent></w:r>'))
    assert read_docx_text(docx_bytes(build)) == "CERTIFICATIONS\nLean Six Sigma"
