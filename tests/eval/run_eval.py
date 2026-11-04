"""Model evals with real API calls (costs money). Not part of `uv run pytest`.

Usage:
    uv run python tests/eval/run_eval.py --suite start_date
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.errors import ApiError, ModelUnavailable  # noqa: E402
from app.start_date import check_start_date  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "cases"


def load_cases(suite: str) -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text())) for p in sorted((CASES_DIR / suite).glob("*.json"))]


async def run_start_date() -> bool:
    """SC-002: verdict matches expected in >= 90% of cases, and never a date for a posting that states none."""
    cases = load_cases("start_date")
    agreed = 0
    invented = []
    print(f"{'case':32} {'expected':24} {'got':24} ok")
    for name, case in cases:
        try:
            result = (await check_start_date(case["posting"], case.get("availability_text"))).to_dict()
            got = result["verdict"]
        except (ApiError, ModelUnavailable) as exc:
            result, got = None, f"error:{getattr(exc, 'code', 'model_unavailable')}"
        ok = got == case["expected_verdict"]
        agreed += ok
        if case["expected_verdict"] == "not_stated" and result and result["mentions"]:
            invented.append(name)
        print(f"{name:32} {case['expected_verdict']:24} {got:24} {'✓' if ok else '✗'}")
        if result and not ok:
            for m in result["mentions"]:
                print(f"{'':32}   quote: {m['quote']!r} → {m['verdict']}")

    total = len(cases)
    print(f"\nAgreement: {agreed}/{total} ({agreed / total:.0%}); target ≥ 90%")
    print(f"Dates returned for postings with no start date: {len(invented)} {invented or ''}; target 0")
    return agreed / total >= 0.9 and not invented


SUITES = {"start_date": run_start_date}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=SUITES, default="start_date")
    args = parser.parse_args()
    passed = asyncio.run(SUITES[args.suite]())
    print("PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
