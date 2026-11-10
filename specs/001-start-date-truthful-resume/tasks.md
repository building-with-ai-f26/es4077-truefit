---

description: "Task list for 001-start-date-truthful-resume"
---

# Tasks: Start-Date Check & Truthful Tailored Resume

**Input**: Design documents from `/specs/001-start-date-truthful-resume/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md), [quickstart.md](./quickstart.md)

**Tests**: Included. The constitution requires a truthfulness check and a start-date check, and
plan.md §Testing sets out unit, API, and eval tests. Within each story, write the tests first and
confirm they fail before implementing.

**Organization**: Tasks are grouped by user story so each can be built and demonstrated on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1, US2, US3)
- Paths follow plan.md: `app/` and `tests/` at the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization

- [X] T001 Create `pyproject.toml` as a uv project with `requires-python = ">=3.12"`. Add runtime dependencies `fastapi`, `uvicorn[standard]`, `httpx`, a dev dependency group with `pytest`, and `[tool.pytest.ini_options] testpaths = ["tests/unit", "tests/api"]`. Then run `uv sync` to create `.venv`.
- [X] T002 [P] Create `.python-version` containing `3.12`
- [X] T003 [P] Create package skeleton: `app/__init__.py`, `app/static/`, `tests/unit/__init__.py`, `tests/api/__init__.py`, `tests/eval/cases/start_date/.gitkeep`, `tests/eval/cases/tailor/.gitkeep`
- [X] T004 [P] Add `OPENROUTER_MODEL=replace-with-model-slug-from-openrouter.ai/models` to `.env.example` under the existing key (placeholder only; never a real value)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, model client, app shell, error format, and the shared quote check. All user stories depend on these.

**⚠️ CRITICAL**: No user-story work starts until this phase is complete.

- [X] T005 Implement `app/config.py`. It reads `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` from the environment (loading `.env` if present). If either is missing, it raises a clear startup error that names the missing variable and never prints its value.
- [X] T006 Implement `app/llm.py` with an async `call(system: str, user: str) -> dict`. It POSTs to `https://openrouter.ai/api/v1/chat/completions` via httpx with `response_format={"type": "json_object"}`, `temperature=0`, and a 60 s timeout. It parses the JSON content and retries once on an HTTP error, timeout, or unparseable JSON. After that it raises `ModelUnavailable`. It never logs prompts or responses (FR-019).
- [X] T007 Implement `app/quotes.py` with `quote_in(source: str, quote: str) -> bool`. It's true only if `quote` is a non-empty exact substring of `source` after collapsing all whitespace runs to single spaces (contracts/api.md guarantee 1). This file is a small addition to plan.md's layout, shared by start-date and gap checks.
- [X] T008 Implement `app/main.py`:
  - a FastAPI app serving `app/static/` and `GET /` → `index.html`
  - an `ApiError(status, code, message)` exception and handler returning `{"error": {"code", "message"}}`
  - a `ModelUnavailable` → 502 `model_unavailable` handler
  - a `check_length(text, field, min, max)` helper raising `<field>_too_short` / `<field>_too_long` (posting 100–20,000 chars, master_resume 200–20,000, bullet_text 1–600)
  - request-logging middleware that records only route, status, duration ms, and model, never bodies
- [X] T009 [P] Create `app/static/index.html` and `app/static/styles.css`. Lay out three areas in order (1. Availability + Posting, 2. Master resume, 3. Results) with no logic yet. Use plain semantic HTML with labeled inputs.
- [X] T010 Create `app/static/app.js` with shared helpers:
  - `api(path, body)`: a fetch wrapper that shows `error.message` in a visible error area
  - `loadProfile()` / `saveProfile({masterResume, availabilityText})` / `clearProfile()` using only `localStorage` key `truefit.v1` with value `{ masterResume: string, availabilityText: string, savedAt: ISO datetime }` (contracts/api.md, Browser storage). Postings are never stored.
- [X] T011 Create `tests/api/conftest.py` with a `client` fixture (FastAPI `TestClient`) and a `fake_llm` fixture. `fake_llm` monkeypatches `app.llm.call` to return queued canned dicts (or raise `ModelUnavailable`) and records the calls made.
- [X] T012 [P] Write `tests/unit/test_quotes.py` covering exact match, whitespace/newline differences, a paraphrase (false), an empty quote (false), and a case difference (false)

**Checkpoint**: `uv run uvicorn app.main:app` serves an empty page; `uv run pytest` passes.

---

## Phase 3: User Story 1 - Start-date check (Priority: P1) 🎯 MVP

