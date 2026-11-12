"""Spreadsheet export (CSV or XLSX) to import rows: column mapping, Hungarian number and date forms, row errors.

A bank or spreadsheet export names its columns differently, so the caller maps them (`ColumnMapping`); the
defaults are FinSync's own generic headers. Every row is checked and every error is collected with its line
number, so the preview can show them all and the import can refuse the whole file ([matching design](
../../docs/design/transaction-matching.md), file import row). XLSX is read with openpyxl: the first sheet,
cell values only (no formulas are evaluated), turned into the same text rows as a CSV.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
import re
from typing import Iterable, Iterator
import zipfile

MAX_ROWS = 5000
_DELIMITERS = ",;\t"
# Hungarian exports print dates as 2026.09.05. (with or without the final dot); ISO dates also work.
# A time after the date is ignored: an export's booking date is a calendar day (day precision).
_DATE = re.compile(r"^\s*(\d{4})[-./](\d{2})[-./](\d{2})\.?(?:[ T].*)?$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class ColumnMapping:
    """Which header names hold which value. Header matching ignores case and surrounding spaces."""

    date: str = "date"
    amount: str = "amount"
    description: str = "description"
    merchant: str | None = "merchant"
    currency: str | None = "currency"
    # The bank's own transaction id, when the export has one; it identifies the row across exports.
    reference: str | None = "reference"
    default_currency: str = "HUF"


@dataclass(frozen=True)
class ImportRow:
    line: int  # line number in the file, the header being line 1
    happened_on: date
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    reference: str | None


@dataclass(frozen=True)
class RowError:
    line: int
    error: str


@dataclass(frozen=True)
class ParsedExport:
    rows: list[ImportRow]
    errors: list[RowError]


def normalize_content(content: str) -> str:
    """The file text without a byte-order mark and with \\n line ends, so the same file always hashes the same."""
    return content.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")


def parse_amount(raw: str) -> Decimal:
    """Amounts as exports print them: -4990, -4 990, -4.990,50, -12,50, +1500, 4990.50."""
    text = raw.strip().replace(" ", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")  # 1.234,50: dot groups thousands, comma is the decimal
    elif "," in text:
        text = text.replace(",", ".")
    try:
        amount = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"invalid amount {raw.strip()!r}") from error
    if not amount.is_finite() or amount == 0:
        raise ValueError("the amount must be a non-zero number")
    return amount


def parse_date(raw: str) -> date:
    match = _DATE.match(raw)
    if not match:
        raise ValueError(f"invalid date {raw.strip()!r}; use 2026-09-05 or 2026.09.05.")
    try:
        return datetime(int(match[1]), int(match[2]), int(match[3])).date()
    except ValueError as error:
        raise ValueError(f"invalid date {raw.strip()!r}") from error


def parse_export(content: str, mapping: ColumnMapping) -> ParsedExport:
    """A CSV file: every data row as an ImportRow, or a RowError naming its line. Raises ValueError for the file."""
    text = normalize_content(content)
    if not text.strip():
        raise ValueError("The file is empty")
    try:
        dialect = csv.Sniffer().sniff(text.split("\n", 1)[0], delimiters=_DELIMITERS)
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    return _parse_rows(csv.reader(io.StringIO(text), delimiter=delimiter), mapping)


def parse_xlsx(data: bytes, mapping: ColumnMapping) -> ParsedExport:
    """An XLSX file, first sheet. Line numbers are the sheet's row numbers, as the spreadsheet shows them."""
    from openpyxl import load_workbook  # only needed for XLSX

    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except (zipfile.BadZipFile, KeyError, OSError, ValueError) as error:
        raise ValueError("The file is not a readable XLSX workbook") from error
    try:
        sheet = workbook.worksheets[0]
        return _parse_rows((_cell_texts(row) for row in sheet.iter_rows(values_only=True)), mapping)
    finally:
        workbook.close()


def _cell_texts(row: Iterable[object]) -> list[str]:
    texts = []
    for value in row:
        if value is None:
            texts.append("")
        elif isinstance(value, datetime):
            texts.append(value.date().isoformat())  # a booking date; a time in the cell is dropped
        elif isinstance(value, date):
            texts.append(value.isoformat())
        elif isinstance(value, float):
            texts.append(str(Decimal(repr(value))))  # 4990.5, never 4990.499999
        else:
            texts.append(str(value))
    return texts


def _parse_rows(reader: Iterator[list[str]], mapping: ColumnMapping) -> ParsedExport:
    try:
        header = [str(name).strip().lower() for name in next(reader)]
    except StopIteration:
        raise ValueError("The file is empty") from None

    def column(name: str | None, required: bool) -> int | None:
        if name is None or not name.strip():
            if required:
                raise ValueError("A required column is not mapped")
            return None
        key = name.strip().lower()
        if key not in header:
            if required:
                raise ValueError(f"Column {name.strip()!r} not found; the file has: {', '.join(header)}")
            return None
        return header.index(key)

    date_at = column(mapping.date, True)
    amount_at = column(mapping.amount, True)
    description_at = column(mapping.description, True)
    merchant_at = column(mapping.merchant, False)
    currency_at = column(mapping.currency, False)
    reference_at = column(mapping.reference, False)

    rows: list[ImportRow] = []
    errors: list[RowError] = []
    for line, values in enumerate(reader, start=2):
        if not any(value.strip() for value in values):
            continue  # blank lines, often at the end of an export
        if len(rows) + len(errors) >= MAX_ROWS:
            raise ValueError(f"The file has more than {MAX_ROWS} rows; split it")

        def value(index: int | None) -> str:
            return values[index].strip() if index is not None and index < len(values) else ""

        try:
            description = value(description_at)
            if not description:
                raise ValueError("the description is empty")
            currency = (value(currency_at) or mapping.default_currency).upper()
            if not _CURRENCY.match(currency):
                raise ValueError(f"invalid currency {currency!r}")
            rows.append(
                ImportRow(
                    line=line,
                    happened_on=parse_date(value(date_at)),
                    amount=parse_amount(value(amount_at)),
                    currency=currency,
                    description=description,
                    merchant=value(merchant_at) or None,
                    reference=value(reference_at) or None,
                )
            )
        except ValueError as error:
            errors.append(RowError(line, str(error)))
    if not rows and not errors:
        raise ValueError("The file has a header but no rows")
    return ParsedExport(rows, errors)
