"""The hybrid categorizer's LLM layer and its evaluation runner, with a fake provider (no network, no cost)."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from finsync.categorization import CategoryDecision
from finsync.categorization.llm import (
    SYSTEM_PROMPT, UNCATEGORIZED, UNKNOWN, AnswerCache, LlmCategorizer, LlmReply, LlmVote, MissingAnswer,
    combine, cost_usd, needs_llm, parse_answer, user_prompt,
)
from finsync.evaluation import hybrid
from finsync.evaluation.categories import DATASET
from finsync.evaluation.generate_categories import read_csv


def reply(category: str) -> LlmReply:
    return LlmReply(json.dumps({"category": category}), 700, 10, 0.5)


def vote(*answers: str) -> LlmVote:
    return LlmVote(answers, tuple(reply(a) for a in answers), 0)


class FakeClient:
    """Answers from a function of the user prompt, cycling through a list per record; counts calls."""

    model = "fake-model"

    def __init__(self, answer) -> None:
        self.answer = answer
        self.calls = 0
        self.seen: dict[str, int] = {}

    def complete(self, system: str, user: str) -> LlmReply:
        self.calls += 1
        n = self.seen.get(user, 0)
        self.seen[user] = n + 1
        return LlmReply(self.answer(user, n), 700, 10, 0.4)


class ParseAnswerTest(unittest.TestCase):
    def test_only_an_allowed_category_in_valid_json_is_used(self) -> None:
        self.assertEqual(parse_answer('{"category": "groceries"}'), "groceries")
        self.assertEqual(parse_answer('{"category": "unknown"}'), UNKNOWN)
        self.assertEqual(parse_answer('{"category": "food"}'), UNKNOWN)
        self.assertEqual(parse_answer('{"category": "transfer"}'), UNKNOWN)
        self.assertEqual(parse_answer("groceries"), UNKNOWN)
        self.assertEqual(parse_answer('["groceries"]'), UNKNOWN)
        self.assertEqual(parse_answer(""), UNKNOWN)

    def test_prompt_sends_only_merchant_description_and_amount(self) -> None:
        text = user_prompt("SPAR 0123", "bevásárlás", "4500", "HUF")
        self.assertIn("Merchant: SPAR 0123", text)
        self.assertIn("Description: bevásárlás", text)
        self.assertIn("Amount: 4500 HUF", text)
        self.assertIn("Merchant: (none)", user_prompt(None, "ebéd", None, None))
        self.assertIn(f'"{UNKNOWN}"', SYSTEM_PROMPT)


class VoteTest(unittest.TestCase):
    def test_share_counts_unknown_and_rejected_samples(self) -> None:
        v = vote("groceries", "groceries", "groceries", UNKNOWN, "clothing")
        self.assertEqual(v.top, "groceries")
        self.assertAlmostEqual(v.share, 0.6)

    def test_all_unknown_has_no_top_and_zero_share(self) -> None:
        v = vote(UNKNOWN, UNKNOWN, UNKNOWN)
        self.assertEqual(v.top, UNKNOWN)
        self.assertEqual(v.share, 0.0)

    def test_a_tie_goes_to_the_category_answered_first(self) -> None:
        self.assertEqual(vote("clothing", "groceries", "groceries", "clothing", UNKNOWN).top, "clothing")


class CombineTest(unittest.TestCase):
    def test_a_high_deterministic_answer_is_never_sent_to_the_llm(self) -> None:
        decision = CategoryDecision("transport", "dictionary", "high")
        self.assertFalse(needs_llm(decision))
        self.assertEqual(combine(decision, vote("groceries"), 0.2), decision)

    def test_a_share_at_the_threshold_settles_the_llm_category(self) -> None:
        decision = CategoryDecision("other", "none", "low")
        settled = combine(decision, vote("health", "health", "health", "health", UNKNOWN), 0.8)
        self.assertEqual(settled, CategoryDecision("health", "llm", "high"))

    def test_below_the_threshold_the_dictionary_suggestion_is_kept(self) -> None:
        decision = CategoryDecision("groceries", "dictionary", "low")
        self.assertEqual(combine(decision, vote("clothing", "clothing", UNKNOWN, UNKNOWN, UNKNOWN), 0.8), decision)

    def test_without_any_suggestion_the_llm_top_is_a_low_suggestion_or_uncategorized(self) -> None:
        decision = CategoryDecision("other", "none", "low")
        self.assertEqual(combine(decision, vote("health", UNKNOWN, UNKNOWN), 0.8),
                         CategoryDecision("health", "llm", "low"))
        self.assertEqual(combine(decision, vote(UNKNOWN, UNKNOWN), 0.8),
                         CategoryDecision(UNCATEGORIZED, "none", "low"))


class CategorizerCacheTest(unittest.TestCase):
    def test_answers_are_cached_and_a_rerun_makes_no_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            client = FakeClient(lambda user, n: '{"category": "health"}')
            first = LlmCategorizer(client, AnswerCache(path), samples=3)
            v = first.vote("BENU 12", None, "2990", "HUF")
            self.assertEqual((v.top, v.share, v.new_calls, client.calls), ("health", 1.0, 3, 3))
            first.cache.save()

            again = LlmCategorizer(None, AnswerCache(path), model="fake-model", samples=3)
            self.assertEqual(again.missing("BENU 12", None, "2990", "HUF"), 0)
            self.assertEqual(again.vote("BENU 12", None, "2990", "HUF").answers, v.answers)

    def test_cache_only_mode_refuses_to_call(self) -> None:
        llm = LlmCategorizer(None, AnswerCache(), model="fake-model", samples=2)
        self.assertEqual(llm.missing("X", None, None, None), 2)
        with self.assertRaises(MissingAnswer):
            llm.vote("X", None)

    def test_cost_uses_the_price_list(self) -> None:
        self.assertAlmostEqual(cost_usd("claude-haiku-5-5", [reply("health")] * 10),
                               (7000 * 0.10 + 100 * 0.50) / 1_000_000)
        self.assertIsNone(cost_usd("fake-model", [reply("health")]))


class OpenAICompatibleClientTest(unittest.TestCase):
    def test_request_carries_the_schema_and_the_reply_is_read(self) -> None:
        import httpx
        from finsync.categorization.llm import OpenAICompatibleClient

        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={
                "choices": [{"message": {"content": '{"category": "health"}'}}],
                "usage": {"prompt_tokens": 650, "completion_tokens": 8},
            })

        client = OpenAICompatibleClient("http://localhost:1234/v1/", "local-model",
                                        transport=httpx.MockTransport(handler))
        result = client.complete("system", "user")
        self.assertEqual(seen["url"], "http://localhost:1234/v1/chat/completions")
        self.assertEqual(seen["body"]["model"], "local-model")
        self.assertEqual(seen["body"]["response_format"]["json_schema"]["schema"]["required"], ["category"])
        self.assertEqual((parse_answer(result.text), result.input_tokens, result.output_tokens),
                         ("health", 650, 8))


class ChooseThresholdTest(unittest.TestCase):
    def point(self, threshold: float, settled: int, correct: int) -> hybrid.Point:
        return hybrid.Point("", threshold, 100, settled, correct, correct)

    def test_highest_coverage_within_the_target_wins(self) -> None:
        sweep = [self.point(0.2, 90, 80), self.point(0.6, 80, 77), self.point(0.8, 70, 68), self.point(1.0, 60, 59)]
        chosen, met = hybrid.choose_threshold(sweep)
        self.assertEqual((chosen.threshold, met), (0.6, True))

    def test_ties_go_to_the_higher_threshold_and_a_missed_target_takes_the_highest(self) -> None:
        tie = [self.point(0.6, 80, 77), self.point(0.8, 80, 77)]
        self.assertEqual(hybrid.choose_threshold(tie)[0].threshold, 0.8)
        bad = [self.point(0.2, 90, 50), self.point(1.0, 60, 40)]
        self.assertEqual(hybrid.choose_threshold(bad), (bad[1], False))


class EvaluationRunTest(unittest.TestCase):
    """The whole runner on the real dataset with a fake provider that answers from the description."""

    @staticmethod
    def answer(user: str, n: int) -> str:
        text = user.lower()
        if "gyógyszer" in text or "patika" in text:
            return '{"category": "health"}'
        return '{"category": "%s"}' % ("other" if n % 2 else UNKNOWN)

    def run_report(self, items) -> tuple[str, FakeClient]:
        client = FakeClient(self.answer)
        llm = LlmCategorizer(client, AnswerCache(), samples=5)
        return hybrid.evaluate(items, DATASET, llm, "test"), client

    def test_report_has_baseline_curve_overlap_cost_and_errors(self) -> None:
        report, client = self.run_report(read_csv(DATASET))
        for heading in ("Decision rule", "Coverage-accuracy curve", "Rule-based baseline",
                        "Overlap of the dictionary", "Latency and cost", "Wrong and settled answers"):
            self.assertIn(heading, report)
        self.assertGreater(client.calls, 0)
        self.assertEqual(client.calls % 5, 0)

    def test_test_labels_do_not_change_the_chosen_threshold(self) -> None:
        items = read_csv(DATASET)
        flipped = [replace(i, true_category="clothing") if i.split == "test" else i for i in items]
        chosen = [line for line in (self.run_report(items)[0], self.run_report(flipped)[0])]
        pick = [next(l for l in report.splitlines() if l.startswith("Chosen:")) for report in chosen]
        self.assertEqual(pick[0], pick[1])

    def test_runner_without_cache_stops_before_spending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = hybrid.main(["--cache", str(Path(tmp) / "empty.json"), "--out", str(Path(tmp) / "r.md")])
            self.assertEqual(code, 2)
            self.assertFalse((Path(tmp) / "r.md").exists())


if __name__ == "__main__":
    unittest.main()