**Goal**: Paste a posting and see its start date, the quoted source, and a verdict against the student's availability.

> **Revised 2026-11-04:** availability is now a single "available starting" month (default June 2027) instead of a range; any later start is in window. T013, T016, T017, and T020 were updated to match. "Immediate" was then dropped as an availability option (students type "ASAP"). See spec Clarifications.

**Independent Test**: Run scenarios 1–6 in quickstart.md plus the start-date eval set. Verdicts match expected results in at least 9 of 10 cases, and there's never a date for a posting that doesn't state one.

### Tests for User Story 1 ⚠️ write first, confirm they fail

- [X] T013 [P] [US1] Write `tests/unit/test_availability.py` covering:
  - `<Month YYYY> – <Month YYYY>` with `-`, `–`, and `to`
  - full and 3-letter month names
  - case-insensitive `Immediate`/`immediate`/`ASAP`/`asap`, all giving `mode: immediate` with `start = today`
  - `ASAP through August 2027` / `until` / `to`, giving an end of Aug 31, 2027
  - `Flexible`, giving `mode: flexible` with `start` and `end` null
  - empty input, giving the default range June 1 2027 – October 31 2027
  - end before start, giving `availability_end_before_start`
  - `soonish`, giving `availability_invalid` with a message listing the accepted forms
- [X] T014 [P] [US1] Write `tests/unit/test_verdict.py`: a table-driven test of the 8 ordered verdict rules in data-model.md §Verdict rules with a fixed `today = 2026-11-04`. Include:
  - spec US1 scenarios 1–8
  - date already passed → `outside_window` + note
  - posting immediate vs range availability → `outside_window` "starts before you're available"
  - posting immediate vs Immediate/ASAP/Flexible → `in_window`
  - "May–July 2027" → `partly_in_window`
  - posting flexible → `flexible_to_discuss`
  - Summer 2027 → `likely_in_window_vague`
  - Fall 2027 with the default window → `partly_in_window` + "exact date not specified"
  - two mentions that disagree → summary `partly_in_window` with per-mention verdicts
- [X] T015 [P] [US1] Write `tests/api/test_start_date_route.py` using `fake_llm`. Cover:
  - a valid mention, giving 200 with the contract shape
  - a model quote that's not in the posting, which is dropped and gives `not_stated`
  - a `verdict` field the model sends anyway, which is ignored
  - model reports `is_job_posting: false` → 422 `not_a_posting`
  - model reports `is_english: false` → 422 `not_english`
  - posting length outside 100–20,000 → 422 `posting_too_short` / `posting_too_long`
  - `ModelUnavailable` → 502

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement `parse_availability(text: str, today: date) -> Availability` in `app/availability.py` per data-model.md §Availability:
  - `mode` is one of `range | immediate | flexible`; "Immediate" and "ASAP" both become `immediate`
  - `start`: first day of the start month (range), today (immediate), or null (flexible)
  - `end`: last day of the end month, optional for immediate, null for flexible
  - `label` is the display text
  - errors are raised as `ApiError(422, ...)`
- [X] T017 [US1] Implement the verdict logic in `app/start_date.py`:
  - `mention_interval()`: exact_date gives start = end; month gives the whole month; seasons are Spring = Mar–May, Summer = Jun–Aug, Fall = Sep–Nov; a bare year is vague
  - `compute_verdict(mentions, availability, today)`, which applies the 8 ordered rules and the summary rule from data-model.md
  - the `VERDICT_LABELS` map with the exact display labels: In window · Outside window · Partly in window · Likely in window (vague) · Flexible / to discuss · Not stated
- [X] T018 [US1] Implement `check_start_date(posting, availability_text)` in `app/start_date.py`. Its extraction prompt asks the model for JSON `{is_job_posting, is_english, mentions: [{quote, kind, start, end, role_hint}]}` with `kind` in `exact_date | month | range | season | immediate | flexible`. The prompt tells the model to quote verbatim, never invent dates, and return an empty list when no start date is stated (FR-007). The function then:
  - drops mentions failing `quotes.quote_in`
  - sets `is_vague`
  - computes `today` in `America/New_York` with `zoneinfo`
  - returns a `StartDateResult`
- [X] T019 [US1] Add `POST /api/start-date` to `app/main.py` per contracts/api.md, with request `{posting, availability_text?}` and a 200 `StartDateResult` including `verdict_label` and `availability.label`
- [X] T020 [US1] Build the start-date UI in `app/static/index.html` and `app/static/app.js`:
  - an availability input pre-filled from `truefit.v1.availabilityText`, with placeholder "June 2027 – October 2027 (or Immediate, ASAP, Flexible)"
  - posting textarea and "Check start date" button
  - result card with the verdict label, each quote in a blockquote with its role hint, "Checked against: <availability.label>", and the note
  - save `availabilityText` to the profile on a successful check
  - on an `availability_*` error, show the message and leave the saved value unchanged
