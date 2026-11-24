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


def sdt(inner: str) -> str:
    return f'<w:sdt {nsdecls("w")}><w:sdtContent>{inner}</w:sdtContent></w:sdt>'


def test_block_content_control_is_read():
    """Word's own resume templates wrap sections in content controls."""
    def build(d):
        d.add_paragraph("EDUCATION")
        d.element.body.insert(1, parse_xml(sdt('<w:p><w:r><w:t>Acme Corp, Analyst</w:t></w:r></w:p>')))
    assert read_docx_text(docx_bytes(build)) == "EDUCATION\nAcme Corp, Analyst"


def test_inline_content_control_is_read():
    def build(d):
        d.add_paragraph("Name: ")._p.append(parse_xml(sdt('<w:r><w:t>Jane Doe</w:t></w:r>')))
    assert read_docx_text(docx_bytes(build)) == "Name: Jane Doe"


def test_first_page_header_comes_first():
    def build(d):
        d.sections[0].different_first_page_header_footer = True
        d.sections[0].first_page_header.paragraphs[0].text = "Jane Doe"
        d.add_paragraph("EDUCATION")
    assert read_docx_text(docx_bytes(build)) == "Jane Doe\nEDUCATION"


def test_tracked_insertion_is_kept_and_deletion_dropped():
    def build(d):
        p = d.add_paragraph("Led ")
        p._p.append(parse_xml(f'<w:ins {nsdecls("w")} w:id="1" w:author="Coach"><w:r><w:t>team of 5</w:t></w:r></w:ins>'))
        p._p.append(parse_xml(f'<w:del {nsdecls("w")} w:id="2" w:author="Coach"><w:r><w:delText> people</w:delText></w:r></w:del>'))
    assert read_docx_text(docx_bytes(build)) == "Led team of 5"


def test_nested_table_in_a_cell_is_read():
    def build(d):
        outer = d.add_table(rows=1, cols=2).rows[0].cells
        outer[0].text = "Acme"
        inner = outer[1].add_table(rows=1, cols=2).rows[0].cells
        inner[0].text, inner[1].text = "Analyst", "2020 – 2022"
    text = read_docx_text(docx_bytes(build))
    assert "Acme" in text and "Analyst 2020 – 2022" in text


def test_bullet_alone_in_a_cell_keeps_its_bullet():
    def build(d):
        cell = d.add_table(rows=1, cols=1).rows[0].cells[0]
        cell.paragraphs[0].text = "Built model"
        cell.paragraphs[0].style = d.styles["List Bullet"]
    assert read_docx_text(docx_bytes(build)) == "- Built model"


def test_damaged_document_xml_raises():
    import zipfile
    good = BytesIO(docx_bytes(lambda d: d.add_paragraph("A")))
    damaged = BytesIO()
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(damaged, "w") as dst:
        for item in src.infolist():
            data = src.read(item)
            dst.writestr(item, data[: len(data) // 2] if item.filename == "word/document.xml" else data)
    with pytest.raises(NotDocx):
        read_docx_text(damaged.getvalue())


def test_numbering_switched_off_is_not_a_bullet():
    """numId 0 means the author turned the list off, e.g. on a heading."""
    def build(d):
        d.add_paragraph("SKILLS")._p.get_or_add_pPr().append(
            parse_xml(f'<w:numPr {nsdecls("w")}><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'))
    assert read_docx_text(docx_bytes(build)) == "SKILLS"


def test_list_paragraph_style_without_numbering_is_not_a_bullet():
    data = docx_bytes(lambda d: d.add_paragraph("EXPERIENCE", style="List Paragraph"))
    assert read_docx_text(data) == "EXPERIENCE"


def test_typed_bullet_in_a_list_item_is_not_doubled():
    data = docx_bytes(lambda d: d.add_paragraph("• Built a model", style="List Bullet"))
    assert read_docx_text(data) == "- Built a model"


def test_leading_minus_sign_is_kept():
    data = docx_bytes(lambda d: d.add_paragraph("-15% cost per order after re-slotting", style="List Bullet"))
    assert read_docx_text(data) == "- -15% cost per order after re-slotting"


def with_extra_part(data: bytes, name: str, blob: bytes, stored: bool = False) -> bytes:
    """Add a part to a .docx, the way Word adds an embedded font file."""
    import zipfile
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(data)) as source, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as copy:
        for item in source.infolist():
            copy.writestr(item, source.read(item))
        copy.writestr(name, blob, compress_type=zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED)
    return out.getvalue()


def test_embedded_fonts_are_ignored():
    """A text-only resume saved with "Embed fonts in the file" carries megabytes of font files."""
    from app.docx_text import unpacks_too_large
    data = with_extra_part(docx_bytes(lambda d: d.add_paragraph("Jane Doe")), "word/fonts/font1.odttf",
                           b"\0" * (60 * 1024 * 1024))
    assert not unpacks_too_large(data)  # fonts don't count toward the zip-bomb limit
    assert read_docx_text(data) == "Jane Doe"


def test_a_document_with_a_picture_still_reads():
    import base64
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    data = docx_bytes(lambda d: (d.add_paragraph("Jane Doe"), d.add_picture(BytesIO(png)), d.add_paragraph("EDUCATION")))
    assert read_docx_text(data).split("\n")[0] == "Jane Doe" and "EDUCATION" in read_docx_text(data)
