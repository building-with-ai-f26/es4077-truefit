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
{"sections": [{"heading": "Experience", "entries": [{"header_line_ids": ["L4", "L5"], "header_fields": {"L4": {"organization": "...", "location": "...", "title": "...", "dates": "..."}}, "bullets": [{"text": "...", "source_line_ids": ["L6"]}]}]}]}

Rules:
- Use ONLY facts in the numbered lines. Never add employers, titles, dates, schools, degrees, skills, tools, certifications, team sizes, or results that aren't there.
- You may select, reorder, shorten, and reword. Keep every number, percentage, dollar amount, and date exactly as written.
- Never use a skill, tool, or keyword from the posting unless the student's lines contain it.
- Every bullet cites ALL the line IDs that back it in "source_line_ids". If a bullet combines facts from several sentences, cite each one. When a bullet credits the student with a result, also cite the line showing the student's own action that led to it. N-lines may be used to write or strengthen bullets for a role.
- From N-lines, use only statements of what the student did, achieved, or has. Ignore goals, interests, things they hope, plan, or are eager to do or learn, opinions, and anything praising or describing a company they were applying to. "I'm eager to build my SQL skills" is NOT evidence of SQL.
- Keep the student's role accurate: if a story says a manager or someone else led something and the student supported it, the bullet must say the student supported or contributed, not led.
- header_line_ids are the lines that name the role, school, or organization (title, company, location, dates), copied by ID, not rewritten. Lines marked (header) go in header_line_ids and NEVER become bullets; every entry lists its header lines.
- Bullet text never repeats a title, company, location, or dates; those show in the header.
- header_fields splits each header line into the parts it contains: organization (company or school), location, title (job title or degree), and dates. Copy each part character for character from that line, and leave out parts the line doesn't have.
- Put each entry in the section it sits under in the master resume (shown in [brackets]). Skip (contact) lines; TrueFit adds them at the top.
- Sections in this order: Education, Experience, then any others in the order they appear in the master resume. Use the student's own heading names.
- Pick the experience most relevant to the posting and aim for about one page: 3-5 bullets for recent or relevant roles, fewer for others.
- Bullets are one sentence, start with a strong verb that doesn't overstate the source, and contain no bullet symbol. No first-person words (I, my, me, we, our): write "the go-to-market plan led by the manager", not "led by my manager"."""


async def tailor_resume(posting: str, master_resume: str, background_notes: str | None = None) -> dict:
    lines = split_lines(master_resume, background_notes)
    numbered = "\n".join(_numbered(line) for line in lines)
    reply = await llm.call(TAILOR_PROMPT, f"Job posting:\n<<<\n{posting}\n>>>\n\nStudent's numbered lines:\n<<<\n{numbered}\n>>>")

    sections = _validate(reply, lines)
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


def _validate(reply: dict, lines: list) -> list[dict]:
    """Keep only well-formed sections, entries, and bullets. Unknown header IDs are dropped; bullet IDs are checked later."""
    # Only header lines belong in an entry's header: never contact lines, headings, or bullet lines.
    header_ok = {line.id for line in lines if line.kind == "header"}
    sections = []
    for raw_section in reply.get("sections") or []:
        if not isinstance(raw_section, dict) or not isinstance(raw_section.get("heading"), str):
            continue
        entries = []
        for raw_entry in raw_section.get("entries") or []:
            if not isinstance(raw_entry, dict):
                continue
            headers = [i for i in raw_entry.get("header_line_ids") or [] if i in header_ok]
            bullets = [
                {"text": b["text"].strip(), "source_line_ids": [i for i in b.get("source_line_ids") or [] if isinstance(i, str)]}
                for b in raw_entry.get("bullets") or []
                if isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"].strip()
            ]
            headers, bullets = _repair_headers(headers, bullets, lines)
            if headers or bullets:
                fields = _verified_fields(raw_entry.get("header_fields"), headers, lines)
                entries.append({"header_line_ids": headers, "header_fields": fields, "bullets": bullets})
        if entries:
            sections.append({"heading": raw_section["heading"].strip(), "entries": entries})
    if not sections:
        raise ModelUnavailable()  # never return an empty or unchecked resume (contract guarantee 6)
    return _regroup_by_master_section(sections, lines)


