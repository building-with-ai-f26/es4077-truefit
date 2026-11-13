# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Second-year NYU Stern MBA students graduating in May 2027 who are recruiting for full-time roles that start in June 2027 or later. They are mid-recruiting, working through many postings, and short on time. Their job: decide quickly whether a role's start date works for them, then send a resume tailored to that posting that gets through applicant tracking systems (Workday, iCIMS) without a single claim they can't back up.

Testers are the builder's classmates in their section, pod, and recruiting clubs, all of whom she can reach directly.

Secondary audience: the course teaching team and the end-of-course sponsor. They read the public Product Page (`docs/index.html`) to evaluate the product, the living PRD, the build log, and the costs.

## Product Purpose

The user pastes one job posting and their master resume. TrueFit then:

1. Finds the start date, quotes the line it came from, and gives a verdict against when the student can start.
2. Writes a tailored, ATS-safe resume in which every bullet traces back to the student's own material.
3. Lists the gaps between the posting and the student's experience, grouped as Required and Preferred.

It replaces the current routine: reading every posting closely for a buried or vague start date, tailoring by hand or with ChatGPT, re-checking every line because the AI invents skills and metrics, then fixing scrambled fields in Workday or iCIMS.

Success means classmates use TrueFit instead of that mix, and say it is faster and that they no longer re-check every line. The PRD's targets are:

- under 30 seconds to a start-date verdict, and under 2 minutes to a copy-ready resume
- at least 9 of 10 start-date verdicts matching a human reviewer, and never a date the posting doesn't state
- 100% of copy-ready bullets traced, with zero altered numbers
- at least 9 of 10 clean pastes into Workday or iCIMS
- at least 3 testers who say it is faster

## Positioning

"100% true" is the claim a general-purpose AI tool can't truthfully make. Inside TrueFit, the model only finds, quotes, and drafts. Plain Python code decides verdicts and verifies claims. It confirms that every quote appears word for word in the posting, checks every bullet against the numbered resume lines it cites (numbers must match exactly, and skill words that appear only in the posting are rejected), and runs a second model support check. Anything that can't be traced is flagged and left out by default. Every fact is shown next to its source text, so the user can check it in seconds.

## Operating Context

- Students paste text: a posting copied from a job board, plus a master resume and optionally other writing about their own experience (notes, past cover letters, STAR stories, application essays). Only statements of what they did count; goals and plans never support a claim.
- Availability is an "available starting" month (default June 2027, and any later start fits), ASAP, or Flexible.
- The finished output is pasted into Workday or iCIMS application forms.
- The product is built for the NYU Stern course "Building with AI" (Fall 2026). Weekly builds are due at noon New York time, there is a 2-minute demo, and a sponsor memo is due Dec 14, 2026. The app runs locally through Week 4 and launches to the cloud with Build 5 on Dec 7, 2026.
- The public Product Page doubles as the living PRD and weekly build log, served by GitHub Pages from `main` → `/docs`.

## Capabilities and Constraints

**Start-date check**

- Verdicts use fixed categories: In window, Likely in window (vague dates), Outside window, Not stated.
- TrueFit never guesses a date. When a posting gives no date, it says "Not stated" and adds a hint that a missing date often means ASAP and that the student should ask the recruiter.
- A graduation window counts as quoted evidence, with a note saying the verdict is based on it.
- Postings aimed at undergraduates or bachelor's-only new-grad programs trigger a warning above the verdict.

**Tailored resume**

- Each bullet shows its source lines and a Traced or Unverified badge.
- Students can remove, restore, or edit bullets, and edits are re-checked.
- The resume is copied in one action.

**Output format**

- Output is plain, single-column text with standard headings and hyphen bullets only: no tables, columns, icons, or decorative formatting.

**Gap list**

- Gaps are grouped Required and Preferred, and unlabeled requirements count as Required. The gap list is planned for Build 3.

**Privacy**

- There are no accounts and nothing is stored on a server.
- The master resume is saved only on the student's device and can be cleared at any time.
- Analytics (PostHog) never include posting or resume text.

**Out of scope**

- Scraping job boards, auto-applying, or auto-filling forms
- Application tracking
- Cover letters, LinkedIn rewrites, and interview prep
- Designed templates or PDF styling
- PDF or Word upload, fetching postings from a URL, non-English postings, and accounts or syncing across devices

**Stack**

- Python 3.12, FastAPI and Uvicorn, a plain HTML/CSS/JS frontend in `app/static/`, OpenRouter (Claude Sonnet 5.5), uv, and pytest.
- The Product Page is a single static `docs/index.html`.

**Open product questions**

- Which model gives the best accuracy for the cost
- How often the fact check flags fair rewordings
- Whether access to a real Workday or iCIMS form is available for paste testing

## Brand Commitments

- **Name:** TrueFit.
- **Pitch line (binding):** "Paste a job posting. Know if you're eligible, starting with the start date, and get a resume for it that's ATS-ready and 100% true."
- **Voice:** plain language, with short literal sentences and no hype. Verdicts and errors are explained in one plain sentence each.
- **Course framing:** the Product Page must show the NYU Stern "Building with AI" (Fall 2026) context, the living PRD, and the weekly build log, including real progress, failures, costs, and hours.

## Evidence on Hand

- A start-date eval run against the real model: 22 of 22 correct, with no invented dates.
- A 13-case tailoring eval (6 normal, 3 messy, 4 adversarial): 0 kept bullets with an untraceable claim.
- 90 automated tests passing.
- Measured costs: about $0.013 per user run, $22.00 cumulative build spend as of Nov 6, 2026.
- Build 1 prototype screenshot at `docs/images/prototype-build1.png`, and a newer screenshot at `docs/Screenshot 2026-11-04 at 3.57.34 PM.png`.
- The detailed spec is in `specs/001-start-date-truthful-resume/`.

Not yet available: outside-user usage, testimonials, PostHog analytics, a live cloud URL, and a 2-minute video. Future work must not invent any of these. Placeholders on the Product Page stay as placeholders until there is real data.

## Product Principles

1. **Truth over polish.** No claim, date, or number appears that the user's own material or the posting doesn't contain. Untraced content stays out by default.
2. **Show the source.** Every extracted fact sits next to the exact text it came from, so it can be checked in seconds. When something isn't stated, the product says "Not stated."
3. **One core workflow.** Posting and resume go in; verdict, tailored resume, and gaps come out. Anything beyond that requires a PRD update first.
4. **Plain output that survives ATS parsers.** Copy-ready text pastes cleanly into Workday and iCIMS.
5. **Simple and explainable.** The builder must be able to defend every component at Demo Day and in the sponsor memo.

## Accessibility & Inclusion

The target is WCAG 2.2 AA for both the app and the Product Page. That covers contrast, full keyboard operation, visible focus, labelled form fields, and verdicts and badges that don't rely on color alone.
