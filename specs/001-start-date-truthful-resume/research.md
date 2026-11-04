# Research: Start-Date Check & Truthful Tailored Resume

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-04

Each entry lists Decision, Rationale, and Alternatives considered.

## R1. Stack

- **Decision**: Python 3.12 + FastAPI + Uvicorn, managed with `uv`. One plain HTML/JS page served
  by the same app.
- **Rationale**: The builder chose it. It has the fewest moving parts, keeps the API key on the
  server, and needs no build step. `uv` installs Python 3.12 without touching the system 3.9.
- **Alternatives considered**: Next.js (more framework to learn and review); Streamlit (saving the
  resume on the device and editing bullets one at a time are both awkward in it).

## R2. Model access

- **Decision**: Call OpenRouter's chat-completions endpoint with httpx and ask for JSON output.
  The model is set by `OPENROUTER_MODEL` in `.env`. Default to a current Claude Sonnet-class model;
  check the exact model slug at openrouter.ai/models when setting up. Use temperature 0. Set a 60 s
  timeout and one automatic retry, then show a plain-language error.
- **Rationale**: The course uses OpenRouter, and `.env.example` already has the key. A
  configurable model lets the eval set compare cost and quality without code changes. Low
  temperature makes eval runs repeatable.
- **Alternatives considered**: An SDK per provider (ties the app to one vendor); a client library
  for OpenRouter (an extra dependency for one HTTP call).

## R3. Model extracts, Python decides

- **Decision**: The model is used only to (a) find and quote start-date text and turn it into a
  structured date shape, (b) list requirements with quotes, (c) draft tailored bullets with
  citations, and (d) judge whether cited lines support a bullet. All verdicts and all accept/flag
  decisions are made by Python functions.
- **Rationale**: Constitution Principles I and II. Deterministic rules can be unit-tested
  exhaustively (every availability × start-date combination). Model mistakes surface as flags,
  not as false claims.
- **Alternatives considered**: Letting the model output the verdict directly (untestable, and it
  can make up dates).

## R4. Start-date shape and verdict rules

