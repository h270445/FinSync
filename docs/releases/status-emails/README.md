# Status e-mails to the supervisor

The text of every progress e-mail sent to the thesis supervisor, one file per e-mail. **This folder is in Hungarian on purpose**, because the e-mails are; it is the only exception to the English-only rule in [docs/README.md](../../README.md#conventions).

- The English release notes in [releases/](../README.md) remain the official description of each milestone; the e-mail is a short Hungarian summary that points to the tag.
- File name: `YYYY-MM-DD-<milestone or topic>.md`, for example `2026-10-09-m0.md`.
- Commit the text in the same pull request as the release notes, before sending. After sending, copy the sent text back into the file (the author may change wording in Gmail), set `Státusz: elküldve` and the send date; later corrections go into a new e-mail, not into the sent one.
- No personal data beyond the supervisor's name and the author's name and programme. The Neptun code stays a `<Neptun-kód>` placeholder and is filled in only in the e-mail itself. No e-mail addresses, passwords, tokens or real financial data.
- Sign-off: `Üdvözlettel:` and the full name in bold, then the Neptun code and the programme with mode of study, each on its own line (see the template).
- Subject: `Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - <téma>`, where the topic names the milestone or the report (for example `M2: <cím> (v0.3.0)` or `Heti jelentés (november 9–15.)`).
- Layout: a blank line above each bold section heading and above the sign-off, and no blank line below a heading (the first line of the section follows right under it); the bold greeting is followed directly by the first paragraph. One short paragraph or list per section. Check that the text keeps its line breaks when pasted into Gmail before sending. The sent e-mail of 2026-11-14 is the reference: [example-sent-email.md](../../../.claude/skills/supervisor-status-email/example-sent-email.md).
- Link the commit with its full URL, so the supervisor can open it from the e-mail.

## Index

| Date | Milestone | Tag | Status |
| --- | --- | --- | --- |
| 2026-10-09 | [M0 — félévi vállalás](2026-10-09-m0.md) | `0.1.0` | Sent |
| 2026-10-28 | [Köztes jelzés — a párosítás állása](2026-10-28-koztes-jelzes.md) (planned for Oct 22, sent later) | – | Sent |
| 2026-11-02 | [M1 — működő mag](2026-11-02-m1.md) | `v0.2.0` | Sent on 2026-11-07, after the deadline |
| 2026-11-14 | [Heti jelentés (november 9–15.)](2026-11-14-heti-jelentes.md) | – | Sent |
| 2026-11-21 | [Heti jelentés (november 16–22.)](2026-11-21-heti-jelentes.md) | – | Draft |
| 2026-11-25 | [M2 zárócsomag, előzetes](2026-11-25-m2-zarocsomag-elozetes.md) | `v0.3.0` on 2026-12-04 | Draft |

## Template

```markdown
# <dátum> — <mérföldkő vagy téma>

- Címzett: <témavezető neve>
- Tag: `vX.Y.Z` (commit: `<teljes commit azonosító>`)
- Státusz: vázlat | elküldve (<dátum>)

---

**Tárgy:** Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - <téma>

**Tisztelt <megszólítás>!**  
<1–2 mondat: mit tartalmaz ez a mérföldkő, és válasz a legutóbbi levélre.>

**Elkészült**
- ...

**Hogyan ellenőrizhető**
- ...

**Eltérések a tervtől, kockázatok**
- ...

**Következő lépések** (<következő határidő>)
- ...
- A repository: https://github.com/h270445/FinSync (tag: `<tag>`, commit: https://github.com/h270445/FinSync/commit/<teljes commit azonosító>)

**Üdvözlettel:**  
**Varga Bence Tamás**  
<Neptun-kód>  
Gazdaságinformatikus nappali hallgató
```
