"""Seed a fresh database with the synthetic M2 demo: ``python -m finsync.api.demo --db demo.db``.

The [demo guide](../../docs/guides/demo.md) walks through it step by step. The seed creates the group
``demo-csalad`` with two members (``anna``, admin, and ``balint``, member), both with a web password, an API
token for ``anna``'s phone or emulator, and a few days of synthetic history that shows every M2 feature:
a settled category, uncertain ones, a mixed-assortment shop, an own-account transfer and one match waiting
for review. It also writes the bank export that the demo imports on W7, dated today, so the phone
notification sent during the demo and the export row describe the same purchase.

Every name, shop and amount is made up. The seed refuses an existing database file, so it never touches
real data.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from finsync.core import FinSyncService
from finsync.core.auth import TokenService
from finsync.core.sessions import SessionService
from finsync.storage import FinSyncStorage

GROUP = "demo-csalad"
ADMIN, MEMBER = "anna", "balint"
DEMO_PASSWORD = "finsync-demo-2026"
BUDAPEST = ZoneInfo("Europe/Budapest")
EXPORT_NAME = "demo-bank-export.csv"
# The notification the demo sends from the phone (the android-emulator-e2e skill's case A).
PHONE_NOTIFICATION = "-4 990 Ft erteken vasarolt a PELDABOLT KFT 12. uzleteben."


def _at(day: date, hour: int, minute: int) -> str:
    """A Budapest wall-clock time as an ISO instant with offset, as the phone sends it (ADR 0008)."""
    return datetime.combine(day, time(hour, minute), BUDAPEST).isoformat()


def _otp(amount: int, merchant: str) -> str:
    """A made-up notification in the masked shape of the supported bank format."""
    return f"-{amount:,} Ft erteken vasarolt a {merchant} uzleteben.".replace(",", " ")


def bank_export(today: date) -> str:
    """The demo's bank export: the phone purchase again, and two equal coffees on the same day.

    Rows carry the bank's reference, so the two coffees are two rows, not one row exported twice."""
    day = today.isoformat()
    return "\n".join(
        [
            "date,amount,currency,description,merchant,reference",
            f"{day},-4990,HUF,VASARLAS KARTYAVAL PELDABOLT KFT 12.,PELDABOLT KFT,DEMO-0001",
            f"{day},-1200,HUF,VASARLAS KARTYAVAL MINTA KAVEZO,MINTA KAVEZO,DEMO-0002",
            f"{day},-1200,HUF,VASARLAS KARTYAVAL MINTA KAVEZO,MINTA KAVEZO,DEMO-0003",
            "",
        ]
    )


def seed(storage: FinSyncStorage, today: date) -> str:
    """Write the demo data; returns the API token of anna's phone (shown once)."""
    service = FinSyncService(storage)
    storage.add_group_membership(ADMIN, GROUP, "admin")
    storage.add_group_membership(MEMBER, GROUP, "member")
    sessions = SessionService(storage)
    for user in (ADMIN, MEMBER):
        sessions.set_email(user, f"{user}@example.org")
        sessions.set_password(user, DEMO_PASSWORD)
    token, _ = TokenService(storage).create(ADMIN, GROUP, "Demó telefon")

    service.create_own_account(ADMIN, GROUP, "MINTA BALINT")
    three_days, two_days, yesterday = (today - timedelta(days=n) for n in (3, 2, 1))

    def manual(user: str, amount: str, description: str, merchant: str | None, when: str) -> None:
        service.create_manual_transaction(
            user,
            GROUP,
            {"amount": amount, "currency": "HUF", "description": description, "merchant": merchant,
             "happened_at": when},
        )

    # An own-account transfer: booked as `transfer` and left out of the totals.
    manual(ADMIN, "-20000", "Atutalas MINTA BALINT", "MINTA BALINT", three_days.isoformat())
    # Settled by the built-in dictionary.
    service.ingest_notification(ADMIN, GROUP, _otp(8450, "SPAR 0123"), posted_at=_at(three_days, 17, 5))
    service.ingest_notification(MEMBER, GROUP, _otp(1450, "BKK AUTOMATA"), posted_at=_at(two_days, 8, 2))
    # Uncertain: a mixed-assortment supermarket (corrected and split into lines in the demo) and a cryptic text.
    service.bulk_create_manual_transactions(
        ADMIN,
        GROUP,
        [
            {"amount": "-12990", "currency": "HUF", "description": "VASARLAS TESCO Aruhaz 41021",
             "merchant": "TESCO Aruhaz 41021", "happened_at": two_days.isoformat()},
            {"amount": "-3200", "currency": "HUF", "description": "KARTYAS FIZETES SUMUP *KJ BT",
             "merchant": "SUMUP *KJ BT", "happened_at": yesterday.isoformat()},
        ],
    )
    # A match waiting for review: anna's phone saw the bakery purchase, balint typed it in later by hand.
    service.ingest_notification(ADMIN, GROUP, _otp(2500, "MINTA PEKSEG"), posted_at=_at(yesterday, 7, 45))
    manual(MEMBER, "-2500", "Reggeli pekaru", "Pekseg a sarkon", yesterday.isoformat())
    return token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m finsync.api.demo", description="Seed the synthetic M2 demo.")
    parser.add_argument("--db", required=True, help="a new SQLite file (must not exist) or an empty database URL")
    parser.add_argument("--export-dir", default=".", help=f"where to write {EXPORT_NAME} (default: here)")
    args = parser.parse_args(argv)

    if "://" not in args.db and Path(args.db).exists():
        print(f"error: {args.db} already exists; the demo seeds only a new database", file=sys.stderr)
        return 2
    storage = FinSyncStorage(args.db)
    if storage.list_group_members(GROUP):
        print(f"error: the database already has the group {GROUP}", file=sys.stderr)
        return 2
    today = datetime.now(timezone.utc).astimezone(BUDAPEST).date()
    token = seed(storage, today)
    export = Path(args.export_dir) / EXPORT_NAME
    export.write_text(bank_export(today), encoding="utf-8")

    print(f"Demo group {GROUP} seeded in {args.db}.")
    print(f"Web sign-in: {ADMIN} (admin) or {MEMBER} (member), password {DEMO_PASSWORD}")
    print(f"Bank export for W7: {export}")
    print(f"API token of the demo phone (shown once): {token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
