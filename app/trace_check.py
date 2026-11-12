"""Checks every tailored bullet against the lines it cites (research.md §R6, Constitution I).

A bullet is traced only if all four checks pass:
1. every cited line exists;
2. every number in the bullet appears in the cited lines;
3. no skill or tool term that appears only in the posting (not in the student's material) is used;
4. a model support check agrees the cited lines back every claim. Any other posting word the bullet uses
   that isn't in the student's material is sent along as a word to verify, so the model checks it by meaning.
Checks 1-3 are plain Python, so invented metrics and skills are caught without trusting the model.
"""

import json
import re

from app import llm
from app.resume_lines import ResumeLine

_NUMBER = re.compile(r"\$?\d+(?:[.,]\d+)*(?:%|\+|[xkmb]\b)?", re.IGNORECASE)
_WORD = re.compile(r"[a-z][a-z0-9+#]*(?:[.\-/][a-z0-9+#]+)*")
_SUFFIXES = ("ations", "ation", "ments", "ment", "ings", "ing", "ers", "er", "ies", "ed", "es", "s", "ly", "al")

STOPWORDS = set("""
a about above after again against all also am an and any are as at be because been before being below between both
but by can could did do does doing down during each either etc few for from further had has have having he her here
hers him his how i if in into is it its itself just me more most my no nor not now of off on once only or other our
ours out over own per same she should so some such than that the their them then there these they this those through
to too under until up upon us very via was we were what when where which while who whom why will with within without
would you your yours
""".split())

# Words any job posting uses. They aren't claims of a specific skill, so reusing them is fine.
GENERIC_JOB_WORDS = set("""
ability able across analysis analytical analyze apply applicant applicants based benefits best build building business
candidate candidates career client clients collaborate collaboration communicate communication company complex
contribute core cross-functional culture customer customers data day decisions deliver demonstrated develop
development drive driven effective environment excellent execute experience expertise fast-paced focus functional
global goals great grow growth help high highly ideal impact including independently insights join key knowledge
lead leader leaders leadership leading learn level looking manage management manager meet mission new office
opportunities opportunity organization own ownership partner partners passion people plan plus position preferred
problem problems process processes product products program programs project projects proven qualifications quality
record related required requirements responsibilities responsible results role roles run senior skill skills solve
solutions stakeholders strategic strategy strong success successful support team teams thinking time tools track
understand understanding use using value various verbal well work working world written year years
""".split())


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if len(w) >= 3 and w not in STOPWORDS]


def extract_numbers(text: str) -> set[tuple[str, str]]:
    """Each number as (digits, unit): '$1.2M' → ('1.2', '$m'), '12%' → ('12', '%'), '1,200' → ('1200', '')."""
    found = set()
    for match in _NUMBER.finditer(text):
        token = match.group(0).lower()
        dollar = token.startswith("$")
        token = token.lstrip("$").rstrip("+")
        unit = token[-1] if token[-1] in "%xkmb" else ""
        core = (token[:-1] if unit else token).replace(",", "")
        found.add((core, ("$" if dollar else "") + unit))
    return found


_TERM = re.compile(r"[A-Za-z][A-Za-z0-9+#]*(?:[.\-/][A-Za-z0-9+#]+)*")
_STARTS_SENTENCE = set(".!?:;•●*-–—(\n")


def _starts_sentence(text: str, index: int) -> bool:
    i = index - 1
    while i >= 0 and text[i] in " \t":
        i -= 1
    return i < 0 or text[i] in _STARTS_SENTENCE


def skill_terms(posting: str) -> set[str]:
    """Words in the posting that name a skill, tool, or credential: acronyms (SQL, CFA), names with
    symbols or digits (C++, S3), and capitalized words mid-sentence (Tableau, Salesforce).

    Ordinary words ("shape", "drive") aren't treated as skills; the model support check judges those by meaning.
    """
    terms = set()
    for match in _TERM.finditer(posting):
        token = match.group(0)
        letters = [c for c in token if c.isalpha()]
        acronym = len(letters) >= 2 and all(c.isupper() for c in letters)
        technical = any(c in "+#" for c in token) or any(c.isdigit() for c in token)
        named = token[0].isupper() and not _starts_sentence(posting, match.start())
        if acronym or technical or named:
            terms.add(token.lower())
    return terms


def posting_only_terms(posting: str, source_text: str) -> set[str]:
    """Stems of the posting's skill and tool terms that never appear in the student's material."""
    source = {_stem(w) for w in _words(source_text)}
    terms = {w for w in _words(" ".join(skill_terms(posting))) if w not in GENERIC_JOB_WORDS}
    return {_stem(w) for w in terms} - source


def posting_words_to_verify(text: str, posting: str, source_text: str) -> list[str]:
    """Ordinary posting words in a bullet that never appear in the student's material ("shape", "forecasting").

    They aren't flagged outright, since they're often fair synonyms; the model support check verifies each one.
    """
    root = lambda w: _stem(w).rstrip("e")  # "shaped" and "shape" share a root
    source = {root(w) for w in _words(source_text)}
    posting_roots = {root(w) for w in _words(posting) if w not in GENERIC_JOB_WORDS}
    found = []
    for word in _words(text):
        if word not in GENERIC_JOB_WORDS and root(word) in posting_roots and root(word) not in source and word not in found:
            found.append(word)
    return found


