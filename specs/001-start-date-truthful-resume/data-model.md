# Data Model: Start-Date Check & Truthful Tailored Resume

**Feature**: [spec.md](./spec.md) | **Date**: 2026-11-04

Nothing here is stored on the server. Everything lives in a single request/response, except the
**Saved Profile** in the browser.

## Availability

When the student can start (FR-006a). It's open-ended: any start on or after it fits. It's
parsed on the server from the text the student typed.

| Field | Type | Notes |
|---|---|---|
| `mode` | `month` \| `asap` \| `flexible` | |
| `start` | date \| null | `month`: first day of the start month. `asap`: today. `flexible`: null |
| `label` | string | Display text, e.g. "Starting June 2027", "ASAP", "Flexible" |

**Validation**:
- Accepted input, case-insensitive:
  - `<Month YYYY>`, optionally prefixed with `Starting` or `From`
  - `ASAP` ("Immediate" is not accepted for availability)
  - `Flexible`
- Month names may be full or 3-letter.
- A range (e.g., "June 2027 – October 2027") → error asking for just the start month. Anything
  else → error listing the accepted forms. The previous availability is kept (FR-006b).
- Default when nothing is saved: `month`, starting June 1 2027.

## StartDateMention

One mention of a start date in a posting. The model extracts it and the server validates it.

| Field | Type | Notes |
|---|---|---|
| `quote` | string | Must be an exact substring of the posting (whitespace collapsed) or the mention is dropped |
| `kind` | `exact_date` \| `month` \| `range` \| `season` \| `immediate` \| `flexible` \| `graduation` | `graduation`: the window when eligible candidates graduate (needs an end month); used only if no start date is stated |
| `start` | date \| null | Set by the server from the kind (see research.md §R4) |
| `end` | date \| null | For `exact_date`, `start = end` |
| `role_hint` | string \| null | For multi-role postings, e.g. "NYC office" |
| `is_vague` | bool | True for `season`, a bare year, and `graduation` |

## StartDateResult

| Field | Type | Notes |
|---|---|---|
| `mentions` | StartDateMention[] | Empty → verdict `not_stated` |
| `verdict` | Verdict | Summary verdict (see below); with multiple mentions, each also carries its own verdict |
| `availability` | Availability | What it was checked against (shown next to the verdict) |
| `note` | string \| null | e.g. "Exact date not specified", "This date has already passed" |
| `undergrad_warning` | `{quote}` \| null | Set when the posting targets people pursuing or finishing a bachelor's degree, or is a new-grad / early-career program whose only named degree is a bachelor's. Not set when an MBA or other graduate degree is named, or when a bachelor's is the minimum for an experienced role. The quote must be an exact substring of the posting or the warning is dropped. Shown above the verdict; does not change it. |

### Verdict

`in_window` · `outside_window` · `partly_in_window` · `likely_in_window_vague` · `flexible_to_discuss` · `not_stated`

Display labels: In window · Outside window · Partly in window · Likely in window (vague) · Flexible / to discuss · Not stated

### Verdict rules

The posting interval `P` is `[start, end]`. Availability `A` is open-ended: `[A.start, ∞)`, where
`asap` means `[today, ∞)` and `flexible` means any future date. Rules are checked in order:

1. No valid mentions → `not_stated`.
2. Posting `kind = flexible` → `flexible_to_discuss`.
2a. Posting `kind = graduation` (only kept when no other mention exists) → `in_window`
   if `A.mode = flexible` or the month after the graduation window's end ≥ `A.start` (the role hires
   people graduating as late as that month, and they start after graduating); otherwise
   `outside_window`. A season end uses its last month ("Spring 2027" → May 2027). The note names the month.
3. `P.end < today` → `outside_window`, note "date has passed".
4. Posting `kind = immediate` → `in_window` if the student is available today (`A.mode` is
   `asap` or `flexible`, or their start month has already arrived); otherwise
   `outside_window`, note "starts before you're available".
5. `A.mode = flexible` → `in_window`.
6. `P.start ≥ A.start` (starts in or after the student's month) → `likely_in_window_vague` if
   `is_vague`, else `in_window`.
7. `P.start < A.start ≤ P.end` (begins before, ends after) → `partly_in_window`, note "exact date
   not specified" if `is_vague`.
8. `P.end < A.start` → `outside_window`.

**Summary verdict for multiple mentions**: if they agree, use that verdict. Otherwise use
`partly_in_window` and list each mention with its own verdict.

## ResumeLine

| Field | Type | Notes |
|---|---|---|
| `id` | string | `L1`, `L2`, … for master-resume lines; `N1`, `N2`, … for sentences from the student's other writing (notes, past cover letters, behavioral stories, essays) |
| `text` | string | Original line, trimmed; blank lines skipped |
| `section` | string \| null | Nearest heading above it (e.g., "Experience"), if one is detected; "Your writing" for N-lines |
| `source` | `resume` \| `notes` | Which input the line came from |

## TailoredResume

| Field | Type | Notes |
|---|---|---|
| `sections` | Section[] | Ordered: Education, Experience, then others in master-resume order |
| `plain_text` | string | Copy-ready text built from included bullets only (research.md §R10) |

**Section**: `heading` (string), `entries` (Entry[])

**Entry**: `header_line_ids` (string[], e.g., the role/company/date lines, copied verbatim), `bullets` (Bullet[])

## Bullet

| Field | Type | Notes |
|---|---|---|
| `id` | string | Stable within a response, e.g. `B1` |
| `text` | string | Current text (generated or edited) |
| `source_line_ids` | string[] | Cited master-resume lines |
| `status` | `traced` \| `flagged` | From the trace check (research.md §R6) |
| `flag_reason` | string \| null | e.g. "'8' not found in source lines", "'SQL' isn't in your master resume", "Team size not supported" |
| `included` | bool | Default: `true` if traced, `false` if flagged (FR-012) |
| `edited` | bool | True after the student changes the text |

**State transitions** (in the browser):
- Generated → `traced` + included, or `flagged` + excluded.
- Remove → `included = false`. Put back → `included = true` (a flagged bullet stays `flagged`
  and marked; FR-012c).
- Edit text → `edited = true`, then re-check (`/api/verify-bullet`), which updates `status`,
  `flag_reason`, and `source_line_ids`. `included` is unchanged.
- Any change rebuilds `plain_text` on the client with the same rules as the server renderer.
  The server renderer is the tested reference, and the client mirrors it.

## Gap

| Field | Type | Notes |
|---|---|---|
| `text` | string | Short requirement name, e.g. "CPA" |
| `quote` | string | Exact posting substring |
| `group` | `required` \| `preferred` | Unlabeled requirements become `required` (FR-016a) |
| `note` | string \| null | e.g. "Related: financial modeling (L7), but Excel not stated" |

`GapList`: `{ required: Gap[], preferred: Gap[], none_found: bool }` (FR-017)

## Saved Profile (browser only)

`localStorage["truefit.v1"]`:

| Field | Type | Notes |
|---|---|---|
| `masterResume` | string | Pre-filled on load (FR-020); always shown and editable before tailoring |
| `backgroundNotes` | string | Optional writing about their experience (notes, cover letters, stories, essays, up to 50,000 chars); saved and cleared with the resume |
| `availabilityText` | string | What the student typed; empty means the default window |
| `savedAt` | ISO datetime | Shown as "Saved on this device on …" |

Clearing it removes the key entirely (FR-021). Postings and results are never written here.
