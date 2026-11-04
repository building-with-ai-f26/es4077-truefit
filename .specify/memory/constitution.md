# TrueFit Constitution

## Core Principles

### I. Truth Over Polish (NON-NEGOTIABLE)

Every claim in a generated resume MUST trace to at least one line of the user's master resume.
The product MUST NOT add employers, titles, dates, degrees, skills, tools, certifications, or
metrics that the master resume does not contain. Numbers, percentages, dollar amounts, and dates
MUST appear exactly as written in the source. Rewording, reordering, selecting, and shortening are
allowed; adding facts is not. Content that cannot be traced MUST be flagged and kept out of the
copy-ready output by default.

**Rationale**: "100% true" is TrueFit's core promise and the main reason to use it instead of
general-purpose AI tools. One invented claim costs the user the trust the product exists to earn.

### II. Show the Source

Any fact TrueFit extracts or asserts (a start date, a requirement, a bullet's backing) MUST be
shown with the exact source text it came from. When the source does not state something, the
product MUST say "Not stated" (or the equivalent) instead of guessing or inferring a specific value.
Verdicts MUST use the fixed, documented categories in the active spec.

**Rationale**: Users can only trust output they can check in seconds. Quoting the source makes
mistakes visible instead of silent.

### III. ATS-Safe Plain Output

Resume output MUST be plain, single-column text with standard section headings and only standard
bullet and punctuation characters: no tables, columns, graphics, icons, or decorative formatting.
The user MUST be able to copy the full copy-ready resume in one action. Any output-format change
MUST be checked by pasting into a plain-text field (and Workday or iCIMS when available).

**Rationale**: Applicant tracking system parsers scramble formatted resumes, and fixing them field
by field is part of the pain TrueFit removes.

### IV. One Core Workflow

The product does one job: one posting plus one master resume in, then a start-date check, a
truthful tailored resume, and a gap list out. Work outside that workflow MUST NOT be built unless the
living PRD in `docs/index.html` is updated first. This includes the PRD's explicit non-goals:
scraping or auto-applying, application tracking, cover letters, LinkedIn rewrites, interview prep,
and designed templates or PDF styling.

**Rationale**: The course has six weeks. A narrow workflow that works for real classmates beats
a broad one that half-works.

### V. Simple, Explainable, Small Batches

Choose the simplest design that meets the spec. Every dependency, abstraction, or extra component
MUST be justified in the plan's Complexity Tracking table. Changes MUST be small enough for the
human builder to review and explain in one pull request: what changed, why, what could break, and
how it was checked.

**Rationale**: The builder must understand and defend the system at Demo Day and in the sponsor
memo. Unexplained complexity is a liability.

## Security, Privacy & Cost

- API keys, tokens, and credentials MUST live only in environment variables (`.env`), never in
  source, browser code, screenshots, or commits. `.env.example` MUST list every required variable
  with placeholder values only.
- Resume and posting text MUST NOT be stored after a session ends unless the user explicitly
  chooses to save it, and MUST NOT be sent to any service other than the model provider needed
  for the workflow.
- Analytics events MUST NOT include resume or posting content.
- Spending limits or alerts MUST be set on any paid provider that supports them. The estimated cost
  per user run MUST be recorded in the PRD and updated when models or prompts change materially.
- External data access and API permissions MUST be least-privilege.

## Development Workflow & Quality Gates

- **Plan before coding**: Changes touching more than one file start with a short plan that the
  human approves before implementation.
- **Verify every change**: Run the relevant checks before calling a change done. For a reproducible
  logic bug, add a failing test first when practical. Record manual checks and known limits.
- **Truthfulness gate**: Any change to resume generation MUST be re-checked against a fixed set
  of posting/resume cases. Zero untraceable claims and zero altered numbers are required to pass.
- **Start-date gate**: Any change to start-date extraction MUST be re-checked against a fixed set of
  postings with known answers, including vague, missing, and multi-date cases.
- **Stop when looping**: If a fix fails twice in a row, stop, summarize what failed, and ask the
  human before trying a third approach.
- **Living record**: PRD changes, costs, and hours MUST be logged on `docs/index.html` each build.

## Governance

This constitution overrides other project practices where they conflict. `AGENTS.md` holds
day-to-day operating instructions for coding agents and MUST stay consistent with it.

- **Amendments**: Propose the change, state its reason, update this file with `/speckit-constitution`,
  and bring any affected specs, plans, and templates in line in the same change.
- **Versioning**: Semantic versioning. MAJOR for removing or redefining a principle, MINOR for
  adding a principle or section or materially expanding guidance, PATCH for clarifications and wording.
- **Compliance**: Every `/speckit-plan` MUST pass the Constitution Check before research and again
  after design. Violations MUST be justified in Complexity Tracking or the design MUST change.
  Principle I can never be waived.

**Version**: 1.0.0 | **Ratified**: 2026-11-04 | **Last Amended**: 2026-11-04