def _repair_headers(headers: list[str], bullets: list[dict], lines: list) -> tuple[list[str], list[dict]]:
    """Keep job titles, companies, and dates as the entry's header, never as bullets.

    A "bullet" that cites only header lines is moved back into the header. An entry with no header gets
    the nearest block of header lines above the first resume line its bullets cite (within its section).
    """
    by_id = {line.id: line for line in lines}
    order = {line.id: i for i, line in enumerate(lines)}
    is_header = lambda i: i in by_id and by_id[i].kind == "header"
    kept = []
    for bullet in bullets:
        ids = bullet["source_line_ids"]
        if ids and all(is_header(i) for i in ids):
            headers = headers + [i for i in ids if i not in headers]
        else:
            for i in headers:
                if is_header(i) and by_id[i].text in bullet["text"]:  # header text pasted into the bullet
                    bullet["text"] = bullet["text"].replace(by_id[i].text, "").strip(" ;,.-–—|")
            kept.append(bullet)

    if not headers:
        cited = min((order[i] for b in kept for i in b["source_line_ids"]
                     if i in by_id and by_id[i].source == "resume"), default=None)
        if cited is not None:
            above = []
            for line in reversed(lines[:cited]):
                if line.kind == "heading" or (above and line.kind != "header"):
                    break  # stop at the section heading, or at the top of the header block
                if line.kind == "header":
                    above.insert(0, line.id)
            headers = above
    return sorted(headers, key=lambda i: order.get(i, 0)), kept


def _numbered(line) -> str:
    tag = f" ({line.kind})" if line.kind in ("header", "contact") else ""
    where = f" [{line.section}]" if line.source == "resume" and line.section and line.kind != "heading" else ""
    return f"{line.id}{tag}{where}: {line.text}"


def _regroup_by_master_section(sections: list[dict], lines: list) -> list[dict]:
    """Each entry goes in the section its header sits under in the master resume, not wherever the model put it.

    Order: Education, Experience, then other sections in master-resume order; entries keep the model's order.
    """
    by_id = {line.id: line for line in lines}
    master_order = []
    for line in lines:
        if line.source == "resume" and line.section and line.section not in master_order:
            master_order.append(line.section)

    def home(entry, fallback):
        for i in entry["header_line_ids"] + [i for b in entry["bullets"] for i in b["source_line_ids"]]:
            line = by_id.get(i)
            if line and line.source == "resume" and line.section:
                return line.section
        return fallback

    grouped: dict[str, list[dict]] = {}
    for section in sections:
        for entry in section["entries"]:
            entries = grouped.setdefault(home(entry, section["heading"]), [])
            # Two entries for the same job (sharing a header line) become one, so its header prints once.
            same = next((e for e in entries if set(e["header_line_ids"]) & set(entry["header_line_ids"])), None)
            if same:
                order = {line.id: n for n, line in enumerate(lines)}
                same["header_line_ids"] = sorted(set(same["header_line_ids"]) | set(entry["header_line_ids"]), key=order.get)
                same["bullets"].extend(entry["bullets"])
                same["header_fields"] = {**entry.get("header_fields", {}), **same.get("header_fields", {})}
            else:
                entries.append(entry)

    def rank(name):
        key = name.lower()
        if key == "education":
            return (0, 0)
        if key in ("experience", "work experience", "professional experience", "employment"):
            return (1, 0)
        return (2, master_order.index(name) if name in master_order else len(master_order))

    return [{"heading": name, "entries": grouped[name]} for name in sorted(grouped, key=rank)]


FIELD_NAMES = ("organization", "location", "title", "dates")


def _verified_fields(raw, header_ids: list[str], lines: list) -> dict:
    """Keep a header line's parts only if each is copied word for word from that line and together they
    cover the whole line, so nothing is invented or dropped. Otherwise the line shows as written."""
    if not isinstance(raw, dict):
        return {}
    by_id = {line.id: line for line in lines}
    collapse = lambda t: " ".join(t.split())
    verified = {}
    for line_id in header_ids:
        parts = raw.get(line_id)
        if not isinstance(parts, dict):
            continue
        parts = {k: collapse(v) for k, v in parts.items() if k in FIELD_NAMES and isinstance(v, str) and v.strip()}
        rest = collapse(by_id[line_id].text)
        if not parts or not all(v in rest for v in parts.values()):
            continue
        for value in sorted(parts.values(), key=len, reverse=True):
            rest = rest.replace(value, " ", 1)
        if sum(c.isalnum() for c in rest) <= 2:  # only separators and punctuation are left over
            verified[line_id] = parts
    return verified
