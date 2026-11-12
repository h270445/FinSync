from __future__ import annotations

import collections
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest

from finsync.core import FinSyncService
from finsync.ingestion import parse_notification
from finsync.evaluation.generate import GROUP_ID, MEMBERS, SCENARIOS, generate, generate_v2, generate_v3, read_csv
from finsync.storage import FinSyncStorage

DATASET = Path(__file__).parent / "data" / "matching_eval.csv"
DATASET_V2 = Path(__file__).parent / "data" / "matching_eval_v2.csv"
DATASET_V3 = Path(__file__).parent / "data" / "matching_eval_v3.csv"


class MatchingDatasetTest(unittest.TestCase):
    def test_committed_dataset_matches_the_generator(self) -> None:
        # Regenerate with: python -m finsync.evaluation.generate
        self.assertEqual(read_csv(DATASET), generate(100, 2026))
        # Regenerate with: python -m finsync.evaluation.generate --version 2
        self.assertEqual(read_csv(DATASET_V2), generate_v2(100, 2026))
        # Regenerate with: python -m finsync.evaluation.generate --version 3
        self.assertEqual(read_csv(DATASET_V3), generate_v3(100, 2026))

    def test_version_3_is_version_2_with_local_notification_times(self) -> None:
        v2, v3 = read_csv(DATASET_V2), read_csv(DATASET_V3)
        self.assertEqual([replace(row, message="") for row in v3], [replace(row, message="") for row in v2])
        changed = [(a.message, b.message) for a, b in zip(v2, v3) if a.message != b.message]
        self.assertEqual(len(changed), sum(1 for row in v2 if row.message))
        # September is summer time, two hours ahead of UTC; the parser reads the text back to the same instant.
        before, after = changed[0]
        self.assertEqual(parse_notification(before).happened_at - parse_notification(after).happened_at, timedelta(hours=-2))
        for row_v2, row_v3 in zip(v2, v3):
            if row_v3.message:
                local = parse_notification(row_v3.message).happened_at
                printed_utc = datetime.strptime(row_v2.message[-16:], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                self.assertEqual(local, printed_utc, row_v3.record_id)

    def test_version_2_keeps_version_1_record_for_record(self) -> None:
        v1, v2 = read_csv(DATASET), read_csv(DATASET_V2)
        self.assertEqual(v2[: len(v1)], v1)
        self.assertEqual(len({row.record_id for row in v2}), len(v2))
        self.assertEqual(len({row.true_event for row in v2}), len({row.true_event for row in v1}) + 16)

    def test_generation_is_reproducible_and_seed_dependent(self) -> None:
        self.assertEqual(generate(60, 7), generate(60, 7))
        self.assertNotEqual(generate(60, 7), generate(60, 8))

    def test_every_scenario_appears_and_splits_keep_purchases_together(self) -> None:
        rows = read_csv(DATASET)
        self.assertGreaterEqual(len(rows), 100)
        self.assertEqual({row.scenario for row in rows}, {name for name, _ in SCENARIOS})
        for key in ("true_event", "case"):
            splits = collections.defaultdict(set)
            for row in rows:
                splits[getattr(row, key)].add(row.split)
            self.assertTrue(all(len(values) == 1 for values in splits.values()), key)
        self.assertEqual({row.split for row in rows}, {"dev", "test"})

    def test_re_deliveries_come_from_one_channel_for_any_seed(self) -> None:
        for seed in range(20):
            rows = generate(60, seed)
            for event in {row.true_event for row in rows if row.kind == "A"}:
                channels = {(row.member, row.source) for row in rows if row.true_event == event}
                self.assertEqual(len(channels), 1, (seed, event))

    def test_every_record_can_be_ingested(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            storage = FinSyncStorage(os.path.join(tempdir, "eval.db"))
            service = FinSyncService(storage)
            for member in MEMBERS:
                storage.add_group_membership(member, GROUP_ID)
            for row in read_csv(DATASET):
                if row.source == "android_notification":
                    service.ingest_notification(row.member, GROUP_ID, row.message)
                else:
                    payload = {
                        "amount": row.amount,
                        "currency": row.currency,
                        "description": row.description,
                        "happened_at": row.happened_at,
                        "merchant": row.merchant or None,
                        "source_ref": row.source_ref or None,
                    }
                    service.create_manual_transaction(row.member, GROUP_ID, payload)
            self.assertEqual(len(storage.list_transactions(GROUP_ID)), len(read_csv(DATASET)))


if __name__ == "__main__":
    unittest.main()
