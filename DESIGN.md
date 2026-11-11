---
name: TrueFit
description: Paste a job posting. Know if the start date works, and get a resume for it that's ATS-ready and 100% true.
colors:
  violet: "#57068c"
  violet-dark: "#3f0566"
  violet-tint: "#f4effa"
  grad-start: "#155799"
  bg: "#f3f6fa"
  card: "#ffffff"
  text: "#3b454a"
  muted: "#606c71"
  border: "#e3e8ee"
  good: "#166534"
  good-bg: "#ecfdf3"
  warn: "#92400e"
  warn-accent: "#d97706"
  warn-bg: "#fffbeb"
  warn-badge-bg: "#fef3c7"
  warn-border: "#fde68a"
  bad: "#991b1b"
  bad-bg: "#fef2f2"
  bad-border: "#fecaca"
  neutral: "#475569"
  neutral-bg: "#f1f5f9"
typography:
  display:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "36px"
    fontWeight: 700
  headline:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1.25
  title:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "20px"
    fontWeight: 600
  body:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.6
  small:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "14px"
    fontWeight: 400
  eyebrow:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "12px"
    fontWeight: 600
    letterSpacing: "0.08em"
  verdict:
    fontFamily: '"Open Sans", -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif'
    fontSize: "15px"
    fontWeight: 700
    letterSpacing: "0.05em"
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "13px"
rounded:
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "14px"
  pill: "999px"
spacing:
  2xs: "6px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.card}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-primary-hover:
    backgroundColor: "{colors.violet-dark}"
  button-link:
    textColor: "{colors.violet}"
    typography: "{typography.small}"
    padding: "0"
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  step-card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.xl}"
    padding: "24px 28px"
  step-marker:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.card}"
    rounded: "{rounded.pill}"
    size: "28px"
  verdict-in-window:
    backgroundColor: "{colors.good-bg}"
    textColor: "{colors.good}"
    typography: "{typography.verdict}"
    rounded: "{rounded.lg}"
    padding: "18px 20px"
  verdict-vague:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn}"
    typography: "{typography.verdict}"
    rounded: "{rounded.lg}"
    padding: "18px 20px"
  verdict-outside:
    backgroundColor: "{colors.bad-bg}"
    textColor: "{colors.bad}"
    typography: "{typography.verdict}"
    rounded: "{rounded.lg}"
    padding: "18px 20px"
  verdict-not-stated:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral}"
    typography: "{typography.verdict}"
    rounded: "{rounded.lg}"
    padding: "18px 20px"
  badge-traced:
    backgroundColor: "{colors.good-bg}"
    textColor: "{colors.good}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  badge-unverified:
    backgroundColor: "{colors.warn-badge-bg}"
    textColor: "{colors.warn}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  bullet:
    backgroundColor: "{colors.card}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  bullet-unverified:
    backgroundColor: "{colors.warn-bg}"
---

# Design System: TrueFit

## Overview

**Creative North Star: "The Receipts"**

Every claim TrueFit makes arrives with its proof attached. The start-date verdict sits above the exact line it was quoted from; every resume bullet carries a Traced or Unverified badge and the source lines it came from. The visual system exists to make that evidence easy to see and quick to check. It is calm, not loud: trust comes from things being visible, never from emphasis.

The world is a quiet academic one. A blue-to-violet gradient (Cayman blue into NYU violet) marks the masthead, and everything below it is white cards on a pale blue-grey page, one column wide, with generous padding. Violet does two jobs only: headings and the primary action. Color beyond that is reserved for verdict status, and every status color is paired with a symbol and a word.

The system has two layouts that share one set of tokens. The app (`app/static/`) is an Operate surface: a gradient header band with three numbered step cards overlapping its lower edge. The Product Page (`docs/index.html`) is a Read surface: a sticky gradient sidebar beside one long text column for the PRD and build log. Both use the same text colors; the app's corner radii are the standard, and the page's tighter corners are noted in Shapes.

**Key Characteristics:**
- Proof sits next to the claim: italic quotes, source lines, Traced badges.
- One column, max 760px in the app, max 820px of text on the Product Page.
- Gradient only in the masthead; white cards and flat interiors everywhere else.
- Four status families (good, warn, bad, neutral), each with a glyph and a label.
- Plain, literal copy; the copy-ready resume is monospace plain text.

## Colors

A restrained palette: one brand violet, one gradient partner blue, cool neutrals, and four status families that are used only to report a result.

### Primary
- **NYU Violet** (violet): h2 headings, step markers, primary buttons, link buttons, the focus ring, and the end of the masthead gradient. It is the one voice that says "act here" or "this is a section."
- **Deep Violet** (violet-dark): primary button hover, and resume-section headings inside the tailored resume.
- **Violet Mist** (violet-tint): a pale violet wash kept available for selected or highlighted rows; currently defined but used sparingly.

### Secondary
- **Cayman Blue** (grad-start): the start of the masthead gradient only (120° in the app header, 160° in the Product Page sidebar). Never used as a flat fill or text color.

