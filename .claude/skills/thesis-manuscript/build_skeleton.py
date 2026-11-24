"""Builds the Word skeleton of the Hungarian thesis manuscript, with the Python standard library only.

Run from the repository root:
    python .claude/skills/thesis-manuscript/build_skeleton.py --out thesis/szakdolgozat.docx

It writes a .docx with the layout of an SZTE Informatikai Intézet thesis (A4, Times New Roman 12 pt,
1.5 line spacing, justified, 2.5 cm margins; cover and title page without page numbers; from the
task description on: the title in the header and the page number in the footer, starting at 1),
the required parts in their order, numbered chapter headings (Heading 1-3, so Word's table of
contents picks them up), and the drafts Claude wrote as tracked insertions by the author "Claude",
so that the author sees, accepts or rewrites every drafted sentence in Word. Placeholders are
highlighted and start with "⟨". The author's personal motivation is read from a JSON file outside
the repository (--drafts), because the repository is public. It refuses to overwrite an existing file: the manuscript is
edited in Word after this first build, never regenerated.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

TITLE = "FinSync – Családi költéskövetés tranzakció-egyeztetéssel és hibrid kategorizálással"
AUTHOR = "Varga Bence Tamás"
DRAFT_AUTHOR = "Claude"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# The skeleton: (kind, text). Kinds: cover, titlepage, h1u (unnumbered heading 1), h1, h2, h3,
# p (author text or placeholder), draft (Claude's draft, tracked), toc, label (bold run + draft),
# pagebreak, section (end of the unnumbered front section).
TASK = (
    "A feladat egy webes és mobil klienssel rendelkező rendszer (FinSync) tervezése és megvalósítása, "
    "amely egy 2–4 fős háztartás tagjainak banki értesítéseiből, banki exportfájljaiból és kézi "
    "bejegyzéseiből egyetlen, ellenőrizhető vásárlási listát állít elő. A rendszer központi feladata a "
    "források közötti tranzakció-egyeztetés: az ugyanazt a vásárlást leíró rekordok összekapcsolása úgy, "
    "hogy a hasonló, de különálló vásárlások ne olvadjanak össze, a bizonytalan esetekről egy tag "
    "döntsön, és minden döntés visszakövethető és visszavonható legyen. További feladat a költések "
    "kategorizálása szabályalapú és nagy nyelvi modellre (LLM) épülő módszer kombinálásával, a módszerek "
    "mérése címkézett szintetikus adathalmazon, valamint a pénzügyi adatok biztonságos, adatminimalizáló "
    "kezelése (hitelesítés, csoportonkénti elkülönítés). A megvalósítás Python (FastAPI) backenddel, "
    "React webes felülettel és Android klienssel történik."
)
# Personal parts (the author's motivation) are never in this file: the repository is public. They
# come from a JSON file outside the repository (--drafts), with the keys below; without it, the
# skeleton has placeholders there.
DRAFT_KEYS = {
    "feladatkiiras_problem": "⟨A probléma két-három mondatban, a szerző saját helyzetéből.⟩",
    "bevezetes_motivacio": "⟨A szerző motivációja: miért ez a téma, és mit akart megtanulni.⟩",
}

SKELETON: list[tuple[str, str]] = [
    ("cover", ""),
    ("titlepage", ""),
    ("section", ""),
    ("h1u", "Feladatkiírás"),
    ("draft-key", "feladatkiiras_problem"),
    ("draft", TASK),
    ("p", "⟨A végleges szöveg a témavezetővel egyeztetett, a Neptunban rögzített feladatkiírás.⟩"),
    ("pagebreak", ""),
    ("h1u", "Tartalmi összefoglaló"),
    ("label", "Téma megnevezése:|" + TITLE),
    ("label", "A megadott feladat megfogalmazása:|" + TASK.split(". ")[0] + "."),
    ("label", "Megoldási mód:|A rekordokat egy közös feldolgozási lánc normalizálja és egyezteti; az "
     "egyeztetés szabályalapú pontszámot számol, a biztos eseteket automatikusan összekapcsolja, a "
     "bizonytalanokat egy tag elé viszi. A kategorizálás rétegzett: csoportszabály, beépített magyar "
     "szótár, végül nagy nyelvi modell, öt válasz egyezéséből számolt bizonyossággal."),
    ("label", "Alkalmazott eszközök, módszerek:|Python, FastAPI, SQLAlchemy, Alembic, SQLite és "
     "PostgreSQL, React és TypeScript, Kotlin (Android), fejlesztési és tesztrészre bontott szintetikus "
     "adathalmazok, Claude Code ágensskillekkel."),
    ("label", "Elért eredmények:|⟨Az M3 mérések számai a docs/evaluation/results fájlokból, a v0.9.0 tag "
     "után.⟩"),
    ("label", "Kulcsszavak:|tranzakció-egyeztetés, duplikátumszűrés, kategorizálás, nagy nyelvi modell, "
     "költéskövetés, FastAPI, React, Android"),
    ("pagebreak", ""),
    ("h1u", "Tartalomjegyzék"),
    ("toc", ""),
    ("pagebreak", ""),
    ("h1u", "Bevezetés"),
    ("draft-key", "bevezetes_motivacio"),
    ("p", "⟨A dolgozat célja és felépítése fejezetenként. Források: README.md, docs/overview.md.⟩"),
    ("pagebreak", ""),
    ("h1", "A probléma és a meglévő megoldások"),
    ("p", "⟨Források: docs/overview.md, docs/design/transaction-matching.md; meglévő költéskövetők, "
     "banki alkalmazások és közös költségmegosztók összevetése táblázatban.⟩"),
    ("h2", "Több bank, több forrás: miért nehéz az egyeztetés"),
    ("h2", "Meglévő megoldások összevetése"),
    ("pagebreak", ""),
    ("h1", "Követelmények, szerepkörök és használati esetek"),
    ("p", "⟨Források: docs/architecture/design-views.md (1. nézet), docs/design/user-interface.md, "
     "ADR 0012.⟩"),
    ("h2", "Szerepkörök: adminisztrátor és tag"),
    ("h2", "Használati esetek"),
    ("h2", "Nem funkcionális követelmények"),
    ("pagebreak", ""),
    ("h1", "Architektúra és technológiák"),
    ("p", "⟨Források: docs/architecture/ (nézetek, ADR 0006, 0007, 0009, 0010), finsync/*/README.md.⟩"),
    ("h2", "Rendszerfelépítés"),
    ("h2", "Felhasznált technológiák"),
    ("h2", "Adatmodell"),
    ("pagebreak", ""),
    ("h1", "Tranzakció-egyeztetés"),
    ("p", "⟨Szakdolgozat II. Források: docs/design/transaction-matching.md, docs/evaluation/results.⟩"),
    ("pagebreak", ""),
    ("h1", "Hibrid kategorizálás és nagy nyelvi modell"),
    ("p", "⟨Szakdolgozat II. Források: docs/design/categorization.md, ADR 0011, ADR 0013, "
     "docs/evaluation/results/2026-11-24-categorization-hybrid.md.⟩"),
    ("pagebreak", ""),
    ("h1", "Biztonság és adatvédelem"),
    ("p", "⟨Szakdolgozat II. Források: docs/architecture/security-and-privacy.md, ADR 0009, 0010, "
     "0012.⟩"),
    ("pagebreak", ""),
    ("h1", "Kliensek: webes felület és Android-alkalmazás"),
    ("p", "⟨Szakdolgozat II. Források: web/README.md, clients/android/README.md, a demó képernyőképei.⟩"),
    ("pagebreak", ""),
    ("h1", "Tesztelés és kiértékelés"),
    ("p", "⟨Szakdolgozat II. Források: tests/README.md, docs/evaluation/ (terv, adathalmazok, eredmények).⟩"),
    ("pagebreak", ""),
    ("h1", "MI-támogatott fejlesztési módszertan"),
    ("p", "⟨Szakdolgozat II. Részletesen két ágensskill: endpoint-and-screen-checklist és "
     "dev-test-evaluation (témavezető, 2026-11-16, D1). Források: docs/ai-usage.md, .claude/skills/. "
     "Itt kell leírni azt is, hogy a kézirat szövegét Claude tervezte, a szerző átírta és ellenőrizte.⟩"),
    ("pagebreak", ""),
    ("h1", "Tapasztalatok, korlátok és továbbfejlesztési lehetőségek"),
    ("p", "⟨Szakdolgozat II. Források: a release notes korlátai, docs/planning/roadmap.md (Future work).⟩"),
    ("pagebreak", ""),
    ("h1u", "Irodalomjegyzék"),
    ("p", "⟨1. Név: https://… (Utolsó megtekintés: ÉÉÉÉ. HH. NN.)⟩"),
    ("pagebreak", ""),
    ("h1u", "Nyilatkozat"),
    ("p", "⟨A hivatalos nyilatkozat szövege a TTIK űrlapjáról, a szerző nevével, a gazdaságinformatikus "
     "BSc szakkal, a tanszékkel, a dátummal és az aláírással.⟩"),
    ("pagebreak", ""),
    ("h1u", "Köszönetnyilvánítás"),
    ("p", "⟨A szerző írja.⟩"),
    ("pagebreak", ""),
    ("h1u", "Elektronikus mellékletek"),
    ("p", "⟨1. A FinSync forráskódja: https://github.com/h270445/FinSync (tag: v1.0.0, commit: a tag "
     "teljes azonosítója) (Utolsó megtekintés: ÉÉÉÉ. HH. NN.)⟩"),
    ("pagebreak", ""),
    ("h1u", "Mellékletek"),
    ("p", "⟨Képernyőképek és ábrák, „n.n.n. ábra: …” felirattal.⟩"),
]

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def run(text: str, *, bold: bool = False, size: int | None = None, highlight: bool = False) -> str:
    props = ""
    if bold:
        props += "<w:b/>"
    if size:
        props += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    if highlight:
        props += '<w:highlight w:val="yellow"/>'
    rpr = f"<w:rPr>{props}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


class Ids:
    value = 0

    @classmethod
    def next(cls) -> int:
        cls.value += 1
        return cls.value


def tracked(inner: str) -> str:
    return f'<w:ins w:id="{Ids.next()}" w:author="{DRAFT_AUTHOR}" w:date="{NOW}">{inner}</w:ins>'


def para(runs: str, *, style: str | None = None, align: str | None = None, numbered: bool = True,
         spacing_before: int | None = None) -> str:
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if style == "Heading1" and not numbered:
        ppr += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'
    if spacing_before is not None:
        ppr += f'<w:spacing w:before="{spacing_before}"/>'
    if align:
        ppr += f'<w:jc w:val="{align}"/>'
    return f"<w:p><w:pPr>{ppr}</w:pPr>{runs}</w:p>"


def text_runs(text: str) -> str:
    """Placeholders (⟨…⟩) are highlighted so they are found before submission."""
    return run(text, highlight=text.startswith("⟨"))


def body(drafts: dict[str, str]) -> str:
    parts = []
    for kind, text in SKELETON:
        if kind == "cover":
            parts += [
                para(run("Szegedi Tudományegyetem", bold=True, size=32), align="center", spacing_before=1200),
                para(run("Informatikai Intézet", bold=True, size=28), align="center"),
                para(run("SZAKDOLGOZAT", bold=True, size=40), align="center", spacing_before=4800),
                para(run(AUTHOR, size=28), align="center", spacing_before=4800),
                para(run("⟨év⟩", size=28, highlight=True), align="center"),
                para('<w:r><w:br w:type="page"/></w:r>'),
            ]
        elif kind == "titlepage":
            parts += [
                para(run("Szegedi Tudományegyetem", size=28), align="center"),
                para(run("Informatikai Intézet", size=28), align="center"),
                para(tracked(run(TITLE, bold=True, size=36)), align="center", spacing_before=3600),
                para(run("Szakdolgozat", size=28), align="center"),
                para(run("Készítette:", bold=True) + run("\t") + run("Témavezető:", bold=True),
                     spacing_before=3600),
                para(run(AUTHOR) + run("\t") + run("Dr. Bilicki Vilmos")),
                para(run("gazdaságinformatikus szakos hallgató (nappali tagozat)") + run("\t") +
                     run("⟨beosztás⟩", highlight=True)),
                para(run("Szeged, ⟨év⟩", highlight=True), align="center", spacing_before=2400),
            ]
        elif kind == "section":
            # End of the front section: no header, no page numbers.
            parts.append(
                '<w:p><w:pPr><w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" '
                'w:footer="709" w:gutter="0"/></w:sectPr></w:pPr></w:p>'
            )
        elif kind == "h1u":
            parts.append(para(run(text), style="Heading1", numbered=False))
        elif kind in ("h1", "h2", "h3"):
            parts.append(para(run(text), style=f"Heading{kind[1]}"))
        elif kind == "p":
            parts.append(para(text_runs(text)))
        elif kind == "draft":
            parts.append(para(tracked(run(text))))
        elif kind == "draft-key":
            parts.append(para(tracked(run(drafts[text])) if text in drafts else text_runs(DRAFT_KEYS[text])))
        elif kind == "label":
            label, value = text.split("|", 1)
            value_runs = text_runs(value) if value.startswith("⟨") else tracked(run(value))
            parts.append(para(run(label, bold=True)))
            parts.append(para(value_runs))
        elif kind == "toc":
            parts.append(
                '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
                '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
                '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                + run("A tartalomjegyzék frissítése: jobb kattintás → Mező frissítése.", highlight=True)
                + '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
            )
        elif kind == "pagebreak":
            parts.append(para('<w:r><w:br w:type="page"/></w:r>'))
    # Main section: header with the title, page number in the footer, numbering restarts at 1.
    sect = (
        '<w:sectPr><w:headerReference w:type="default" r:id="rIdHeader"/>'
        '<w:footerReference w:type="default" r:id="rIdFooter"/>'
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418" w:header="709" w:footer="709" '
        'w:gutter="0"/><w:pgNumType w:start="1"/></w:sectPr>'
    )
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>' \
           + "".join(parts) + sect + "</w:body></w:document>"


STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {W}>
<w:docDefaults>
<w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="hu-HU"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr><w:spacing w:before="240" w:after="240"/><w:jc w:val="left"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr><w:spacing w:before="240" w:after="120"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:keepNext/><w:numPr><w:ilvl w:val="2"/><w:numId w:val="1"/></w:numPr><w:spacing w:before="120" w:after="120"/><w:jc w:val="left"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
<w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:i/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Header"><w:name w:val="header"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr><w:rPr><w:sz w:val="20"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr></w:style>
</w:styles>"""