- [X] T021 [US1] Create at least 10 anonymized posting cases in `tests/eval/cases/start_date/*.json` as `{posting, availability_text, expected_verdict}`. Cover explicit date, month, range crossing the window, Summer, Fall, missing, application deadline + start date, multi-role, "ASAP" posting, and "flexible start" posting. Then write `tests/eval/run_eval.py --suite start_date`, which calls the real app logic and prints agreement and any case that returned a date where expected was `not_stated` (SC-002).

**Checkpoint**: US1 works on its own. It's demo-able for Build 1 and Build 2 as the start-date check.

---

## Phase 4: User Story 2 - Truthful tailored resume (Priority: P1)

**Goal**: Turn a posting and master resume into tailored bullets, each traced to master-resume lines or flagged. The student can remove, put back, and edit bullets with a re-check.

**Independent Test**: Run quickstart scenarios 7–10 and 13–14 plus the tailor eval set. 100% of default-included bullets trace, there are zero altered numbers, and 100% of edits with claims that can't be traced are flagged (SC-003).

### Tests for User Story 2 ⚠️ write first, confirm they fail

- [x] T022 [P] [US2] Write `tests/unit/test_resume_lines.py`: blank lines are skipped, IDs run `L1…Ln` in order, text is trimmed, and `section` is the nearest heading above (e.g., "Experience", "Education")
- [x] T023 [P] [US2] Write `tests/unit/test_trace_check.py`, covering:
  - number extraction for `12%`, `$1.2M`, `3x`, `2023`, `Jun 2024`, and `1,500`
  - a bullet with "15%" citing a line with "12%" → flagged "'15%' not found in source lines"
  - an unknown line ID → flagged
  - a posting-only term "SQL" (in the posting, not anywhere in the master) → flagged "'SQL' isn't in your master resume"
  - a generic job word in the posting (e.g., "team", "experience") → not flagged
  - support check returns unsupported → flagged with its claim
  - all checks pass → `traced`
- [x] T024 [P] [US2] Write `tests/api/test_tailor_route.py` using `fake_llm`, covering:
  - 200 contract shape with `resume_lines` and `resume.sections`
  - a fake bullet with a fabricated metric → `status: flagged`, `included: false`
  - every flagged bullet has `included: false` (guarantee 4)
  - malformed model JSON twice → 502 `model_unavailable`, with no partial output
  - `master_resume` length outside 200–20,000 → 422
- [x] T025 [P] [US2] Write `tests/api/test_verify_bullet_route.py` using `fake_llm`, covering:
  - an edited bullet "Led a team of 8 …" whose master has no "8" → `flagged` with a reason naming "8"
  - an unchanged-meaning rewording → `traced`
  - `bullet_text` length outside 1–600 → 422

### Implementation for User Story 2

- [x] T026 [P] [US2] Implement `split_lines(master_resume) -> list[ResumeLine]` in `app/resume_lines.py`. Each line has `id` `L1`, `L2`, … in order of appearance, with `text` as the original line trimmed and blank lines skipped. `section` is the nearest heading above it if one is detected (a short line in caps or matching common headings), else null.
- [x] T027 [US2] Implement the deterministic checks in `app/trace_check.py` (research.md §R6, checks 1–3): `extract_numbers(text)`, `posting_only_terms(posting, master)` (with a stopword list and a generic-job-word list in the same file), and `deterministic_check(bullet, lines, posting, master) -> (ok, reason)`
- [x] T028 [US2] Implement `support_check(bullets, lines)` in `app/trace_check.py`. It makes one batched `llm.call` returning `{results: [{bullet_id, supported, unsupported_claim}]}`. Add `check_bullets(...)`, which sets `status: traced` only if the deterministic check and the support check both pass, and otherwise `flagged` with `flag_reason` set. It also sets `included = (status == "traced")` for generated bullets.
- [x] T029 [US2] Implement `tailor_resume(posting, master_resume)` in `app/tailor.py`. The tailoring prompt sends numbered lines and the posting. It asks for JSON `{sections: [{heading, entries: [{header_line_ids, bullets: [{text, source_line_ids}]}]}]}`. Instructions: only reword/select/reorder, keep numbers exactly, cite line IDs for every bullet, aim for about one page, order Education, Experience, then others in master-resume order. The function then assigns bullet IDs `B1…` and runs `trace_check.check_bullets`.
- [x] T030 [US2] Add `POST /api/tailor` to `app/main.py`. It takes `{posting, master_resume}`, validates lengths, and returns `{resume_lines, resume: {sections}}` per contracts/api.md. US3 adds `plain_text` and `gaps`.
- [x] T031 [US2] Add `POST /api/verify-bullet` to `app/main.py`. It takes `{bullet_text, master_resume, posting, source_line_ids}`, runs `check_bullets` on the single bullet, and returns `{status, source_line_ids, flag_reason}`. Only existing line IDs count.
- [x] T032 [US2] Build the master-resume UI in `app/static/index.html` and `app/static/app.js`:
  - textarea pre-filled from `truefit.v1.masterResume` (FR-020) with "Saved on this device on <savedAt>"
  - "Save on this device" and "Clear saved resume" buttons (FR-021). Clear removes the key and resets availability to the default.
  - a "Tailor resume" button that stays disabled until a start-date result is on screen (FR-008)
