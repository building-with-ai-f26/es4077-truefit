"""Model evals with real API calls (costs money). Not part of `uv run pytest`.

Usage:
    uv run python tests/eval/run_eval.py --suite start_date
    uv run python tests/eval/run_eval.py --suite tailor
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


def load_cases(suite: str) -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text())) for p in sorted((CASES_DIR / suite).glob("*.json"))]


async def run_start_date() -> bool:
    """SC-002: verdict (and undergrad warning) match expected in >= 90% of cases, and never a date for a posting that states none.
    Cases with "expected_requirements" also score degree (verdict), work authorization (stance), and years
    of experience ("required:5" / "preferred:2"):
    each row must match in >= 90% of checks, and never a quoted requirement the posting doesn't state."""
    meter = CostMeter()
    llm._transport = meter
    cases = load_cases("start_date")
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


async def run_tailor() -> bool:
    """SC-003: no kept bullet with a number or posting-only word missing from its sources, and none claiming an expected gap."""
    meter = CostMeter()
    llm._transport = meter
    cases = load_cases("tailor")
    violations, flagged_for_review, seconds = [], [], []
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
        print(f"{name:30} {len(bullets):7} {len(kept):5} {len(flagged):8} ${meter.cost - before:6.4f} {seconds[-1]:5.1f}s")

    total = len(cases)
    print(f"\nCost: ${meter.cost:.4f} total, ${meter.cost / total:.4f} per tailoring run; "
          f"avg {sum(seconds) / max(len(seconds), 1):.1f}s")
    print(f"Violations (target 0): {len(violations)}")
    for v in violations:
        print("  " + v)
    print(f"\nFlagged bullets to review by hand (false flag = a fair rewording you'd accept): {len(flagged_for_review)}")
    for name, b in flagged_for_review:
        print(f"  {name} {b['id']}: {b['text']!r}\n      reason: {b['flag_reason']}")
    return not violations


SUITES = {"start_date": run_start_date, "tailor": run_tailor}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=SUITES, default="start_date")
    args = parser.parse_args()
    passed = asyncio.run(SUITES[args.suite]())
    print("PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
