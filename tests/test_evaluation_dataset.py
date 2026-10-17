from __future__ import annotations

import collections
import os
from pathlib import Path
import tempfile
import unittest

from finsync.core import FinSyncService
from finsync.evaluation.generate import GROUP_ID, MEMBERS, SCENARIOS, generate, read_csv
from finsync.storage import FinSyncStorage

DATASET = Path(__file__).parent / "data" / "matching_eval.csv"


class MatchingDatasetTest(unittest.TestCase):
    def test_committed_dataset_matches_the_generator(self) -> None:
        # Regenerate with: python -m finsync.evaluation.generate
        self.assertEqual(read_csv(DATASET), generate(100, 2026))

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
