"""Tailored resume (User Story 2).

The model only selects, reorders, and rewords the student's numbered lines, citing them for every bullet.
Python then checks each bullet (trace_check) and renders the copy-ready text (plain_text).
"""


from app import llm
from app.errors import ModelUnavailable
from app.plain_text import render_plain_text
from app.resume_lines import split_lines
from app.trace_check import check_bullets

TAILOR_PROMPT = """You tailor a student's resume to a job posting. Reply with one JSON object only.

You get the student's material as numbered lines: L-lines are their master resume; N-lines are other things they wrote about their experience, such as notes, past cover letters, behavioral (STAR) stories, or application essays.

Shape:
{"sections": [{"heading": "Experience", "entries": [{"header_line_ids": ["L4", "L5"], "bullets": [{"text": "...", "source_line_ids": ["L6"]}]}]}]}

Rules:
- Use ONLY facts in the numbered lines. Never add employers, titles, dates, schools, degrees, skills, tools, certifications, team sizes, or results that aren't there.
- You may select, reorder, shorten, and reword. Keep every number, percentage, dollar amount, and date exactly as written.
- Never use a skill, tool, or keyword from the posting unless the student's lines contain it.
- Every bullet cites ALL the line IDs that back it in "source_line_ids". If a bullet combines facts from several sentences, cite each one. When a bullet credits the student with a result, also cite the line showing the student's own action that led to it. N-lines may be used to write or strengthen bullets for a role.
- From N-lines, use only statements of what the student did, achieved, or has. Ignore goals, interests, things they hope, plan, or are eager to do or learn, opinions, and anything praising or describing a company they were applying to. "I'm eager to build my SQL skills" is NOT evidence of SQL.
- Keep the student's role accurate: if a story says a manager or someone else led something and the student supported it, the bullet must say the student supported or contributed, not led.
- header_line_ids are the lines that name the role, school, or organization (title, company, location, dates), copied by ID, not rewritten.
- Sections in this order: Education, Experience, then any others in the order they appear in the master resume. Use the student's own heading names.
- Pick the experience most relevant to the posting and aim for about one page: 3-5 bullets for recent or relevant roles, fewer for others.
- Bullets are one sentence, start with a strong verb that doesn't overstate the source, and contain no bullet symbol. No first-person words (I, my, me, we, our): write "the go-to-market plan led by the manager", not "led by my manager"."""


async def tailor_resume(posting: str, master_resume: str, background_notes: str | None = None) -> dict:
    lines = split_lines(master_resume, background_notes)
    numbered = "\n".join(f"{line.id}: {line.text}" for line in lines)
    reply = await llm.call(TAILOR_PROMPT, f"Job posting:\n<<<\n{posting}\n>>>\n\nStudent's numbered lines:\n<<<\n{numbered}\n>>>")

    sections = _validate(reply, {line.id for line in lines})
    bullets, context = [], {}
    for entry in (e for s in sections for e in s["entries"]):
        for bullet in entry["bullets"]:
            bullet["id"] = f"B{len(bullets) + 1}"
            context[bullet["id"]] = entry["header_line_ids"]
            bullets.append(bullet)
    await check_bullets(bullets, lines, posting, context)
    for bullet in bullets:
        bullet["included"] = bullet["status"] == "traced"  # flagged bullets start excluded (FR-012)
        bullet["edited"] = False

    lines_by_id = {line.id: line for line in lines}
    return {
        "resume_lines": [line.to_dict() for line in lines],
        "resume": {"sections": sections, "plain_text": render_plain_text(sections, lines_by_id)},
    }


async def verify_bullet(text: str, source_line_ids: list[str], posting: str, master_resume: str,
                        background_notes: str | None = None, header_line_ids: list[str] | None = None) -> dict:
    """Re-check one edited bullet (FR-012b) with the same four checks."""
    lines = split_lines(master_resume, background_notes)
    bullet = {"id": "B1", "text": text, "source_line_ids": [i for i in source_line_ids if isinstance(i, str)]}
    await check_bullets([bullet], lines, posting, {"B1": header_line_ids or []})
    return {"status": bullet["status"], "source_line_ids": bullet["source_line_ids"], "flag_reason": bullet["flag_reason"]}


def _validate(reply: dict, line_ids: set[str]) -> list[dict]:
    """Keep only well-formed sections, entries, and bullets. Unknown header IDs are dropped; bullet IDs are checked later."""
    sections = []
    for raw_section in reply.get("sections") or []:
        if not isinstance(raw_section, dict) or not isinstance(raw_section.get("heading"), str):
            continue
        entries = []
        for raw_entry in raw_section.get("entries") or []:
            if not isinstance(raw_entry, dict):
                continue
            headers = [i for i in raw_entry.get("header_line_ids") or [] if i in line_ids]
            bullets = [
                {"text": b["text"].strip(), "source_line_ids": [i for i in b.get("source_line_ids") or [] if isinstance(i, str)]}
                for b in raw_entry.get("bullets") or []
                if isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"].strip()
            ]
            if headers or bullets:
                entries.append({"header_line_ids": headers, "bullets": bullets})
        if entries:
            sections.append({"heading": raw_section["heading"].strip(), "entries": entries})
    if not sections:
        raise ModelUnavailable()  # never return an empty or unchecked resume (contract guarantee 6)
    return sections
