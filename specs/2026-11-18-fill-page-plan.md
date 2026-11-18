# Downloads Fill the Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Word and PDF downloads use 1-inch margins when they fit, put clear space between schools and between jobs, and spread spare space so a resume that fits reaches the bottom margin.

**Architecture:** `app/docx_resume.py` owns the layout table and spacing constants that both downloads share. One shared notion of "gaps" (section headings, and each school/job after the first in its section) gets a base size plus an `extra_pt` that is the same for every gap. The PDF finds the largest `extra_pt` (capped) that still renders on one page; the Word file computes it from its height estimate with a safety margin.

**Tech Stack:** Python 3.12, python-docx, reportlab, pypdf (tests), pytest; Microsoft Word on this Mac for a manual check.

**Spec:** `specs/2026-11-18-fill-page-design.md`

## Global Constraints

- `LAYOUTS = [(11, 1.0), (10.5, 1.0), (10, 1.0), (10, 0.9), (10, 0.8), (10, 0.7), (10, 0.6), (10, 0.5), (9.5, 0.5), (9, 0.5), (8.5, 0.5), (8, 0.5)]` (0.1-inch steps; changed during the build) (body pt, margin in), tried in order.
- `SECTION_GAP_PT = 12` above each section heading; `ENTRY_GAP_PT = 8` above each school/job after the first in its section; the first entry in a section keeps `FIRST_ENTRY_GAP_PT = 4`.
- `extra_pt` is added to every section and entry gap; `0 <= extra_pt <= body_pt * 1.2` (one body line).
- Text never grows above 11 pt; 8 pt floor, name at least 11 pt, never cut bullets (unchanged).
- The Word file must never spill onto a second page.
- `uv run pytest` must pass; never run the model evals.

## Review Focus

1. A long resume that needs the smallest layout: `extra_pt` must be 0 and it still fits (or reports bullets to remove) exactly as before. → Task 1 `test_full_page_gets_no_extra_space`
2. A two-line resume: gaps stop at the cap and space stays at the bottom, no giant gaps. → Task 1 `test_short_resume_gaps_are_capped`
3. A section with one entry (no "after the first" gaps) and a resume with no sections: no division by zero. → Task 1 `test_no_entry_gaps`
4. The Word estimate: a resume that just fits at 1 inch must not spill in real Word. → Task 2 manual check with Microsoft Word
5. Header lines that wrap (long school names): the estimate counts the wrap so the gap isn't over-grown. → Task 2 `test_word_extra_space_counts_wrapped_headers`

---

### Task 1: Shared spacing and the PDF

**Files:**
- Modify: `app/docx_resume.py` (constants, `LAYOUTS`, new `gap_kinds`), `app/pdf_resume.py` (`build_pdf`, `_render`)
- Test: `tests/unit/test_pdf_resume.py`, `tests/unit/test_docx_resume.py` (layout table and name-size test)

**Interfaces:**
- Produces (in `docx_resume.py`): the constants above; `gap_kinds(blocks: list[tuple]) -> list[str | None]`, one entry per block: `"section"` for a heading, `"entry"` for a first header line that isn't first in its section, `"first_entry"` for the first one in a section, else `None`; `Layout` gains `extra_pt: float = 0`.
- Produces (in `pdf_resume.py`): `_render(blocks, body_pt, margin_in, extra_pt=0) -> tuple[bytes, int]`; `build_pdf` returns `Layout(..., extra_pt=...)`.

- [ ] **Step 1: Write the failing tests** (positions from pypdf text runs, as the existing layout test does).

```python
def test_layouts_start_at_one_inch(): LAYOUTS[:3] == [(11, 1.0), (10.5, 1.0), (10, 1.0)] and LAYOUTS[-1] == (8, 0.5)
def test_short_resume_uses_one_inch_margins(): left x of "Education" == 72
def test_schools_have_space_between(): y("NYU Stern…") - y("University of Michigan…") >= 11 * 1.2 + ENTRY_GAP_PT
def test_pdf_fills_the_page(): medium resume (sample + 8 bullets) → 1 page; lowest text baseline <= 72 + 11 * 1.2 * 1.5
def test_short_resume_gaps_are_capped(): name + 1 school → Layout.extra_pt == 11 * 1.2; lowest baseline > 72 + 100
def test_full_page_gets_no_extra_space(): the existing too-long resume → extra_pt == 0, same fits_one_page/remove_bullets as before
def test_no_entry_gaps(): blocks with only name, details, one heading, one entry → builds, 1 page
# test_docx_resume.py: the name/heading size test lists distinct body sizes from LAYOUTS
```

