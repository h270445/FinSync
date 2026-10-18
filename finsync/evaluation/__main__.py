"""Matching evaluation: `python -m finsync.evaluation [--out docs/evaluation/results/<date>-matching.md]`.

Sweeps the auto-link threshold on the dev split, picks one, and reports the test split at that
threshold in arrival and reverse order, next to the store-every-row baseline.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
from typing import Sequence

from finsync.evaluation.generate import Row, read_csv
from finsync.evaluation.runner import ORDERS, SWEEP, Result, choose_threshold, run_baseline, run_matcher
from finsync.matching import decision as decision_rules

DATASET = Path("tests/data/matching_eval.csv")


def evaluate(rows: Sequence[Row], dataset: Path) -> str:
    """The whole report as Markdown."""
    by_split = {split: [row for row in rows if row.split == split] for split in ("dev", "test")}
    sweep = [run_matcher(by_split["dev"], "dev", "arrival", threshold) for threshold in SWEEP]
    chosen = choose_threshold(sweep)
    threshold = float(chosen.system.rsplit("@", 1)[1])
    test = [run_baseline(by_split["test"], "test")]
    test += [run_matcher(by_split["test"], "test", order, threshold) for order in ORDERS]
    labels = {row.record_id: row for row in rows}

    lines = [
        "# Matching evaluation",
        "",
        f"- Code: commit `{_commit()}`, matcher `{decision_rules.MATCHER_VERSION}`",
        f"- Command: `python -m finsync.evaluation --dataset {dataset.as_posix()}`",
        f"- Dataset: `{dataset.as_posix()}` (sha256 `{_sha256(dataset)[:12]}`), {len(rows)} records, "
        f"dev {len(by_split['dev'])}, test {len(by_split['test'])}",
        f"- Fixed: review threshold {decision_rules.REVIEW_THRESHOLD:.2f}, "
        f"runner-up margin {decision_rules.RUNNER_UP_MARGIN:.2f}",
        "",
        "Metric definitions are in [evaluation-plan.md](../evaluation-plan.md#1-transaction-matching). "
        "*Double counted* is the number of purchases that appear as more than one expense; "
        "a false merge hides a purchase inside another one's event and is listed separately below.",
        "",
        "## 1. Auto-link threshold sweep (dev split, arrival order)",
        "",
        *_table(sweep),
        "",
        f"Chosen: **{threshold:.2f}** (fewest false merges, then highest recall, then lowest review rate; "
        "ties go to the higher threshold). The test split was not used for this choice.",
        "",
        f"## 2. Test split at {threshold:.2f}",
        "",
        *_table(test),
        "",
        "`reverse` replays the same records from the last arrival to the first, to show how much the "
        "result depends on arrival order.",
        "",
        "## 3. False merges",
        "",
    ]
    merges = [(result, merge) for result in [*sweep, *test[1:]] for merge in result.false_merges]
    if merges:
        lines += ["| Run | Records | Scenarios | Purchases | Outcome per record |", "| --- | --- | --- | --- | --- |"]
        lines += [
            f"| {_run(result)} | {', '.join(merge.record_ids)} | {', '.join(merge.scenarios)} | "
            f"{', '.join(merge.true_events)} | {', '.join(merge.outcomes)} |"
            for result, merge in merges
        ]
    else:
        lines.append("None.")
    lines += ["", f"## 4. Missed duplicates on the test split at {threshold:.2f}", ""]
    missed = [(result, pair) for result in test[1:] for pair in result.missed]
    if missed:
        lines += ["| Order | Records | Scenario | Outcome per record |", "| --- | --- | --- | --- |"]
        lines += [
            f"| {result.order} | {left}, {right} | {labels[left].scenario} | "
            f"{result.outcomes.get(left, '')}, {result.outcomes.get(right, '')} |"
            for result, (left, right) in missed
        ]
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def _table(results: Sequence[Result]) -> list[str]:
    rows = [
        "| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | "
        "Events (true) | Double counted |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        rows.append(
            f"| {result.system} | {result.order} | {_pct(result.precision)} | {_pct(result.recall)} | "
            f"{len(result.false_merges)} | {_pct(result.false_merge_rate)} | {_pct(result.missed_rate)} | "
            f"{_pct(result.review_rate)} | {result.predicted_events} ({result.true_events}) | {result.double_counted} |"
        )
    return rows


def _run(result: Result) -> str:
    return f"{result.system}, {result.split}, {result.order}"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "describe", "--always", "--dirty"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate transaction matching on the labelled dataset.")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--out", type=Path, help="write the report here instead of printing it")
    args = parser.parse_args()
    report = evaluate(read_csv(args.dataset), args.dataset)
    if args.out is None:
        print(report, end="")
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
