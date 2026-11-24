"""Model evals with real API calls (costs money). Not part of `uv run pytest`.

Usage:
    uv run python tests/eval/run_eval.py --suite start_date
    uv run python tests/eval/run_eval.py --suite tailor
    uv run python tests/eval/run_eval.py --suite tailor --cases 13 16   # only these cases, by number
    uv run python tests/eval/run_eval.py --suite build4 --label before  # Build 4 scorecard; saves outputs
    uv run python tests/eval/run_eval.py --suite build4 --label before --rescore  # rebuild scorecard.md from saved files (free)
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
        violations += truth_violations(name, case, kept, by_id, only, gap_terms)
        flagged = [b for b in bullets if b["status"] == "flagged"]
        flagged_for_review += [(name, b) for b in flagged]
        gap_score = score_gaps(case.get("expected_gaps", {}), result["gaps"])
        violations += not_gap_violations(name, case, result["gaps"])
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


def truth_violations(name: str, case: dict, kept: list[dict], by_id: dict, only: set, gap_terms: list[str]) -> list[str]:
    """Kept bullets with a number or posting-only word missing from their sources, or claiming a gap or forbidden phrase."""
    out = []
    for b in kept:
        cited = " ".join(by_id[i].text for i in b["source_line_ids"] if i in by_id)
        if not extract_numbers(b["text"]) <= extract_numbers(cited):
            out.append(f"{name} {b['id']}: number not in sources: {b['text']!r}")
        words = {w.strip(".,;:()").lower() for w in b["text"].split()}
        if any(_stem(w) in only for w in words if w not in GENERIC_JOB_WORDS):
            out.append(f"{name} {b['id']}: posting-only word: {b['text']!r}")
        for term in gap_terms:
            if term in b["text"].lower():
                out.append(f"{name} {b['id']}: claims a gap ({term}): {b['text']!r}")
        for phrase in case.get("forbidden_claims", []):
            if phrase in b["text"].lower():
                out.append(f"{name} {b['id']}: forbidden claim ({phrase}): {b['text']!r}")
    return out


def not_gap_violations(name: str, case: dict, gaps: dict) -> list[str]:
    """Requirements listed as gaps although the student's lines back them (case "not_gaps", e.g. related industry work)."""
    return [f"{name}: listed as a gap but the student's lines back it ({term}): {g['text']!r}"
            for term in case.get("not_gaps", [])
            for g in gaps["required"] + gaps["preferred"]
            if term in g["text"].lower() or term in g["quote"].lower()]


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


RESULTS_DIR = Path(__file__).resolve().parent / "results"
RULES = ("truthful", "start_date", "relevant", "honest_gaps")
HAND_READ_KINDS = {"adversarial"}  # rule 4 on these needs a read: did TrueFit answer clearly instead of tailoring?
STOP_NOTE = "the eligibility check stopped here, so the app never offers Tailor; no resume is the right answer"


def score_check_stop(record: dict, expected: str, got: str) -> None:
    """The check refused the input (e.g. not_a_posting). In the app, Tailor stays locked after that, so
    when the refusal is the expected answer, the case passes every rule: nothing was invented, and the
    student got a clear answer instead of a tailored resume."""
    if got == expected:
        record["scores"] = dict.fromkeys(RULES, 1)
        record["notes"].append(STOP_NOTE)
    else:
        record["notes"].append(f"the check stopped with {got!r}; the app would not offer Tailor")


