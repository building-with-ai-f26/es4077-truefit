"""Model evals with real API calls (costs money). Not part of `uv run pytest`.

Usage:
    uv run python tests/eval/run_eval.py --suite start_date
    uv run python tests/eval/run_eval.py --suite tailor
    uv run python tests/eval/run_eval.py --suite tailor --cases 13 16   # only these cases, by number
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.errors import ApiError, ModelUnavailable  # noqa: E402
from app import llm  # noqa: E402
from app.resume_lines import split_lines  # noqa: E402
from app.start_date import check_start_date  # noqa: E402
from app.tailor import tailor_resume  # noqa: E402
from app.trace_check import GENERIC_JOB_WORDS, _stem, extract_numbers, posting_only_terms  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "cases"


def load_cases(suite: str, only: list[str] | None = None) -> list[tuple[str, dict]]:
    paths = sorted((CASES_DIR / suite).glob("*.json"))
    if only:
        paths = [p for p in paths if p.stem.split("_")[0].lstrip("0") in {n.lstrip("0") for n in only}]
        if not paths:
            sys.exit(f"No {suite} cases numbered {', '.join(only)}")
    return [(p.stem, json.loads(p.read_text())) for p in paths]


async def run_start_date(only: list[str] | None = None) -> bool:
    """SC-002: verdict (and undergrad warning) match expected in >= 90% of cases, and never a date for a posting that states none.
    Cases with "expected_requirements" also score degree (verdict), work authorization (stance), and years
    of experience ("required:5" / "preferred:2"):
    each row must match in >= 90% of checks, and never a quoted requirement the posting doesn't state."""
    meter = CostMeter()
    llm._transport = meter
    cases = load_cases("start_date", only)
    agreed = 0
    invented = []
    req_checks = req_agreed = 0
    invented_reqs = []
    print(f"{'case':36} {'expected':24} {'got':24} ok")
    for name, case in cases:
        try:
            result = (await check_start_date(case["posting"], case.get("availability_text"))).to_dict()
            got = result["verdict"]
        except (ApiError, ModelUnavailable) as exc:
            result, got = None, f"error:{getattr(exc, 'code', 'model_unavailable')}"
        warned = bool(result and result["undergrad_warning"])
        ok = got == case["expected_verdict"] and warned == case.get("expected_undergrad_warning", False)
        agreed += ok
        if case["expected_verdict"] in ("not_stated", "likely_too_early") and result and result["mentions"]:
            invented.append(name)
        print(f"{name:36} {case['expected_verdict']:24} {got:24} {'✓' if ok else '✗'}{'  (undergrad warning)' if warned else ''}")
        if result and not ok:
            for m in result["mentions"]:
                print(f"{'':36}   quote: {m['quote']!r} → {m['verdict']}")
        rows = {r["requirement"]: r for r in result["requirements"]} if result else {}
        for key, expected in case.get("expected_requirements", {}).items():
            row = rows.get(key, {})
            req_checks += 1
            got_req = row.get("detail") or row.get("verdict", "missing")  # information-only rows report what they found
            req_ok = got_req == expected
            req_agreed += req_ok
            if expected == "not_stated" and row.get("quote"):
                invented_reqs.append(f"{name}:{key}")
            print(f"{'':36}   {key:22} {expected:20} {got_req:20} {'✓' if req_ok else '✗'}"
                  + (f"  quote: {row['quote']!r}" if row.get("quote") and not req_ok else ""))

    total = len(cases)
    print(f"\nAgreement: {agreed}/{total} ({agreed / total:.0%}); target ≥ 90%")
    print(f"Dates returned for postings with no start date: {len(invented)} {invented or ''}; target 0")
    req_rate = req_agreed / req_checks if req_checks else 1
    print(f"Requirement agreement: {req_agreed}/{req_checks} ({req_rate:.0%}); target ≥ 90%")
    print(f"Requirements quoted that the posting doesn't state: {len(invented_reqs)} {invented_reqs or ''}; target 0")
    print(f"Cost: ${meter.cost:.4f} total, ${meter.cost / total:.4f} per check")
    return agreed / total >= 0.9 and not invented and req_rate >= 0.9 and not invented_reqs


class CostMeter(httpx.AsyncHTTPTransport):
    """Adds up the cost OpenRouter reports in each response's usage block."""

    def __init__(self):
        super().__init__()
        self.cost = 0.0

    async def handle_async_request(self, request):
        response = await super().handle_async_request(request)
        await response.aread()
        try:
            self.cost += float(json.loads(response.content).get("usage", {}).get("cost") or 0)
        except ValueError:
            pass
        return response


