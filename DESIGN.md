---
name: TrueFit
description: Paste a job posting. Know if the start date works, and get a resume for it that's ATS-ready and 100% true.
colors:
  navy: "#14213d"
  ground: "#f6f7f9"
  panel: "#ffffff"
  ink: "#1b2333"
  muted: "#5b6474"
  rule: "#d9dde4"
  field-border: "#aab2bf"
  teal: "#0f7c7a"
  teal-dark: "#0b5f5d"
  highlight: "#f2c94c"
  good: "#1e7a46"
  warn: "#8a5a12"
  warn-mark: "#b7791f"
  warn-bg: "#fdf6e3"
  bad: "#b42318"
  bad-bg: "#fdf0ee"
  none: "#6b7484"
typography:
  action-title:
    fontFamily: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif'
    fontSize: "36px"
    fontWeight: 800
    lineHeight: 1.15
    letterSpacing: "-0.015em"
  action-title-narrow:
    fontFamily: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif'
    fontSize: "28px"
    fontWeight: 800
    lineHeight: 1.15
  wordmark:
    fontFamily: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif'
    fontSize: "24px"
    fontWeight: 800
  tab:
    fontFamily: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 500
  row-label:
    fontFamily: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 700
  caps-label:
    fontFamily: '"Schibsted Grotesk", "Helvetica Neue", Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 700
    letterSpacing: "0.08em"
  body:
    fontFamily: '"Source Sans 3", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  footnote:
    fontFamily: '"Source Sans 3", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif'
    fontSize: "13px"
    fontWeight: 400
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "13px"
rounded:
  sm: "2px"
  md: "4px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "16px"
  lg: "22px"
  xl: "40px"
  xxl: "64px"
components:
  topbar:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.panel}"
    typography: "{typography.tab}"
    height: "64px"
  button-primary:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.panel}"
    typography: "{typography.row-label}"
    rounded: "{rounded.md}"
    padding: "12px 22px"
  button-primary-hover:
    backgroundColor: "{colors.teal-dark}"
  button-link:
    textColor: "{colors.teal}"
    typography: "{typography.footnote}"
    padding: "0"
  button-link-quiet:
    textColor: "{colors.muted}"
    typography: "{typography.footnote}"
    padding: "0"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  input-panel:
    backgroundColor: "{colors.panel}"
    padding: "36px 40px"
    width: "440px"
  exhibit:
    backgroundColor: "{colors.ground}"
    padding: "40px 64px"
  status-mark:
    size: "24px"
    rounded: "{rounded.md}"
---

# Design System: TrueFit

## Overview

**Creative North Star: "The Exhibit"**

Every result TrueFit gives is laid out like an exhibit in a consulting deck, the format Stern MBAs read every day. The exhibit's action title states the answer in one sentence. Each row underneath gives one requirement or bullet, a status mark with a word, and the proof: the quoted line, highlighted, with where it came from. Trust comes from the proof being visible, not from emphasis.

The app (`app/static/`) is an Operate surface. A deck-navy top bar holds the wordmark and the three steps as tabs. Below it, each step is a band: a 440px white input panel on the left, and that step's exhibit on a cool grey ground on the right. On narrow screens each band stacks, with the exhibit under its inputs.

The Product Page (`docs/index.html`) is a Read surface in the same system: the navy top bar (wordmark, section links, course line), the pitch as a 36px action title over a 2px navy rule on a Ground band, then one reading column (980px, prose at 70ch) with 36px section titles, 16px subsection titles over a 2px navy rule, hairline tables with caps headers, and the unit economics as a ledger of labelled rows rather than cards.

**Key Characteristics:**
- An action title per exhibit: one plain sentence that answers the question.
- A status mark and a word on every row, never color alone.
- Proof is highlighted: posting quotes sit on a highlighter-yellow wash.
- Hairline rules and a 2px navy rule under each action title; 4px corners; no shadows.
- Three type sizes carry the hierarchy: 36px titles, 16px body, 13px caps labels and footnotes.

## Colors

Restrained: deck navy owns the shell, teal owns the one action per step, highlighter yellow owns proof, and the four status families report results only.

### Shell and action
- **Deck Navy** (navy): the top bar, action titles, row labels, and the 2px rule under each action title.
- **Teal** (teal / teal-dark): the primary button in each step, link buttons, the focus ring, and exhibit numbers ("Exhibit 1 · Start date"). Hover darkens to teal-dark.
- **Highlighter** (highlight): the wash behind quoted posting lines (at 50% opacity), the active tab's underline, and text selection.

### Neutrals
- **Ground** (ground): the exhibit side of each band and the copy-ready resume box.
- **Panel** (panel): the input panel and field fills.
- **Ink** (ink): body text. **Muted** (muted): hints, footnotes, column headers, empty-state titles; 5.6:1 on Ground.
- **Rule** (rule): 1px hairlines between rows and bands. **Field Edge** (field-border): input and textarea borders, darker than Rule so fields read as fields.

### Status
- **Good** (good): Meets / In window, Traced.
- **Warn** (warn text, warn-mark glyph, warn-bg): vague, partial, or flexible verdicts; Unverified bullets; the "Who it's for" undergraduate check.
- **Bad** (bad, bad-bg): Outside window and request errors.
- **None** (none): Not stated, and rows not checked yet.
- **Information** (navy): information-only eligibility rows (work authorization, years of experience). They report what the posting says and never count for or against the student.

