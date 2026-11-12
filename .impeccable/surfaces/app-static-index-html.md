---
version: 1
slug: "app-static-index-html"
primary_target: "app/static/index.html"
related_targets: []
---

# Surface brief: TrueFit app (app/static/)

Mode: Operate. A student pastes a posting, gets a start-date verdict with quoted proof, then a tailored resume with traced bullets, then copies plain text. Constraints: plain HTML/CSS/JS, WCAG 2.2 AA, no claims beyond what the app checks (start date and undergraduate warning today; eligibility is planned for Build 3).

## Direction contract

THESIS: Every result is an exhibit, like a consulting deck: the verdict is a one-sentence action title, each requirement or bullet carries a status glyph and word, and the proof sits under it as a highlighted quote with its source. Refuses the white-card form template and the gradient hero.

OWN-WORLD: Deck navy (#14213d) top bar; cool ground #f6f7f9; white input panel; teal #0f7c7a primary action; highlighter yellow behind quoted proof; status glyphs (green check, amber question mark, red cross, grey dash) always with a word. Schibsted Grotesk for titles, tabs, labels; Source Sans 3 for body. Three sizes only: 36 title, 16 body, 13 caps labels and footnotes. 1px hairline rules, 2px navy rule under each action title, 4px corners.

STORY: The student sees at once where to paste and what they'll get; after checking, the action title tells them the answer in a sentence and the highlighted quote proves it; they move to their experience, tailor, check each bullet's source, and copy.

FIRST VIEWPORT: Navy bar: TrueFit wordmark, then tabs 1 Start date, 2 Your experience, 3 Tailored resume (active tab underlined yellow). Below, a two-column band: left 440px white panel with Available starting, Job posting (quiet "Try a sample posting"), teal Check start date button; right, Exhibit 1 with a 36px action title (empty state explains what appears), status table, and source footnotes.

FORM: Consulting-deck exhibit, candidate 3 of 7 on my ordered list, assigned by the roll and revised with the user's notes (check marks, no header meta). seed:1c0d3b319b1b4845

Signature interaction: when an exhibit fills, a highlighter swipe draws across each quoted line once (background only; text visible from the start; off under reduced motion).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
