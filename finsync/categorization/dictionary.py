"""Built-in Hungarian merchant and keyword dictionary: the hybrid categorizer's deterministic layer.

Two tables, both in the nine allowed categories (`CATEGORIES` in merchant_rules.py):

- **Merchants**: well-known Hungarian chains and services as they appear in bank notifications and
  exports ("SPAR Magyarország Kft.", "MAV-START ZRT", "DM DROGERIE 0855"). An entry applies when every
  word of its key is a word of the merchant (the same normalisation as the group's merchant rules), so
  "spar" covers "SPAR 0123 BUDAPEST". The entry with the most words wins ("mol bubi" before "mol").
  An entry marked **mixed** is a mixed-assortment merchant (Tesco, dm, eMAG): its category is only the
  usual one, so it comes out with `low` confidence ([design](../../docs/design/categorization.md)).
- **Keywords**: words members and banks write in Hungarian and English ("gyógyszertár", "lakbér",
  "étteremben", "Monthly rent"). Matching is accent-free and case-free; a keyword ending in `*` is a
  word prefix, because Hungarian adds suffixes ("étterem*" covers "étteremben"), any other keyword is a
  whole word or phrase.

The tables were written from general knowledge of Hungarian merchants and shopping words, not from the
labelled categorization dataset (the dev/test protocol forbids choosing dictionary entries from test
items). Change them only together with `DICTIONARY_VERSION`, so a measurement names the version it used.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from finsync.categorization.merchant_rules import ascii_lower
from finsync.matching.normalize import merchant_tokens

DICTIONARY_VERSION = "hu-1"


@dataclass(frozen=True)
class MerchantEntry:
    key: str  # normalised words, as merchant_key() would produce them
    category: str
    mixed: bool = False


def _entries(category: str, keys: str, mixed: bool = False) -> tuple[MerchantEntry, ...]:
    return tuple(MerchantEntry(key.strip(), category, mixed) for key in keys.split(",") if key.strip())


# Keys are lowercase and accent-free words; "h m" is H&M, "e on" is E.ON. Short or everyday words are
# only safe as part of a longer key: "bolt" alone is Hungarian for "shop", so Bolt rides are "bolt eu".
MERCHANTS: tuple[MerchantEntry, ...] = (
    # Mixed-assortment merchants: the usual category, always `low`.
    *_entries("groceries", "tesco, spar, interspar, auchan, lidl, aldi, penny, cba, coop", mixed=True),
    *_entries("household", "rossmann, dm, muller, emag, amazon, temu, aliexpress, pepco, tedi", mixed=True),
    *_entries("clothing", "decathlon, shein, kik, sinsay", mixed=True),
    # Clear merchants.
    *_entries(
        "transport",
        "mol, mol bubi, omv, shell, lukoil, bkk, mav, mav start, volanbusz, gysev, bolt eu, uber, "
        "flixbus, wizz air, wizzair, ryanair, hu go, nemzeti mobilfizetesi",
    ),
    *_entries(
        "eating_out",
        "wolt, foodora, foodpanda, mcdonald, burger king, kfc, subway, starbucks, costa coffee, "
        "pizza hut, domino",
    ),
    *_entries(
        "entertainment",
        "netflix, spotify, hbo, disney, cinema city, steam, playstation, youtube premium, jegymester, "
        "eventim, libri, bookline",
    ),
    *_entries(
        "housing_utilities",
        "mvm, e on, elmu, fotav, vizmuvek, tigaz, telekom, yettel, vodafone, digi, invitel",
    ),
    *_entries("health", "benu, dr max"),
    *_entries(
        "clothing",
        "h m, zara, reserved, deichmann, ccc, humanic, bershka, pull bear, new yorker, about you",
    ),
    *_entries("household", "ikea, obi, praktiker, bauhaus, jysk, momax, xxxlutz, kika"),
    *_entries("other", "magyar posta, posta"),
)

# Hungarian and English words, accent-free. "stem*" is a word prefix, anything else a whole word or phrase.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "groceries": (
        "elelmiszer*", "heti bevasarlas*", "nagybevasarl*", "kaja", "kajat", "pekseg*", "zoldseg*",
        "gyumolcs*", "hentes*", "piac*", "tej", "kenyer*", "abc",
        "grocery", "groceries", "supermarket", "market", "food shop*",
    ),
    "eating_out": (
        "etterem*", "etterm*", "gyorsetterem*", "pizzeri*", "pizza*", "bisztro*", "kavezo*", "cukraszd*",
        "bufe*", "kifozde*", "menza*", "ebed*", "vacsor*", "etelfutar*",
        "restaurant*", "cafe", "coffee", "lunch", "dinner", "takeaway",
    ),
    "transport": (
        "benzin*", "tankol*", "uzemanyag*", "gazolaj*", "diesel", "parkol*", "autopalya*", "e matrica*",
        "ematrica*", "vonat", "vonaton", "vonatjegy*", "buszjegy*", "busz", "metro", "taxi*", "menetjegy*", "repjegy*",
        "repulojegy*", "autoszerviz*", "gumiszerviz*",
        "fuel", "petrol", "parking", "train", "bus", "uber", "flight",
    ),
    "housing_utilities": (
        "lakber", "lakbert", "lakberre", "alberlet*", "kozos koltseg*", "kozoskoltseg*", "rezsi*", "villanyszaml*", "aram",
        "aramszaml*", "gazszaml*", "vizdij*", "vizszaml*", "tavho*", "internetszaml*", "telefonszaml*",
        "mobilszaml*", "jelzalog*",
        "rent", "mortgage", "housing", "utility", "utilities", "electricity", "water bill", "gas bill",
    ),
    "health": (
        "gyogyszer*", "patika*", "orvos*", "fogorvos*", "rendelo*", "laborvizsgalat*", "vitamin*",
        "szemuveg*", "optika*", "kontaktlencse*",
        "pharmacy", "doctor", "dentist", "medicine*",
    ),
    "clothing": (
        "ruha*", "ruhazat*", "cipo*", "zokni*", "polo", "polot", "nadrag*", "kabat*", "dzseki*",
        "pulover*", "pulcsi*", "farmernadrag*", "alsonemu*",
        "shirt", "t shirt", "jacket", "shoes", "socks", "trousers", "jeans", "dress", "clothes", "clothing",
    ),
    "entertainment": (
        "mozi*", "szinhaz*", "koncert*", "jatek*", "tarsasjatek*", "konyv", "konyvet", "konyvek*", "konyvesbolt*", "fesztival*", "muzeum*",
        "kiallitas*", "strand*", "uszoda*", "termalfurdo*", "lego",
        "cinema", "movie", "concert", "theatre", "theater", "game", "games", "board game", "book",
        "subscription",
    ),
    "household": (
        "haztartas*", "mososzer*", "tisztitoszer*", "szivacs*", "wc papir*", "toalettpapir*", "izzo*",
        "butor*", "lakberendez*", "barkacs*", "szerszam*", "edeny*", "agynemu*", "torolkozo*",
        "furdoszob*",
        "cleaning", "detergent", "light bulb*", "furniture", "tools", "towel*",
    ),
    "other": ("ajandek*", "gift", "postage"),
}

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def _pattern(keywords: tuple[str, ...]) -> re.Pattern[str]:
    parts = []
    for keyword in keywords:
        if keyword.endswith("*"):
            parts.append(re.escape(keyword[:-1]))
        else:
            parts.append(re.escape(keyword) + r"\b")
    return re.compile(r"\b(?:" + "|".join(parts) + ")")


_KEYWORD_PATTERNS = tuple((category, _pattern(words)) for category, words in KEYWORDS.items())


def find_merchant(text: str | None) -> MerchantEntry | None:
    """The dictionary entry for a merchant name, or None. The entry with the most words wins."""
    words = merchant_tokens(text)
    if not words:
        return None
    applicable = [entry for entry in MERCHANTS if set(entry.key.split()) <= words]
    if not applicable:
        return None
    # Ties keep the table order (max returns the first).
    return max(applicable, key=lambda entry: len(entry.key.split()))


def keyword_categories(text: str) -> list[str]:
    """The categories whose keywords occur in the text, in the order of their first occurrence."""
    normalised = " ".join(_NON_ALPHANUMERIC.sub(" ", ascii_lower(text)).split())
    found: list[tuple[int, str]] = []
    for category, pattern in _KEYWORD_PATTERNS:
        match = pattern.search(normalised)
        if match:
            found.append((match.start(), category))
    return [category for _, category in sorted(found)]
