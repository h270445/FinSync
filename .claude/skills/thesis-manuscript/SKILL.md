---
name: thesis-manuscript
description: Use when working on the Hungarian FinSync thesis manuscript (Word, SZTE TTIK gazdaságinformatikus BSc), for example drafting a chapter, the task description or the summary, adding figures or references, or checking the manuscript before a milestone or submission. Claude drafts Hungarian text as tracked changes from the repository's evidence; the author rewrites and accepts it. Includes a skeleton builder, a manuscript checker and the term glossary.
---

# Thesis manuscript

- Version: 1.0 (2026-11-24)
- Owner: Bence Varga
- Why it exists: the thesis is written in Hungarian in Word, in the SZTE layout, from the English `docs/` and the [thesis map](../../../docs/thesis-map.md); the skeleton of the first chapters is due on Dec 14–18 (supervisor, 2026-11-16) and the full text in Szakdolgozat II. Every claim in it must match the code, the tests and the measured results, the Hungarian terms must match the web app, and the reader must be able to tell what the author wrote and what was drafted by AI. The layout rules below were measured from a sample SZTE Informatikai Intézet thesis of 2026 with the same supervisor, which the author has (it is not public and is not stored or quoted here).

## Author's decisions (2026-11-24)

- The manuscript is a **Word** document.
- **Claude drafts Hungarian text, the author rewrites and checks it** (option b of the skill review). Every drafted passage goes into the document as a **tracked insertion by the author "Claude"**, so the author sees each one and accepts it or rewrites it in Word; the methods chapter says openly how the text was made.
- Degree: **gazdaságinformatikus BSc, nappali tagozat**, SZTE TTIK Informatikai Intézet; supervisor Dr. Bilicki Vilmos.
- Chapters (see the skeleton): Bevezetés; 1. A probléma és a meglévő megoldások; 2. Követelmények, szerepkörök és használati esetek; 3. Architektúra és technológiák; 4. Tranzakció-egyeztetés; 5. Hibrid kategorizálás és nagy nyelvi modell; 6. Biztonság és adatvédelem; 7. Kliensek; 8. Tesztelés és kiértékelés; 9. MI-támogatott fejlesztési módszertan; 10. Tapasztalatok, korlátok és továbbfejlesztési lehetőségek. The December skeleton covers Bevezetés and chapters 1–3.
- The methods chapter presents two skills in depth: [endpoint-and-screen-checklist](../endpoint-and-screen-checklist/SKILL.md) and [dev-test-evaluation](../dev-test-evaluation/SKILL.md) (the supervisor's suggestion of 2026-11-16, D1).

## Input

- The chapter or part to work on, and the current manuscript file from the author (the latest copy; the author keeps the master).
- The evidence: the thesis map's row for that topic, the docs and ADRs it links, the result files in `docs/evaluation/results/`, the release notes, the code and tests.

## Output

1. The manuscript with the new drafts as tracked insertions by "Claude", handed back to the author (SendUserFile), and the checker's output.
2. A short report in the reply, in Hungarian: per drafted paragraph its evidence (file, section, commit or result file), the open questions, and what the author should rewrite in their own words (opinions, experience, motivation).
3. A row in `docs/ai-usage.md` (Log: which part was drafted, how many paragraphs, how it was checked), the evidence for chapter 9.

## Where the manuscript lives

The repository is **public**; the manuscript holds the author's personal motivation and will be submitted before it is published by the university. So the Word file is **not committed**: `thesis/` is ignored by git, the author keeps the master (for example in OneDrive) and gives Claude a copy for each session. Personal drafts for the skeleton (`--drafts`) are kept outside the repository as well. What is committed: this skill, its helpers and the glossary. If the author later decides to commit the manuscript, that is a change to this section and to `.gitignore`.

## Prohibitions

- **Never write a claim without evidence.** Every statement about FinSync points to a file, a test, an ADR or a result; every number comes from a committed result file or a gate output with its commit. A number that will change before submission (test counts, measurements) is marked in the report so it is refreshed at M3.
- **Never accept, reject or silently change the author's text.** Claude's changes are tracked insertions and deletions by "Claude"; text the author wrote is changed only as a tracked change with the reason in the report. Never accept tracked changes on the author's behalf.
- **Never copy text** from the sample thesis or any other thesis, article or web page. Facts from outside sources are written in own words and cited; a quotation is short, in quotation marks, with its reference.
- **Never invent a reference.** Every entry in the Irodalomjegyzék was opened and is dated; a source that cannot be checked is not cited.
- **No personal data** of anyone but the author; the author's personal details only where the author gave them for the manuscript, and never in the repository. Figures and screenshots use the synthetic demo data (`python -m finsync.api.demo`), never real transactions.
- Never draft the parts that must be the author's own: Köszönetnyilvánítás, the personal judgements in chapter 10, the signature of the Nyilatkozat. For these the skeleton holds a placeholder.
- Never let the terms drift: the [glossary](glossary.md) decides; a new concept gets a row there first.

## Layout (SZTE Informatikai Intézet, measured from the sample)

- A4, Times New Roman 12 pt, 1.5 line spacing, justified, 2.5 cm margins.
- Cover (university, institute, SZAKDOLGOZAT, name, year) and title page (title, Szakdolgozat, Készítette / Témavezető with the degree and the supervisor's title, Szeged and the year) without page numbers. From the Feladatkiírás on: the title in the header, the page number in the footer, starting at 1.
- Order: Feladatkiírás → Tartalmi összefoglaló (labels: Téma megnevezése, A megadott feladat megfogalmazása, Megoldási mód, Alkalmazott eszközök, módszerek, Elért eredmények, Kulcsszavak) → Tartalomjegyzék → Bevezetés (unnumbered) → numbered chapters → Irodalomjegyzék → Nyilatkozat → Köszönetnyilvánítás → Elektronikus mellékletek → Mellékletek.
- Headings Heading 1–3, numbered "1.", "1.1.", "1.1.1."; the front and back parts unnumbered; the table of contents is a Word field.
- Figures: caption under the figure, numbered within the section, "3.1.1. ábra: …"; large screenshots go to Mellékletek.
- References: numbered list "n. Név: URL (Utolsó megtekintés: ÉÉÉÉ. HH. NN.)", cited in the text as [n].
- Elektronikus mellékletek: the repository URL with the tag and the full commit id of the submitted version.

## Steps

### 0. Skeleton (once, done on 2026-11-24)

```bash
python .claude/skills/thesis-manuscript/build_skeleton.py --out thesis/szakdolgozat.docx --drafts <outside the repo>/thesis-drafts.json
```

It writes the layout above, the parts and chapter headings, placeholders (highlighted, starting with ⟨) with the evidence to use, and the drafts of the Feladatkiírás and the Tartalmi összefoglaló as tracked insertions. It refuses to overwrite: after the first build the master is the author's Word file.

### 1. Outline with evidence

For the chapter at hand, list its sections and, per section, the points and their evidence from the thesis map. Show the outline to the author before drafting (checkpoint 1).

### 2. Draft

- Hungarian, factual, in the first person singular where the author acts ("megterveztem", "mértem"), present tense for how the system works.
- Write into a copy of the author's file: unpack it with `zipfile`, insert paragraphs into `word/document.xml` wrapped in `<w:ins w:author="Claude" w:date="…">` (style `Heading2`/`Heading3` for new sections, `Caption` for captions), keep the rest of the XML byte for byte, zip it again. Delete only placeholders, as tracked deletions.
- Terms from the [glossary](glossary.md); names of screens and buttons exactly as the web app shows them.
- Figures: the design views of [design-views.md](../../../docs/architecture/design-views.md) and screenshots of the demo, numbered by the section.

### 3. Check

```bash
python .claude/skills/thesis-manuscript/check_manuscript.py <copy>.docx            # while writing: must print OK
python .claude/skills/thesis-manuscript/check_manuscript.py <copy>.docx --final    # before submission
```

Then read the draft once against the evidence: every number with its source, no sentence that only sounds right. The agent's computer has no Word: the author opens the file, updates the table of contents (right click → Mező frissítése) and reports anything the layout check cannot see.

### 4. Hand back and log

Send the file to the author, give the evidence table, add the AI-usage row and the time-log row in the session's wrap-up ([session-wrap-up](../session-wrap-up/SKILL.md)).

## Self-check

- `check_manuscript.py` prints `OK`; with `--final` before submission (no placeholder, no tracked change, the commit id present).
- Every drafted paragraph has its evidence in the report; no number without a source.
- `git status` shows no `.docx` and no drafts file; the leak search of session-wrap-up is clean.

## Human checkpoints

1. **Before** drafting a chapter: the author approves its outline.
2. **After** each draft: the author rewrites and accepts every tracked insertion in Word; nothing is accepted for the author.
3. **Before** submission: the author confirms with the supervisor that AI-drafted text, rewritten and checked by the author and disclosed in chapter 9, is acceptable under the faculty's rules and the Nyilatkozat ("saját munkám eredménye"); the final text of the Feladatkiírás is the one recorded in Neptun.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-24 | First version, after the author's decisions on the manuscript (Word, drafts by Claude rewritten by the author, degree, chapters, the two skills of the methods chapter), with the skeleton builder, the checker and the glossary. |
