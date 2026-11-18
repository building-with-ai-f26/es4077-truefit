"""Text of an uploaded Word file, so a student can choose their resume or notes instead of pasting them.

Only the text is used: Word list items come back as "- " bullets (Word stores the bullet as formatting,
not text), table rows as one line each, header text first, and text boxes after the paragraph that holds
them. Tabs are left for the existing tab rule. Nothing here is stored or logged.
"""

import zipfile
from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


class NotDocx(Exception):
    """The bytes aren't a Word (.docx) file TrueFit can open."""


def read_docx_text(data: bytes) -> str:
    try:
        document = Document(BytesIO(data))
    except (PackageNotFoundError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        raise NotDocx() from exc
    lines = []
    header = document.sections[0].header
    if not header.is_linked_to_previous:  # a linked first-section header has no text of its own
        lines += [line for line in _block_lines(header.iter_inner_content()) if line.strip()]
    lines += _block_lines(document.iter_inner_content())
    return "\n".join(lines).strip("\n")


def _block_lines(blocks) -> list[str]:
    lines = []
    for block in blocks:
        if isinstance(block, Table):
            lines += _table_lines(block)
        else:
            lines += _paragraph_lines(block)
    return lines


def _paragraph_lines(paragraph: Paragraph) -> list[str]:
    text = paragraph.text
    if text.strip() and _is_list_item(paragraph):
        text = f"- {text.strip()}"
    boxed = [Paragraph(p, paragraph).text for box in _text_boxes(paragraph) for p in box.iter(qn("w:p"))]
    return [text] + [t for t in boxed if t.strip()]


def _text_boxes(paragraph: Paragraph) -> list:
    """Each text box once: Word repeats it under mc:Fallback for older versions."""
    return [box for box in paragraph._p.iter(qn("w:txbxContent"))
            if not any(a.tag == f"{{{MC}}}Fallback" for a in box.iterancestors())]


def _is_list_item(paragraph: Paragraph) -> bool:
    p_pr = paragraph._p.pPr
    has_numbering = p_pr is not None and p_pr.numPr is not None
    return has_numbering or (paragraph.style is not None and paragraph.style.name.startswith("List"))


def _table_lines(table: Table) -> list[str]:
    lines = []
    for row in table.rows:
        cells = [cell for cell in _unique_cells(row) if cell.text.strip()]
        if all(len([p for p in cell.paragraphs if p.text.strip()]) <= 1 for cell in cells):
            if cells:
                lines.append(" ".join(cell.text.strip() for cell in cells))
        else:  # a template that puts a whole job (header and bullets) in one cell: keep its lines
            for cell in cells:
                lines += [line for line in _block_lines(cell.iter_inner_content()) if line.strip()]
    return lines


def _unique_cells(row):
    """Merged cells repeat in row.cells; read each once."""
    seen, cells = set(), []
    for cell in row.cells:
        if id(cell._tc) not in seen:
            seen.add(id(cell._tc))
            cells.append(cell)
    return cells
