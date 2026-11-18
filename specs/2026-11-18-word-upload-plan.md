# Word File Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Students can choose Word (.docx) files for the master resume (locked preview with Edit text / Remove) and for More about your experience (several files plus the still-editable textbox), as an alternative to pasting.

**Architecture:** The browser sends the raw file bytes to a new `POST /api/read-docx`; `app/docx_text.py` pulls the text out with python-docx (already a dependency) and returns it. The page puts that text where pasted text goes today, so tailoring, tracing, and downloads are unchanged. Nothing is stored or logged on the server.

**Tech Stack:** Python 3.12, FastAPI, python-docx 1.2, plain HTML/JS, pytest, Playwright (dev, for the browser check).

**Spec:** `specs/2026-11-18-word-upload-design.md`

## Global Constraints

- Word files only (`.docx`). Anything else: "TrueFit reads Word files (.docx). For a PDF, open it and paste the text."
- 5 MB per file.
- The file and its text are never stored or logged on the server, and the file is never sent to the model.
- PostHog events never include the file name or text.
- No new dependencies: python-docx is already installed; send the bytes as the request body so `python-multipart` isn't needed.
- Internal names stay as they are (`master_resume`, `background_notes`, the `truefit.v1` localStorage key).
- `uv run pytest` must pass; never run the model evals for this change.

## Review Focus

1. A resume template that lays jobs out in a table (company left, dates right): each row should read as one line, in document order, not column by column. → Task 1 `test_table_row_is_one_line_in_order`
2. Name and contact sitting only in the Word page header: they should come first, not vanish. → Task 1 `test_header_text_comes_first`
3. Numbered lists ("1.", "2.") as well as bulleted ones: both should come back as "- " bullets. → Task 1 `test_numbered_list_items_become_bullets`
4. A PDF or old .doc renamed to .docx, or a damaged file: a plain message, never a crash or a blank preview. → Task 2 `test_renamed_pdf_is_rejected`
5. The same file added twice to More about your experience: it should appear once (the second add replaces the first), not double the notes. → Task 3 browser check, step 4

---

### Task 1: Read text from a Word file

**Files:**
- Create: `app/docx_text.py`
- Test: `tests/unit/test_docx_text.py`