### Neutral
- **Slate Ink** (text): body text, labels, entry headers. The standard text color for both surfaces.
- **Fog Grey** (muted): hints, captions, `meta` lines, stat-box labels, source-line notes, optional-field labels.
- **Paper White** (card): card, input, and bullet backgrounds.
- **Blue-Grey Wash** (bg): the app page background behind the cards; also the Product Page table-header and stat-box tint.
- **Hairline** (border): card, input, bullet, and section-divider borders.

### Status
- **Proof Green** (good / good-bg): In window verdicts and Traced badges.
- **Caution Amber** (warn / warn-bg / warn-accent / warn-badge-bg / warn-border): vague, partial, and flexible verdicts; Unverified bullets and badges; the undergraduate warning. `warn-accent` colors the verdict glyph disc and left rule; `warn` colors text.
- **Stop Red** (bad / bad-bg / bad-border): Outside window verdicts and request errors.
- **Slate Neutral** (neutral / neutral-bg): Not stated verdicts, and the background of the copy-ready resume box.

### Named Rules
**The Proof Is Green Rule.** Green means "checked and it holds": an In window verdict or a Traced bullet. It is never used as decoration, branding, or a generic success toast.

**The One Violet Rule.** Violet marks headings and the single primary action in a step. If two things on screen are both violet buttons, one of them should be a link button.

## Typography

**Body Font:** Open Sans (with -apple-system, BlinkMacSystemFont, Helvetica Neue, Helvetica, Arial, sans-serif)
**Mono Font:** ui-monospace (with SFMono-Regular, Menlo, monospace), for the copy-ready resume only

**Character:** One humanist sans at a few weights, set at a comfortable 1.6 line height. Hierarchy comes from weight and violet color, not from size jumps. Both surfaces load Open Sans from Google Fonts (400, 600, 700, and 400 italic for quotes, with `display=swap`); any new weight or style must be added to that link on both pages.

### Hierarchy
- **Display** (700, 36px): the "TrueFit" wordmark in the app header band, in white. The Product Page sidebar sets it at 40px, weight 600, line height 1.1; 30px on phones in the app.
- **Headline** (600, 26px, 1.25): Product Page section headings, in violet.
- **Title** (600, 20px): app step-card headings, in violet with a numbered step marker; Product Page h3 subheads use 18px.
- **Body** (400, 16px, 1.6): everything else. Text measure is capped by the column (760px card, 820px page section), roughly 75–90 characters.
- **Label** (600, 16px): form field labels and primary button text.
- **Small** (400, 14px): hints, captions, "checked against" lines, link buttons (at 600).
- **Eyebrow** (600, 12px, 0.08em, uppercase): the line above the wordmark in the masthead, at 75–80% white opacity. Stat-box labels on the Product Page use the same caps treatment at 0.04em.
- **Verdict** (700, 15px, 0.05em, uppercase): the verdict label in the start-date result, in the status text color.
- **Mono** (13px): the read-only copy-ready resume textarea.

### Named Rules
**The Quote Rule.** Italic means "this is someone else's exact words": posting quotes in blockquotes and source lines under bullets. Nothing else is set in italic, so a reader can trust that anything slanted is verbatim.

## Layout

**App.** A full-width gradient header band (40px top, 72px bottom padding) holds the eyebrow, wordmark, and tagline inside a 760px column. The content column (max 760px, 20px side gutters) is pulled up 44px so the first card overlaps the band. Three step cards stack vertically with 20px between them, padded 24px × 28px (20px on phones). Inside a card, label/field groups are separated by 16px above each label and 6px below; primary buttons sit 16px below their field. Rows that pair a label with a link button use a space-between flex row. Breakpoint at 600px: wordmark drops to 30px and card padding to 20px.

**Product Page.** A two-column grid: a 320px sticky sidebar (full viewport height, 48px × 32px padding, gradient) and one text column (max 820px, 44px × 56px padding). Sections are separated by a 1px hairline rule. Supporting content uses full-width bordered tables and an auto-fit stat grid (min 220px columns, 14px gap). Below 860px the sidebar becomes a centered banner on top, its buttons wrap into a row, and sections pad to 32px × 22px.

**Shared rhythm.** Spacing steps cluster at 6, 8, 12, 16, 20, and 28px. Density is relaxed: whitespace between steps is part of what makes the evidence feel checkable.

## Elevation & Depth

The system is mostly flat. There is exactly one shadow, a soft two-layer ambient lift on the app's top-level step cards, which makes them read as sheets of paper resting on the blue-grey page and over the header band. Everything inside a card is flat and separated by 1px hairlines and pale tinted fills. The Product Page uses no shadows at all; it separates content with rules, borders, and tints.

### Shadow Vocabulary
- **Card lift** (`box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04), 0 4px 16px rgba(16, 24, 40, 0.06)`): app step cards only.
- **Focus halo** (`box-shadow: 0 0 0 3px rgba(87, 6, 140, 0.15)`): focused inputs and textareas, together with a violet border.

