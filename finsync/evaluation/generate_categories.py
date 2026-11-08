"""Synthetic, labelled dataset for evaluating transaction categorization.

Every item is one purchase as a categorizer would see it: description, merchant and amount.
`true_category` is what the member actually bought; `ambiguity` says whether that can be told
from the item at all (see docs/design/categorization.md#evaluation). The categorizer never sees
the labels. The output is deterministic for a given seed, so a result can be reproduced from the commit id.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, fields
import hashlib
from pathlib import Path
import random

# The proposed list from docs/design/categorization.md (open question 3).
CATEGORIES = (
    "groceries",
    "eating_out",
    "transport",
    "housing_utilities",
    "health",
    "clothing",
    "entertainment",
    "household",
    "other",
)

# (bank notification text, merchant a member would type, category, typical amounts)
CLEAR_MERCHANTS = (
    ("BKK Automata", "BKK", "transport", (450, 900, 8950)),
    ("MOL Töltőállomás", "MOL", "transport", (18500, 22000, 15600)),
    ("BOLT.EU/O/2610", "Bolt", "transport", (2890, 4150)),
    ("MAV-START ZRT", "MÁV", "transport", (3720, 6450)),
    ("NETFLIX.COM", "Netflix", "entertainment", (4490,)),
    ("Spotify P2B8E1", "Spotify", "entertainment", (2390,)),
    ("CINEMA CITY ARENA", "Cinema City", "entertainment", (5980, 2990)),
    ("Wolt", "Wolt", "eating_out", (5890, 7450)),
    ("PIZZERIA ROMA", "Pizzeria Roma", "eating_out", (12000, 9800)),
    ("BURGER KING 0412", "Burger King", "eating_out", (3290, 4580)),
    ("MVM NEXT ENERGIA", "MVM", "housing_utilities", (14320, 21870)),
    ("Magyar Telekom Nyrt.", "Telekom", "housing_utilities", (9990, 12490)),
    ("FOTAV ZRT", "Főtáv", "housing_utilities", (18640,)),
    ("BENU GYOGYSZERTAR 112", "Benu", "health", (3450, 7820, 1290)),
    ("H&M 0921", "H&M", "clothing", (9990, 5990, 14990)),
    ("DEICHMANN 233", "Deichmann", "clothing", (12990, 8990)),
    ("OBI 1043", "OBI", "household", (6490, 15990)),
    ("MAGYAR POSTA 1132", "Posta", "other", (1150, 2890)),
)

# (bank notification text, merchant, usual category, {category: share of purchases}, typical amounts)
MIXED_MERCHANTS = (
    ("TESCO Áruház 41021", "Tesco", "groceries",
     {"groceries": 70, "household": 15, "clothing": 10, "entertainment": 5}, (3490, 8990, 12450, 4500)),
    ("SPAR Magyarország Kft.", "Spar", "groceries",
     {"groceries": 85, "household": 10, "other": 5}, (1890, 2590, 6720)),
    ("AUCHAN SOROKSAR", "Auchan", "groceries",
     {"groceries": 60, "household": 20, "clothing": 10, "entertainment": 10}, (15430, 9870, 22340)),
    ("LIDL 0231", "Lidl", "groceries",
     {"groceries": 75, "household": 15, "clothing": 10}, (4120, 7680, 2990)),
    ("ROSSMANN 207", "Rossmann", "household",
     {"household": 50, "health": 40, "groceries": 10}, (2340, 4890)),
    ("DM DROGERIE 0855", "dm", "household",
     {"household": 50, "health": 40, "groceries": 10}, (3120, 5460)),
    ("EMAG.HU", "eMAG", "household",
     {"household": 40, "entertainment": 30, "clothing": 15, "health": 15}, (8990, 24990, 4590)),
    ("AMAZON MKTPL*2K4L9", "Amazon", "household",
     {"household": 40, "entertainment": 40, "clothing": 20}, (11870, 6420)),
    ("DECATHLON", "Decathlon", "clothing",
     {"clothing": 60, "entertainment": 40}, (8990, 11990)),
)

# What a member types when the merchant alone would not tell (English and Hungarian, as members write).
DETAIL_DESCRIPTIONS = {
    "groceries": ("Weekly food shop", "heti bevásárlás", "kaja hétvégére"),
    "household": ("Cleaning supplies", "mosószer és szivacs", "Light bulbs"),
    "clothing": ("T-shirt for the kid", "zokni", "Winter jacket"),
    "entertainment": ("Board game", "PS5 játék", "Lego for birthday"),
    "health": ("Vitamins", "gyógyszer", "Painkillers"),
    "other": ("Gift card", "ajándékkártya"),
}

# Merchants the keyword rules do not know but a reader can place from the name.
UNFAMILIAR_MERCHANTS = (
    ("KOVACS PEKSEG BT", "Kovács Pékség", "groceries", (890, 1450)),
    ("ZOLDSEG-GYUMOLCS 14", "Zöldséges", "groceries", (2100, 3380)),
    ("ZOLD KERT BISZTRO", "Zöld Kert Bisztró", "eating_out", (6800, 11200)),
    ("KAVEZO A SARKON", "Kávézó a Sarkon", "eating_out", (1650, 2400)),
    ("DR NAGY FOGASZATI REND", "Dr. Nagy fogászat", "health", (25000, 18000)),
    ("VAROSI USZODA", "Városi Uszoda", "entertainment", (2800, 3500)),
    ("KONYVESBOLT LIBRI", "Libri", "entertainment", (4990, 3590)),
    ("CIPOBOLT KFT", "Cipőbolt", "clothing", (16990, 21990)),
    ("PARKOLAS BP XIII", "Parkolás", "transport", (600, 1200)),
    ("VIZMUVEK ZRT", "Vízművek", "housing_utilities", (7340,)),
    ("PRAKTIKER 21", "Praktiker", "household", (5490, 12990)),
    ("FODRASZAT ANNA", "Anna fodrászat", "other", (6500, 9000)),
)

# Manual entries with a Hungarian description only, no merchant.
HUNGARIAN_DESCRIPTIONS = (
    ("benzin", "transport", (16000, 21000)),
    ("BKV bérlet", "transport", (8950,)),
    ("villanyszámla", "housing_utilities", (14300,)),
    ("lakbér", "housing_utilities", (180000,)),
    ("ebéd a menzán", "eating_out", (1890, 2200)),
    ("vacsora étteremben", "eating_out", (14500,)),
    ("fogorvos", "health", (22000,)),
    ("patika", "health", (2890, 4300)),
    ("mozijegy", "entertainment", (2990, 5980)),
    ("cipő", "clothing", (17990,)),
    ("porszívó", "household", (39990,)),
    ("piaci zöldség", "groceries", (2600,)),
)

# Payment-provider texts that hide the merchant; the true category comes from the purchase behind them.
CRYPTIC_TEXTS = (
    ("SUMUP *KJ BT", ("eating_out", "groceries", "other")),
    ("PAYPAL *4029357733", ("entertainment", "household", "clothing")),
    ("SIMPLEP*7731 BUDAPEST", ("entertainment", "eating_out", "transport", "household")),
    ("SZEP KARTYA ELFOG 0193", ("eating_out", "groceries")),
    ("POS 00451 BUDAPEST", ("groceries", "health", "other")),
    ("BARION*ONLINE FIZ", ("entertainment", "clothing", "household")),
)

# Fixed number of items per scenario, so the mix does not depend on the seed.
SCENARIOS: tuple[tuple[str, str, int], ...] = (
    # (scenario, ambiguity, items)
    ("clear_merchant", "clear", 50),
    ("mixed_merchant", "ambiguous", 50),
    ("mixed_with_detail", "clear", 30),
    ("unfamiliar_merchant", "clear", 30),
    ("hungarian_description", "clear", 20),
    ("cryptic_text", "ambiguous", 20),
)


@dataclass(frozen=True)
class Item:
    item_id: str
    scenario: str
    ambiguity: str
    split: str
    source: str
    description: str
    merchant: str
    amount: str
    currency: str
    true_category: str
    usual_category: str


class _Builder:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)

    def _amount(self, typical: tuple[int, ...]) -> str:
        """A typical amount, sometimes shifted a little, so equal texts do not always carry equal amounts."""
        base = self.rng.choice(typical)
        return str(base if self.rng.random() < 0.6 else round(base * self.rng.uniform(0.8, 1.2) / 10) * 10)

    def _by_category(self, options: tuple) -> tuple:
        """Category first, then an entry of it, so rare categories are not left to chance."""
        category = self.rng.choice(sorted({option[-2] for option in options}))
        return self.rng.choice([option for option in options if option[-2] == category])

    def _source(self) -> str:
        return self.rng.choices(("android_notification", "manual", "file_import"), (5, 3, 2))[0]

    def _record(self, bank_text: str, merchant: str) -> tuple[str, str, str]:
        """(source, description, merchant) as each channel delivers a purchase without extra detail."""
        source = self._source()
        if source == "android_notification":
            return source, bank_text, ""
        if source == "file_import":
            return source, f"VÁSÁRLÁS KÁRTYÁVAL {bank_text.upper()}", ""
        return source, merchant, merchant

    def clear_merchant(self) -> tuple:
        bank_text, merchant, category, amounts = self._by_category(CLEAR_MERCHANTS)
        return (*self._record(bank_text, merchant), self._amount(amounts), category, category)

    def mixed_merchant(self) -> tuple:
        bank_text, merchant, usual, shares, amounts = self.rng.choice(MIXED_MERCHANTS)
        category = self.rng.choices(list(shares), list(shares.values()))[0]
        return (*self._record(bank_text, merchant), self._amount(amounts), category, usual)

    def mixed_with_detail(self) -> tuple:
        _, merchant, usual, shares, amounts = self.rng.choice(MIXED_MERCHANTS)
        category = self.rng.choices(list(shares), list(shares.values()))[0]
        description = f"{merchant} - {self.rng.choice(DETAIL_DESCRIPTIONS[category])}"
        return ("manual", description, merchant, self._amount(amounts), category, usual)

    def unfamiliar_merchant(self) -> tuple:
        bank_text, merchant, category, amounts = self._by_category(UNFAMILIAR_MERCHANTS)
        return (*self._record(bank_text, merchant), self._amount(amounts), category, category)

    def hungarian_description(self) -> tuple:
        description, category, amounts = self._by_category(HUNGARIAN_DESCRIPTIONS)
        return ("manual", description, "", self._amount(amounts), category, category)

    def cryptic_text(self) -> tuple:
        bank_text, categories = self.rng.choice(CRYPTIC_TEXTS)
        source = self.rng.choice(("android_notification", "file_import"))
        description = bank_text if source == "android_notification" else f"VÁSÁRLÁS KÁRTYÁVAL {bank_text}"
        amount = str(self.rng.randrange(800, 30000, 10))
        return (source, description, "", amount, self.rng.choice(categories), "")


def _split_of(item_id: str) -> str:
    """dev or test, fixed per item from a hash, the same way as the matching dataset."""
    return "dev" if hashlib.sha256(item_id.encode()).digest()[0] % 2 == 0 else "test"


def generate(seed: int = 2026) -> list[Item]:
    builder = _Builder(seed)
    drawn = [(scenario, ambiguity, getattr(builder, scenario)())
             for scenario, ambiguity, count in SCENARIOS for _ in range(count)]
    builder.rng.shuffle(drawn)
    items = []
    for index, (scenario, ambiguity, (source, description, merchant, amount, category, usual)) in enumerate(drawn, start=1):
        item_id = f"C{index:04d}"
        items.append(Item(item_id, scenario, ambiguity, _split_of(item_id), source, description, merchant,
                          amount, "HUF", category, usual))
    return items


def write_csv(items: list[Item], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(Item)], lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(item) for item in items)


def read_csv(path: Path) -> list[Item]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [Item(**row) for row in csv.DictReader(handle)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the synthetic categorization dataset.")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=Path("tests/data/categorization_eval.csv"))
    args = parser.parse_args()
    items = generate(args.seed)
    write_csv(items, args.out)
    ambiguous = sum(item.ambiguity == "ambiguous" for item in items)
    print(f"Wrote {len(items)} items ({ambiguous} ambiguous) to {args.out}")


if __name__ == "__main__":
    main()
