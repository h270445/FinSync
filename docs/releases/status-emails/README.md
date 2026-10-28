# Status e-mails to the supervisor

The text of every progress e-mail sent to the thesis supervisor, one file per e-mail. **This folder is in Hungarian on purpose**, because the e-mails are; it is the only exception to the English-only rule in [docs/README.md](../../README.md#conventions).

- The English release notes in [releases/](../README.md) remain the official description of each milestone; the e-mail is a short Hungarian summary that points to the tag.
- File name: `YYYY-MM-DD-<milestone or topic>.md`, for example `2026-10-09-m0.md`.
- Commit the text in the same pull request as the release notes, before sending. After sending, set `Státusz: elküldve` and the send date; later corrections go into a new e-mail, not into the sent one.
- No personal data beyond the supervisor's name and the author's name and programme. The Neptun code stays a `<Neptun-kód>` placeholder and is filled in only in the e-mail itself. No e-mail addresses, passwords, tokens or real financial data.
- Sign-off: full name, Neptun code, and programme with mode of study, each on its own line (see the template).
- Layout: one blank line between paragraphs, before and after each bold section heading, and around each list; one short paragraph or list per section. Check that the text keeps its paragraphs when pasted into Gmail before sending.
- Link the commit with its full URL, so the supervisor can open it from the e-mail.

## Index

| Date | Milestone | Tag | Status |
| --- | --- | --- | --- |
| 2026-10-09 | [M0 — félévi vállalás](2026-10-09-m0.md) | `0.1.0` | Sent |
| 2026-10-28 | [Köztes jelzés — a párosítás állása](2026-10-28-koztes-jelzes.md) (planned for Oct 22, sent later) | – | Sent |

## Template

```markdown
# <dátum> — <mérföldkő>

- Címzett: <témavezető neve>
- Tag: `vX.Y.Z` (commit: `<teljes commit azonosító>`)
- Státusz: vázlat | elküldve (<dátum>)

---

**Tárgy:** FinSync szakdolgozat – <mérföldkő> (<tag>)

Tisztelt <megszólítás>!

<1–2 mondat: mit tartalmaz ez a mérföldkő.>

**Elkészült**

- ...

**Hogyan ellenőrizhető**

- ...

**Eltérések a tervtől, kockázatok**

- ...

**Következő lépések (<következő határidő>)**

- ...

A repository: https://github.com/h270445/FinSync (tag: `<tag>`, commit: https://github.com/h270445/FinSync/commit/<teljes commit azonosító>)

Üdvözlettel:  
Varga Bence Tamás  
<Neptun-kód>  
Gazdaságinformatikus nappali hallgató
```
