# Quickstart & Validation: Start-Date Check & Truthful Tailored Resume

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/api.md](./contracts/api.md)

This guide shows how to run TrueFit locally and confirm the feature works end to end. Exact
commands also belong in `AGENTS.md` §2 once the code exists.

## Prerequisites

- `uv` installed (it is: `/opt/homebrew/bin/uv`)
- An OpenRouter API key with a spend limit set in the OpenRouter dashboard

## Setup

```bash
cd ~/Desktop/es4077-truefit
cp .env.example .env              # then paste your real key into .env
# .env must contain:
#   OPENROUTER_API_KEY=sk-or-...
#   OPENROUTER_MODEL=<model slug from openrouter.ai/models>
uv sync                           # installs Python 3.12 + dependencies into .venv
```

## Run

```bash
uv run uvicorn app.main:app --reload
# open http://localhost:8000
```

## Automated checks

```bash
uv run pytest tests/unit tests/api     # deterministic; no API key or cost
uv run python tests/eval/run_eval.py   # real model calls; costs money; prints SC-002/003/005
```

**Expected**:
- unit and API tests all pass
- eval reports start-date agreement of 9/10 or better
- 0 untraced bullets included by default
- 0 altered numbers
- gap recall of at least 80%

## Manual validation scenarios

| # | Do this | Expect | Covers |
|---|---|---|---|
| 1 | Paste a posting with "Start date: July 13, 2027", leave availability as default | "In window", quote shown, availability "June 2027 – October 2027" shown | US1-1, FR-005, FR-006a |
| 2 | Paste a posting that only says "Summer 2027" | "Likely in window (vague)" + note | US1-3 |
| 3 | Paste a posting with no start date | "Not stated", no date shown | US1-4, FR-007 |
| 4 | Set availability to `asap through August 2027`, then paste "Start date: September 8, 2027" | "Outside window" | US1-5, FR-006a (case-insensitive) |
| 5 | Set availability to `Flexible`, then paste "Start date: March 6, 2028" | "In window", date still shown | US1-7 |
| 6 | Set availability to `soonish` | Plain error listing accepted forms; previous availability kept | Edge case, FR-006b |
| 7 | Continue to tailoring with a master resume that never mentions SQL, for a posting that asks for SQL | No bullet claims SQL; SQL appears in the gap list | US2-2, US3-2 |
| 8 | Find a bullet with a number; compare to its source line | Number matches exactly; source line shown | US2-1, US2-3 |
| 9 | Edit a bullet to add "led a team of 8" | Bullet becomes flagged with a reason within ~15 s | US2-5, FR-012b |
| 10 | Put a flagged bullet back, then click Copy | It's in the copied text; still marked in the review view | US2-6, FR-012c |
| 11 | Paste the copied resume into a plain-text field (TextEdit in plain-text mode) and into a Workday or iCIMS resume field if you can reach one | One column, headings and bullets in order, no odd characters | US3-1, SC-004 |
| 12 | Posting with "CPA required" and "Python a plus" (neither in resume) | CPA under Required, Python under Preferred | US3-3 |
| 13 | Reload the page | Master resume and availability pre-filled; posting box empty | FR-020 |
| 14 | Click "Clear saved resume", reload | Resume box empty; availability back to default | FR-021 |
| 15 | Run any of the above, then check the server terminal output | No resume or posting text in the logs | FR-019, Constitution |

## Timing check (SC-001)

During scenarios 1 and 7, note the time from clicking the button to seeing the result. The
targets are under 30 s for the start date and under 2 min for tailoring. Record the results in
the Build log.
