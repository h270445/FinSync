"""File import of spreadsheet exports (CSV and XLSX): parsing, the whole-file rule, re-imports and matching.

Every row here is made up: synthetic members, made-up shops and amounts.
"""

from __future__ import annotations

import base64
from datetime import date, datetime, timezone
from decimal import Decimal
import io
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.core import ConflictError, FinSyncService, TokenService
from finsync.ingestion import ColumnMapping, parse_export, parse_xlsx
from finsync.ingestion.csv_import import parse_amount, parse_date
from finsync.storage import FinSyncStorage

EXPORT = """date,amount,description,merchant
2026-09-05,-4500,Weekly shop,Tesco
2026-09-06,-1290,Pekseg,Minta Pekseg
"""
# A Hungarian-style export: semicolons, decimal comma, dotted dates, the bank's own column names and reference.
BANK_EXPORT = """Könyvelés dátuma;Összeg;Pénznem;Közlemény;Partner;Tranzakció azonosító
2026.09.05.;-4 500;HUF;Kártyás vásárlás;PELDABOLT KFT;000000101
2026.09.07.;-12,50;EUR;Kártyás vásárlás;CAFE PELDA;000000102
"""
BANK_MAPPING = ColumnMapping(
    date="Könyvelés dátuma", amount="Összeg", currency="Pénznem", description="Közlemény",
    merchant="Partner", reference="Tranzakció azonosító",
)


def make_xlsx(rows: list[list[object]]) -> bytes:
    """A workbook built in the test, the shape a bank's XLSX export has: real dates and numbers in cells."""
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


XLSX_ROWS: list[list[object]] = [
    ["Könyvelés dátuma", "Összeg", "Pénznem", "Közlemény", "Partner", "Tranzakció azonosító"],
    [datetime(2026, 9, 5, 0, 0), -4500, "HUF", "Kártyás vásárlás", "PELDABOLT KFT", "000000101"],
    [date(2026, 9, 7), -12.5, "EUR", "Kártyás vásárlás", "CAFE PELDA", "000000102"],
    [None, None, None, None, None, None],
    ["2026.09.08.", "-1 290", None, "Pékség", None, None],
]


class ParseXlsxTest(unittest.TestCase):
    def test_dates_numbers_and_text_cells_become_rows(self) -> None:
        parsed = parse_xlsx(make_xlsx(XLSX_ROWS), BANK_MAPPING)
        self.assertEqual(parsed.errors, [])
        self.assertEqual([row.happened_on for row in parsed.rows], [date(2026, 9, 5), date(2026, 9, 7), date(2026, 9, 8)])
        self.assertEqual([row.amount for row in parsed.rows], [Decimal("-4500"), Decimal("-12.5"), Decimal("-1290")])
        self.assertEqual([row.currency for row in parsed.rows], ["HUF", "EUR", "HUF"])
        self.assertEqual([row.line for row in parsed.rows], [2, 3, 5])  # the sheet's row numbers; row 4 is blank
        self.assertEqual(parsed.rows[0].reference, "000000101")

    def test_a_bad_cell_is_reported_with_its_row(self) -> None:
        parsed = parse_xlsx(make_xlsx([XLSX_ROWS[0], [date(2026, 9, 5), "sok", "HUF", "Bolt", None, None]]), BANK_MAPPING)
        self.assertEqual([(error.line, error.error) for error in parsed.errors], [(2, "invalid amount 'sok'")])

    def test_a_file_that_is_not_a_workbook_is_refused(self) -> None:
        for data in (b"", b"not a zip", EXPORT.encode("utf-8")):
            with self.assertRaisesRegex(ValueError, "not a readable XLSX"):
                parse_xlsx(data, ColumnMapping())

    def test_an_empty_sheet_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_xlsx(make_xlsx([]), ColumnMapping())


