# Job Posting From a Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A student can put a job posting's link in the Job posting box; TrueFit reads it from Greenhouse, Lever, Ashby, Workday, or a page's JobPosting data, shows the text locked with Edit text / Remove, and gives a specific next step when it can't.

**Architecture:** New `app/posting_link.py` turns a link into posting text: pure helpers (link checks, site detection, HTML-to-text), then one fetch per site kind through an httpx client whose transport tests replace. New `POST /api/posting-link` returns the text; `app.js` calls it when the posting box holds only a link and reuses the locked-text pattern from Word upload. Nothing new is installed (httpx and the standard library's `html.parser` are enough).

**Tech Stack:** Python 3.12, FastAPI, httpx, stdlib `html.parser` / `ipaddress` / `socket`, plain JS, pytest, Playwright (browser check).

**Spec:** `specs/2026-11-18-posting-link-design.md`

## Global Constraints

- Sites read through public data: Greenhouse (`boards.greenhouse.io`, `job-boards.greenhouse.io`), Lever (`jobs.lever.co`), Ashby (`jobs.ashbyhq.com`), Workday (`*.myworkdayjobs.com`); any other link: the page's JobPosting data only.
- Answered without fetching: linkedin.com, indeed.com, glassdoor.com, joinhandshake.com, 12twenty.com (and their subdomains).
- Only http/https; never local or private network addresses (checked on every redirect hop); 10-second timeout; responses over 2 MB refused.
- Text: title; company and location on one line; description with paragraphs as lines and list items as "- "; start date or employment type only when the site gives it as its own field. Nothing invented or summarized.
- The link and the text are never stored or logged. PostHog gets the site kind, line count, or reason code only.
- Tests never use the network. `uv run pytest` must pass; never run the model evals.

### Messages (exact copy, by reason code)

| code | message |
|---|---|
| `blocked_site` | TrueFit can't open LinkedIn, Indeed, or school job boards like 12twenty. Open the posting, click Apply, and paste that link, or paste the posting text. |
| `bad_link` | TrueFit can only open web links (https://…). Paste the posting text. |
| `needs_login` | This page needs a login, so TrueFit can't read it. Paste the posting text. |
| `not_found` | This posting wasn't found. It may have closed. Check the link, or paste the posting text. |
| `no_job_data` | TrueFit couldn't find the job details on this page. Paste the posting text. |
| `several_jobs` | This page lists more than one job. Open the one you want, or paste the posting text. |
| `too_large` | This page is too large to read. Paste the posting text. |
| `one_link` (browser only) | Paste one link at a time. |
| `site_unreachable` | The job site didn't respond. Try again, or paste the posting text. |

## Review Focus

1. A Greenhouse job shown on the company's own site (`…/careers?gh_jid=123`) with no JobPosting data: `no_job_data` message, not a crash or a page of menus. → Task 2 `test_company_page_without_job_data`
2. A link that redirects to a login or to a private address: never read the login page's text, never fetch the private address. → Task 2 `test_redirect_to_private_address_refused`, `test_redirect_to_login_page_has_no_job_data`
3. A page whose JobPosting data lists several jobs: `several_jobs`, never one picked at random (wrong-job text is the spec's first anti-goal). → Task 2 `test_several_jobs_on_a_page`
4. A link with tracking parameters or surrounding spaces is still read; a box with a link plus other words is treated as text. → Task 1 `test_site_detection_ignores_query_and_spaces`, Task 3 browser check step 3
5. Greenhouse's description arrives HTML-escaped (`&lt;p&gt;`): the text must read cleanly with no tags or entities. → Task 2 `test_greenhouse_posting`

---

### Task 1: Link checks, site detection, HTML to text

**Files:**
- Create: `app/posting_link.py`
- Test: `tests/unit/test_posting_link.py`

**Interfaces:**
- Produces:
  - `class LinkProblem(Exception)` with `.code: str`, `.message: str` (message from the table, looked up by code: `LinkProblem("needs_login")`).
  - `site_kind(url: str) -> tuple[str, dict]`: `("greenhouse", {"board", "job_id"})`, `("lever", {"company", "posting_id"})`, `("ashby", {"org", "job_id"})`, `("workday", {"host", "tenant", "site", "path"})`, or `("page", {})`. Raises `LinkProblem("blocked_site")` for the blocked list and `LinkProblem("bad_link")` for non-http(s).
  - `html_to_text(html: str) -> str`.
  - `posting_text(title: str, company: str | None, location: str | None, description_html: str, extras: list[str]) -> str`: title line; `"Company · Location"` line (whichever exist); `extras` lines (e.g. `"Start date: June 2027"`, `"Employment type: Full-time"`); blank line; `html_to_text(description_html)`.
  - `is_public_address(host: str) -> bool` (resolves with `socket.getaddrinfo`; false for loopback, private, link-local, reserved, or unresolvable).

- [ ] **Step 1: Write the failing tests**

```python
def test_greenhouse_links(): site_kind("https://boards.greenhouse.io/acme/jobs/4012345") == ("greenhouse", {"board": "acme", "job_id": "4012345"})
    # also job-boards.greenhouse.io/acme/jobs/4012345
def test_lever_link(): ("lever", {"company": "acme", "posting_id": "5b1c…"}) from jobs.lever.co/acme/5b1c…(/apply)
def test_ashby_link(): ("ashby", {"org": "acme", "job_id": "uuid"}) from jobs.ashbyhq.com/acme/uuid(/application)
def test_workday_link():  # https://acme.wd5.myworkdayjobs.com/en-US/External/job/New-York/Analyst_R123
    # → ("workday", {"host": "acme.wd5.myworkdayjobs.com", "tenant": "acme", "site": "External", "path": "job/New-York/Analyst_R123"}); also without the locale segment
def test_other_link_is_a_page(): site_kind("https://careers.example.com/jobs/123")[0] == "page"
def test_site_detection_ignores_query_and_spaces(): site_kind("  https://jobs.lever.co/acme/abc?utm_source=linkedin  ")[0] == "lever"
@pytest.mark.parametrize("url", ["https://www.linkedin.com/jobs/view/1", "https://www.indeed.com/viewjob?jk=1",
    "https://nyu.12twenty.com/jobPostings/1", "https://app.joinhandshake.com/jobs/1", "https://www.glassdoor.com/job-listing/x"])
def test_blocked_sites(url): LinkProblem with code "blocked_site" and the exact message
def test_not_a_web_link(): "ftp://x/y" and "file:///etc/passwd" → "bad_link"
def test_html_to_text():
    html_to_text("<p>About us</p><ul><li>SQL</li><li>Python &amp; R</li></ul><p>Start: June&nbsp;2027<br>NYC</p>")
    == "About us\n- SQL\n- Python & R\nStart: June 2027\nNYC"
def test_posting_text_layout(): title, "Acme · New York, NY", "Employment type: Full-time", "", body
def test_private_addresses(): is_public_address("127.0.0.1"), ("10.0.0.5"), ("169.254.169.254"), ("localhost") all False
```

- [ ] **Step 2:** `uv run pytest tests/unit/test_posting_link.py -q`. Expected: FAIL (module not found).
- [ ] **Step 3: Implement** with `urllib.parse`, `html.parser.HTMLParser` (block tags `p div br h1-h6 tr section` end a line; `li` starts "- "; collapse runs of blank lines to one; `html.unescape`; non-breaking spaces to spaces), `ipaddress` + `socket.getaddrinfo`.
- [ ] **Step 4:** Same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: posting link basics (site detection, blocked sites, HTML to text)`.

### Task 2: Read a posting from each kind of site, and the route

**Files:**
- Modify: `app/posting_link.py`, `app/main.py` (route after `/api/read-docx`)
- Test: `tests/unit/test_posting_link.py`, `tests/api/test_posting_link_route.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `_transport: httpx.AsyncBaseTransport | None = None` (tests swap in `httpx.MockTransport`, as in `app/llm.py`); `_public = is_public_address` (tests swap in `lambda host: host != "internal.example"`).
  - `async def read_posting_link(url: str) -> dict` → `{"text": str, "lines": int, "site": "greenhouse"|"lever"|"ashby"|"workday"|"job data", "host": str}`; raises `LinkProblem`.
  - `POST /api/posting-link`, body `{"url": str}` → 200 that dict; `LinkProblem` → 422 `{"error": {"code", "message"}}`.

Data sources (field names fixed by the sites):
- Greenhouse: `GET https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}` → `title`, `company_name`, `location.name`, `content` (HTML-escaped HTML: unescape once, then `html_to_text`).
- Lever: `GET https://api.lever.co/v0/postings/{company}/{posting_id}` → `text` (title), `categories.location`, `categories.commitment` (employment type), `description` + each `lists[]` as `<h3>{text}</h3><ul>{content}</ul>` + `additional`.
- Ashby: `GET https://api.ashbyhq.com/posting-api/job-board/{org}` → the `jobs[]` item whose `id` matches → `title`, `location`, `employmentType`, `descriptionHtml`; no match → `not_found`.
- Workday: `GET https://{host}/wday/cxs/{tenant}/{site}/{path}` → `jobPostingInfo.title`, `.location`, `.timeType` (employment type), `.jobDescription`. Its `startDate` is the date posted, **not** the job's start: never use it.
- Page: `GET` the link; every `<script type="application/ld+json">`, parsed (a list, an object, or one with `@graph`); keep objects whose `@type` is or includes `"JobPosting"`. 0 → `no_job_data`; more than one distinct `title`+`url` → `several_jobs`. Use `title`, `hiringOrganization.name`, the first `jobLocation.address` (`addressLocality`, `addressRegion`), `employmentType`, `jobStartDate`, `description`.
- Every request: `follow_redirects=False`, up to 5 hops by hand, each hop's host checked with `_public` (fail → `bad_link`); status 401/403 → `needs_login`, 404/410 → `not_found`, other non-2xx, timeouts and connection errors → `site_unreachable`; `Content-Length` or body over 2 MB → `too_large`. 10-second timeout.

- [ ] **Step 1: Write the failing tests** (fixtures are small inline dicts/strings in the test file); no pytest-asyncio here, so the async tests below are plain functions calling `asyncio.run(read_posting_link(url))`, as `tests/unit/test_llm.py` does).

```python
async def test_greenhouse_posting(): content "&lt;p&gt;Build models&lt;/p&gt;&lt;ul&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;"
    # → text == "Analyst\nAcme · New York, NY\n\nBuild models\n- SQL", site "greenhouse"; no "&lt;" or "<p>" in text
async def test_lever_posting(): lists [{"text": "Requirements", "content": "<li>MBA</li>"}], commitment "Full-time"
    # → "Employment type: Full-time" line; "Requirements" then "- MBA"
async def test_ashby_posting(): job found by id; and test_ashby_job_missing → not_found
async def test_workday_posting(): startDate "2026-11-01" is NOT in the text; timeType "Full time" is
async def test_page_with_job_data(): one JobPosting inside @graph with jobStartDate "2027-06-01" → "Start date: 2027-06-01" line
async def test_company_page_without_job_data(): HTML with nav and text, no ld+json → no_job_data
async def test_several_jobs_on_a_page(): two JobPostings with different titles → several_jobs
async def test_redirect_to_private_address_refused(): 302 Location https://internal.example/x → bad_link, and the transport never saw internal.example
async def test_redirect_to_login_page_has_no_job_data(): 302 to https://login.example.com → 200 sign-in HTML → no_job_data
@pytest.mark.parametrize("status,code", [(401, "needs_login"), (403, "needs_login"), (404, "not_found"), (500, "site_unreachable")])
async def test_http_errors(status, code)
async def test_timeout(): transport raises httpx.ReadTimeout → site_unreachable
async def test_too_large(): Content-Length 3_000_000 → too_large
# tests/api/test_posting_link_route.py
def test_route_returns_text(client, monkeypatch): 200 {"text", "lines", "site", "host"}
def test_route_blocked_site(client): linkedin link → 422, code "blocked_site", no network call
def test_link_and_text_not_logged(client, monkeypatch, caplog): "SECRETPOSTING" in content and "secret-slug" in URL not in caplog.text
```

- [ ] **Step 2:** `uv run pytest tests/unit/test_posting_link.py tests/api/test_posting_link_route.py -q`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement** `read_posting_link` and `post_posting_link(body: PostingLinkRequest)` (`class PostingLinkRequest(BaseModel): url: str`; reject `url` over 2,000 characters as `bad_link`).
- [ ] **Step 4:** Same command, then `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: read a job posting from Greenhouse, Lever, Ashby, Workday, or a page's job data`.

### Task 3: One box for text or a link

**Files:**
- Modify: `app/static/index.html` (posting field), `app/static/app.js` (step 1), `app/static/styles.css` only if needed (reuse `.file-row`, `.file-name`, `.file-error`, `textarea.locked`).

**Interfaces:**
- Consumes: `POST /api/posting-link` (Task 2), the existing `api()` helper is **not** used for this call (its errors go to the top error box); use `fetch` and show errors under the box, as Word upload does.

Behavior:
- Placeholder: "Paste the job posting text, or a link to it".
- When the box's trimmed value matches `^https?://\S+$` (only a link), read it on `paste` and on `change`; while reading, the status row says "Reading the posting…" and the box is read-only. Success: the box holds the text, locked; status "✓ Read from {host} · {lines} lines" (1 → "line"), **Edit text** (unlocks, status becomes "From {host}"), **Remove** (clears the box and status). Failure: the box keeps the link, editable; `#posting-link-error` under the box shows the message.
- **One link at a time:** when the box holds only links (whitespace-separated, each matching `^https?://\S+$`) and there are two or more, no request is made and `#posting-link-error` says "Paste one link at a time." (`posting_link_failed` `{ error_code: "one_link" }`).
- "Try a sample posting" clears any link status/error and unlocks the box.
- PostHog: `posting_link_read` `{ site, lines }`; `posting_link_failed` `{ error_code }`.

- [ ] **Step 1: Implement the markup and JS above** (ids: `posting-link-status`, `posting-link-edit`, `posting-link-remove`, `posting-link-error`).
- [ ] **Step 2:** `node --check app/static/app.js` and `uv run pytest -q`. Expected: OK, all pass.
- [ ] **Step 3: Browser check (Playwright; `/api/posting-link` intercepted with fixed replies, PostHog blocked), desktop and phone:** paste a Greenhouse link → locked text and "✓ Read from boards.greenhouse.io · N lines"; Edit text unlocks; Remove empties. Paste a LinkedIn link → the blocked message under the box, top error box hidden, link still in the box. Paste "Apply here: https://x.com/1 for this role" → no request made (treated as text). Paste two links ("https://a.com/1 https://b.com/2", and on two lines) → "Paste one link at a time." and no request made. Sample posting after a link → unlocked, no status. Check eligibility after reading a link sends the read text as `posting`. No sideways scroll.
- [ ] **Step 4: Commit** `feat: paste a posting link in the Job posting box`.

### Task 4: Real links, docs, pull request

**Files:**
- Modify: `docs/index.html`, `PRODUCT.md`, `AGENTS.md`, `specs/2026-11-18-posting-link-design.md` (Status → "approved Nov 18, built")

- [ ] **Step 1: Manual check with real links (network, free):** one live posting each from Greenhouse, Lever, Ashby, Workday, and one company page with JobPosting data, through `read_posting_link`; record which worked in the PR. A site whose live format differs from Task 2's fields is a bug: add a failing test from the live shape, then fix.
- [ ] **Step 2: Product Page.** Decision row after the Nov 18 Word upload row: *Should students be able to paste a link to a posting instead of its text?* / *Yes, changed from Build 2. Pasting long postings is error-prone, and tech companies mostly post on sites with public job data (Greenhouse, Lever, Ashby, Workday) or pages that label the job for Google. LinkedIn, Indeed, and school boards like 12twenty still can't be read, but their Apply button usually leads to a page that can, so TrueFit says to paste that link instead. TrueFit uses only the job's own labeled content, never the rest of the page.* / Nov 18, 2026. Out-of-scope line: drop "fetching postings from a URL", add "reading LinkedIn, Indeed, or pages behind a login". Out of Scope #1: "Users paste postings (or a link to them) in themselves." How it works: posting text or link.
- [ ] **Step 3:** `PRODUCT.md` inputs and `AGENTS.md` (structure: `app/posting_link.py`; route list) match.
- [ ] **Step 4:** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `docs: posting links on the Product Page, PRODUCT.md, AGENTS.md`, then final review, push `posting-link`, open the PR, and **ask before merging**.
