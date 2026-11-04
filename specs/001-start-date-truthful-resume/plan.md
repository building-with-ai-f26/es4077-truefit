# Implementation Plan: Start-Date Check & Truthful Tailored Resume

**Branch**: `speckit-setup` (feature `001-start-date-truthful-resume`) | **Date**: 2026-11-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-start-date-truthful-resume/spec.md`

## Summary

A student pastes a job posting. They get a start-date verdict against their availability (starting June
2027 by default, or another start month, Immediate, ASAP, or Flexible). Then they get a tailored,
plain-text resume where every bullet is traced to their master resume, with gaps grouped as
Required or Preferred.

Technical approach: a small, stateless Python server holds the OpenRouter key and makes the model
calls. A single plain HTML/JS page is the whole UI and saves the master resume and availability in
the browser's local storage. The model only *extracts and drafts*. Every rule that protects
truthfulness and every verdict is decided by plain Python code that can be unit-tested without a
model:

- the start-date verdict
- the check that the quote really appears in the posting
- the number/fact trace check
- plain-text output

See [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.12 (installed and run with `uv`; the system Python 3.9 isn't used); vanilla HTML/CSS/JavaScript for the page

**Primary Dependencies**: FastAPI + Uvicorn (web server), httpx (OpenRouter calls), Pydantic (request/response shapes; ships with FastAPI). Dev only: pytest

**Storage**: None on the server. The browser's `localStorage` holds the master resume and availability (FR-020, FR-021)

**Testing**: pytest for deterministic logic and API routes, with the model call replaced by a fake. Separate model eval script in `tests/eval/` for SC-002, SC-003, and SC-005 (Build 4 Track A)

**Target Platform**: Local Mac through Week 4 (`localhost:8000`); one small cloud web service in Build 5 (e.g., Render or Railway). Modern desktop browsers

**Project Type**: Web app: single Python service serving one static page plus a JSON API

**Performance Goals**: Start-date verdict shown within 30 s of submit; tailored resume within 2 min (SC-001). Re-checking an edited bullet within 15 s

**Constraints**:
- No resume or posting content stored on the server or written to logs (FR-019)
- API key only on the server (Constitution: Security)
- Copy-ready output is plain text that pastes cleanly into ATS fields (FR-014)
- Inputs capped at 20,000 characters each

**Scale/Scope**: Classmate testing: under 50 users, a few runs each per week. One page, three API routes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Section | How this plan complies | Status |
|---|---|---|
| I. Truth Over Polish | The model must cite master-resume line IDs for every bullet. Python code then checks that every number, percent, dollar amount, and date in a bullet appears in its cited lines. It also checks that no posting keyword appears unless it's in the master resume. A second model "support" check confirms the meaning. A bullet is "Traced" only if **both** pass; otherwise it's flagged and excluded by default. Edited bullets go through the same check (FR-012b). | Pass |
| II. Show the Source | Start-date quotes and requirement quotes must be exact substrings of the posting. Python verifies this, and an unverifiable quote becomes "Not stated" instead of being shown. Verdicts come from a fixed enum in code, never from free model text. | Pass |
| III. ATS-Safe Plain Output | A deterministic plain-text renderer produces the copy-ready text: standard headings, `- ` bullets, straight quotes, no tables or special characters. It's unit-tested, and a manual Workday/iCIMS paste check is in the quickstart. | Pass |
| IV. One Core Workflow | Three routes, all inside the spec's workflow. No accounts, scraping, tracking, or styling. | Pass |
| V. Simple, Explainable, Small Batches | 4 runtime dependencies, no frontend framework, no database, no build step. | Pass |
| Security, Privacy & Cost | Key in `.env` and read only by the server. Request bodies are never logged; logs contain route, timing, and status only. The OpenRouter spend limit is set in Build 2. Cost per run is estimated in research.md and recorded in the PRD. | Pass |
| Quality gates | Truthfulness and start-date eval sets live in `tests/eval/`, and they're required to pass for any prompt or model change. | Pass |

No violations, so the Complexity Tracking table is empty.

**Post-design re-check (after Phase 1)**: Still passes. The contracts keep the model's output
behind deterministic checks (see `contracts/api.md` → "Server-side guarantees"). The data model
stores nothing on the server. One new risk is recorded in research.md §R6: the keyword check
can flag legitimate rewording. The safe default is to flag rather than allow, which matches
Principle I.

## Project Structure

### Documentation (this feature)

```text
specs/001-start-date-truthful-resume/
├── plan.md              # This file
├── research.md          # Phase 0: decisions and rationale
├── data-model.md        # Phase 1: entities, fields, validation
├── quickstart.md        # Phase 1: how to run and validate end-to-end
├── contracts/
│   └── api.md           # Phase 1: JSON API + browser storage contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
app/
├── main.py              # FastAPI app: serves static page, defines 3 API routes
├── config.py            # Reads OPENROUTER_API_KEY / OPENROUTER_MODEL from env
├── llm.py               # One function that calls OpenRouter and returns parsed JSON
├── availability.py      # Parses a start month ("June 2027") / Immediate / ASAP / Flexible
├── start_date.py        # Model extraction prompt + deterministic verdict rules
├── resume_lines.py      # Splits master resume into numbered, referenceable lines
├── tailor.py            # Tailoring + gap-list prompts, orchestration
├── trace_check.py       # Deterministic fact checks + model support check
├── plain_text.py        # ATS-safe plain-text renderer and character cleanup
└── static/
    ├── index.html       # The whole UI
    ├── app.js           # Calls the API, renders results, localStorage, copy button
    └── styles.css

tests/
├── unit/                # availability, verdict rules, quote check, trace check, plain text
├── api/                 # route tests with the model call replaced by a fake
└── eval/
    ├── cases/           # Anonymized postings + master resumes with expected answers
    └── run_eval.py      # Real model runs; scores SC-002, SC-003, SC-005

pyproject.toml           # uv project: Python 3.12, dependencies, pytest config
.env.example             # OPENROUTER_API_KEY, OPENROUTER_MODEL (placeholders)
```

**Structure Decision**: A single Python project. FastAPI serves the static page from
`app/static/` and the JSON API from the same process, so local run is one command and the Build 5
deploy is one service. Each file maps to one idea in the spec, so the builder can explain it
file by file. `tests/` keeps the existing `README.md` and adds the three folders above.

## Complexity Tracking

No constitution violations to justify.