- [x] T033 [US2] Render tailored results in `app/static/app.js`: entries with header lines, and each bullet with its text, its source line(s) shown under it, and a Traced/Unverified badge with `flag_reason`. Flagged bullets start excluded.
- [x] T034 [US2] Add bullet controls in `app/static/app.js`:
  - Remove/Put back toggles `included` (FR-012a)
  - inline Edit sets `edited = true`, calls `/api/verify-bullet`, and updates the status, reason, and sources, showing "Checking…" while waiting (FR-012b)
  - a put-back flagged bullet stays visibly marked Unverified (FR-012c)
- [x] T035 [US2] Create 10 anonymized posting + master-resume pairs in `tests/eval/cases/tailor/*.json` (5 normal, 3 messy, 2 adversarial: a posting that pushes for skills the student lacks, and a resume full of metrics). Each holds `{posting, master_resume, expected_gaps: {required: [], preferred: []}}`. Extend `tests/eval/run_eval.py --suite tailor` to report:
  - default-included bullets whose numbers aren't in their cited lines (must be 0)
  - default-included bullets with posting-only terms (must be 0)
  - the false flag rate (flagged bullets a reviewer would accept), as a manual count prompt

**Checkpoint**: US1 + US2 work end to end. The student can check a date, then get and refine a traced resume.

---

## Phase 5: User Story 3 - ATS-ready output and gap list (Priority: P2)

**Goal**: One-click copy of clean plain text, plus gaps grouped as Required and Preferred.

**Independent Test**: Run quickstart scenarios 11–12, and paste into a plain-text field and Workday/iCIMS when available (SC-004). Run the tailor eval for gap recall (at least 80%) and grouping agreement (at least 90%) (SC-005).

### Tests for User Story 3 ⚠️ write first, confirm they fail

- [ ] T036 [P] [US3] Write `tests/unit/test_plain_text.py`, covering:
  - output contains only included bullets
  - headings sit on their own line with a blank line before
  - role lines are copied verbatim from header lines
  - bullets start with `- `
  - curly quotes become straight quotes
  - `•`/`▪` and tabs are removed or replaced
  - `–` is kept only in date ranges and turned into `-` elsewhere
  - every character is printable ASCII or a newline, except `–` in date ranges (guarantee 5)
- [ ] T037 [P] [US3] Write `tests/api/test_gaps.py` using `fake_llm`, covering:
  - "CPA required" + "Python a plus" → CPA under `required`, Python under `preferred`
  - an `unlabeled` requirement → `required`
  - `supported: true` with no valid line IDs → kept as a gap
  - a requirement quote not in the posting → dropped
  - all supported → `none_found: true` with empty groups (FR-017)

### Implementation for User Story 3

- [x] T038 [P] [US3] Implement `normalize_chars(text)` and `render_plain_text(resume, lines) -> str` in `app/plain_text.py` per research.md §R10
- [ ] T039 [US3] Implement `build_gap_list(posting, master_resume, lines)` in `app/tailor.py`:
  - the requirements prompt asks for JSON `{requirements: [{text, quote, group, supported, line_ids}]}` with `group` in `required | preferred | unlabeled`, reading the posting's wording ("required", "must have" vs "preferred", "nice to have", "a plus")
  - drop requirements whose quote fails `quote_in`
  - map `unlabeled` to `required`
  - treat supported-without-valid-line-IDs as unsupported
  - return `{required, preferred, none_found}`