- **Decision**: The model returns one or more `StartDateMention`s. Each has `quote`, `kind`
  (`exact_date`, `month`, `range`, `season`, `immediate`, `flexible`), plus `start`/`end` dates
  where applicable. It returns an empty list if none are found. Python then:
  1. Drops any mention whose `quote` isn't an exact substring of the posting (after collapsing
     whitespace). If none remain → **Not stated**.
  2. Turns each mention into a date interval:
     - month = whole month
     - season: Spring = Mar–May, Summer = Jun–Aug, Fall = Sep–Nov
     - immediate = today
  3. Compares that interval to the student's availability using the rules in
     [data-model.md](./data-model.md#verdict-rules).
- **Rationale**: This covers every acceptance scenario and edge case in the spec with code that
  doesn't depend on the model. Multiple mentions handle multi-role postings.
- **"Today"**: The server's date in America/New_York, so "ASAP" and "date has passed" are consistent.

## R5. Master resume lines

- **Decision**: The server splits the master resume into non-empty lines and numbers them `L1…Ln`
  before calling the model. The model must cite line IDs; it never sees or returns free-form
  "sources".
- **Rationale**: Gives FR-010 a concrete, checkable link, and lets the UI show the exact source
  line next to each bullet.
- **Alternatives considered**: Asking the model to quote source text (harder to verify; quotes
  drift).

## R6. Trace check (Principle I)

- **Decision**: A bullet is **Traced** only if all of the following pass:
  1. Every cited line ID exists.
  2. Every number token in the bullet appears exactly in the cited lines. This covers integers,
     decimals, percents, dollar amounts, multipliers like "3x", years, and month-year dates.
  3. No *posting-only term* appears in the bullet. A posting-only term is a word or phrase that
     appears in the posting but nowhere in the master resume, after lowercasing and removing
     stopwords and generic job words.
  4. A model support check answers "supported" for the bullet against its cited lines. It returns
     the specific claim it couldn't support, which becomes the flag note.

  Otherwise the bullet is **Flagged** with a reason. Flagged bullets are excluded from the
  copy-ready resume by default.
- **Rationale**: Checks 2 and 3 catch the two failures the PRD names, invented metrics and
  invented skills, without relying on the model. Check 4 catches meaning-level additions such as
  "led a team" when no team is mentioned.
- **Known risk**: Check 3 can flag a fair rewording that happens to reuse a posting word. That
  fails safe (flag, not allow), and the student can put the bullet back. It's tracked in the eval
  set as the "false flag rate".
- **Alternatives considered**: A model check only (not acceptable for a non-negotiable rule);
  exact sentence reuse only (blocks the rewording the spec allows).

## R7. Gap list

- **Decision**: One model call returns the posting's requirements. Each has `quote`, `text`,
  `group` (`required` / `preferred` / `unlabeled`), `supported` (bool), and the supporting line IDs.
  Python then:
  - drops requirements whose quote isn't in the posting
  - maps `unlabeled` to Required
  - keeps only unsupported requirements as Gaps
  - treats any "supported" claim with no valid line IDs as unsupported
- **Rationale**: FR-016 and FR-016a, with the same quote-check discipline as R4.

## R8. Calls per run and cost

- **Decision**: `/api/start-date` = 1 model call. `/api/tailor` = 2 calls in parallel (tailor
  bullets, extract requirements) plus 1 batched support-check call for all bullets.
  `/api/verify-bullet` = 1 small call.
- **Cost estimate**: About 4 calls per full run, roughly 15–25k input and 3–5k output tokens in
  total. At Sonnet-class prices that's about $0.05–$0.15 per run; a smaller model would be under
  $0.02. Record the measured number in the PRD's "Est. Cost Per User Run" after Build 2.
- **Rationale**: Meets SC-001 (2 min) with room to spare. Batching the support check keeps it to
  one call regardless of how many bullets there are.

## R9. Browser storage

- **Decision**: `localStorage` key `truefit.v1` holds `{ masterResume, availabilityText, savedAt }`.
  A "Clear saved resume" button removes the key (FR-021). Postings are never stored.
- **Rationale**: Clarification Q1. No accounts or server storage, and it survives page reloads on
  the same device.
- **Alternatives considered**: `sessionStorage` (lost on tab close); IndexedDB (unnecessary for
  one small record).

## R10. Plain-text output

- **Decision**: The server renders the copy-ready text as:
  - section headings in Title Case on their own line, with a blank line before
  - role lines as `Title, Company | City | Mon YYYY – Mon YYYY` copied from the master resume
  - bullets as `- `

  Characters are normalized: curly quotes become straight, en/em dashes inside text become `-`
  except in date ranges, bullet symbols become `-`, and tabs and non-printing characters are
  removed. The UI copies this exact string with the Clipboard API.
- **Rationale**: FR-014 and FR-015 with a single tested function. A hyphen bullet is the safest
  across ATS parsers.

## R11. Logging, analytics, and limits

- **Decision**:
  - Logs record route, status, duration, and the model used, never request bodies.
  - PostHog (Build 2) events are `start_date_checked` (verdict only), `resume_tailored` (bullet
    and flag counts), `bullet_edited`, `resume_copied`, and `resume_cleared`, with no content
    properties.
  - Inputs over 20,000 characters or under 200 characters (resume) / 100 characters (posting) are
    rejected with a plain message.
- **Rationale**: The constitution's Security, Privacy & Cost section, and FR-018.

## R12. Testing strategy

- **Decision**:
  - `tests/unit` covers availability parsing, verdict rules (a table of availability × mention
    kinds), the quote check, the trace check, and the plain-text renderer.
  - `tests/api` covers each route with `llm.call` replaced by canned JSON, including bad model
    output.
  - `tests/eval` runs real model calls on 10 anonymized posting/resume cases (5 normal, 3 messy,
    2 adversarial) and reports SC-002, SC-003, SC-005, and the false flag rate.
- **Rationale**: Deterministic tests run in seconds on every change. The eval set is the quality
  gate the constitution requires for prompt or model changes, and doubles as Build 4 Track A.