- [ ] **Step 2:** `uv run pytest tests/unit/test_pdf_resume.py tests/unit/test_docx_resume.py -q`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement.** `_render` puts a `Spacer` of the gap's base + `extra_pt` before each heading (replacing the heading style's `spaceBefore=10`) and each entry; `first_entry` gets `FIRST_ENTRY_GAP_PT` only. `build_pdf`: for the first layout that fits at `extra_pt=0`, binary-search `extra_pt` in `[0, body_pt * 1.2]` (8 rounds) for the largest that still renders on one page.
- [ ] **Step 4:** Same command, then `uv run pytest -q`. Expected: all pass (update the existing 0.75-inch position test to 1 inch).
- [ ] **Step 5: Commit** `feat: PDF download uses 1-inch margins, spaces schools and jobs apart, and fills the page`.

### Task 2: The Word download

**Files:**
- Modify: `app/docx_resume.py` (`choose_layout`, `_estimated_height`, `_render`)
- Test: `tests/unit/test_docx_resume.py`

**Interfaces:**
- Consumes: Task 1's constants, `gap_kinds`, `Layout.extra_pt`.
- Produces: `choose_layout(blocks) -> Layout` with `extra_pt` set; `_estimated_height` in points, counting gaps at their base sizes and Word's single line height (`WORD_LEADING = 1.22` × font size).

- [ ] **Step 1: Write the failing tests.**

```python
def test_word_short_resume_uses_one_inch_margins(): section margins == Inches(1)
def test_word_schools_have_space_between(): second school's first paragraph space_before >= Pt(8)
def test_word_extra_space_fills_estimate(): medium resume → extra_pt > 0 and estimated height + gaps * extra_pt <= 0.95 * page height
def test_word_extra_space_counts_wrapped_headers(): same resume with a 150-character school name → smaller extra_pt
def test_word_full_page_gets_no_extra_space(): too-long resume → extra_pt == 0, same remove_bullets as before
```

- [ ] **Step 2:** `uv run pytest tests/unit/test_docx_resume.py -q`. Expected: new tests FAIL.
- [ ] **Step 3: Implement.** `extra_pt = min(body_pt * 1.2, 0.95 * spare_pt / gap_count)` (0 when there are no gaps or no spare space); `_render` sets `space_before` = base + `extra_pt` on headings and entries.
- [ ] **Step 4:** Same command, then `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Manual check with Microsoft Word (Review Focus #4).** Save three sample Word files (short, medium, just-fits at 1 inch) and convert each to PDF with Word; each is 1 page, and the medium one ends near the bottom margin. If Word can't be automated, the student opens them.
- [ ] **Step 6: Commit** `feat: Word download uses 1-inch margins, spaces schools and jobs apart, and fills the page`.

### Task 3: Docs and pull request

**Files:** `docs/index.html`, `AGENTS.md`, `specs/2026-11-18-fill-page-design.md` (Status → "approved Nov 18, built")

- [ ] **Step 1:** Decision row after the posting-link row (or the Word upload row if that PR isn't merged): *Should the downloads fill the page?* / *Yes, by spreading the spacing, after testing with my own resume: schools and jobs ran together and a resume that fit left empty space at the bottom. Downloads use Word's standard 1-inch margins whenever the resume fits at 10 pt or larger; longer resumes narrow the margins (to 0.5 inch) before the text shrinks. Text stays at most 11 pt.* / Nov 18, 2026. Update the Product Page and `AGENTS.md` lines that describe margins ("0.75", "margins to 0.5 in").
- [ ] **Step 2:** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 3: Commit** `docs: downloads fill the page with 1-inch margins`, final review, push `fill-page`, open the PR, **ask before merging**.
