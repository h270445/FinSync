# Status e-mails to the supervisor

The text of every progress e-mail sent to the thesis supervisor, one file per e-mail. **This folder is in Hungarian on purpose**, because the e-mails are; it is the only exception to the English-only rule in [docs/README.md](../../README.md#conventions).

- The English release notes in [releases/](../README.md) remain the official description of each milestone; the e-mail is a short Hungarian summary that points to the tag.
- File name: `YYYY-MM-DD-<milestone or topic>.md`, for example `2026-10-09-m0.md`.
- Commit the text in the same pull request as the release notes, before sending. After sending, set `Státusz: elküldve` and the send date; later corrections go into a new e-mail, not into the sent one.
- No personal data beyond the supervisor's name (no e-mail addresses); no passwords, tokens or real financial data.

## Index

| Date | Milestone | Tag | Status |
| --- | --- | --- | --- |
| 2026-10-09 | [M0 — félévi vállalás](2026-10-09-m0.md) | `v0.1.0` | Draft |

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

A repository: https://github.com/h270445/FinSync (tag: `<tag>`)

Üdvözlettel:
Varga Bence
```
