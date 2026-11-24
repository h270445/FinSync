"""Hybrid categorizer evaluation: `python -m finsync.evaluation.hybrid [--estimate | --call-llm] [--out FILE]`.

Measures the deterministic layer (group rules are empty here, so the built-in Hungarian dictionary) plus
the LLM layer plus the abstention threshold on the labelled dataset, next to the rule-based baseline:
the coverage-accuracy curve, latency and cost (supervisor, 2026-11-16).

Protocol ([dev-test-evaluation skill](../../.claude/skills/dev-test-evaluation/SKILL.md)):

1. The decision rule is fixed in code before any run (`choose_threshold`): the highest coverage at which
   at most `TARGET_ERROR` of the settled dev answers are wrong; ties go to the higher threshold; when no
   threshold meets the target, the highest one is taken and the report says so.
2. The dev split is categorized and the threshold chosen from dev results alone.
3. Only then is the test split categorized, once, at the chosen threshold.

Without `--call-llm` the runner uses cached answers only and stops if one is missing, so no run spends
money by accident. `--estimate` prints how many calls are missing and what they would cost.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import statistics
import sys
from typing import Callable, Sequence

from finsync.categorization import categorize_record
from finsync.categorization.dictionary import DICTIONARY_VERSION, find_merchant
from finsync.categorization.hybrid import HIGH, CategoryDecision
from finsync.categorization.llm import (
    DEFAULT_MODEL, DEFAULT_SAMPLES, PRICES_PER_MTOK, PROMPT_VERSION, AnswerCache, LlmCategorizer, LlmClient,
    LlmVote, MissingAnswer, combine, cost_usd, needs_llm,
)
from finsync.evaluation.categories import DATASET, _commit, _pct, _sha256, rules_categorizer
from finsync.evaluation.generate_categories import SCENARIOS, Item, read_csv

TARGET_ERROR = 0.05
CACHE_DIR = Path("docs/evaluation/results/llm-cache")
# Rough tokens per call for --estimate before any answer is cached: system prompt plus one record, and a
# short JSON answer. The report itself uses the provider's counted tokens.
ESTIMATE_TOKENS = (700, 40)


@dataclass(frozen=True)
class Outcome:
    item: Item
    decision: CategoryDecision
    vote: LlmVote | None

    def at(self, threshold: float | None) -> CategoryDecision:
        """The hybrid decision at this threshold; None means the deterministic layer alone."""
        if threshold is None:
            return self.decision
        return combine(self.decision, self.vote, threshold)


@dataclass(frozen=True)
class Point:
    """One configuration on one set of items."""

    label: str
    threshold: float | None
    items: int
    settled: int
    settled_correct: int
    shown_correct: int

    @property
    def coverage(self) -> float | None:
        return self.settled / self.items if self.items else None

    @property
    def settled_accuracy(self) -> float | None:
        return self.settled_correct / self.settled if self.settled else None

    @property
    def settled_error(self) -> float | None:
        return None if self.settled_accuracy is None else 1 - self.settled_accuracy

    @property
    def wrong_settled(self) -> int:
        return self.settled - self.settled_correct

    @property
    def abstained(self) -> int:
        return self.items - self.settled


def point(outcomes: Sequence[Outcome], threshold: float | None, label: str) -> Point:
    settled = correct = shown = 0
    for outcome in outcomes:
        decision = outcome.at(threshold)
        right = decision.category == outcome.item.true_category
        shown += right
        if decision.confidence == HIGH:
            settled += 1
            correct += right
    return Point(label, threshold, len(outcomes), settled, correct, shown)


def thresholds(samples: int) -> list[float]:
    """Every share a vote of `samples` answers can have: 1/n, 2/n, ..., 1."""
    return [round(k / samples, 4) for k in range(1, samples + 1)]


def choose_threshold(sweep: Sequence[Point]) -> tuple[Point, bool]:
    """The dev point to use and whether it meets the target. Receives dev results only."""
    meeting = [p for p in sweep if p.settled_error is not None and p.settled_error <= TARGET_ERROR]
    if not meeting:
        return max(sweep, key=lambda p: p.threshold or 0.0), False
    return max(meeting, key=lambda p: (p.settled, p.threshold or 0.0)), True


def categorize(items: Sequence[Item], llm: LlmCategorizer) -> list[Outcome]:
    outcomes = []
    for item in items:
        decision = categorize_record(item.merchant or None, item.description or None)
        vote = llm.vote(item.merchant or None, item.description or None, item.amount, item.currency) \
            if needs_llm(decision) else None
        outcomes.append(Outcome(item, decision, vote))
    return outcomes


def missing_calls(items: Sequence[Item], llm: LlmCategorizer) -> int:
    total = 0
    for item in items:
        decision = categorize_record(item.merchant or None, item.description or None)
        if needs_llm(decision):
            total += llm.missing(item.merchant or None, item.description or None, item.amount, item.currency)
    return total


def estimate_cost(model: str, calls: int) -> float | None:
    prices = PRICES_PER_MTOK.get(model)
    if prices is None:
        return None
    return calls * (ESTIMATE_TOKENS[0] * prices[0] + ESTIMATE_TOKENS[1] * prices[1]) / 1_000_000


def in_dictionary(item: Item) -> bool:
    return find_merchant(item.merchant or item.description) is not None


def evaluate(items: Sequence[Item], dataset: Path, llm: LlmCategorizer, command: str) -> str:
    """The whole report as Markdown. Test items are categorized only after the threshold is chosen."""
    dev_items = [item for item in items if item.split == "dev"]
    test_items = [item for item in items if item.split == "test"]

    dev = categorize(dev_items, llm)
    sweep = [point(dev, t, f"hybrid @ {t:.2f}") for t in thresholds(llm.samples)]
    chosen, met = choose_threshold(sweep)
    threshold = chosen.threshold
    # The threshold is frozen here; the test split is categorized for the first time below.
    test = categorize(test_items, llm)

    def rules_point(split_items: Sequence[Item]) -> Point:
        correct = sum(rules_categorizer(i) == i.true_category for i in split_items)
        return Point("rule-based baseline (never abstains)", None, len(split_items), len(split_items),
                     correct, correct)

    def table(split: dict[str, Sequence[Outcome]], configs: list[tuple[str, Callable]]) -> list[str]:
        rows = ["| Method | Split | Items | Coverage (settled) | Accuracy of settled | Wrong and settled "
                "| Bizonytalan | Accuracy of shown category |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for label, make in configs:
            for name, outcomes in split.items():
                p = make(name, outcomes)
                rows.append(f"| {label} | {name} | {p.items} | {_pct(p.coverage)} | {_pct(p.settled_accuracy)} "
                            f"| {p.wrong_settled} | {p.abstained} | {_pct(p.shown_correct / p.items if p.items else None)} |")
        return rows

    by_split = {"dev": dev, "test": test}
    items_of = {"dev": dev_items, "test": test_items}
    configs = [
        ("Rule-based baseline", lambda name, o: rules_point(items_of[name])),
        ("Dictionary layer alone", lambda name, o: point(o, None, "")),
        (f"Hybrid @ {threshold:.2f} (chosen on dev)", lambda name, o: point(o, threshold, "")),
    ]

    llm_outcomes = [o for o in dev + test if o.vote is not None]
    replies = llm.distinct_replies()
    answers = sum(len(o.vote.replies) for o in llm_outcomes)
    call_seconds = [r.seconds for r in replies]
    item_seconds = [sum(r.seconds for r in o.vote.replies) for o in llm_outcomes]
    cost = cost_usd(llm.model, replies)
    new_calls = sum(o.vote.new_calls for o in llm_outcomes)

    lines = [
        "# Categorization evaluation: hybrid categorizer (dictionary + LLM + abstention)",
        "",
        f"- Code: commit `{_commit()}`, dictionary `{DICTIONARY_VERSION}`, prompt `{PROMPT_VERSION}`",
        f"- Command: `{command}`",
        f"- Dataset: `{dataset.as_posix()}` (sha256 `{_sha256(dataset)[:12]}`), {len(items)} items, "
        f"dev {len(dev_items)}, test {len(test_items)}",
        f"- LLM: `{llm.model}`, {llm.samples} samples per record, JSON schema output (Anthropic API: effort "
        f"`low`, no temperature, current models do not take one; an OpenAI-compatible server: its default "
        f"sampling); answers cached in "
        f"`{llm.cache.path.as_posix() if llm.cache.path else '(memory)'}`; "
        f"{new_calls} new calls in this run; report date {date.today().isoformat()}",
        "- Group merchant rules: none (the dataset has no group), so the deterministic layer is the "
        "built-in dictionary.",
        "",
        "## Decision rule (fixed before the run)",
        "",
        "The LLM is asked only for records where the dictionary gives nothing or only a `low` answer. Its "
        f"confidence is the share of the {llm.samples} samples that name the most frequent category. A record "
        "is *settled* when the dictionary answers `high` or the LLM share reaches the threshold; otherwise "
        "it is *Bizonytalan* (uncertain) and keeps a suggestion that a member confirms. Rule: the highest "
        f"coverage at which at most {TARGET_ERROR:.0%} of the settled dev answers are wrong; ties go to the "
        "higher threshold; if no threshold meets the target, the highest threshold is used. The test split "
        "was categorized only after the threshold was chosen and did not influence it.",
        "",
        "## 1. Coverage-accuracy curve (dev split)",
        "",
        "| Threshold | Coverage (settled) | Accuracy of settled | Wrong and settled | Bizonytalan |",
        "| --- | --- | --- | --- | --- |",
    ]
    dict_dev = point(dev, None, "")
    lines.append(f"| dictionary alone | {_pct(dict_dev.coverage)} | {_pct(dict_dev.settled_accuracy)} "
                 f"| {dict_dev.wrong_settled} | {dict_dev.abstained} |")
    for p in sweep:
        lines.append(f"| {p.threshold:.2f} | {_pct(p.coverage)} | {_pct(p.settled_accuracy)} "
                     f"| {p.wrong_settled} | {p.abstained} |")
    lines += [
        "",
        f"Chosen: **{threshold:.2f}**." + ("" if met else
            f" No threshold met the {TARGET_ERROR:.0%} target on dev, so the highest was used."),
        "",
        "## 2. Dev and test at the chosen threshold, next to the baselines",
        "",
        *table(by_split, configs),
        "",
        "*Accuracy of shown category* counts every record with the category the app would show, settled "
        "or suggested (`uncategorized` counts as wrong). The rule-based baseline is the keyword "
        "categorizer of the [Nov 8 report](2026-11-08-categorization-rules.md).",
        "",
        "## 3. Test split by scenario (chosen threshold)",
        "",
        "| Scenario | Items | Coverage | Accuracy of settled | Wrong and settled | Bizonytalan |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for scenario, _, _ in SCENARIOS:
        p = point([o for o in test if o.item.scenario == scenario], threshold, scenario)
        lines.append(f"| {scenario} | {p.items} | {_pct(p.coverage)} | {_pct(p.settled_accuracy)} "
                     f"| {p.wrong_settled} | {p.abstained} |")
    lines += [
        "",
        "## 4. Overlap of the dictionary and the dataset",
        "",
        "The dictionary was written from general knowledge, but it names the same large Hungarian chains as "
        "the synthetic dataset, so its numbers on records with a known merchant are optimistic. Records "
        "whose merchant (or description, without a merchant) is a dictionary merchant are reported apart:",
        "",
        "| Group | Split | Items | Coverage | Accuracy of settled | Wrong and settled |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, outcomes in by_split.items():
        for label, wanted in (("merchant in dictionary", True), ("merchant not in dictionary", False)):
            p = point([o for o in outcomes if in_dictionary(o.item) == wanted], threshold, label)
            lines.append(f"| {label} | {name} | {p.items} | {_pct(p.coverage)} | {_pct(p.settled_accuracy)} "
                         f"| {p.wrong_settled} |")
    lines += [
        "",
        "## 5. Latency and cost of the LLM layer",
        "",
        f"- Records sent to the LLM: {len(llm_outcomes)} of {len(items)} "
        f"({sum(o.vote is not None for o in dev)} dev, {sum(o.vote is not None for o in test)} test), "
        f"{answers} answers, {len(replies)} distinct calls (records with the same text share cached answers)",
        f"- Latency per call: median {_seconds(call_seconds, statistics.median)}, "
        f"worst {_seconds(call_seconds, max)}",
        f"- Latency per record ({llm.samples} calls one after another): median "
        f"{_seconds(item_seconds, statistics.median)}, worst {_seconds(item_seconds, max)}; the calls are "
        "independent, so in parallel a record takes about one call's time",
        f"- Tokens: {sum(r.input_tokens for r in replies)} in, {sum(r.output_tokens for r in replies)} out",
        f"- Cost: {_usd(cost)} in total, {_usd(cost / len(llm_outcomes) if cost is not None and llm_outcomes else None)} "
        f"per record sent to the LLM, {_usd(cost / len(items) * 100 if cost is not None else None)} per 100 "
        "records of this mix (prices of 2026-11-03)",
        "",
        "Latency and token counts are those of the first, uncached call of each answer.",
        "",
        "## 6. Wrong and settled answers (test split, chosen threshold)",
        "",
        "| Item | Scenario | Merchant | Description | True | Given | Source |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for outcome in test:
        decision = outcome.at(threshold)
        if decision.confidence == HIGH and decision.category != outcome.item.true_category:
            i = outcome.item
            lines.append(f"| {i.item_id} | {i.scenario} | {_cell(i.merchant)} | {_cell(i.description)} "
                         f"| {i.true_category} | {decision.category} | {decision.source} |")
    return "\n".join(lines) + "\n"


def _cell(text: str) -> str:
    return (text or "").replace("|", "\\|")


def _seconds(values: Sequence[float], how: Callable) -> str:
    return f"{how(values):.2f} s" if values else "n/a"


def _usd(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.4f}"


def preflight(args: argparse.Namespace, items: Sequence[Item], llm: LlmCategorizer) -> int:
    """Everything a paid run needs, checked without a call; returns 0 when the run can start."""
    import importlib.util
    import os

    problems = []
    if args.base_url:
        print(f"provider: OpenAI-compatible server at {args.base_url}, model {args.model}")
    else:
        print(f"provider: Anthropic API, model {args.model}")
        if importlib.util.find_spec("anthropic") is None:
            problems.append("the anthropic package is missing: pip install -r requirements.txt")
        if os.environ.get("FINSYNC_ANTHROPIC_API_KEY"):
            print("credential: FINSYNC_ANTHROPIC_API_KEY, sent to https://api.anthropic.com")
        elif os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            print("credential: ANTHROPIC_API_KEY")
        else:
            problems.append("no FINSYNC_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY in the environment")
    dev = sum(1 for i in items if i.split == "dev")
    print(f"dataset: {args.dataset.as_posix()} ({len(items)} items, dev {dev}, test {len(items) - dev})")
    print(f"cache: {llm.cache.path.as_posix()} ({len(llm.cache.entries)} answers cached)")
    calls = missing_calls(items, llm)
    print(f"missing calls: {calls}, estimated cost {_usd(estimate_cost(args.model, calls))}")
    for problem in problems:
        print(f"NOT READY: {problem}")
    if not problems:
        print("READY: run again with --call-llm --out docs/evaluation/results/<date>-categorization-hybrid.md")
    return 1 if problems else 0


def default_cache(model: str) -> Path:
    return CACHE_DIR / f"categorization-{model}-{PROMPT_VERSION}.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the hybrid categorizer on the labelled dataset.")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", help="an OpenAI-compatible server (for example LM Studio: "
                        "http://localhost:1234/v1) instead of the Anthropic API; key from FINSYNC_LLM_API_KEY")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--cache", type=Path, help="answer cache (default: per model and prompt version)")
    parser.add_argument("--out", type=Path, help="write the report here instead of printing it")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--estimate", action="store_true", help="print missing calls and their cost, call nothing")
    mode.add_argument("--preflight", action="store_true",
                      help="check the SDK, the credential and the cache before a paid run, call nothing")
    mode.add_argument("--call-llm", action="store_true", help="call the provider for missing answers (costs money)")
    args = parser.parse_args(argv)

    items = read_csv(args.dataset)
    cache = AnswerCache(args.cache or default_cache(args.model))
    client: LlmClient | None = None
    if args.call_llm:
        if args.base_url:
            import os
            from finsync.categorization.llm import OpenAICompatibleClient
            client = OpenAICompatibleClient(args.base_url, args.model, os.environ.get("FINSYNC_LLM_API_KEY"))
        else:
            from finsync.categorization.llm import AnthropicClient
            client = AnthropicClient(args.model)
    llm = LlmCategorizer(client, cache, model=args.model, samples=args.samples)

    if args.preflight:
        return preflight(args, items, llm)

    if args.estimate:
        calls = missing_calls(items, llm)
        print(f"{calls} calls missing for {args.model} (prompt {PROMPT_VERSION}, {args.samples} samples); "
              f"estimated cost {_usd(estimate_cost(args.model, calls))}")
        return 0

    command = "python -m finsync.evaluation.hybrid" + (f" --dataset {args.dataset.as_posix()}"
                                                      if args.dataset != DATASET else "")
    try:
        report = evaluate(items, args.dataset, llm, command)
    except MissingAnswer as error:
        print(f"{error}. Run with --estimate to see the cost, then --call-llm to fetch the answers.",
              file=sys.stderr)
        return 2
    finally:
        if client is not None:
            cache.save()
    if args.out is None:
        print(report, end="")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
