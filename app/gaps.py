"""Gap list (User Story 3): what the posting asks for that the student's own lines don't back up.

The model only lists the posting's requirements, quotes each one, and says which lines (if any) back it.
Python checks every quote and line ID, groups the gaps (unlabeled counts as Required), and writes each
gap's note, so the model never decides on its own what the student can or can't claim.

The required/preferred wording guide and the gap notes are adapted from the job-description-analyzer
skill (Paramchoudhary/ResumeSkills, MIT). Its match score and red-flag scan are left out on purpose.
"""

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
  - "other": anything else.
- "supported" is true only if a numbered line shows the student has it; list those lines in "line_ids". Goals and interests ("I'm eager to learn SQL") are NOT support.
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
            "group": group,
            "note": _note(kind, group),
            "related_line_ids": [i for i in _ids(raw.get("related_line_ids")) if i in evidence][:2],
        })
    return {**gaps, "none_found": not gaps["required"] and not gaps["preferred"]}


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