def deterministic_check(text: str, cited_ids: list[str], lines_by_id: dict[str, ResumeLine],
                        posting_only: set[str], context_ids: list[str] = ()) -> str | None:
    """Checks 1-3. Returns the reason the bullet fails, or None if it passes.

    context_ids are the role's header lines (title, employer, dates); numbers in them, like years, may be reused.
    """
    if not cited_ids or any(line_id not in lines_by_id for line_id in cited_ids):
        return "Doesn't cite a line from your resume or notes"
    cited_text = " ".join(lines_by_id[i].text for i in [*cited_ids, *context_ids] if i in lines_by_id)
    cited_numbers = extract_numbers(cited_text)
    for match in _NUMBER.finditer(text):
        if not extract_numbers(match.group(0)) <= cited_numbers:
            return f'"{match.group(0)}" isn\'t in the cited lines'
    for word in _words(text):
        if word not in GENERIC_JOB_WORDS and _stem(word) in posting_only:
            return f'"{word}" is a skill or tool from the posting that isn\'t in your resume or notes'
    return None


SUPPORT_PROMPT = """You check tailored resume bullets against the student's own source lines. Reply with one JSON object only:
{"results": [{"bullet_id": "B1", "supported": true|false, "unsupported_claim": "..."|null}]}

Each bullet comes with its cited_lines and role_context: the header lines of the role it sits under (title, employer, location, dates). role_context may support the employer, title, location, and dates, but not actions or results.

Some bullets also list words_to_verify: words the bullet shares with the job posting that never appear in the student's material. Check each one closely. It's fine only if the cited lines say the same thing in other words ("shaped" for "designed and synthesized"). If it claims a skill, tool, method, credential, or experience the cited lines don't show ("forecasting", "underwriting", "machine learning"), the bullet is NOT supported and unsupported_claim names it.

A bullet is supported only if every fact in it (actions, scope, team sizes, tools, skills, results, numbers, employers, titles, dates) is stated in, or directly follows from, its cited lines.
- Rewording, shortening, and reordering are fine.
- A stronger verb is NOT fine if it adds scope or ownership (e.g., "helped with" → "led", "supported" → "managed").
- A line about goals, interests, or intentions ("I hope to", "I'm eager to learn", "I want to") or about an employer the student was applying to never supports a claim that the student did or has something.
- If unsupported, unsupported_claim names the specific claim in a few words, e.g. "Team size of 8" or "Led the project". Otherwise null.
Return one result for every bullet."""


async def support_check(items: list[dict]) -> dict[str, str | None]:
    """Check 4 for many bullets in one model call. Returns bullet_id → None if supported, else the unsupported claim."""
    if not items:
        return {}
    reply = await llm.call(SUPPORT_PROMPT, json.dumps({"bullets": items}, ensure_ascii=False))
    verdicts = {}
    for result in reply.get("results") or []:
        if isinstance(result, dict) and isinstance(result.get("bullet_id"), str):
            claim = result.get("unsupported_claim")
            verdicts[result["bullet_id"]] = None if result.get("supported") is True else (
                claim if isinstance(claim, str) and claim.strip() else "Not supported by the cited lines")
    return verdicts


async def check_bullets(bullets: list[dict], lines: list[ResumeLine], posting: str,
                        context: dict[str, list[str]] | None = None) -> None:
    """Set status and flag_reason on each bullet dict ({id, text, source_line_ids}) in place.

    context maps a bullet ID to the header line IDs of the role it sits under.
    """
    context = context or {}
    lines_by_id = {line.id: line for line in lines}
    source_text = " ".join(line.text for line in lines)
    posting_only = posting_only_terms(posting, source_text)

    to_model = []
    for bullet in bullets:
        headers = [i for i in context.get(bullet["id"], []) if i in lines_by_id]
        bullet["flag_reason"] = deterministic_check(bullet["text"], bullet["source_line_ids"], lines_by_id,
                                                    posting_only, headers)
        if bullet["flag_reason"] is None:
            item = {"bullet_id": bullet["id"], "text": bullet["text"],
                    "cited_lines": [{"id": i, "text": lines_by_id[i].text} for i in bullet["source_line_ids"]],
                    "role_context": [lines_by_id[i].text for i in headers]}
            watch = posting_words_to_verify(bullet["text"], posting, source_text)
            if watch:
                item["words_to_verify"] = watch
            to_model.append(item)

    verdicts = await support_check(to_model)
    for item in to_model:
        bullet = next(b for b in bullets if b["id"] == item["bullet_id"])
        if item["bullet_id"] not in verdicts:
            bullet["flag_reason"] = "Couldn't be checked; review it yourself"
        else:
            bullet["flag_reason"] = verdicts[item["bullet_id"]]

    for bullet in bullets:
        bullet["status"] = "traced" if bullet["flag_reason"] is None else "flagged"