class ParseExportTest(unittest.TestCase):
    def test_the_generic_format_needs_no_mapping(self) -> None:
        parsed = parse_export(EXPORT, ColumnMapping())
        self.assertEqual(parsed.errors, [])
        self.assertEqual([(row.line, row.happened_on, row.amount, row.merchant) for row in parsed.rows], [
            (2, date(2026, 9, 5), Decimal("-4500"), "Tesco"),
            (3, date(2026, 9, 6), Decimal("-1290"), "Minta Pekseg"),
        ])
        self.assertEqual({row.currency for row in parsed.rows}, {"HUF"})

    def test_a_bank_style_export_with_a_mapping(self) -> None:
        parsed = parse_export("﻿" + BANK_EXPORT.replace("\n", "\r\n"), BANK_MAPPING)
        self.assertEqual(parsed.errors, [])
        first, second = parsed.rows
        self.assertEqual((first.happened_on, first.amount, first.currency, first.reference), (date(2026, 9, 5), Decimal("-4500"), "HUF", "000000101"))
        self.assertEqual((second.amount, second.currency, second.merchant), (Decimal("-12.50"), "EUR", "CAFE PELDA"))

    def test_amount_and_date_forms(self) -> None:
        for raw, expected in {"-4990": "-4990", "-4 990": "-4990", "-4 990": "-4990", "-4.990,50": "-4990.50",
                              "-12,50": "-12.50", "+1500": "1500", "4990.50": "4990.50"}.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_amount(raw), Decimal(expected))
        for raw in ("2026-09-05", "2026.09.05.", "2026.09.05", "2026-09-05 16:42", "2026-09-05T16:42:00"):
            with self.subTest(raw=raw):
                self.assertEqual(parse_date(raw), date(2026, 9, 5))
        for bad_amount in ("0", "x", "", "NaN", "Infinity"):
            with self.subTest(bad_amount=bad_amount), self.assertRaises(ValueError):
                parse_amount(bad_amount)
        for bad_date in ("05.09.2026", "2026-13-01", "2026-02-30", ""):
            with self.subTest(bad_date=bad_date), self.assertRaises(ValueError):
                parse_date(bad_date)

    def test_every_bad_row_is_reported_with_its_line(self) -> None:
        content = "date,amount,description\n2026-09-05,x,Bolt\n2026-09-06,-100,\n\n2026-09-07,-200,Bolt\n2026-99-01,-1,Bolt\n"
        parsed = parse_export(content, ColumnMapping())
        self.assertEqual([row.line for row in parsed.rows], [5])
        self.assertEqual([error.line for error in parsed.errors], [2, 3, 6])
        self.assertIn("invalid amount", parsed.errors[0].error)

    def test_file_level_problems(self) -> None:
        for content, message in (
            ("", "empty"),
            ("date,amount,description\n", "no rows"),
            ("datum,amount,description\n2026-09-05,-1,Bolt\n", "not found"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                parse_export(content, ColumnMapping())


class FileImportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        self.storage.add_group_membership("anna", "lakas")
        self.storage.add_group_membership("balint", "lakas")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _state(self):
        return (self.storage.list_transactions("lakas"), self.storage.list_events("lakas"), self.storage.list_decisions("lakas"))

    def test_rows_are_stored_as_day_precision_file_records_of_one_batch(self) -> None:
        result = self.service.import_file("anna", "lakas", EXPORT)
        self.assertEqual([item.match_outcome for item in result.results], ["separate", "separate"])
        stored = sorted(self.storage.list_transactions("lakas"), key=lambda tx: tx.id)
        self.assertEqual({tx.source for tx in stored}, {"file_import"})
        self.assertEqual({tx.happened_at_precision for tx in stored}, {"day"})
        self.assertEqual({tx.import_batch_id for tx in stored}, {result.import_batch_id})
        self.assertEqual(stored[0].happened_at, datetime(2026, 9, 5, tzinfo=timezone.utc))
        self.assertTrue(all(tx.source_ref for tx in stored))

    def test_the_preview_stores_nothing_and_shows_the_errors(self) -> None:
        content = EXPORT + "2026-09-07,x,Bolt,Bolt\n"
        preview = self.service.import_file("anna", "lakas", content, dry_run=True)
        self.assertEqual((len(preview.rows), [error.line for error in preview.errors], preview.results), (2, [4], []))
        self.assertFalse(preview.already_imported)
        self.assertEqual(self.storage.list_transactions("lakas"), [])

    def test_one_bad_row_refuses_the_whole_file(self) -> None:
        before = self._state()
        with self.assertRaisesRegex(ValueError, "Nothing was imported. Line 4: invalid amount"):
            self.service.import_file("anna", "lakas", EXPORT + "2026-09-07,x,Bolt,Bolt\n")
        self.assertEqual(self._state(), before)

    def test_the_same_file_again_is_refused_before_anything_is_stored(self) -> None:
        self.service.import_file("anna", "lakas", EXPORT)
        before = self._state()
        # The same bytes with other line ends and a byte-order mark are the same file.
        again = "﻿" + EXPORT.replace("\n", "\r\n")
        self.assertTrue(self.service.import_file("balint", "lakas", again, dry_run=True).already_imported)
        with self.assertRaisesRegex(ConflictError, "already imported"):
            self.service.import_file("balint", "lakas", again)
        self.assertEqual(self._state(), before)

    def test_an_overlapping_later_export_adds_only_the_new_rows(self) -> None:
        self.service.import_file("anna", "lakas", EXPORT)
        later = EXPORT + "2026-09-08,-990,Ujsag,Minta Trafik\n"
        result = self.service.import_file("anna", "lakas", later)
        self.assertEqual([item.match_outcome for item in result.results], ["exact_duplicate", "exact_duplicate", "separate"])
        self.assertEqual(len(self.storage.list_events("lakas")), 3)

    def test_the_banks_reference_identifies_a_row_across_exports(self) -> None:
        self.service.import_file("anna", "lakas", BANK_EXPORT, BANK_MAPPING)
        # The next export prints the same booking with a changed description; the reference still matches.
        later = BANK_EXPORT.replace("2026.09.05.;-4 500;HUF;Kártyás vásárlás", "2026.09.05.;-4 500;HUF;Vásárlás")
        result = self.service.import_file("anna", "lakas", later, BANK_MAPPING)
        self.assertEqual([item.match_outcome for item in result.results], ["exact_duplicate", "exact_duplicate"])
        self.assertEqual(len(self.storage.list_events("lakas")), 2)

    def test_a_second_identical_row_of_one_file_goes_to_review(self) -> None:
        content = "date,amount,description\n2026-09-05,-450,Jegy\n2026-09-05,-450,Jegy\n"
        first, second = self.service.import_file("anna", "lakas", content).results
        self.assertEqual((first.match_outcome, second.match_outcome), ("separate", "needs_review"))
        self.assertNotEqual(first.event_id, second.event_id)
        [review] = self.service.list_open_reviews("anna", "lakas")
        self.assertEqual((review.transaction.id, review.candidate_event.id), (second.transaction_id, first.event_id))
        # Two tickets after all: rejecting keeps them apart.
        self.service.reject_match("anna", "lakas", review.decision_id)
        self.assertEqual(len(self.storage.list_events("lakas")), 2)
        # Exporting the same two rows again (with a third) adds only the third, which again goes to review.
        again = self.service.import_file("anna", "lakas", content + "2026-09-05,-450,Jegy\n")
        self.assertEqual([item.match_outcome for item in again.results], ["exact_duplicate", "exact_duplicate", "needs_review"])

    def test_confirming_the_identical_row_makes_it_a_re_delivery(self) -> None:
        content = "date,amount,description\n2026-09-05,-450,Jegy\n2026-09-05,-450,Jegy\n"
        first, second = self.service.import_file("anna", "lakas", content).results
        [review] = self.service.list_open_reviews("anna", "lakas")
        self.service.confirm_match("anna", "lakas", review.decision_id)
        events = self.storage.list_events("lakas")
        self.assertEqual([len(event.transactions) for event in events], [2])
        moved = next(tx for tx in self.storage.list_transactions("lakas") if tx.id == second.transaction_id)
        self.assertEqual(moved.duplicate_of_id, first.transaction_id)

    def test_a_row_links_to_the_notification_of_the_same_purchase(self) -> None:
        # The bank books the purchase a day later; the notification carried the purchase time.
        notification = self.service.ingest_notification(
            "anna", "lakas", "-4 990 Ft értékben vásárolt a PELDABOLT KFT 12. üzletében.",
            posted_at="2026-09-05T15:42:00+00:00", source_ref="000000101",
        )
        result = self.service.import_file(
            "anna", "lakas", "date,amount,description,merchant\n2026-09-06,-4990,Kártyás vásárlás,PELDABOLT KFT\n"
        )
        outcome = result.results[0]
        self.assertIn(outcome.match_outcome, ("auto_linked", "needs_review"))
        if outcome.match_outcome == "auto_linked":
            self.assertEqual(outcome.event_id, notification.event_id)

    def test_an_xlsx_file_is_imported_and_refused_the_second_time(self) -> None:
        data = make_xlsx(XLSX_ROWS)
        result = self.service.import_file("anna", "lakas", data, BANK_MAPPING)
        self.assertEqual(len(result.results), 3)
        self.assertEqual({tx.source for tx in self.storage.list_transactions("lakas")}, {"file_import"})
        with self.assertRaisesRegex(ConflictError, "already imported"):
            self.service.import_file("anna", "lakas", data, BANK_MAPPING)

    def test_only_members_can_import(self) -> None:
        from finsync.core import AuthorizationError
        with self.assertRaises(AuthorizationError):
            self.service.import_file("cecil", "lakas", EXPORT)
        self.assertEqual(self.storage.list_transactions("lakas"), [])


class FileImportApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.storage.add_group_membership("anna", "lakas")
        token, _ = TokenService(self.storage).create("anna", "lakas", "Anna")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = TestClient(create_app(self.storage))

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()

    def test_preview_then_import_then_refused_repeat(self) -> None:
        preview = self.client.post("/v1/imports", json={"content": BANK_EXPORT, "mapping": {
            "date": "Könyvelés dátuma", "amount": "Összeg", "currency": "Pénznem", "description": "Közlemény",
            "merchant": "Partner", "reference": "Tranzakció azonosító"}, "dry_run": True}, headers=self.headers)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual([row["amount"] for row in preview.json()["rows"]], ["-4500", "-12.50"])
        self.assertEqual((preview.json()["results"], preview.json()["summary"]), ([], {}))

        body = {"content": EXPORT}
        done = self.client.post("/v1/imports", json=body, headers=self.headers)
        self.assertEqual(done.status_code, 201, done.text)
        self.assertEqual(done.json()["summary"], {"separate": 2})
        repeat = self.client.post("/v1/imports", json=body, headers=self.headers)
        self.assertEqual(repeat.status_code, 409)
        self.assertIn("already imported", repeat.json()["error"])

    def test_an_xlsx_file_as_base64(self) -> None:
        body = {"xlsx_base64": base64.b64encode(make_xlsx(XLSX_ROWS)).decode("ascii"), "dry_run": True,
                "mapping": {"date": "Könyvelés dátuma", "amount": "Összeg", "currency": "Pénznem",
                            "description": "Közlemény", "merchant": "Partner", "reference": "Tranzakció azonosító"}}
        preview = self.client.post("/v1/imports", json=body, headers=self.headers)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual([row["amount"] for row in preview.json()["rows"]], ["-4500", "-12.5", "-1290"])

    def test_exactly_one_file_field(self) -> None:
        for body in ({}, {"content": EXPORT, "xlsx_base64": "UEs="}, {"xlsx_base64": "nem base64!"}):
            response = self.client.post("/v1/imports", json=body, headers=self.headers)
            self.assertEqual(response.status_code, 400, body)


if __name__ == "__main__":
    unittest.main()
