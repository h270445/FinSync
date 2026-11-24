---
name: thesis-manuscript
description: Use when working on the Hungarian FinSync thesis manuscript (Word), for example the December skeleton, a chapter draft, the Feladatkiírás or the Tartalmi összefoglaló. Drafts Hungarian text from the repository's evidence for the author to rewrite, in the SZTE format, with every claim and number traced to a commit, test or result file.
---

# Thesis manuscript

- Version: 1.0 (2026-11-24)
- Owner: Bence Varga
- Why it exists: the BSc thesis is written in Hungarian in Word, from the English evidence in `docs/` (the [thesis map](../../../docs/thesis-map.md)). The supervisor asked for the skeleton of the first chapters in December (2026-11-16). The author decided on 2026-11-24: Word as the tool; Claude Code writes Hungarian draft text and the author rewrites and checks it, which chapter 9 says openly; the December skeleton is the Bevezetés and chapters 1–3. Without fixed rules a draft could carry numbers from memory, invented sources or terms that differ from the UI.

## Input

- The chapter or part to work on, and the current manuscript: the author's Word file in the project files, `/mnt/project-files/thesis/` (never in the repository: it is a binary and holds the author's personal motivation).
- The evidence the [thesis map](../../../docs/thesis-map.md) lists for that chapter, and the [terminology](terminology.md).
- The format the author observed in a sample SZTE thesis (summarised below; the sample itself is another student's work and is never copied or stored).

## Output

1. A Hungarian draft as a separate Word file in `/mnt/project-files/thesis/` (`fejezet-<n>-tervezet-v<k>.docx`, or `FinSync-szakdolgozat-vaz-v<k>.docx` for the skeleton), built with the generator in `/mnt/project-files/thesis/tools/` (docx-js, available in the agent's environment; not a repository dependency). Each drafted part starts with a grey note "MI-tervezet, a szerző átírja", which the author deletes when the part is rewritten.
2. Next to each paragraph group, a grey "Repó:" note naming the evidence (file, test, result file, commit), so the author can check and cite it.
3. In the repository: the thesis map row of the chapter updated ("draft v<k> delivered on ..."), an `ai-usage.md` log row (what was drafted, how it was checked) and, when the author states one, the author decision.
4. `python .claude/skills/thesis-manuscript/check_manuscript.py <file.docx>` prints OK on every delivered file (layout, part order, summary labels, captions, reference format and citations, avoided words of the terminology); before submission the author runs it with `--final`, which also refuses placeholders, AI-draft markers, "Repó:" notes, tracked changes and a missing commit id.
5. A short report: what was drafted, the open `[KITÖLTENDŐ]` and `[ELLENŐRIZENDŐ]` points, and questions for the author.

## Format (SZTE practice, from the sample the author provided)

- Word, A4, Times New Roman 12 pt, about 25 mm margins, the thesis title in every header, page numbers from the Feladatkiírás (starting at 1).
- Order: cover, title page (title, Készítette / Témavezető with position, major, Szeged, year), Feladatkiírás, Tartalmi összefoglaló with the fixed subheadings (A téma megnevezése, A megadott feladat megfogalmazása, A megoldási mód, Alkalmazott eszközök, módszerek, Elért eredmények, Kulcsszavak), Tartalomjegyzék, Bevezetés (unnumbered), numbered chapters, Irodalomjegyzék, Nyilatkozat, Köszönetnyilvánítás, Elektronikus mellékletek, Mellékletek.
- Figures numbered per chapter ("3.1. ábra"), with a caption under each; tables likewise ("3.1. táblázat").
- References: a numbered list, cited as [n] in the text; a web source with its URL and "Utolsó megtekintés: ÉÉÉÉ. HH. NN.".
- Electronic appendix: the GitHub repository, the branch, the release tag and the full commit hash.
- The author's details: Varga Bence, gazdaságinformatikus BSc, nappali tagozat (TTIK); supervisor Dr. Bilicki Vilmos (position to be filled in by the author).
- The working outline: Bevezetés; 1. A probléma és a meglévő megoldások; 2. Követelmények, szerepkörök és használati esetek; 3. Architektúra és technológiák; 4. Tranzakció-egyeztetés; 5. Hibrid kategorizálás és nyelvi modell; 6. Biztonság és adatvédelem; 7. Kliensek és adatforrások; 8. Tesztelés és kiértékelés; 9. MI-támogatott fejlesztési módszertan (endpoint-and-screen-checklist and dev-test-evaluation in depth, author's choice of 2026-11-24); 10. Korlátok és továbbfejlesztés.

## Prohibitions

- **Never copy text, sentences or distinctive wording from the sample thesis or any other thesis**, and never store the sample or an extract of it in the repository or in an output file. Only the format conventions above are taken from it.
- **Never put a number in the draft that is not in a result file, a test output of this session or a linked document**; numbers are copied, not recalled. A number that cannot be traced is left as `[ELLENŐRIZENDŐ]`.
- **Never invent a source.** A reference enters the Irodalomjegyzék only after the page was opened in this session, with the date; otherwise the claim is marked `[FORRÁS ELLENŐRIZENDŐ]`.
- Never overwrite the author's edited manuscript. Drafts are new files; a change to the author's file is made only when asked, and then as tracked changes.
- Never write in the author's name what the author did not do or decide, and never present AI-drafted text as written by the author: the drafts carry their marker until the author rewrites them, and chapter 9 describes the method. The Nyilatkozat and the Köszönetnyilvánítás are the author's own.
- Never put the author's personal motivation (family finances, workplace), another person's data, an e-mail address or a token in the repository; they belong only in the Word files in the project files. The Bevezetés asks the author how much of the family background is to appear in the public thesis.
- Never put the Feladatkiírás draft forward as final: the supervisor issues it; the draft is marked "TERVEZET".
- Never use a term that differs from the UI or the [terminology](terminology.md) for the same thing; a new term is added to the terminology first.
- Never name a model identifier except where the result files do (the measured categorizer in chapter 8).

## Steps

1. **Scope.** Which part, which version of the manuscript, which evidence (thesis map row). Read the evidence files, not summaries of them.
2. **Outline first.** For a new chapter: section headings with one line each and the evidence per section. The author confirms the outline before the prose (checkpoint 1).
3. **Draft.** Hungarian, plain academic register, first person plural avoided where the sample's practice is impersonal; short paragraphs; terms from the terminology; each claim with its "Repó:" note; figures from the design views rendered to PNG (Mermaid, the render step of the [docs-and-comments](../docs-and-comments/SKILL.md) skill) and numbered per chapter.
4. **Build, check and look.** Run the generator, then `check_manuscript.py` on the file (OK required), convert the file to PDF and look at the pages (headers, page numbers, headings, captions); fix and rebuild.
5. **Log.** Thesis map row, `ai-usage.md` log row ("Hungarian draft of chapter N, checked against ..."), time log through the [session-wrap-up](../session-wrap-up/SKILL.md) skill.

## Self-check

- Every number in the draft appears in a linked result file or a command output of the session.
- Every reference has a URL or bibliographic data and a "last opened" date from this session.
- No paragraph without a "Repó:" note in a chapter about the system.
- `grep` of the repository diff finds no Hungarian sentence of the Word draft (the drafts stay in the project files).
- The terms of the draft are in the terminology, and `check_manuscript.py` prints OK.

## Human checkpoints

1. **Before** the prose of a chapter: the author confirms the outline.
2. **Before** the family background or any personal detail appears in a draft: the author says how much of it goes into the public thesis.
3. **After**: the author rewrites the draft in Word; the AI marker is removed only by the author.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-24 | First version, from the sample SZTE thesis the author provided (format only) and the author's decisions of 2026-11-24: Word, AI drafts that the author rewrites, the December skeleton of the Bevezetés and chapters 1–3. The checker `check_manuscript.py` (standard library only) taken from the parallel Remote Control draft at the author's choice, reading the Avoid column of the terminology. |