NUMBERING = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering {W}>
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="multilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="Heading1"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="567" w:hanging="567"/></w:pPr></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="Heading2"/><w:lvlText w:val="%1.%2."/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="709" w:hanging="709"/></w:pPr></w:lvl>
<w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:pStyle w:val="Heading3"/><w:lvlText w:val="%1.%2.%3."/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="851" w:hanging="851"/></w:pPr></w:lvl>
</w:abstractNum>
<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>
</w:numbering>"""

HEADER = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr {W}><w:p><w:pPr><w:pStyle w:val="Header"/></w:pPr>{run(TITLE)}</w:p></w:hdr>"""

FOOTER = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr {W}><w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>"""

SETTINGS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings {W}><w:defaultTabStop w:val="4536"/><w:updateFields w:val="true"/><w:themeFontLang w:val="hu-HU"/></w:settings>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rIdNumbering" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
<Relationship Id="rIdSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
<Relationship Id="rIdHeader" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>"""

CORE = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>{escape(TITLE)}</dc:title><dc:creator>{escape(AUTHOR)}</dc:creator><dc:language>hu-HU</dc:language>
<dcterms:created xsi:type="dcterms:W3CDTF">{NOW}</dcterms:created></cp:coreProperties>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--drafts", type=Path, help="JSON with the personal drafts (kept outside the repository)")
    args = parser.parse_args()
    drafts = json.loads(args.drafts.read_text(encoding="utf-8")) if args.drafts else {}
    unknown = set(drafts) - set(DRAFT_KEYS)
    if unknown:
        print(f"unknown draft keys: {', '.join(sorted(unknown))}", file=sys.stderr)
        return 1
    if args.out.exists():
        print(f"{args.out} exists; the manuscript is edited in Word, not rebuilt", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    files = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "docProps/core.xml": CORE,
        "word/document.xml": body(drafts),
        "word/styles.xml": STYLES,
        "word/numbering.xml": NUMBERING,
        "word/settings.xml": SETTINGS,
        "word/header1.xml": HEADER,
        "word/footer1.xml": FOOTER,
        "word/_rels/document.xml.rels": DOC_RELS,
    }
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    print(f"written {args.out}: {sum(1 for k, _ in SKELETON if k.startswith('h1'))} headings of level 1, "
          f"{Ids.value} tracked drafts by {DRAFT_AUTHOR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
