---
name: build-log-entry
description: Write or update a weekly entry in the TrueFit Product Page build log (docs/index.html, "Weekly Build Log") - drafting What shipped, what broke, and what changed in the PRD from the commits, pull requests, and decisions made that week, then asking the user only for what the repo can't know (hours, costs, lessons). Use this whenever the user mentions the build log, a Build 1-5 entry, filling in "this week", a weekly update or reflection for the course, or logging hours or costs on the Product Page, even if they don't say "build log".
---

# Weekly build log entry

The Product Page (`docs/index.html`) has a "Weekly Build Log" with one `<div class="log-entry">` per course build (Build 1 to Build 5, each with a due date in its heading). Future builds hold placeholder text in square brackets, like `[Fill in]` or `$[0.00] · [0] hours`. The instructor grades from this log, so it needs to be accurate, specific, and in the student's own voice.

Most of an entry can be drafted from what the repo already records. The student's time is best spent on what only they know. So: draft from history, then ask.

## 1. Find the entry and the week

Read the Weekly Build Log section. The entry to write is usually the first one that still has `[...]` placeholders, unless the user names a build.

The week starts on the previous build's due date (builds are due at noon, so that afternoon's work belongs to the next build) and ends on this build's due date. Anything the previous entry already reported is not news, even if it falls in this week, so read it and don't repeat it.

If the user gives a due date that disagrees with the entry's heading, check the course site if the Icerynk tools are connected (read-only; `list_my_assignments`), otherwise ask. Mention the mismatch instead of silently changing the heading.

Keep the bullet labels that are already in that entry's template. They differ by build (Build 3 combines "What broke / changed in PRD" into one bullet, Build 4 has "Chosen track" and "Results and improvements", Build 5 has "Launch Ops & Safety"), because they follow the course assignment; when the template and the advice below differ, the template wins. You may add a "Lessons" or "Things learned with AI" bullet before "Cost & time" if the user gives you one, as earlier entries did.

The bracketed placeholder text is the assignment's requirement (for example, Build 3's "[End-to-end workflow working with real inputs + PostHog funnel events]"). Compare the week's work against it, and if something it asks for is missing, say so when you ask your questions.

**Mid-week drafts.** Students often start the entry before the week is over. Then label the bullet "What shipped (so far):" as Build 2 did, write only what has merged, and keep a short bracketed note for what's still planned (e.g. "[Still to come: the gap list and Word download]") so it's obvious what to fill in later. Offer to update it again before the due date.

## 2. Gather what happened

Collect evidence for the week before writing anything:

- `git log --no-merges --since='<start> 12:00' --until='<end + 1 day> 00:00' --format='%ad %s' --date=short`. Include the times: with a bare date, git uses the current time of day and silently drops part of the first day.
- `gh pr list --state merged --search "merged:<start>..<end>" --json number,title,body` for what each change was and why. PR descriptions often hold the test counts and eval results to quote.
- `uv run pytest -q` if you need the current test count (free, no model calls). Never run the model evals for this.
- dated rows in the decisions table (Open Questions) that fall in the week
- the PRD sections and "Unit Economics" ledger, for numbers that changed (test counts, eval scores, cost per run)
- earlier log entries, for the voice and for what was promised last week (e.g. "Resume tailoring is next")

Group related commits into a few themes. Ten commits about the same feature become one sentence.

## 3. Draft in the existing voice

Read the Build 1 and Build 2 entries first and match them:

- First person, plain language, written for an instructor who knows the course but not the code.
- Specific and checkable: numbers with dates ("31 of 31 start dates right on the eval (Nov 13)"), names of features as students see them, not file names or function names.
- Say what changed for the user, then briefly how.
- Reversals are recorded honestly with a date ("*Update, Nov 12:* after testing real postings with no start date, I reversed this.").
- "What changed in PRD" also covers changes that were considered and rejected, with the reason.
- Use the app's current names for things (e.g. "Sponsorship", not the older "work authorization"); earlier entries keep the names they used at the time.
- If you can't tell where a change came from (group feedback, a pod test, a sponsor call), ask rather than guess. The instructor cares about where the evidence came from.
- Each bullet is one `<li><strong>Label:</strong> text</li>`. Use `<code>` for file names, `<em>` sparingly, and HTML entities where the page already does.

Only state numbers that appear in the repo, PR descriptions, the page itself, or what the user tells you. Never estimate hours, costs, or eval results. If something isn't recorded, leave it out or ask.

## 4. Ask for what you can't know

Show the draft, then ask in one message for the gaps, offering what you found as a starting point:

- **Hours** spent this week.
- **Costs**: OpenRouter credits used this week (the page tracks the running total, e.g. "credits used went from $0.08 to $2.56"), plus any new subscriptions. Show last week's line as the format to follow.
- **Lessons** or what they learned working with AI, if they want that bullet.
- Anything that broke that never made it into a commit (a blocker, a dead end).

Format the cost line like the others: `$<total> (<what it was>) · <n> hours`.

If the costs change the totals, also offer to update the "Cumulative Build Spend" figure and its "As of" date in the Unit Economics ledger, since it should agree with the log.

## 5. Write it and ship it

Replace the placeholder text in that entry only; don't touch earlier entries. Show the final entry text to the user.

Then land it like any other TrueFit change (the `truefit-change` skill covers this in full): a branch such as `build-3-log`, a `docs:` commit (e.g. `docs: Build 3 log entry (shipped, PRD changes, cost and hours)`), push, open a PR, and ask before merging, since merging updates the public page.
