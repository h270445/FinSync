from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import unittest

from finsync.matching import MatchRecord, decide, fingerprint, local_date, merchant_tokens, score
from finsync.matching.scoring import Features


def _record(**overrides: object) -> MatchRecord:
    values: dict[str, object] = {
        "group_id": "group-1",
        "channel": "android_notification:user-1",
        "amount": Decimal("-4500"),
        "currency": "HUF",
        "direction": "expense",
        "happened_at": datetime(2026, 9, 5, 16, 42, tzinfo=timezone.utc),
        "precision": "minute",
        "merchant_text": "Tesco",
    }
    values.update(overrides)
    return MatchRecord(**values)  # type: ignore[arg-type]


def _features(value: float) -> Features:
    return Features(amount=1.0, time=1.0, merchant=1.0, delta="0h", score=value)


class NormalizeTest(unittest.TestCase):
    def test_merchant_tokens_drop_accents_numbers_and_legal_suffixes(self) -> None:
        self.assertEqual(merchant_tokens("TESCO Áruház 41021"), {"tesco", "aruhaz"})
        self.assertEqual(merchant_tokens("Spar Magyarország Kft."), {"spar", "magyarorszag"})
        self.assertEqual(merchant_tokens(None), frozenset())

    def test_local_date_uses_budapest_time_for_minute_records(self) -> None:
        late_evening = datetime(2026, 9, 5, 22, 30, tzinfo=timezone.utc)  # 00:30 on 6 September in Budapest
        self.assertEqual(str(local_date(late_evening, "minute")), "2026-09-06")
        self.assertEqual(str(local_date(datetime(2026, 9, 5, tzinfo=timezone.utc), "day")), "2026-09-05")


class FingerprintTest(unittest.TestCase):
    def test_same_payload_and_channel_give_the_same_fingerprint(self) -> None:
        first = fingerprint("group-1", "android_notification:user-1", "CARD PURCHASE -4500 HUF at Tesco")
        self.assertEqual(first, fingerprint("group-1", "android_notification:user-1", "CARD PURCHASE -4500 HUF at Tesco"))
        self.assertNotEqual(first, fingerprint("group-1", "android_notification:user-2", "CARD PURCHASE -4500 HUF at Tesco"))
        self.assertNotEqual(first, fingerprint("group-2", "android_notification:user-1", "CARD PURCHASE -4500 HUF at Tesco"))


class ScoreTest(unittest.TestCase):
    def test_identical_values_score_one(self) -> None:
        features = score(_record(channel="manual:user-1"), _record())
        self.assertIsNotNone(features)
        assert features is not None
        self.assertEqual(features.score, 1.0)

    def test_blocking_gates(self) -> None:
        existing = _record()
        for name, new in (
            ("other group", _record(group_id="group-2")),
            ("other currency", _record(currency="EUR")),
            ("other direction", _record(direction="income", amount=Decimal("4500"))),
            ("other amount", _record(amount=Decimal("-4600"))),
            ("more than 48 hours", _record(happened_at=datetime(2026, 9, 7, 16, 43, tzinfo=timezone.utc))),
            (
                "more than 3 days at day precision",
                _record(happened_at=datetime(2026, 9, 9, tzinfo=timezone.utc), precision="day"),
            ),
        ):
            with self.subTest(name):
                self.assertIsNone(score(new, existing))

    def test_amount_equal_only_after_rounding_scores_lower(self) -> None:
        features = score(_record(amount=Decimal("-1235")), _record(amount=Decimal("-1234.56")))
        assert features is not None
        self.assertEqual(features.amount, 0.7)

    def test_day_precision_same_day_has_full_time_score(self) -> None:
        manual = _record(happened_at=datetime(2026, 9, 5, tzinfo=timezone.utc), precision="day")
        features = score(manual, _record())
        assert features is not None
        self.assertEqual(features.time, 1.0)

    def test_missing_merchant_scores_half(self) -> None:
        features = score(_record(merchant_text=None), _record())
        assert features is not None
        self.assertEqual(features.merchant, 0.5)


class DecideTest(unittest.TestCase):
    def test_thresholds(self) -> None:
        self.assertEqual(decide({}).outcome, "separate")
        self.assertEqual(decide({1: _features(0.85)}).outcome, "auto_linked")
        self.assertEqual(decide({1: _features(0.8499)}).outcome, "needs_review")
        self.assertEqual(decide({1: _features(0.60)}).outcome, "needs_review")
        self.assertEqual(decide({1: _features(0.5999)}).outcome, "separate")

    def test_close_runner_up_sends_to_review(self) -> None:
        decision = decide({1: _features(0.95), 2: _features(0.90)})
        self.assertEqual(decision.outcome, "needs_review")
        self.assertEqual(decision.event_id, 1)
        self.assertEqual(decide({1: _features(0.95), 2: _features(0.85)}).outcome, "auto_linked")


if __name__ == "__main__":
    unittest.main()
