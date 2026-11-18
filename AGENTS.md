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
- **Run model evals:** `uv run python tests/eval/run_eval.py --suite start_date` (add `--cases 13 16` to run only some cases)
  (real model calls — costs money; ask before running)

## 3. Project Structure
- `app/main.py` — FastAPI app: serves the page, the `/api/start-date` (start date + eligibility), `/api/tailor`, `/api/verify-bullet`, `/api/read-docx`, and `/api/posting-link` routes, error handlers, and the PostHog server client.
- `app/start_date.py` — Start-date check. The model only finds and quotes start-date text; Python checks the quote and decides the verdict.
- `app/llm.py` — The one place TrueFit calls the model (OpenRouter). Prompts and responses are never logged.
- `app/eligibility.py` — Degree, sponsorship (internal key `work_authorization`), and years of experience, quoted in the start-date call. Python confirms each quote; degree gets a verdict, the other two are information only.
- `app/gaps.py` — Gap list: the model lists and quotes the posting's requirements and the lines that back them; Python checks quotes and line IDs, groups Required/Preferred, and writes each gap's note. Runs alongside tailoring.
- `app/quotes.py` — Confirms each quote really appears in the posting.
- `app/availability.py` — Parses the student's "available starting" text (month, ASAP, Flexible).
- `app/tailor.py` — Tailored resume. The model only selects, reorders, and rewords the student's numbered lines, citing them for every bullet.
- `app/resume_lines.py` — Splits the master resume (L1, L2, ...) and the student's other writing (N1, N2, ...) into numbered lines; restores line breaks lost in PDF paste.
- `app/trace_check.py` — Checks each bullet against the lines it cites: Python checks numbers and posting-only skills, then a model support check.
- `app/plain_text.py` — Copy-ready, ATS-safe plain text (`app.js` mirrors these rules after edits).
- `app/docx_resume.py` — One-page Word download from the same header rows and kept bullets; right-aligned tab stops for location and dates; 1-inch margins while the text is 10 pt or larger, then narrower margins (to 0.5 in), then all text shrinks together (body no smaller than 8 pt, name no smaller than 11 pt), never cuts bullets. A resume that fits fills the page: extra space between sections and entries, then between bullets (`gap_kinds`, `Layout.extra_pt`). Word's layout is estimated with Calibri's real widths (`app/calibri_widths.py`) and measured line heights, checked against Microsoft Word; the PDF is measured exactly. Route: `/api/resume-docx`.
- `app/pdf_resume.py` — The same blocks as a text-based one-page PDF (reportlab); measures pages exactly to fit or to say how many bullets to remove. Route: `/api/resume-pdf`.
- `app/docx_text.py` — Text of an uploaded Word file (list items as "- " bullets, table rows as one line, header text first, text boxes once); nothing stored or logged. Route: `/api/read-docx` (5 MB limit).
- `app/posting_link.py` — A job posting from a link: Greenhouse, Lever, and Workday public job data; Ashby and other pages through their JobPosting data only (never the rest of the page). LinkedIn, Indeed, Glassdoor, Handshake, and 12twenty answered without fetching. Every redirect checked for private addresses; 10 s timeout; 2 MB limit; links and text never logged (httpx request logging is turned down). Route: `/api/posting-link`.
- `app/rate_limit.py` — Limits for the live site, checked in `main.py` before any route: AI routes (start-date, tailor, verify-bullet) 10 a minute and 50 a day per visitor, 200 a day for the whole site; other API routes 30 a minute per visitor. In memory; resets on restart. The visitor is `CF-Connecting-IP` (set by Cloudflare in front of Render), else the last `X-Forwarded-For` address.
- `render.yaml` — Render web service (free plan, no database); secrets entered in the Render dashboard.
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
7. **Never log what students send, or where TrueFit fetches from** *(from a real mistake, Nov 18)*: when I added posting links, the web library (httpx) wrote every link it fetched into the server log at its default level. A test caught it. Any new library that makes requests or handles uploads gets a test that puts a marker string in the input and checks it's not in the logs.
8. **Respect a site's limits and blocks** *(from a real mistake, Nov 18)*: when Workday answered "too many requests," I retried with browser-like settings to get around it, and the permission check stopped me. If a site rate-limits or blocks TrueFit, stop and ask; test with one real link the student gives instead.
9. **Stage files by name, and look for " 2" copies** *(from a real mistake, Nov 18)*: this repo sits on an iCloud-synced Desktop, which makes copies like `rate_limit 2.py` when files change mid-sync. `git add -A` committed two of them into PR #47. Add files by name, and check `git status` for names ending in " 2" before committing.

## 5. Shipping
- **Live site:** Render web service `truefit` (free plan, no database), connected to this GitHub repo. https://es4077-truefit.onrender.com
- **How a change ships:** branch → pull request → `uv run pytest` passes → the student approves the merge → Render deploys `main` on its own (Auto-Deploy on commit, live in about 2 minutes; turned on Nov 18 after the class organization approved Render's GitHub access). **Manual Deploy → Deploy latest commit** in Render still works if a deploy needs a retry.
- **After a deploy:** open the live URL, run a sample posting through "Check eligibility," and confirm the event in PostHog.
- **Secrets:** `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `POSTHOG_PROJECT_TOKEN`, `POSTHOG_HOST`, `PYTHON_VERSION`, `ENVIRONMENT=production` live in Render's environment settings, never in the repo. `render.yaml` lists them without values.
- **Rollback:** in Render, open **Events**, pick the last good deploy, and choose **Rollback**. Then fix forward on a branch.
- **Limits:** see `app/rate_limit.py` and `SECURITY.md`. The OpenRouter key has its own credit limit ($10).

## 6. Ask me first
- Merging anything to `main` (it publishes the Product Page and is what gets deployed).
- Anything that spends OpenRouter credit: the model evals, live tests that tailor a resume.
- Changing Render settings, environment variables, or the rate limits.
- Changing what's logged, what's sent to PostHog, or what's stored anywhere (TrueFit stores nothing on the server).
- Changing a model prompt or the truthfulness rules.
- Adding a dependency, a database, or sign-in.
- Deleting files, branches, or anything that can't be undone.
