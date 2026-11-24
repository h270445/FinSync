"""Checks the Word manuscript of the thesis against the SZTE layout and the skill's rules.

Run from the repository root:
    python .claude/skills/thesis-manuscript/check_manuscript.py <manuscript.docx>           # while writing
    python .claude/skills/thesis-manuscript/check_manuscript.py <manuscript.docx> --final   # before submission

Checks, with the Python standard library only: A4 pages with 2.5 cm margins, Times New Roman 12 pt
as the default, the required parts in their order, the six labels of the content summary, figure
captions ("3.1.1. ábra: ..."), the reference list format with "Utolsó megtekintés" and that every
[n] in the text has an entry and every entry is cited, and the glossary's avoided words. It lists
the placeholders (⟨...⟩) and the tracked changes by author. With --final, placeholders, tracked
changes and a missing commit id in "Elektronikus mellékletek" are errors. Prints OK, or the
problems, and exits with 1 on a problem.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{%s}" % NS["w"]
GLOSSARY = Path(__file__).with_name("glossary.md")
REQUIRED_PARTS = [
    "Feladatkiírás",
    "Tartalmi összefoglaló",
    "Tartalomjegyzék",
    "Bevezetés",
    "Irodalomjegyzék",
    "Nyilatkozat",
    "Köszönetnyilvánítás",
    "Elektronikus mellékletek",
]
SUMMARY_LABELS = [
    "Téma megnevezése:",
    "A megadott feladat megfogalmazása:",
    "Megoldási mód:",
    "Alkalmazott eszközök, módszerek:",
    "Elért eredmények:",
    "Kulcsszavak:",
]
CAPTION = re.compile(r"^\d+(\.\d+)*\.? ábra: \S")
REFERENCE = re.compile(r"^(\d+)\. .+: https?://\S+ \(Utolsó megtekintés: \d{4}\. \d{2}\. \d{2}\.\)$")
CITATION = re.compile(r"\[(\d+)\]")
COMMIT = re.compile(r"\b[0-9a-f]{40}\b")


def paragraphs(document: ElementTree.Element) -> list[tuple[str, str]]:
    """(style, text) for every paragraph; deleted text is left out, inserted text is kept."""
    result = []
    for p in document.iter(W + "p"):
        style = p.find("w:pPr/w:pStyle", NS)
        text = "".join(t.text or "" for t in p.iter(W + "t"))
        result.append((style.get(W + "val") if style is not None else "", text.strip()))
    return result


def avoided_words() -> dict[str, str]:
    """Avoid word -> term, from the glossary table."""
    words = {}
    for line in GLOSSARY.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[2] not in ("", "–", "Avoid") and not cells[2].startswith("---"):
            for word in cells[2].split(","):
                words[word.strip()] = cells[1]
    return words


def check(path: Path, final: bool) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    with zipfile.ZipFile(path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))
        styles = ElementTree.fromstring(archive.read("word/styles.xml"))

    for sect in document.iter(W + "sectPr"):
        size, margins = sect.find("w:pgSz", NS), sect.find("w:pgMar", NS)
        if size is None or (size.get(W + "w"), size.get(W + "h")) != ("11906", "16838"):
            problems.append("a section is not A4 portrait")
        if margins is not None and any(abs(int(margins.get(W + side, "1418")) - 1418) > 30
                                       for side in ("top", "right", "bottom", "left")):
            problems.append("a section's margins are not 2.5 cm")
    defaults = styles.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
    font = defaults.find("w:rFonts", NS) if defaults is not None else None
    size = defaults.find("w:sz", NS) if defaults is not None else None
    if font is None or font.get(W + "ascii") != "Times New Roman" or size is None or size.get(W + "val") != "24":
        problems.append("the default font is not Times New Roman 12 pt")

    paras = paragraphs(document)
    headings = [text for style, text in paras if style == "Heading1"]
    positions = [headings.index(part) if part in headings else -1 for part in REQUIRED_PARTS]
    for part, position in zip(REQUIRED_PARTS, positions):
        if position < 0:
            problems.append(f"missing part: {part}")
    found = [p for p in positions if p >= 0]
    if found != sorted(found):
        problems.append("the required parts are not in the order " + ", ".join(REQUIRED_PARTS))

    texts = [text for _, text in paras]
    for label in SUMMARY_LABELS:
        if label not in texts:
            problems.append(f"content summary label missing: {label}")

    for style, text in paras:
        looks_like_caption = style == "Caption" or (len(text) < 200 and re.search(r"(?i)(?<!\w)ábra(?!\w)", text[:30]))
        if looks_like_caption and not CAPTION.match(text):
            problems.append(f"figure caption not in the form 'n.n.n. ábra: ...': {text[:60]}")

    # Reference list: the paragraphs between "Irodalomjegyzék" and the next Heading 1.
    entries, in_refs, body_text = {}, False, []
    for style, text in paras:
        if style == "Heading1":
            in_refs = text == "Irodalomjegyzék"
            continue
        if in_refs and text and not text.startswith("⟨"):
            match = REFERENCE.match(text)
            if match:
                entries[int(match[1])] = text
            else:
                problems.append(f"reference not in the form 'n. Name: URL (Utolsó megtekintés: ÉÉÉÉ. HH. NN.)': {text[:70]}")
        elif not in_refs:
            body_text.append(text)
    cited = {int(n) for text in body_text for n in CITATION.findall(text)}
    for n in sorted(cited - set(entries)):
        problems.append(f"[{n}] is cited but not in the reference list")
    for n in sorted(set(entries) - cited):
        problems.append(f"reference {n} is never cited")

    joined = "\n".join(body_text)
    for word, term in avoided_words().items():
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", joined, re.IGNORECASE):
            problems.append(f"glossary: '{word}' used; the manuscript uses '{term}'")

    placeholders = [text for text in texts if "⟨" in text]
    tracked = Counter(e.get(W + "author", "?") for tag in ("ins", "del") for e in document.iter(W + tag))
    notes.append(f"{len(placeholders)} placeholder paragraph(s)")
    notes.append("tracked changes: " + (", ".join(f"{a}: {n}" for a, n in tracked.items()) or "none"))
    if final:
        problems += [f"placeholder left: {text[:70]}" for text in placeholders]
        if tracked:
            problems.append("tracked changes left; every draft is accepted or rewritten by the author before submission")
        appendix = "\n".join(texts[texts.index("Elektronikus mellékletek"):]) if "Elektronikus mellékletek" in texts else ""
        if not COMMIT.search(appendix):
            problems.append("no full commit id in 'Elektronikus mellékletek'")
    return problems, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manuscript", type=Path)
    parser.add_argument("--final", action="store_true", help="no placeholders, no tracked changes, commit id present")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to a code page
    problems, notes = check(args.manuscript, args.final)
    print("\n".join(notes))
    if problems:
        print("\n".join(problems))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
