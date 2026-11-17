---
name: truefit-change
description: Make a change to TrueFit (wording, a label, a rule, a feature, a fix) and carry it all the way through - the app, its tests, the Product Page (docs/index.html), the other project docs, then a branch, commit, and pull request, stopping to ask before merging. Use this whenever the user asks to change, rename, reword, add, remove, or fix anything in TrueFit, including when it comes from group, classmate, sponsor, or instructor feedback ("my group said...", "change X to Y", "can you make it say..."), and when they ask to "update the docs to match" a change.
---

# TrueFit change workflow

TrueFit is a student project (an MBA course) with a public Product Page that doubles as the living PRD and weekly build log. A change isn't finished when the code changes: the page and the other docs have to say the same thing, and it has to land through a pull request, because that's how the repo works and `main` publishes the page. This skill is that whole path in one go.

The user is an MBA student, not an engineer. Explain what you did in plain words (what changed, where, whether tests pass), and avoid git jargon unless you define it.

`AGENTS.md` is the project's operating manual. Its rules apply on top of this skill, especially: propose a short plan before touching many files, keep the change small enough for one PR, never run the model evals without asking (they cost money), and stop to ask if a fix fails twice.

## 1. Find everything the change touches

Search the whole repo for the thing being changed, not just the obvious file. A label usually lives in several places:

- `app/` - Python (labels and messages often sit in dicts near the top of a module, e.g. `REQUIREMENT_NAMES`, `STANCE_LABELS` in `app/eligibility.py`) and the frontend in `app/static/` (`index.html` placeholders, text built in `app.js`).
- `tests/` - unit and API tests that assert on the old wording.
- `docs/index.html` - the Product Page.
- `PRODUCT.md`, `DESIGN.md`, `AGENTS.md`, `README.md` - project docs that describe the app.

Use a case-insensitive search and try spelling variants (`work authorization`, `work-authorization`, `Work authorization`). Then check two things the search won't show you:

- **Nearby wording that reads oddly after the change.** Renaming the "Work authorization" row to "Sponsorship" left a value, "Authorization required", that no longer fit next to the new label.
- **Collisions.** Search for the *new* wording too. A new label that matches an existing one on the same screen (a tab, a section heading) can confuse students.

Point these out and offer a fix instead of silently changing them.

Also note leftovers from earlier changes you come across (docs still using an old name the app already dropped). Offer to fix them in the same PR; don't bury them.

AGENTS.md asks for a plan before touching more than one file. Keep it short: one line per file saying what changes, then wait for a yes. If the user already told you to go ahead, or answered your plan, proceed.

## 2. Change user-facing text, keep internal names

When the request is about what students see (a label, a message, a heading), change the displayed text and leave internal identifiers alone: dict keys like `work_authorization`, JSON field names, the model prompt's field names, and eval case files. Renaming those would break the API, the eval set, and stored data for no visible benefit. Tell the user you kept the internal name and why, in one line.

If the user really does want the internal name changed, that's a bigger change: plan it, and update the eval cases and prompt together.

## 3. Update the docs: current state yes, history no

The Product Page mixes two kinds of text, and they're treated differently.

**Update** text that describes how TrueFit works now: the "After" workflow, scope and non-goals, "How it works", the pitch, the unit economics notes, user stories, and the matching lines in `PRODUCT.md`, `DESIGN.md`, `AGENTS.md`, and `README.md`.

For a rename, change prose where it uses the old word as the *name* of the thing ("work authorization and years of experience are shown for information" names the rows, so it became "sponsorship and ..."). Leave prose where the words describe *what is checked* and are still true: "the posting's years-of-experience requirement" stays accurate after the row is relabeled "Experience", and shortening it would lose meaning. When unsure, ask.

**Leave alone** text that records what happened on a date:
- rows in the Open Questions / decisions table that carry a past date
- earlier weekly build log entries
- captions and alt text for dated screenshots (they describe the image as it was taken; if the screenshot shows the old wording, say so and suggest retaking it)

**Add a decision row** when the change reflects a product decision (most feedback-driven changes do). Put it in the decisions table after the related row, dated today, in the same voice as the others: a question, then the answer, naming where it came from. Give the reason only if the user gave one; don't invent one, because the decisions log is graded evidence of how the student decided. Example:

```html
<tr><td>Should the row be called "Work authorization" or "Sponsorship"?</td><td>"Sponsorship," after group feedback. When a posting asks for authorization but doesn't say whether it sponsors visas, the row now says "Ask recruiter" instead of "Authorization required."</td><td>Nov 17, 2026</td></tr>
```

If you think a reason would help, ask the user for it.

## 4. Check it

Run `uv run pytest` (unit and API tests, free and fast). Update tests that asserted the old wording; don't delete them. Don't add new tests just to pin a label. Report the pass count. Don't run `tests/eval/run_eval.py` unless the user says so, because it calls the real model and costs money.

If the app is running locally, remind the user to restart it to see the change.

## 5. Branch, commit, pull request, then ask

The repo works through one branch and one PR per change, and `main` publishes the Product Page through GitHub Pages.

1. If you're on `main`, create a short kebab-case branch first (`sponsorship-label`, `fix-headers-copy`).
2. Commit with the repo's prefixes: `feat:` new behavior or changed wording in the app, `fix:` bug fix, `docs:` page and docs only, `style:` look and layout, `chore:` tooling. The subject says what changed in plain words; the body says why (for example "Group feedback: ...") and anything kept on purpose (like the internal key).
3. Put the app change and its doc updates in one PR by default, since they're one change and the page shouldn't lag the app. Split only if the user asks.
4. Push and open the PR with `gh pr create`. The description lists what changed, what was kept on purpose, and the test result.
5. Stop and ask before merging, because merging updates the public page. Give the PR link.

When the user says to merge: check `gh pr view <n> --json mergeable,mergeStateStatus`, then `gh pr merge <n> --merge --delete-branch` (the repo uses merge commits). Confirm you're back on an up-to-date `main`, and say the page takes about a minute to rebuild.

## 6. Report back

Keep it short: what changed and where (with file:line references), what you kept on purpose, the test result, the PR link or the next step, and anything you noticed but didn't change (an old screenshot, a value that reads oddly).
