"""Synthetic, labelled dataset for evaluating transaction matching.

Every purchase is built from one scenario that says which records describe it and how they
differ. Records of the same purchase share a `true_event` label; the matcher never sees it.
The output is deterministic for a given seed, so a result can be reproduced from the commit id.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
import hashlib
from pathlib import Path
import random
from typing import Callable

GROUP_ID = "eval-group"
MEMBERS = ("member-a", "member-b")
START = datetime(2026, 9, 1, tzinfo=timezone.utc)
DAYS = 28

# (bank notification text, merchant a member would type, description a member would type, typical amounts)
MERCHANTS = (
    ("TESCO Áruház 41021", "Tesco", "Tesco weekly shop", (3490, 8990, 12450, 4500)),
    ("SPAR Magyarország Kft.", "Spar", "Groceries", (1890, 2590, 6720)),
    ("LIDL 0231", "Lidl", "Lidl shopping", (4120, 7680, 2990)),
    ("ALDI 112", "Aldi", "Aldi", (3560, 5210)),
    ("ROSSMANN 207", "Rossmann", "Drugstore", (2340, 4890)),
    ("MOL Töltőállomás", "MOL", "Fuel", (18500, 22000, 15600)),
    ("BKK Automata", "BKK", "Bus ticket", (450, 900)),
    ("Wolt", "Wolt", "Dinner delivery", (5890, 7450)),
    ("PIZZERIA ROMA", "Pizzeria Roma", "Dinner", (12000, 9800)),
    ("IKEA Budaörs", "IKEA", "Household items", (14990, 6490)),
    ("DECATHLON", "Decathlon", "Sports gear", (8990, 11990)),
    ("NETFLIX.COM", "Netflix", "Netflix subscription", (4490,)),
)


@dataclass(frozen=True)
class Row:
    record_id: str
    case: str
    true_event: str
    scenario: str
    kind: str
    split: str
    member: str
    source: str
    arrives_at: str
    message: str = ""
    amount: str = ""
    currency: str = "HUF"
    description: str = ""
    merchant: str = ""
    happened_at: str = ""
    source_ref: str = ""


class _Builder:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.rows: list[Row] = []
        self._events = 0
        self._sheet_rows = 0
        self._cases = 0

    def start_case(self) -> None:
        """One scenario run; all its records share a case id and a split, so look-alike pairs stay together."""
        self._cases += 1

    # Helpers -------------------------------------------------------------------------------

    def _new_event(self) -> str:
        self._events += 1
        return f"E{self._events:04d}"

    def _moment(self) -> datetime:
        day = self.rng.randrange(DAYS)
        minute = self.rng.randrange(7 * 60, 22 * 60)
        return START + timedelta(days=day, minutes=minute)

    def _merchant(self, *, exclude: tuple[str, ...] = ()) -> tuple[str, str, str, tuple[int, ...]]:
        return self.rng.choice([m for m in MERCHANTS if m[1] not in exclude])

    def _add(self, event: str, scenario: str, kind: str, member: str, source: str, arrives: datetime, **values: str) -> None:
        case = f"C{self._cases:04d}"
        self.rows.append(
            Row(
                record_id="",
                case=case,
                true_event=event,
                scenario=scenario,
                kind=kind,
                split=_split_of(case),
                member=member,
                source=source,
                arrives_at=arrives.isoformat(),
                **values,
            )
        )

    def notification(self, event: str, scenario: str, kind: str, when: datetime, bank_name: str, amount: Decimal,
                     member: str = MEMBERS[0], arrives: datetime | None = None) -> None:
        sign = "-" if amount < 0 else "+"
        text_amount = f"{sign}{abs(amount)}"
        if amount < 0:
            message = f"CARD PURCHASE {text_amount} HUF at {bank_name} on {when:%Y-%m-%d %H:%M}"
        else:
            message = f"Incoming transfer {text_amount} HUF from {bank_name} {when:%Y-%m-%d %H:%M}"
        self._add(event, scenario, kind, member, "android_notification", arrives or when, message=message)

    def manual(self, event: str, scenario: str, kind: str, when: datetime, amount: Decimal, description: str,
               merchant: str = "", member: str | None = None, date_only: bool = False,
               arrives: datetime | None = None, source_ref: str = "") -> None:
        # Either member may type an entry; notifications come from member A's phone.
        member = member or self.rng.choice(MEMBERS)
        happened = when.date().isoformat() if date_only else when.isoformat()
        self._add(
            event, scenario, kind, member, "manual", arrives or when + timedelta(hours=self.rng.randint(1, 6)),
            amount=str(amount), description=description, merchant=merchant, happened_at=happened,
            source_ref=source_ref,
        )

    def sheet_ref(self) -> str:
        self._sheet_rows += 1
        return f"sheet-row-{self._sheet_rows}"

    # Scenarios -------------------------------------------------------------------------------
    # Each method creates one purchase (or one pair of separate purchases) and its records.

    def single_notification(self) -> None:
        bank, _, _, amounts = self._merchant()
        self.notification(self._new_event(), "single_notification", "none", self._moment(), bank, -Decimal(self.rng.choice(amounts)))

    def single_manual(self) -> None:
        _, name, description, amounts = self._merchant()
        self.manual(self._new_event(), "single_manual", "none", self._moment(), -Decimal(self.rng.choice(amounts)), description,
                    merchant=name if self.rng.random() < 0.5 else "", member=self.rng.choice(MEMBERS))

    def notification_and_manual(self) -> None:
        event, when = self._new_event(), self._moment()
        bank, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.notification(event, "notification_and_manual", "B", when, bank, amount)
        self.manual(event, "notification_and_manual", "B", when + timedelta(minutes=self.rng.randint(-20, 20)),
                    amount, description, merchant=name)

    def manual_first(self) -> None:
        event, when = self._new_event(), self._moment()
        bank, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.manual(event, "manual_first", "B", when, amount, description, merchant=name,
                    arrives=when - timedelta(minutes=5))
        self.notification(event, "manual_first", "B", when, bank, amount)

    def date_only_manual(self) -> None:
        event, when = self._new_event(), self._moment()
        bank, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.notification(event, "date_only_manual", "B", when, bank, amount)
        with_merchant = self.rng.random() < 0.5
        self.manual(event, "date_only_manual", "B", when, amount, description,
                    merchant=name if with_merchant else "", date_only=True)

    def rounded_manual(self) -> None:
        event, when = self._new_event(), self._moment()
        bank, name, description, amounts = self._merchant()
        exact = -(Decimal(self.rng.choice(amounts)) + Decimal(self.rng.randint(1, 49)) / 100)
        typed = -abs(exact).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        self.notification(event, "rounded_manual", "B", when, bank, exact)
        self.manual(event, "rounded_manual", "B", when, typed, description, merchant=name, date_only=True)

    def late_manual(self) -> None:
        event, when = self._new_event(), self._moment()
        bank, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        days_late = self.rng.choice((1, 2))
        self.notification(event, "late_manual", "B", when, bank, amount)
        # The member logs it days later and types the day of logging, not the day of the purchase.
        self.manual(event, "late_manual", "B", when + timedelta(days=days_late), amount, description,
                    merchant=name, date_only=True, arrives=when + timedelta(days=days_late))

    def two_members_same_purchase(self) -> None:
        event, when = self._new_event(), self._moment()
        _, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.manual(event, "two_members_same_purchase", "B", when, amount, description, merchant=name, member=MEMBERS[0])
        self.manual(event, "two_members_same_purchase", "B", when, amount, description, merchant=name,
                    member=MEMBERS[1], date_only=True)

    def repeated_notification(self) -> None:
        event, when = self._new_event(), self._moment()
        bank, _, _, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.notification(event, "repeated_notification", "A", when, bank, amount)
        self.notification(event, "repeated_notification", "A", when, bank, amount,
                          arrives=when + timedelta(minutes=self.rng.randint(1, 90)))

    def resent_sheet_row(self) -> None:
        event, when = self._new_event(), self._moment()
        _, name, description, amounts = self._merchant()
        amount, ref = -Decimal(self.rng.choice(amounts)), self.sheet_ref()
        arrives, member = when + timedelta(hours=8), self.rng.choice(MEMBERS)
        # A re-delivery comes from the same channel, so both rows are sent by the same member.
        for delay in (0, 30):
            self.manual(event, "resent_sheet_row", "A", when, amount, description, merchant=name, member=member,
                        date_only=True, arrives=arrives + timedelta(minutes=delay), source_ref=ref)

    def same_amount_same_phone(self) -> None:
        when = self._moment()
        bank, _, _, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.notification(self._new_event(), "same_amount_same_phone", "C", when, bank, amount)
        self.notification(self._new_event(), "same_amount_same_phone", "C",
                          when + timedelta(minutes=self.rng.randint(3, 40)), bank, amount)

    def same_amount_other_shop(self) -> None:
        """Two same-amount purchases in different shops on one day; the manual entry belongs to the second."""
        when = self._moment()
        first_bank, first_name, _, _ = self._merchant()
        second_bank, second_name, description, _ = self._merchant(exclude=(first_name,))
        amount = -Decimal(self.rng.choice((2990, 4500, 5890)))
        self.notification(self._new_event(), "same_amount_other_shop", "C", when, first_bank, amount)
        second = self._new_event()
        later = when + timedelta(hours=2)
        self.notification(second, "same_amount_other_shop", "B", later, second_bank, amount)
        self.manual(second, "same_amount_other_shop", "B", later, amount, description, merchant=second_name)

    def identical_manual_rows(self) -> None:
        """Two equal bus tickets typed by the same member: separate purchases with identical rows."""
        when = self._moment().replace(hour=8, minute=0)
        for _ in range(2):
            self.manual(self._new_event(), "identical_manual_rows", "C", when, Decimal("-450"), "Bus ticket",
                        merchant="BKK", member=MEMBERS[0], date_only=True)

    def monthly_subscription(self) -> None:
        when = START + timedelta(days=self.rng.randrange(3), hours=9)
        for offset in (0, 30):
            self.notification(self._new_event(), "monthly_subscription", "C", when + timedelta(days=offset),
                              "NETFLIX.COM", Decimal("-4490"))

    def refund(self) -> None:
        when = self._moment()
        bank, _, _, amounts = self._merchant()
        amount = Decimal(self.rng.choice(amounts))
        self.notification(self._new_event(), "refund", "C", when, bank, -amount)
        self.notification(self._new_event(), "refund", "C", when + timedelta(days=1), bank, amount)

    def very_late_manual(self) -> None:
        """Logged five days later: outside the window, a known limitation counted as a missed duplicate."""
        event, when = self._new_event(), self._moment()
        bank, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        self.notification(event, "very_late_manual", "B", when, bank, amount)
        self.manual(event, "very_late_manual", "B", when + timedelta(days=5), amount, description,
                    merchant=name, date_only=True, arrives=when + timedelta(days=5))

    def same_amount_neighbour_days(self) -> None:
        """Two same-amount purchases in one shop two days apart, each with a date-only manual entry.

        Member A logs the first one a day late, on the day between the two purchases, so in reverse
        order the late entry fits the second purchase as well as its own (the 2026-10-18 IKEA case).
        """
        when = self._moment()
        bank, name, description, amounts = self._merchant()
        amount = -Decimal(self.rng.choice(amounts))
        first, second = self._new_event(), self._new_event()
        self.notification(first, "same_amount_neighbour_days", "B", when, bank, amount)
        self.manual(first, "same_amount_neighbour_days", "B", when + timedelta(days=1), amount, description,
                    merchant=name, member=MEMBERS[0], date_only=True, arrives=when + timedelta(days=1))
        later = when + timedelta(days=2, minutes=self.rng.randint(-120, 120))
        self.notification(second, "same_amount_neighbour_days", "B", later, bank, amount)
        self.manual(second, "same_amount_neighbour_days", "B", later, amount, description, merchant=name,
                    member=MEMBERS[1], date_only=True)


# Relative frequency of each scenario. Singletons dominate, as in a real household.
SCENARIOS: tuple[tuple[str, int], ...] = (
    ("single_notification", 16),
    ("single_manual", 10),
    ("notification_and_manual", 4),
    ("manual_first", 2),
    ("date_only_manual", 3),
    ("rounded_manual", 2),
    ("late_manual", 2),
    ("two_members_same_purchase", 2),
    ("repeated_notification", 2),
    ("resent_sheet_row", 2),
    ("same_amount_same_phone", 2),
    ("same_amount_other_shop", 1),
    ("identical_manual_rows", 1),
    ("monthly_subscription", 1),
    ("refund", 1),
    ("very_late_manual", 1),
)


def _split_of(case: str) -> str:
    """dev or test, fixed per case, so the records of one purchase and its look-alikes stay together."""
    return "dev" if hashlib.sha256(case.encode()).digest()[0] % 2 == 0 else "test"


def generate(records: int = 100, seed: int = 2026) -> list[Row]:
    """At least `records` rows; every scenario appears at least once, the rest are drawn by weight."""
    builder = _Builder(seed)
    names = [name for name, _ in SCENARIOS]
    weights = [weight for _, weight in SCENARIOS]
    for name in names:
        builder.start_case()
        getattr(builder, name)()
    while len(builder.rows) < records:
        scenario: Callable[[], None] = getattr(builder, builder.rng.choices(names, weights)[0])
        builder.start_case()
        scenario()
    ordered = sorted(builder.rows, key=lambda row: (row.arrives_at, row.true_event))
    return [Row(**{**asdict(row), "record_id": f"R{index:04d}"}) for index, row in enumerate(ordered, start=1)]


# Version 2 adds cases of these scenarios to version 1, which stays unchanged record for record.
V2_ADDITIONS: tuple[tuple[str, int], ...] = (("same_amount_neighbour_days", 8),)


def generate_v2(records: int = 100, seed: int = 2026) -> list[Row]:
    """Version 1 followed by the V2_ADDITIONS cases, numbered after it and drawn from their own seed."""
    base = generate(records, seed)
    builder = _Builder(seed + 1)
    builder._cases = len({row.case for row in base})
    builder._events = len({row.true_event for row in base})
    for name, count in V2_ADDITIONS:
        for _ in range(count):
            builder.start_case()
            getattr(builder, name)()
    added = sorted(builder.rows, key=lambda row: (row.arrives_at, row.true_event))
    return base + [Row(**{**asdict(row), "record_id": f"R{index:04d}"})
                   for index, row in enumerate(added, start=len(base) + 1)]


def write_csv(rows: list[Row], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(Row)], lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def read_csv(path: Path) -> list[Row]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [Row(**row) for row in csv.DictReader(handle)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic matching dataset.")
    parser.add_argument("--records", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--version", type=int, choices=(1, 2), default=2)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    rows = (generate_v2 if args.version == 2 else generate)(args.records, args.seed)
    args.out = args.out or Path("tests/data/matching_eval_v2.csv" if args.version == 2 else "tests/data/matching_eval.csv")
    write_csv(rows, args.out)
    events = len({row.true_event for row in rows})
    print(f"Wrote {len(rows)} records describing {events} purchases to {args.out}")


if __name__ == "__main__":
    main()
