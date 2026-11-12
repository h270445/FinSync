"""Write units run one at a time, on SQLite and on PostgreSQL (FinSyncStorage.transaction)."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest

from finsync.core import FinSyncService
from finsync.storage import FinSyncStorage

TEXT = "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42"


class ConcurrentIngestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "test.db")
        storage = FinSyncStorage(self.path)
        storage.add_group_membership("anna", "lakas")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_the_same_notification_sent_at_once_from_many_threads_is_one_record(self) -> None:
        # Without the write lock, several threads would find no earlier copy and each store an original.
        threads, start, errors = 8, threading.Barrier(8), []

        def send() -> None:
            try:
                service = FinSyncService(FinSyncStorage(self.path))
                start.wait()
                service.ingest_notification("anna", "lakas", TEXT)
            except Exception as error:  # reported below; a thread cannot fail the test itself
                errors.append(error)

        workers = [threading.Thread(target=send) for _ in range(threads)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=60)
        self.assertEqual(errors, [])
        storage = FinSyncStorage(self.path)
        originals = [tx for tx in storage.list_transactions("lakas") if tx.duplicate_of_id is None]
        self.assertEqual(len(originals), 1)
        self.assertEqual(len(storage.list_transactions("lakas")), threads)
        self.assertEqual(len(storage.list_events("lakas")), 1)


if __name__ == "__main__":
    unittest.main()