async def run_build4(only: list[str] | None = None, label: str = "before") -> bool:
    """Build 4 (Track A) scorecard: 4 rules x 10 cases, see specs/2026-11-24-build4-eval-plan.md.
    Rules 1, 2 and 4 are scored here; rule 3 (relevant and specific) is left blank for scoring by hand.
    Every case's full output is saved to tests/eval/results/build4/<label>/ with a scorecard.md."""
    meter = CostMeter()
    llm._transport = meter
    cases = load_cases("build4", only)
    out_dir = RESULTS_DIR / "build4" / label
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"{'case':38} {'truthful':>8} {'date':>5} {'gaps':>5} {'cost':>7}  date verdict (expected → got)")
    for name, case in cases:
        before = meter.cost
        record = {"case": name, "kind": case.get("kind"), "label": label, "rubric_notes": case.get("rubric_notes", ""),
                  "notes": [], "scores": dict.fromkeys(RULES)}
        try:
            sd = (await check_start_date(case["posting"], case.get("availability_text"))).to_dict()
            got_verdict = sd["verdict"]
        except ApiError as exc:
            sd, got_verdict = None, exc.code  # a refusal the student sees, e.g. not_a_posting
        except ModelUnavailable:
            sd, got_verdict = None, "error:model_unavailable"
        record["start_date"] = sd
        record["start_date_got"] = got_verdict
        record["scores"]["start_date"] = int(got_verdict == case["expected_verdict"])
        record["notes"].append(f"start date: expected {case['expected_verdict']}, got {got_verdict}")
        if sd is None:
            # Like the app: no check result, no Tailor button. Don't tailor or pay for it.
            score_check_stop(record, case["expected_verdict"], got_verdict)
            record["tailor"] = None
            finish_case(record, meter.cost - before, out_dir, rows, case, got_verdict)
            continue

        lines = split_lines(case["master_resume"], case.get("background_notes"))
        by_id = {line.id: line for line in lines}
        posting_only = posting_only_terms(case["posting"], " ".join(line.text for line in lines))
        gap_terms = [t.lower() for group in case.get("expected_gaps", {}).values() for t in group]
        try:
            result = await tailor_resume(case["posting"], case["master_resume"], case.get("background_notes"))
        except (ApiError, ModelUnavailable) as exc:
            result = None
            record["tailor_error"] = getattr(exc, "code", "model_unavailable")
        record["tailor"] = result
        if result is None:
            # No tailored resume. For a non-posting that may be the right answer; leave rules 1 and 4 to a read.
            record["notes"].append(f"tailoring returned no resume ({record['tailor_error']}); score rules 1 and 4 by hand")
        else:
            bullets = [b for s in result["resume"]["sections"] for e in s["entries"] for b in e["bullets"]]
            kept = [b for b in bullets if b["included"]]
            truth = truth_violations(name, case, kept, by_id, posting_only, gap_terms)
            record["scores"]["truthful"] = int(not truth)
            record["notes"] += truth
            flagged = [b for b in bullets if b["status"] == "flagged"]
            record["notes"] += [f"flagged (read by hand): {b['id']} {b['text']!r}: {b['flag_reason']}" for b in flagged]

            gap_score = score_gaps(case.get("expected_gaps", {}), result["gaps"])
            wrong_gaps = not_gap_violations(name, case, result["gaps"])
            gaps_ok = (gap_score["found"] == gap_score["expected"] == gap_score["same_group"]) and not wrong_gaps
            record["notes"] += wrong_gaps
            record["notes"] += [f"missed expected gap {t!r}" for t in gap_score["missed"]]
            record["notes"] += [f"{t!r} grouped {got}, expected {want}" for t, want, got in gap_score["wrong_group"]]
            record["notes"] += [f"extra gap (read by hand): {t!r}" for t in gap_score["extra"]]
            if case.get("kind") in HAND_READ_KINDS:
                record["notes"].append(f"rule 4 script check {'passed' if gaps_ok else 'failed'}; "
                                       "confirm by reading the output (bad input should get a clear answer)")
            else:
                record["scores"]["honest_gaps"] = int(gaps_ok)
        finish_case(record, meter.cost - before, out_dir, rows, case, got_verdict)

    print(f"\nCost this run: ${meter.cost:.4f}")
    write_scorecard(out_dir, label)
    return True  # a scorecard, not a pass/fail gate