### Named Rules
**The One Lift Rule.** Only the step card is lifted. Verdict cards, bullets, badges, and inputs inside it stay flat; depth inside a card comes from tint and border, never from another shadow.

## Shapes

Gently rounded, friendly but not bubbly. In the app: blockquotes 8px (square on the left, where the quote rule sits), inputs, buttons, and bullets 10px, verdict cards 12px, step cards 14px, and full pills for badges, step markers, and verdict glyph discs. Radius grows with container size. The Product Page uses tighter corners (about 5px on sidebar buttons and stat boxes, 8px on figures); treat the app scale as the standard for new work. Status is also carried by a left rule: 5px on verdict cards and 3px on blockquotes.

## Components

Calm and checkable: soft cards, generous space, and evidence visible at a glance.

### Buttons
- **Shape:** gently rounded (10px).
- **Primary:** NYU Violet fill, white 600-weight label, 10px × 20px padding, 16px above. Holds an inline 16px spinner while working; the disabled state drops to 75% opacity with a wait cursor (50% and not-allowed for "Tailor resume" before a start-date check).
- **Hover / Focus:** hover darkens to Deep Violet over 0.15s. Focus-visible draws a 3px violet outline at 35% opacity, offset 2px.
- **Link button:** unstyled text button in violet, 14px/600, underlined on hover. Used for secondary actions such as "Try a sample posting", "Save on this device", "Remove", and "Put back".
- **Product Page sidebar button:** full-width ghost button on the gradient, translucent white fill (8%) and border (25%), brightening to 20% fill on hover.

### Cards / Containers
- **Step card:** white, 14px radius, 1px hairline border, card-lift shadow, 24px × 28px padding. Its h2 leads with a 28px violet step-number disc.
- **Stat box (Product Page):** Blue-Grey Wash fill, pale blue border, small uppercase label over a 19px bold violet value.

### Inputs / Fields
- **Style:** full width, white, 1px hairline border, 10px radius, 10px × 12px padding, inherits body type. Textareas resize vertically only.
- **Focus:** border turns violet plus the 3px focus halo; the native outline is removed only because this replaces it.
- **Read-only output:** the copy-ready resume textarea uses the mono font at 13px on a Slate Neutral background, so it reads as "plain text, ready to paste."

### Verdict Card (signature)
The start-date result. A 12px-radius panel with a 5px status-colored left rule and a pale status fill. The head pairs a 32px glyph disc (white ✓ for in window, ~ for vague, partial, or flexible, ✕ for outside, ? for not stated) with an uppercase verdict label. Below it: a one-sentence plain explanation, the quoted evidence in an italic blockquote on a 70% white wash, and a small "checked against" note. An undergraduate-posting warning, when present, sits above the verdict in a Caution Amber box.

### Traced Bullet (signature)
Each tailored-resume bullet is a 10px-radius bordered tile. A pill badge leads the row: "✓ Traced" in Proof Green, or "Unverified" in Caution Amber, which also tints the whole tile amber. Under the text: an amber flag reason (Unverified only), then italic 13px source lines ("From your resume: …"), then link-button controls. Excluded bullets fade to 60% with the text struck through, so a removed claim stays visible and can be restored.

### Error Banner
A Stop Red tinted box (10px radius, pale red border) above the steps with `role="alert"`, holding one plain sentence.

### Named Rules
**The Never Color Alone Rule.** Every status color travels with a glyph and a word: ✓ In window, ✕ Outside window, "Unverified". If you remove the color, the meaning must survive.

## Do's and Don'ts

### Do:
- **Do** put the source next to every claim: an italic blockquote for posting quotes, an italic source line for resume bullets.
- **Do** pair each status color with its glyph and label (✓ ~ ✕ ?, "✓ Traced", "Unverified").
- **Do** use NYU Violet (#57068c) for h2 headings and the one primary button per step; use link buttons for everything secondary.
- **Do** keep the copy-ready resume monospace and plain: standard headings, hyphen bullets, a single column.
- **Do** keep focus visible: a violet border plus a 3px halo on fields, a 3px violet outline on buttons.
- **Do** use Fog Grey (#606c71) as the lightest text color; it clears 4.5:1 on white and on the Blue-Grey Wash.

### Don't:
- **Don't** use the gradient anywhere but the app header band and the Product Page sidebar.
- **Don't** add new hues; the palette is violet, Cayman blue, cool neutrals, and the four status families.
- **Don't** use green, amber, or red as decoration; they report results only.
- **Don't** add shadows inside a step card; only the card itself is lifted.
- **Don't** set anything in italic that isn't verbatim source text.
- **Don't** introduce a grey lighter than Fog Grey for text; anything paler fails WCAG AA at the 14px captions use.
- **Don't** add tables, columns, icons, or decorative formatting to the copy-ready resume output.