### Named Rules
**The Highlighter Rule.** Yellow means "this is the proof." It sits behind quoted posting text and nothing else on the page, apart from the active-tab underline and selection.

**The One Teal Rule.** Each step has exactly one teal button. Everything secondary is a link button.

## Typography

**Display:** Schibsted Grotesk (500, 700, 800) for the wordmark, tabs, action titles, row labels, and caps labels.
**Body:** Source Sans 3 (400, 600, 400 italic) for everything else.
**Mono:** ui-monospace, for the copy-ready plain-text resume only.

### Hierarchy
- **Action title** (800, 36px, 1.15, -0.015em): one per exhibit, in Deck Navy; Muted in the empty state; 28px under 900px.
- **Wordmark** (800, 24px): "TrueFit" in the top bar.
- **Tab** (500, 16px; numbers at 700): step tabs in the top bar, 78% white, full white when hovered or current.
- **Row label** (700, 16px): requirement names, resume entry headers, primary button text.
- **Caps label** (700, 13px, 0.06–0.08em, uppercase): panel titles, exhibit numbers, table headers, resume section headings.
- **Body** (400, 16px, 1.55): everything else.
- **Footnote** (400, 13px): hints, sources, flag reasons, link buttons (at 600).

### Named Rules
**The Quote Rule.** Italic means verbatim: posting quotes and resume source lines. Nothing else is italic.

**The Three Sizes Rule.** Hierarchy comes from weight, case, color, and rules, not from more sizes. New text uses 36, 16, or 13px.

## Layout

A band per step: `grid-template-columns: 440px 1fr`. The input panel is white with a 1px right rule and 36px × 40px padding. The exhibit pads 40px × 64px and caps at 980px. Bands are separated by a 1px rule. Under 900px, bands stack, padding drops to 28px × 20px, tabs shorten to "Experience" and "Resume", and exhibit table rows become label + status on one line with the quote below.

Field groups are 22px apart; hints sit 6px under their field; a primary button sits 22px under the last field.

## Elevation & Depth

Flat. No shadows anywhere. Depth comes from the white panel against the grey ground, 1px rules, and the 2px navy rule under each action title. Focus uses a 3px teal halo on fields and a 3px teal outline on buttons.

## Motion

One authored moment: when an exhibit fills, a highlighter swipe draws across each quoted line (0.7s, `cubic-bezier(0.16, 1, 0.3, 1)`, staggered 0.12s per row). Only the background animates, so the text is readable from the start. It is off under `prefers-reduced-motion`.

## Components

### Top bar
Deck Navy, 64px tall, wordmark then three tabs ("1 Start date", "2 Your experience", "3 Tailored resume"). The current step's tab has `aria-current="step"`, full white text, and a 3px highlighter underline.

### Exhibit (signature)
Exhibit number in teal caps, then the action title, then a Muted sub-line ("Checked against your availability: …") over a 2px navy rule. Below, a table: Requirement | Status | What the posting says. The empty state shows the same table with one "Not checked yet" row and a grey bar where the quote will go.

### Status mark
A 24px SVG glyph followed by the status word, in the status color: filled green check (Meets / In window / Traced), amber outlined question mark (vague, partial, flexible, Unverified, Check), filled red cross (Outside window), grey outlined dash (Not stated, not checked yet), navy outlined "i" (information only, with a label naming what the posting says, e.g. "No sponsorship" or "4+ years required"). 20px inside resume bullets.

### Quoted proof
Italic text on a highlighter wash, with a 13px Muted source line under it ("Quoted word for word from the posting").

### Traced bullet
A row in Exhibit 2: status mark and word in a 130px column, then the bullet text, an amber flag reason (Unverified only), italic source lines ("From your resume: …"), and Remove / Put back / Edit link buttons. Unverified rows get a warm wash fading right; removed bullets are struck through in Muted and stay visible.

### Buttons
- **Primary:** Teal, white 700 16px label, 12px × 22px, 4px corners. Disabled at 75% with a wait cursor while working; "Tailor resume" sits at 45% and not-allowed until a start date is checked.
- **Link:** Teal 600 13px, underline on hover. **Quiet link** ("Try a sample posting"): Muted 400 with a Rule-colored underline, turning teal on hover.

### Fields
White, 1px Field Edge border, 4px corners, 10px × 12px. Focus: teal border and a 3px teal halo. Textareas grow with their content (min 9em, max 32em) where the browser supports `field-sizing`.

## Do's and Don'ts

### Do:
- **Do** open every exhibit with a one-sentence action title that answers the question.
- **Do** pair every status color with its glyph and word.
- **Do** put the quoted proof, highlighted, next to every claim, with where it came from.
- **Do** show only what the app actually checks. Rows the app reports but doesn't judge use the information mark, never a status color.

### Don't:
- **Don't** add shadows, gradients, or rounded corners beyond 4px.
- **Don't** use yellow for anything but proof, the current tab, and selection.
- **Don't** use green, amber, or red as decoration.
- **Don't** invent source details the app doesn't have, such as posting line numbers.
- **Don't** add decorative formatting to the copy-ready resume.
