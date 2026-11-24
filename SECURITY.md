# TrueFit security audit

Build 3 · Nov 18, 2026 · Lane: Beginner (live at a public URL on Render, free plan)

**Live site:** https://es4077-truefit.onrender.com

## What TrueFit holds, and where

| Data | Where it lives | Leaves the student's device? |
|---|---|---|
| Master resume and notes | The student's own browser (`localStorage`, only if they click "Save on this device") | Sent to the server for each check; never stored there |
| Job posting | Nowhere; typed or read from a link for one check | Sent to the server for each check; never stored |
| Word files | Read on the server, then discarded | The file is uploaded, its text returned; nothing kept |
| OpenRouter key | Render's environment settings (secret) | Never sent to the browser |
| PostHog project token | The page (it's designed to be public) | Yes, by design |

There is **no database and no sign-in**: the server stores nothing between requests. That removes the usual biggest risks (a leaked table, one student seeing another's data, a weak Row Level Security rule). The main risks left are **someone spending my OpenRouter credit** and **the server being used to reach places it shouldn't**.

## What I checked

| Area | What I checked | Result |
|---|---|---|
| Secrets in the repo | `.env` is in `.gitignore`; searched the whole Git history for OpenRouter and PostHog keys | `.env` never committed; no OpenRouter key anywhere. Only the PostHog project token appears, which is public by design |
| Secrets on the live site | Downloaded the live page and every script and stylesheet it loads (`index.html`, `app.js`, `posthog.js`, `styles.css`) and searched them for `sb_secret_`, `service_role`, `sk-or-`, `sk-ant-`, `sk-proj-`, and `sk_live_` (Nov 20) | None found. The only key in them is the PostHog project token (`phc_`), which is public by design |
| Secrets on the host | Keys entered in Render's dashboard, not in `render.yaml` or code | ✓ (`render.yaml` marks them `sync: false`) |
| Spending my credit | Every AI route, per visitor and site-wide | **Fixed:** rate limits (below), plus a hard $10 limit on the OpenRouter key. The limit is lifetime and never resets, which is stricter than a monthly cap: once the key has spent $10 in total, OpenRouter refuses its calls (checked Nov 20: $4.37 used so far). Auto top-up is off, so the account can't buy more credit on its own |
| Libraries | `pip-audit` on every production dependency (Nov 18) | No known vulnerabilities |
| Logs | Route logs, the model call, and the libraries that fetch web pages | **Fixed:** the web-page library wrote every link it fetched into the log; now off. Tests check that resume text, posting text, and links never appear in logs |
| Posting links (server fetching a page) | Private and local addresses, redirects, proxies, slow and huge pages | Every address checked before every hop (redirects too); local and private networks refused; proxy settings ignored; 10 s timeout; 2 MB limit |
| Word uploads | Size, damaged files, files that unpack huge ("zip bombs") | 20 MB upload limit (raised from 5 MB on Nov 24: a text-only resume with embedded fonts was refused); only the document's text parts are ever unpacked, and if those would pass 50 MB the file is refused unopened; embedded fonts, images and other non-text parts are never unpacked; damaged files get a plain message, not a crash |
| Oversized requests | Requests larger than any real one | **Fixed:** refused from their declared size (over 21 MB, just above the Word upload limit) before reading |
| What the page shows | Text from files, links, and the model put on the page | Shown as text, never as HTML, so a posting can't inject code (checked: the one HTML insert is a fixed icon) |
| Browser protections | Headers on every response | **Fixed:** added `nosniff`, `X-Frame-Options: DENY` (no framing), and a referrer policy |
| Public API listing | FastAPI's automatic `/docs` and `/openapi.json` | **Fixed:** turned off |
| Analytics privacy | What PostHog receives, including session replay | **Fixed:** replay hid what students type, but not what the page shows, so a replay would show a student's tailored resume and the posting's quotes. Now replays mask all text and clicks never send the clicked text (`app/static/posthog.js`); a browser check that unpacks the recording found shown text before the fix and none after, and a test keeps the setting. Events carry names, verdicts, counts, and error codes only; never posting, resume, file name, or link text. Checked on the live site with a phone test (Nov 18). |

## How the audit was done

My coding agent (Claude Code) did the review: I asked it to look for vulnerabilities and to try to break the app, first in the code and then on the live site. It reported each problem to me and fixed it on a branch with a test, and I approved each fix before it merged (pull requests #46, #47, and #54). What it tried on the live site:

- **30 quick calls to an AI route.** The first try let 25 of 30 through, because TrueFit read the visitor from a relay server's address. After the fix, calls 11–30 were refused with `429` (Nov 18, re-run Nov 19 for the submission screenshot).
- **Opening the automatic API listing** (`/docs`): returns 404.
- **Checking the browser protection headers** on live responses: `nosniff` and `X-Frame-Options: DENY` are there.
- **A phone session with session replay on:** the recording showed the page's text, including the tailored resume. Replays now mask all text.
- **Searching the live page and its scripts for secret keys** (Nov 20): none found.

The other rows in the table above came from its review of the code, and each fix there has a test.

## The rate limits

Checked before any route runs (`app/rate_limit.py`):

- **AI routes** (eligibility check, tailoring, bullet re-check): **10 a minute** and **50 a day** per visitor; **200 a day for the whole site**. At about $0.02 per tailoring, a bad day costs about $4.
- **Other routes** (posting links, Word upload, downloads): **30 a minute** per visitor.
- Refused calls get a plain message ("Too many requests. Try again in a minute.").

### Proof: 30 calls, calls 11–30 refused

- Automated: `tests/api/test_rate_limit.py::test_thirty_quick_calls_are_refused_after_ten`.
- Live (Nov 18, after the fix below): 30 calls in a row to `/api/start-date` with a too-short posting (no AI used): **calls 1–10 allowed, 11–30 refused** with `429` and "Too many requests. Try again in a minute." Also live: `/docs` returns 404; `nosniff` and `X-Frame-Options: DENY` on responses.

## Left, and why

- **Rejected requests still count.** A request that's refused for being too short still counts toward the visitor's and the site's AI limits, so someone could use up the 200-a-day cap with junk requests: the site would stop checking for the day, but no credit is spent.
- **Limits are kept in memory.** They reset when the server restarts (Render's free plan sleeps after 15 minutes idle). Someone could wait for a restart to get a fresh 50; the 200-a-day site cap and the OpenRouter credit limit still bound the cost.
- **The visitor is identified by network address**: the `CF-Connecting-IP` header that Cloudflare (in front of Render) sets and visitors can't fake. People behind one network (a school's Wi-Fi) share a limit. *Found live, Nov 18:* the first version used the last `X-Forwarded-For` entry, which on Render is one of several relay servers, so the first live 30-call test let 25 through; fixed with a test, and the live 30-call test now refuses calls 11–30.
- **A domain that changes its address between the check and the fetch** (DNS rebinding) could still reach a private address. The fetch is a blind read of job data from the server's own network, and Render's network has nothing private of mine on it; fixing this fully needs a custom network layer.
- **No Content-Security-Policy yet.** PostHog loads scripts from its own domain; a strict policy needs testing so it doesn't break analytics.
- **The model sees what students paste.** It goes to OpenRouter for each check, under OpenRouter's terms. The page doesn't say this yet.