**Interfaces:**
- Produces: `read_docx_text(data: bytes) -> str` and `class NotDocx(Exception)` (raised when the bytes aren't a readable .docx).

- [ ] **Step 1: Write the failing tests.** Build each sample with `docx.Document()` saved to a `BytesIO`; helper `docx_bytes(build) -> bytes`.

```python
def test_paragraphs_in_order(): ...           # "EDUCATION", "NYU Stern" → "EDUCATION\nNYU Stern"
def test_bullet_list_items_become_bullets():  # style "List Bullet" → line starts "- Built a model"
def test_numbered_list_items_become_bullets():# style "List Number" → "- Ran 15 interviews"
def test_table_row_is_one_line_in_order():    # row ("Alpine Logistics | Chicago", "Jul 2018 – Jul 2025") then a paragraph
    # → "Alpine Logistics | Chicago Jul 2018 – Jul 2025" appears before the paragraph
def test_header_text_comes_first():           # section header "Jane Doe" + body "EDUCATION" → starts "Jane Doe\n"
def test_text_box_text_is_read():             # append a w:txbxContent with one w:p "Lean Six Sigma" → in output
def test_tabs_are_kept_for_the_existing_rule():# "Analyst\tJun 2018" → contains "Analyst\tJun 2018"
def test_empty_paragraphs_keep_line_breaks(): # "A", "", "B" → "A\n\nB"
def test_not_a_docx_raises():                 # b"%PDF-1.7 ..." and b"" → pytest.raises(NotDocx)
```

- [ ] **Step 2:** Run `uv run pytest tests/unit/test_docx_text.py -q`. Expected: FAIL (module not found).
- [ ] **Step 3: Implement `read_docx_text`.** Header paragraphs first (first section's header), then `Document.iter_inner_content()` in order: a paragraph is a list item when its `pPr` has `numPr` or its style name starts with "List" (prefix "- "); a table yields one line per row, cell texts joined by a space, empty cells skipped; text-box paragraphs (`.//w:txbxContent//w:p`) are added after the paragraph that holds them. Catch python-docx's open errors (`PackageNotFoundError`, `KeyError`, `zipfile.BadZipFile`, `ValueError`) and raise `NotDocx`. Strip trailing blank lines.
- [ ] **Step 4:** Run the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: read the text of a Word file (bullets, tables, header, text boxes)`.

### Task 2: `POST /api/read-docx`

**Files:**
- Modify: `app/main.py` (route after `/api/tailor`)
- Test: `tests/api/test_read_docx_route.py`

**Interfaces:**
- Consumes: `read_docx_text`, `NotDocx` (Task 1).
- Produces: `POST /api/read-docx`, body = raw file bytes. 200 → `{"text": str, "lines": int}` (`lines` = non-empty lines). Errors via `ApiError` → `{"error": {"code", "message"}}`:
  - 413 `file_too_large`: "This file is over 5 MB. Save a copy without images, or paste the text."
  - 415 `not_docx`: "TrueFit reads Word files (.docx). For a PDF, open it and paste the text."
  - 422 `docx_empty`: "TrueFit couldn't find any text in this file. Check it's the right file, or paste the text."

- [ ] **Step 1: Write the failing tests** (reuse the `client` fixture; build files as in Task 1).

```python
def test_reads_a_resume(client):        # 200, text starts "Jane Doe", lines == 4
def test_too_large(client):             # 5 * 1024 * 1024 + 1 bytes → 413, code "file_too_large"
def test_renamed_pdf_is_rejected(client):# b"%PDF-1.7..." → 415, code "not_docx"
def test_empty_document(client):        # Document() with no text → 422, code "docx_empty"
def test_text_is_not_logged(client, caplog):  # read a file containing "SECRETLINE" → not in caplog.text
```

- [ ] **Step 2:** `uv run pytest tests/api/test_read_docx_route.py -q`. Expected: FAIL (404).
- [ ] **Step 3: Implement `post_read_docx(request: Request)`.** `data = await request.body()`; check size before reading; `MAX_DOCX_BYTES = 5 * 1024 * 1024`.
- [ ] **Step 4:** Run the same command, then `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: /api/read-docx returns the text of an uploaded Word file`.

### Task 3: Choose Word files on the page

**Files:**
- Modify: `app/static/index.html` (step 2 inputs), `app/static/app.js` (step 2 section, `loadProfile`/`saveProfile`, tailor request at line ~317, and the two `background_notes` reuses at ~552 and ~617), `app/static/styles.css`

**Interfaces:**
- Consumes: `POST /api/read-docx` (Task 2).
- Produces (in `app.js`): `readDocx(file: File) -> Promise<{text, lines}>` (raw `fetch` with the file as body; shows errors with the existing `showError`); `noteFiles: Array<{name, text, lines}>`; `backgroundNotesText() -> string` = each file's text in order added, then `notesInput.value`, joined by `"\n\n"`, empty parts skipped. Every place that sends `background_notes` uses `backgroundNotesText()`.

Behavior (copy is fixed by the design):
- **Master resume:** "Choose Word file" button (hidden `<input type="file" accept=".docx">`) beside the label, "or paste" hint. After reading: textarea filled and `readOnly`, a status row "✓ {name} · {lines} lines read" with **Edit text** (clears `readOnly`, keeps the name as a note) and **Remove** (clears text and status). Choosing a new file replaces the text.
- **More about your experience:** "Add Word file" button; the textarea never locks. Each file is a row under it: "✓ {name} · {lines} lines" with **Preview** (toggles a read-only block of its text) and **Remove**. Adding a file with the same name replaces that row.
- **Saving on this device:** `saveProfile` also stores `noteFiles` (name, text, lines) under the same key; `loadProfile` restores them (missing → `[]`); **Clear saved** empties them. The resume's file name isn't stored.
- **PostHog:** `track("file_read", { box: "resume" | "notes", lines })` on success, `track("file_read_failed", { box, error_code })` on failure.

- [ ] **Step 1: Implement the markup, styles, and JS above.**
- [ ] **Step 2:** `uv run pytest -q`. Expected: all pass (no Python changes; confirms nothing else broke).
- [ ] **Step 3: Browser check (Playwright, fake AI response, analytics blocked, as in PR #37).** Desktop and phone widths: upload a resume .docx → locked, line count shown → Edit text → editable → Remove → empty. Add two note files → both listed, Preview works, textbox still typeable.
- [ ] **Step 4: Review Focus #5.** Add the same note file twice → one row. Tailor → the request's `background_notes` contains each file's text once, then the typed text.
- [ ] **Step 5:** Save on this device, reload → note files and resume text restored; Clear saved → all gone.
- [ ] **Step 6: Commit** `feat: choose Word files for the resume and notes (locked resume preview)`.

### Task 4: Docs and pull request

**Files:**
- Modify: `docs/index.html`, `PRODUCT.md`, `AGENTS.md`, `specs/2026-11-18-word-upload-design.md` (Status → "approved Nov 18, built")

- [ ] **Step 1: Product Page.** "Also out of scope for v1" line: PDF upload stays out; Word upload removed from the list. Add a decision row after the last dated row: *Should students be able to upload files instead of pasting?* / *Word files, yes, for the master resume and More about your experience. Pasting a lot of text is messy: it's easy to miss part of it or make a typo or accidental deletion while reviewing it in a textbox. The resume shows locked after reading, with Edit text; notes take several files plus typed text. PDFs stay paste-only because reading them breaks the line structure.* / Nov 18, 2026. Update "How it works" step 2 to mention Word files.
- [ ] **Step 2:** `PRODUCT.md` (inputs) and `AGENTS.md` (project structure: `app/docx_text.py`; the new route) match.
- [ ] **Step 3:** `uv run pytest -q`. Expected: all pass; note the count.
- [ ] **Step 4: Commit** `docs: Word file upload on the Product Page, PRODUCT.md, AGENTS.md`, push `word-upload`, open the PR (what changed, kept on purpose, test count, browser check), and **ask before merging**.