- [ ] T040 [US3] In `app/tailor.py`, run the tailoring call and `build_gap_list` concurrently with `asyncio.gather`. Extend `POST /api/tailor` in `app/main.py` to return `resume.plain_text` (from included bullets) and `gaps` per contracts/api.md.
- [ ] T041 [US3] In `app/static/app.js`:
  - add `renderPlainText(state)`, mirroring `app/plain_text.py` (same headings, `- ` bullets, character rules), and rebuild it on every include/remove/edit
  - add a "Copy resume" button using `navigator.clipboard.writeText` with a "Copied" confirmation (FR-015)
  - render the gap list as "Required" and "Preferred" groups with quotes and notes, or "No gaps found" (FR-017)
- [ ] T042 [US3] Extend `tests/eval/run_eval.py --suite tailor` to score gaps against `expected_gaps`: recall of at least 80% and group agreement of at least 90% (SC-005)

**Checkpoint**: All three stories work; the full core workflow is complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T043 [P] Write `tests/api/test_no_content_logs.py`. It runs each route with a posting and resume containing a unique marker string, captures logs with `caplog`, and asserts the marker never appears (FR-019, constitution).
- [ ] T044 [P] Fill in `AGENTS.md` §1 (overview, user and workflow, stack: Python 3.12 / FastAPI / plain HTML+JS / OpenRouter) and §2. The §2 commands are `uv sync`, `uv run uvicorn app.main:app --reload`, `uv run pytest`, and `uv run python tests/eval/run_eval.py` (Constitution governance: keep AGENTS.md consistent).
- [ ] T045 [P] Update the "Local setup" section of `README.md` with the same install and run commands and the `.env` steps from quickstart.md
- [ ] T046 Run all 15 manual scenarios in `specs/001-start-date-truthful-resume/quickstart.md`, time scenarios 1 and 7 (SC-001), and record results and known limits in the Build log in `docs/index.html`
- [ ] T047 Update `docs/index.html` PRD §3 (architecture: Page → Python server → OpenRouter model → deterministic checks → result) and §4 "Est. Cost Per User Run", using measured token usage from an eval run

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories → **Polish (Phase 6)**
- **US1 (Phase 3)**: depends only on Foundational.
- **US2 (Phase 4)**: depends on Foundational. Its API and tests don't need US1. Only the UI gate in T032 (FR-008) needs the US1 result card, so build US1 first for the UI.
- **US3 (Phase 5)**: depends on US2 (it extends `/api/tailor` and the results view).

### Within each story

Tests (written to fail) → pure logic modules → model-calling functions → routes → UI → eval cases.

### Key task dependencies

- T006 → T018, T028, T029, T039 (all model calls)
- T007 → T018, T039 (quote checks)
- T008 → T019, T030, T031
- T016, T017 → T018 → T019 → T020
- T026, T027, T028 → T029 → T030 → T032 → T033 → T034
- T038, T039 → T040 → T041

## Parallel Opportunities

**Phase 1**: T002, T003, and T004 together after T001.

**Phase 2**: T009 and T012 alongside T005–T008.

**US1**:
```text
T013 test_availability.py   T014 test_verdict.py   T015 test_start_date_route.py
then: T016 availability.py  (in parallel with T017 verdict logic once tests exist)
```

**US2**:
```text
T022 test_resume_lines.py   T023 test_trace_check.py   T024 test_tailor_route.py   T025 test_verify_bullet_route.py
then: T026 resume_lines.py  (in parallel with T027 deterministic checks)
```

**US3**:
```text
T036 test_plain_text.py   T037 test_gaps.py
then: T038 plain_text.py  (in parallel with T039 gap list)
```

**Polish**: T043, T044, and T045 together.

## Implementation Strategy

### MVP first (User Story 1)

1. Phases 1–2 (setup and foundation)
2. Phase 3 (US1: start-date check)
3. **Stop and validate**: run quickstart scenarios 1–6 and `run_eval.py --suite start_date`
4. This is enough for the Build 2 "smallest local version" and tests the start-date risk first

### Incremental delivery

1. US1 → demo the start-date check (Build 2, Nov 16)
2. US2 → traced, editable resume, which tests the riskiest assumption: truthfulness (Build 3, Nov 23)
3. US3 → copy-ready ATS text and the gap list, completing the core workflow (Build 3)
4. Polish plus the eval sets → Build 4 Track A evidence (Nov 30)

### Rules while building

- Stop and ask after two failed fixes in a row (constitution)
- Any prompt or model change re-runs `tests/eval/run_eval.py` before it's committed
- Commit after each task or small group; keep each change small enough to explain
