# Job posting from a link (design)

Nov 18, 2026 · Status: draft for approval

## Why
Pasting a long job posting is error-prone in the same ways as pasting a resume: part of it gets missed and text gets mangled. Many postings can be read from a link. This revisits the Build 2 decision to stay paste-only ("many job sites block automated reading or need a login"): that is still true for LinkedIn, Indeed, and school job boards like NYU's 12twenty, but their **Apply** button usually leads to the company's own job site, which often can be read, and tech companies mostly post on sites with public, login-free data.

## Goals
- A student can put a posting's link in the Job posting box instead of its text; TrueFit reads the posting and shows the text before checking it.
- Links that can't be read get a clear, specific next step instead of an error.

## Non-goals
- LinkedIn, Indeed, Glassdoor, Handshake, 12twenty, or any page behind a login.
- Guessing which part of an arbitrary web page is the job (no general page scraping).
- Fetching resumes or anything other than the posting.

## Anti-goals (a failure even if it "works")
- Text from another job, a "similar jobs" list, or page menus ending up in the eligibility check or gap list.
- Storing or logging the link or the posting text.

## Approaches
- A. Only Greenhouse, Lever, Ashby, and Workday, through their public data. Cleanest, but company career pages on other systems fail even though nothing blocks them.
- B. Any link: download the page and pull out its main text. Widest, but picks up menus, banners, and other jobs, and many job pages fill in their text with JavaScript after loading.
- **C. (chosen by the student)** The four sites above through their public data, plus any page that carries Google's standard "JobPosting" data (the label career sites add so jobs appear in Google search: SmartRecruiters, iCIMS, many company pages). TrueFit uses only that labeled job content. Anything else: paste.

## What the student sees (decided: one box)
```
Job posting                         Try a sample posting
┌──────────────────────────────────────────────┐
│ Paste the job posting text, or a link to it  │
└──────────────────────────────────────────────┘
```
- When the box holds only a link, TrueFit reads it right away. The posting text replaces the link, **locked** like a resume read from Word, with "✓ Read from boards.greenhouse.io · 42 lines", **Edit text**, and **Remove**.
- When the link can't be read, the box keeps the link and a note appears under it, e.g. for LinkedIn: "TrueFit can't open LinkedIn, Indeed, or school job boards like 12twenty. Open the posting, click Apply, and paste that link, or paste the posting text." Other failures say what happened (page needs a login, no job data on the page, site didn't respond) and end with "paste the posting text."
- Pasting text works exactly as today.

## Decisions
- Approach C; one box; locked text with Edit text / Remove; the LinkedIn/Indeed/12twenty note with the Apply-button tip.

## Builder's calls (proposed; the student can correct)
- **Sites read through their public data:** Greenhouse (`boards.greenhouse.io`, `job-boards.greenhouse.io`), Lever (`jobs.lever.co`), Ashby (`jobs.ashbyhq.com`), Workday (`*.myworkdayjobs.com`). Any other link: the page's JobPosting data, if present.
- **Known blocked sites, answered without fetching:** linkedin.com, indeed.com, glassdoor.com, joinhandshake.com, 12twenty.com.
- **Text TrueFit builds:** job title, then company and location on one line, then the description with paragraphs as lines and list items as "- " bullets; a start date or employment type from the job data is added only when the site provides it as its own field. Nothing is invented or summarized.
- **Safety and limits:** only http/https links; never local or private network addresses; 10-second timeout; pages over 2 MB refused. The link and text are never stored or logged.
- **PostHog:** `posting_link_read` with the kind of site (greenhouse, lever, ashby, workday, job data) and line count; `posting_link_failed` with the reason code. Never the link or text.
- **Tests:** saved sample responses for each site kind and for failures, so tests never use the network. One manual check with real links before the PR.
- **Docs:** decision row (Nov 18) noting the change from Build 2; the out-of-scope line ("fetching postings from a URL") and Out of Scope #1 ("Users paste postings in themselves") updated; How it works; `PRODUCT.md`; `AGENTS.md`.
