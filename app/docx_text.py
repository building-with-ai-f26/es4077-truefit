"""Text of an uploaded Word file, so a student can choose their resume or notes instead of pasting them.

Only the text is used: Word list items come back as "- " bullets (Word stores the bullet as formatting,
not text), table rows as one line each, header text first, and text boxes after the paragraph that holds
them. Tabs are left for the existing tab rule. Nothing here is stored or logged.

The file's XML is walked directly rather than through python-docx's paragraph and table helpers, because
those skip text Word's own templates rely on: content controls (w:sdt), tracked insertions, and nested tables.
"""

import zipfile
from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from lxml.etree import XMLSyntaxError

MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
# Never read: deleted text, Word's old-version copy of a text box, and text boxes (read after their paragraph).
SKIPPED = {qn("w:del"), MC_FALLBACK, qn("w:txbxContent"), qn("w:pPr"), qn("w:rPr")}
CONTAINERS = {qn("w:sdt"), qn("w:sdtContent"), qn("w:customXml"), qn("w:ins")}


class NotDocx(Exception):
    """The bytes aren't a Word (.docx) file TrueFit can open."""


def read_docx_text(data: bytes) -> str:
    try:
        document = Document(BytesIO(data))
        style_names = {style.style_id: style.name for style in document.styles}
        lines = _header_lines(document.sections[0], style_names)
        lines += _block_lines(document.element.body, style_names)
    except (PackageNotFoundError, KeyError, ValueError, zipfile.BadZipFile, XMLSyntaxError) as exc:
        raise NotDocx() from exc
    return "\n".join(lines).strip("\n")


def _header_lines(section, style_names) -> list[str]:
    """The first page's header (where a two-page resume puts the name), then the usual header, each line once."""
    headers = [section.first_page_header] if section.different_first_page_header_footer else []
    lines = []
    for header in headers + [section.header]:
        if header.is_linked_to_previous:  # a linked first-section header has no text of its own
            continue
        lines += [line for line in _block_lines(header._element, style_names) if line.strip() and line not in lines]
    return lines


def _block_lines(parent, style_names) -> list[str]:
    lines = []
    for child in parent:
        if child.tag == qn("w:p"):
            lines += _paragraph_lines(child, style_names)
        elif child.tag == qn("w:tbl"):
            lines += _table_lines(child, style_names)
        elif child.tag in CONTAINERS:
            lines += _block_lines(child, style_names)
    return lines


def _paragraph_lines(p, style_names) -> list[str]:
    text = "".join(_run_text(p))
    if text.strip() and _is_list_item(p, style_names):
        text = f"- {text.strip()}"
    boxed = [line for box in _text_boxes(p) for line in _block_lines(box, style_names) if line.strip()]
    return [text] + boxed


def _run_text(element):
    for child in element:
        if child.tag in SKIPPED:
            continue
        if child.tag == qn("w:t"):
            yield child.text or ""
        elif child.tag == qn("w:tab"):
            yield "\t"
        elif child.tag in (qn("w:br"), qn("w:cr")):
            yield "\n"
        elif child.tag == qn("w:noBreakHyphen"):
            yield "-"
        else:  # runs, hyperlinks, content controls, tracked insertions, simple fields
            yield from _run_text(child)


def _is_list_item(p, style_names) -> bool:
    p_pr = p.find(qn("w:pPr"))
    if p_pr is None:
        return False
    if p_pr.find(qn("w:numPr")) is not None:
        return True
    style = p_pr.find(qn("w:pStyle"))
    return style is not None and style_names.get(style.get(qn("w:val")), "").startswith("List")


def _text_boxes(p) -> list:
    """Each text box once: Word repeats it under mc:Fallback for older versions."""
    return [box for box in p.iter(qn("w:txbxContent"))
            if not any(a.tag == MC_FALLBACK for a in box.iterancestors())]


def _table_lines(table, style_names) -> list[str]:
    lines = []
    for row in _rows(table):
        cells = [[line for line in _block_lines(cell, style_names) if line.strip()] for cell in _row_cells(row)]
        cells = [cell for cell in cells if cell]
        if all(len(cell) == 1 for cell in cells):
            if cells:
                lines.append(" ".join(cell[0].strip() for cell in cells))
        else:  # a template that puts a whole job (header and bullets) in one cell: keep its lines
            lines += [line for cell in cells for line in cell]
    return lines


def _rows(table):
    """This table's own rows (nested tables are read with the cell that holds them)."""
    for child in table:
        if child.tag == qn("w:tr"):
            yield child
        elif child.tag in CONTAINERS:
            yield from _rows(child)


def _row_cells(row):
    for child in row:
        if child.tag == qn("w:tc"):
            yield child
        elif child.tag in CONTAINERS:
            yield from _row_cells(child)
