# API Contract: TrueFit v1

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md)

The server is stateless. All routes take and return JSON. Field shapes follow data-model.md.
Dates are ISO `YYYY-MM-DD`.

## GET /

Serves `app/static/index.html`.

## POST /api/start-date

Checks a posting's start date against the student's availability (User Story 1).

**Request**
```json
{
  "posting": "string, 100–20,000 chars",
  "availability_text": "string, optional; e.g. \"August 2027\", \"ASAP\", \"Flexible\"; empty or missing = starting June 2027"
}
```

**200 Response**: `StartDateResult`
```json
{
  "verdict": "likely_in_window_vague",
  "verdict_label": "Likely in window (vague)",
  "availability": { "mode": "month", "start": "2027-06-01", "label": "Starting June 2027" },
  "mentions": [
    { "quote": "Associates join us in Summer 2027", "kind": "season",
      "start": "2027-06-01", "end": "2027-08-31", "role_hint": null, "is_vague": true,
      "verdict": "likely_in_window_vague" }
  ],
  "note": "Exact date not specified"
}
```

**Errors** (all use `{ "error": { "code": "...", "message": "plain-language text" } }`)

| Status | `code` | When |
|---|---|---|
| 422 | `posting_too_short` / `posting_too_long` | Length out of range |
| 422 | `not_a_posting` | The model reports the text isn't a job posting |
| 422 | `not_english` | The posting isn't in English |
| 422 | `availability_invalid` | Availability doesn't match an accepted form; a range gets a message asking for just the start month (FR-006b) |
| 502 | `model_unavailable` | OpenRouter failed or timed out after one retry |

## POST /api/tailor

Builds the tailored resume and gap list (User Stories 2 and 3). `gaps` is added in Build 3; until
then the response has `resume_lines` and `resume` only. The UI calls it only after the
student chooses to continue from the start-date result (FR-008).

**Request**
```json
{
  "posting": "string, 100–20,000 chars",
  "master_resume": "string, 200–20,000 chars",
  "background_notes": "optional string, up to 20,000 chars (bullets or paragraphs about past roles)"
}
```

**200 Response**
```json
{
  "resume_lines": [ { "id": "L1", "text": "...", "section": "Experience", "source": "resume" },
                    { "id": "N1", "text": "...", "section": "Background notes", "source": "notes" } ],
  "resume": {
    "sections": [
      { "heading": "Experience",
        "entries": [
          { "header_line_ids": ["L4", "L5"],
            "bullets": [
              { "id": "B1", "text": "Grew regional revenue 12% by ...",
                "source_line_ids": ["L6"], "status": "traced", "flag_reason": null,
                "included": true, "edited": false }
            ] } ] } ],
    "plain_text": "Experience\nAssociate, Acme Corp | New York, NY | Jun 2022 – Jul 2025\n- Grew regional revenue 12% by ...\n"
  },
  "gaps": {
    "required": [ { "text": "CPA", "quote": "CPA required", "group": "required", "note": null } ],
    "preferred": [ { "text": "Python", "quote": "Python a plus", "group": "preferred", "note": null } ],
    "none_found": false
  }
}
```

**Errors**: same format. `resume_too_short` / `resume_too_long`, `posting_too_short` /
`posting_too_long`, `not_a_posting`, `not_english`, `model_unavailable`.

## POST /api/verify-bullet

Re-checks one bullet after the student edits it (FR-012b).

**Request**
```json
{
  "bullet_text": "string, 1–600 chars",
  "master_resume": "string, 200–20,000 chars",
  "background_notes": "optional, same as /api/tailor",
  "posting": "string, 100–20,000 chars",
  "source_line_ids": ["L6"]
}
```

`source_line_ids` is the bullet's previous citation. The server may add or replace lines if the
edit now matches others better, but only lines that exist count.

**200 Response**
```json
{ "status": "flagged", "source_line_ids": ["L6"],
  "flag_reason": "Team size \"8\" isn't in your master resume" }
```

## Server-side guarantees

These hold for every response, whatever the model returns:

1. Every `quote` in `mentions` and `gaps` is an exact substring of the submitted posting
   (whitespace collapsed).
2. `verdict` is computed by the rules in data-model.md, never taken from model text.
3. A bullet has `status: "traced"` only if all four checks in research.md §R6 pass.
4. Every bullet with `status: "flagged"` has `included: false` in `/api/tailor` responses.
5. `plain_text` contains only included bullets. Its only characters are printable ASCII and
   newlines, plus `–` in date ranges. Bullets start with `- `.
6. If model output can't be parsed or fails validation, the server retries once. It then returns
   `model_unavailable` instead of passing on partial or unchecked output.
7. Request bodies are never logged or stored.

## Browser storage contract

| Key | Value | Written when | Removed when |
|---|---|---|---|
| `truefit.v1` | `{ "masterResume": string, "availabilityText": string, "savedAt": ISO datetime }` | Student clicks "Save on this device", or changes availability | Student clicks "Clear saved resume" |

No other keys are used, and postings are never stored.
