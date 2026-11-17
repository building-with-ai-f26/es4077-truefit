"""Gap list (User Story 3): what the posting asks for that the student's own lines don't back up.

The model only lists the posting's requirements, quotes each one, and says which lines (if any) back it.
Python checks every quote and line ID, groups the gaps (unlabeled counts as Required), and writes each
gap's note, so the model never decides on its own what the student can or can't claim.

The required/preferred wording guide and the gap notes are adapted from the job-description-analyzer
skill (Paramchoudhary/ResumeSkills, MIT). Its match score and red-flag scan are left out on purpose.
"""

import re

from app import llm
from app.quotes import quote_in

GAPS_PROMPT = """You compare a job posting's requirements with a student's own lines. Reply with one JSON object only.

You get the posting and the student's material as numbered lines: L-lines are their master resume; N-lines are other things they wrote about their experience.

Shape:
{"requirements": [{"text": "CPA", "quote": "CPA required", "group": "required"|"preferred"|"unlabeled", "kind": "credential"|"tool_or_skill"|"experience"|"soft_skill"|"eligibility"|"other", "supported": true|false, "line_ids": ["L6"], "related_line_ids": ["L7"]}]}

Rules:
- List each qualification the posting asks candidates to have: credentials, tools, skills, and kinds of experience. Not the job's duties ("you'll build models"), and not facts about the company.
- "text" is a short name for it (2-5 words). "quote" is the posting's words for it, copied character for character.
- "group" comes from the posting's wording:
  - "required": "required", "must have", "you have", "you bring", "essential", "minimum qualifications", or listed under a Requirements or Qualifications heading.
  - "preferred": "preferred", "nice to have", "a plus", "bonus", "ideally", "desired", or listed under a Preferred heading.
  - "unlabeled": the posting doesn't say either way.
- "kind":
  - "credential": a license, certification, or clearance (CPA, CFA, PMP, security clearance).
  - "tool_or_skill": a specific tool, language, or hard skill (SQL, Python, Tableau, financial modeling).
  - "experience": a kind of work or industry experience (consumer goods, M&A, managing a team).
  - "soft_skill": communication, leadership, teamwork, curiosity, and other traits.
  - "eligibility": start date, degree or graduation timing, work authorization or sponsorship, years of experience, or location. TrueFit checks these separately.
  - When a years line also names a kind of experience ("6+ years of experience in B2B product management"), list that kind of experience as its own requirement with kind "experience", quoting only those words ("B2B product management"). The number of years stays "eligibility".
  - "other": anything else.
- "supported" is true only if a numbered line shows the student has it; list those lines in "line_ids". Goals and interests ("I'm eager to learn SQL") are NOT support.
- For industry or domain experience, work in that industry or on closely related products counts, the way a recruiter would read it: invoicing and billing work at a bank counts as payments or fintech experience; market sizing for consumer clients counts as consumer goods experience. Credentials, tools, and named skills stay strict: they count only if a line names them.
- If the student doesn't have it, "related_line_ids" lists up to two lines showing the closest related experience they do have, or [] if none.
- List each requirement once."""

KINDS_NOT_GAPS = {"soft_skill", "eligibility"}  # soft skills can't be traced to a line; eligibility has its own exhibit
NO_EVIDENCE_KINDS = {"heading", "contact"}

NOTE_CREDENTIAL_REQUIRED = "Often a dealbreaker: a license or certification you can't get quickly."
NOTE_CREDENTIAL_PREFERRED = "Preferred, so not having it usually won't rule you out."
NOTE_TOOL = "Usually something you can learn. If you've used something similar, say so."
NOTE_EXPERIENCE = "Your resume doesn't show this. If you have it, add it to your master resume."


async def build_gap_list(posting: str, lines: list, numbered: str) -> dict:
    reply = await llm.call(GAPS_PROMPT, f"Job posting:\n<<<\n{posting}\n>>>\n\nStudent's numbered lines:\n<<<\n{numbered}\n>>>")
    evidence = {line.id for line in lines if line.kind not in NO_EVIDENCE_KINDS}
    gaps, seen = {"required": [], "preferred": []}, set()
    for raw in reply.get("requirements") or []:
        if not isinstance(raw, dict):
            continue
        text, quote, kind = raw.get("text"), raw.get("quote"), raw.get("kind")
        if not isinstance(text, str) or not text.strip() or not isinstance(quote, str) or not quote_in(posting, quote):
            continue
        if kind in KINDS_NOT_GAPS or text.strip().lower() in seen:
            continue
        if raw.get("supported") is True and any(i in evidence for i in _ids(raw.get("line_ids"))):
            continue  # backed by the student's own lines
        seen.add(text.strip().lower())
        group = "preferred" if raw.get("group") == "preferred" else "required"  # unlabeled counts as Required (FR-016a)
        gaps[group].append({
            "text": text.strip(),
            "quote": quote,
            "posting_bullet": _posting_bullet(posting, quote),
            "group": group,
            "note": _note(kind, group),
            "related_line_ids": [i for i in _ids(raw.get("related_line_ids")) if i in evidence][:2],
        })
    return {**gaps, "none_found": not gaps["required"] and not gaps["preferred"]}


MAX_BULLET_CHARS = 400  # a "bullet" longer than this is a paragraph; show just the quote instead
BULLET_START = re.compile(r"^\s*(?:[-*•●▪◦·–—]|\d{1,2}[.)])\s+")
CARRIES_ON = re.compile(r"(?:[,&/(-]|\b(?:and|or|with|of|in|to|for|the|a|an))$", re.IGNORECASE)


def _posting_bullet(posting: str, quote: str) -> str:
    """The posting bullet the quote sits in, so gaps from the same bullet show together and can be found
    in the posting. Falls back to the quote for long paragraphs."""
    for bullet in _bullets(posting):
        if quote_in(bullet, quote):
            return bullet if len(bullet) <= MAX_BULLET_CHARS else quote
    return quote


def _bullets(posting: str) -> list[str]:
    """Rejoin bullets that wrap onto several lines (common when pasting from a PDF).

    A line continues the bullet above it if it's indented under a bullet, starts in lowercase, or the line
    above stops mid-sentence ("..., or"). A bullet mark, a blank line, or a heading ending in ":" starts anew.
    """
    blocks: list[list[str]] = []
    for raw in posting.splitlines():
        text = " ".join(raw.split())
        if not text:
            blocks.append([])
            continue
        current = blocks[-1] if blocks else []
        is_bullet = bool(BULLET_START.match(raw))
        carries_on = current and not current[-1].endswith(":") and not is_bullet and (
            (raw[:1].isspace() and BULLET_START.match(current[0]))
            or text[0].islower()
            or CARRIES_ON.search(current[-1]))
        if carries_on:
            current.append(text)
        else:
            blocks.append([BULLET_START.sub("", raw).strip() if is_bullet else text])
    return [" ".join(block) for block in blocks if block]


def _ids(raw) -> list[str]:
    return [i for i in raw if isinstance(i, str)] if isinstance(raw, list) else []


def _note(kind, group: str) -> str | None:
    if kind == "credential":
        return NOTE_CREDENTIAL_REQUIRED if group == "required" else NOTE_CREDENTIAL_PREFERRED
    if kind == "tool_or_skill":
        return NOTE_TOOL
    if kind == "experience":
        return NOTE_EXPERIENCE
    return None