def finish_case(record: dict, cost: float, out_dir: Path, rows: list, case: dict, got_verdict: str) -> None:
    record["cost"] = round(cost, 4)
    (out_dir / f"{record['case']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    rows.append(record)
    sc = record["scores"]
    mark = lambda v: "-" if v is None else ("✓" if v else "✗")
    print(f"{record['case']:38} {mark(sc['truthful']):>8} {mark(sc['start_date']):>5} {mark(sc['honest_gaps']):>5} "
          f"${record['cost']:6.4f}  {case['expected_verdict']} → {got_verdict}")


def rescore_build4(label: str) -> None:
    """Re-apply the check-stop rule to saved results (no model calls), then rebuild scorecard.md.
    Hand scores typed into a case's JSON "scores" are kept. Results saved before Nov 25 recorded a
    refusal as "error:<code>"; those are read as the code the student saw."""
    out_dir = RESULTS_DIR / "build4" / label
    for path in sorted(out_dir.glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("start_date") is None and "start_date_got" not in record:
            got = next(n.split("got ", 1)[1] for n in record["notes"] if n.startswith("start date:"))
            got = got if got == "error:model_unavailable" else got.removeprefix("error:")
            expected = next(n for n in record["notes"] if n.startswith("start date:")).split("expected ")[1].split(",")[0]
            record["start_date_got"] = got
            record["notes"] = [f"start date: expected {expected}, got {got}"] + [
                n for n in record["notes"] if not n.startswith(("start date:", "rule 4 script check"))]
            record["scores"]["start_date"] = int(got == expected)
            score_check_stop(record, expected, got)
            if record.get("tailor") is not None:
                record["notes"].append("the saved tailored resume came from an old script that tailored anyway; "
                                       "the app would not, so it isn't scored")
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    write_scorecard(out_dir, label)


def write_scorecard(out_dir: Path, label: str) -> None:
    """A Markdown table built from every saved case JSON in out_dir (so a --cases re-run merges in).
    Blank cells are rule 3 and anything the script couldn't decide; fill them in the JSON "scores" and
    run --rescore. The Total appears once a row has no blanks."""
    rows = [json.loads(p.read_text()) for p in sorted(out_dir.glob("*.json"))]
    cost = sum(r.get("cost", 0) for r in rows)
    cell = lambda v: " " if v is None else str(v)
    total = lambda sc: str(sum(sc.values())) if None not in sc.values() else ""
    lines = [f"# Build 4 scorecard: {label}", "",
             f"Updated {time.strftime('%Y-%m-%d %H:%M')}; model cost ${cost:.4f}. "
             "1 = pass, 0 = fail, blank = score by hand (see each case's JSON for outputs and notes).", "",
             "| Case | Kind | 1 Truthful | 2 Start date | 3 Relevant | 4 Honest | Total |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        sc = r["scores"]
        lines.append(f"| {r['case']} | {r['kind']} | " + " | ".join(cell(sc[k]) for k in RULES) + f" | {total(sc)} |")
    lines += ["", "## Notes from the script", ""]
    for r in rows:
        lines.append(f"**{r['case']}**: {r['rubric_notes']}")
        lines += [f"- {n}" for n in r["notes"]] + [""]
    done = [r for r in rows if None not in r["scores"].values()]
    if len(done) == len(rows):
        lines[2:2] = [f"**Total: {sum(sum(r['scores'].values()) for r in rows)}/{len(rows) * len(RULES)}**", ""]
    (out_dir / "scorecard.md").write_text("\n".join(lines))
    scored = sum(v for r in rows for v in r["scores"].values() if v is not None)
    open_cells = sum(v is None for r in rows for v in r["scores"].values())
    print(f"Scored so far: {scored}/{len(rows) * len(RULES)}; {open_cells} cells left to score by hand")
    print(f"Saved: {out_dir}/ (scorecard.md + one JSON per case)")


SUITES = {"start_date": run_start_date, "tailor": run_tailor, "build4": run_build4}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", choices=SUITES, default="start_date")
    parser.add_argument("--cases", nargs="+", metavar="N", help="run only these case numbers, e.g. --cases 13 16")
    parser.add_argument("--label", default="before", help="build4 only: results folder name, e.g. before or after")
    parser.add_argument("--rescore", action="store_true",
                        help="build4 only: rebuild scorecard.md from saved results, no model calls")
    args = parser.parse_args()
    if args.rescore:
        rescore_build4(args.label)
        return
    run = SUITES[args.suite]
    passed = asyncio.run(run(args.cases, args.label) if args.suite == "build4" else run(args.cases))
    print("PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