async def run_tailor(only: list[str] | None = None) -> bool:
    """SC-003: no kept bullet with a number or posting-only word missing from its sources, and none claiming an expected gap."""
    meter = CostMeter()
    llm._transport = meter
    cases = load_cases("tailor", only)
    violations, flagged_for_review, seconds, gap_scores = [], [], [], []
    print(f"{'case':30} {'bullets':>7} {'kept':>5} {'flagged':>8} {'cost':>7} {'time':>6}")
    for name, case in cases:
        lines = split_lines(case["master_resume"], case.get("background_notes"))
        by_id = {line.id: line for line in lines}
        only = posting_only_terms(case["posting"], " ".join(line.text for line in lines))
        gap_terms = [t.lower() for group in case.get("expected_gaps", {}).values() for t in group]
        before, started = meter.cost, time.time()
        try:
            result = await tailor_resume(case["posting"], case["master_resume"], case.get("background_notes"))
        except (ApiError, ModelUnavailable) as exc:
            print(f"{name:30} error:{getattr(exc, 'code', 'model_unavailable')}")
            violations.append(f"{name}: no result")
            continue
        seconds.append(time.time() - started)
        bullets = [b for s in result["resume"]["sections"] for e in s["entries"] for b in e["bullets"]]
        kept = [b for b in bullets if b["included"]]
        for b in kept:
            cited = " ".join(by_id[i].text for i in b["source_line_ids"] if i in by_id)
            if not extract_numbers(b["text"]) <= extract_numbers(cited):
                violations.append(f"{name} {b['id']}: number not in sources: {b['text']!r}")
            words = {w.strip(".,;:()").lower() for w in b["text"].split()}
            if any(_stem(w) in only for w in words if w not in GENERIC_JOB_WORDS):
                violations.append(f"{name} {b['id']}: posting-only word: {b['text']!r}")
            for term in gap_terms:
                if term in b["text"].lower():
                    violations.append(f"{name} {b['id']}: claims a gap ({term}): {b['text']!r}")
            for phrase in case.get("forbidden_claims", []):
                if phrase in b["text"].lower():
                    violations.append(f"{name} {b['id']}: forbidden claim ({phrase}): {b['text']!r}")
        flagged = [b for b in bullets if b["status"] == "flagged"]
        flagged_for_review += [(name, b) for b in flagged]
        gap_score = score_gaps(case.get("expected_gaps", {}), result["gaps"])
        for term in case.get("not_gaps", []):  # requirements the student's lines do back, e.g. related industry work
            for g in result["gaps"]["required"] + result["gaps"]["preferred"]:
                if term in g["text"].lower() or term in g["quote"].lower():
                    violations.append(f"{name}: listed as a gap but the student's lines back it ({term}): {g['text']!r}")
        gap_scores.append((name, gap_score))
        print(f"{name:30} {len(bullets):7} {len(kept):5} {len(flagged):8} ${meter.cost - before:6.4f} {seconds[-1]:5.1f}s "
              f"gaps {gap_score['found']}/{gap_score['expected']}")

    total = len(cases)
    print(f"\nCost: ${meter.cost:.4f} total, ${meter.cost / total:.4f} per tailoring run; "
          f"avg {sum(seconds) / max(len(seconds), 1):.1f}s")
    print(f"Violations (target 0): {len(violations)}")
    for v in violations:
        print("  " + v)
    print(f"\nFlagged bullets to review by hand (false flag = a fair rewording you'd accept): {len(flagged_for_review)}")
    for name, b in flagged_for_review:
        print(f"  {name} {b['id']}: {b['text']!r}\n      reason: {b['flag_reason']}")

    # SC-005: the gap list catches at least 80% of expected gaps and groups at least 90% of those correctly.
    expected = sum(s["expected"] for _, s in gap_scores)
    found = sum(s["found"] for _, s in gap_scores)
    same_group = sum(s["same_group"] for _, s in gap_scores)
    recall = found / expected if expected else 1.0
    agreement = same_group / found if found else 1.0
    print(f"\nGap recall (target 80%): {found}/{expected} = {recall:.0%}")
    print(f"Gap grouping agreement (target 90%): {same_group}/{found} = {agreement:.0%}")
    for name, s in gap_scores:
        for term in s["missed"]:
            print(f"  {name}: missed expected gap {term!r}")
        for term, wanted, got in s["wrong_group"]:
            print(f"  {name}: {term!r} grouped {got}, expected {wanted}")
        for text in s["extra"]:
            print(f"  {name}: extra gap to review by hand: {text!r}")
    return not violations and recall >= 0.8 and agreement >= 0.9


def score_gaps(expected: dict, gaps: dict) -> dict:
    """Match each expected gap term to a gap TrueFit listed (by name or quote) and compare their groups."""
    listed = [(g, group) for group in ("required", "preferred") for g in gaps[group]]
    matches = lambda term, g: term in g["text"].lower() or term in g["quote"].lower() or g["text"].lower() in term
    score = {"expected": 0, "found": 0, "same_group": 0, "missed": [], "wrong_group": [], "extra": []}
    used = set()
    for wanted, terms in expected.items():
        for term in terms:
            score["expected"] += 1
            hit = next(((i, group) for i, (g, group) in enumerate(listed) if matches(term.lower(), g)), None)
            if hit is None:
                score["missed"].append(term)
                continue
            used.add(hit[0])
            score["found"] += 1
            if hit[1] == wanted:
                score["same_group"] += 1
            else:
                score["wrong_group"].append((term, wanted, hit[1]))
    score["extra"] = [g["text"] for i, (g, _) in enumerate(listed) if i not in used]
    return score


SUITES = {"start_date": run_start_date, "tailor": run_tailor}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=SUITES, default="start_date")
    parser.add_argument("--cases", nargs="+", metavar="N", help="run only these case numbers, e.g. --cases 13 16")
    args = parser.parse_args()
    passed = asyncio.run(SUITES[args.suite](args.cases))
    print("PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
