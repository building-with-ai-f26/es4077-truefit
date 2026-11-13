# AGENTS.md — Coding Agent Operating Manual

> Give this file to your coding agent and check that it is using these instructions. Keep the stack, commands, and ground rules current.

## 1. Project Overview
- **What this repo builds:** TrueFit — paste a job posting, learn whether its start date fits
  your availability, and get a tailored, ATS-ready resume where every bullet traces back to
  your master resume (nothing invented, numbers never altered).
- **Primary user & core workflow:** MBA students recruiting for roles starting in 2027.
  Paste posting → start-date verdict with quoted evidence → tailored resume + gap list → copy.
  See the living PRD in `docs/index.html` and the feature spec in `specs/001-start-date-truthful-resume/`.
- **Tech stack:** Python 3.12 / FastAPI + Uvicorn / plain HTML-CSS-JS frontend (`app/static/`) /
  OpenRouter API via httpx / uv for dependencies / pytest.

## 2. Commands
- **Install dependencies:** `cp .env.example .env` (add your key and model), then `uv sync`
- **Run locally:** `uv run uvicorn app.main:app --reload` → http://localhost:8000
- **Run deterministic tests:** `uv run pytest` (unit + API tests; no API key, no cost)
- **Run model evals:** `uv run python tests/eval/run_eval.py --suite start_date`
  (real model calls — costs money; ask before running)

## 3. Project Structure
- `app/main.py` — FastAPI app: serves the page, the `/api/start-date`, `/api/tailor`, and `/api/verify-bullet` routes, error handlers, and the PostHog server client.
- `app/start_date.py` — Start-date check. The model only finds and quotes start-date text; Python checks the quote and decides the verdict.
- `app/llm.py` — The one place TrueFit calls the model (OpenRouter). Prompts and responses are never logged.
- `app/quotes.py` — Confirms each quote really appears in the posting.
- `app/availability.py` — Parses the student's "available starting" text (month, ASAP, Flexible).
- `app/tailor.py` — Tailored resume. The model only selects, reorders, and rewords the student's numbered lines, citing them for every bullet.
- `app/resume_lines.py` — Splits the master resume (L1, L2, ...) and the student's other writing (N1, N2, ...) into numbered lines; restores line breaks lost in PDF paste.
- `app/trace_check.py` — Checks each bullet against the lines it cites: Python checks numbers and posting-only skills, then a model support check.
- `app/plain_text.py` — Copy-ready, ATS-safe plain text (`app.js` mirrors these rules after edits).
- `app/config.py`, `app/errors.py` — Reads `.env`; shared error types.
- `app/static/` — Plain HTML/CSS/JS frontend (`index.html`, `styles.css`, `app.js`, `posthog.js`).
- `docs/index.html` — Public Product Page, living PRD, and weekly build log (GitHub Pages from `main` → `/docs`).
- `specs/001-start-date-truthful-resume/` — Feature spec, plan, data model, and tasks.
- `tests/unit/`, `tests/api/` — Deterministic tests (`uv run pytest`). `tests/eval/` — real-model eval cases (cost money).

## 4. Non-Negotiable Engineering Rules
1. **Plan before coding:** Before touching multiple files, propose a brief plan and wait for approval.
2. **Small batches:** Make small, focused changes that can be reviewed and explained by a human in a single Pull Request.
3. **Explainability:** Avoid unnecessary abstractions or dependencies. Help the human builder understand the main components, what changed, why it matters, what could break, and how it was checked.
4. **Verify changes:** Run relevant checks. For a reproducible logic bug, use a failing test to demonstrate the fix when practical. Record manual checks and known limitations; follow the selected Build 4 evaluation track.
5. **Zero secrets in code:** Never hardcode API keys, tokens, or credentials. Always read from environment variables (`.env`) and update `.env.example` when new variables are needed.
6. **Stop when looping:** If a fix fails twice in a row, stop, summarize what failed, and ask the human before trying a third approach.
