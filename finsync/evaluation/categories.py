"""Categorization evaluation: `python -m finsync.evaluation.categories [--out docs/evaluation/results/<date>-categorization-rules.md]`.

Runs the rule-based categorizer on the labelled dataset and reports accuracy per split, for clear and
ambiguous items and per scenario. The categorizer sees only the description and the merchant.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
from typing import Callable, Sequence

from finsync.categorization import categorize_transaction
from finsync.evaluation.generate_categories import CATEGORIES, SCENARIOS, Item, read_csv

DATASET = Path("tests/data/categorization_eval.csv")

# The rule-based categorizer still uses the old four-plus-other list; this maps it onto the dataset's
# nine categories. Its labels are kept as they are, so the baseline is measured without new rules.
RULES_TO_DATASET = {
    "groceries": "groceries",
    "transport": "transport",
    "entertainment": "entertainment",
    "housing": "housing_utilities",
    "other": "other",
}


def rules_categorizer(item: Item) -> str:
    """The baseline: keyword rules on the description and the merchant, mapped to the dataset's list."""
    return RULES_TO_DATASET[categorize_transaction(f"{item.description} {item.merchant}")]


@dataclass(frozen=True)
class Score:
    label: str
    items: int
    correct: int

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.items if self.items else None


def score(items: Sequence[Item], predict: Callable[[Item], str], label: str) -> Score:
    predictions = [predict(item) for item in items]
    for prediction in predictions:
        if prediction not in CATEGORIES:
            raise ValueError(f"category outside the allowed list: {prediction!r}")
    return Score(label, len(items), sum(p == item.true_category for p, item in zip(predictions, items)))


def evaluate(items: Sequence[Item], dataset: Path) -> str:
    """The whole report as Markdown."""
    splits = ("dev", "test")
    by_split = {split: [item for item in items if item.split == split] for split in splits}

    def groups(split_items: Sequence[Item]) -> list[Score]:
        result = [score(split_items, rules_categorizer, "all")]
        result += [score([i for i in split_items if i.ambiguity == a], rules_categorizer, a)
                   for a in ("clear", "ambiguous")]
        result += [score([i for i in split_items if i.scenario == s], rules_categorizer, f"scenario: {s}")
                   for s, _, _ in SCENARIOS]
        return result

    scores = {split: groups(by_split[split]) for split in splits}
    usual = {split: score([i for i in by_split[split] if i.scenario == "mixed_merchant"],
                          lambda i: i.usual_category, "usual category") for split in splits}

    lines = [
        "# Categorization evaluation: rule-based baseline",
        "",
        f"- Code: commit `{_commit()}`",
        f"- Command: `python -m finsync.evaluation.categories --dataset {dataset.as_posix()}`",
        f"- Dataset: `{dataset.as_posix()}` (sha256 `{_sha256(dataset)[:12]}`), {len(items)} items, "
        f"dev {len(by_split['dev'])}, test {len(by_split['test'])}",
        "- Label mapping: the rules' `housing` is scored as `housing_utilities`; the other four labels are "
        "the same in both lists. The rules never return `eating_out`, `health`, `clothing` or `household`.",
        "",
        "The rules never abstain, so the abstention rate is 0 % and every miss is a confident wrong answer.",
        "",
        "## Accuracy",
        "",
        "| Group | Dev items | Dev accuracy | Test items | Test accuracy |",
        "| --- | --- | --- | --- | --- |",
    ]
    for dev, test in zip(scores["dev"], scores["test"]):
        lines.append(f"| {dev.label} | {dev.items} | {_pct(dev.accuracy)} | {test.items} | {_pct(test.accuracy)} |")
    lines += [
        "",
        "## Ceiling on mixed-assortment merchants",
        "",
        "Without detail, the best a merchant-only categorizer can do is the merchant's usual category. "
        f"Scored against the labels, that reaches {_pct(usual['dev'].accuracy)} on dev and "
        f"{_pct(usual['test'].accuracy)} on test (`mixed_merchant` items only). The shares behind these "
        "labels are the author's assumptions (see [datasets.md](../datasets.md)).",
    ]
    return "\n".join(lines) + "\n"


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
    parser = argparse.ArgumentParser(description="Evaluate transaction categorization on the labelled dataset.")
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
