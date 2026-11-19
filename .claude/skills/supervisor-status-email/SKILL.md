---
name: supervisor-status-email
description: Use when drafting a FinSync progress or milestone e-mail to the thesis supervisor (M2, M3, M4 or an interim note). Produces the Hungarian draft in docs/releases/status-emails/ from the release notes and the repository state, with every claim checked.
---

# Supervisor status e-mail

- Version: 1.1 (2026-11-14)
- Owner: Bence Varga
- Why it exists: each milestone ends with a Hungarian e-mail that points to a tag and summarises what was done, how to check it and what changed in the plan. The rules are in [status-emails/README.md](../../../docs/releases/status-emails/README.md); this skill adds the order of work and the checks, so a claim in the e-mail always has a commit, a test or a result file behind it.

## Input

- The milestone (M2, M3, M4) or the topic of an interim note or weekly report, and the tag and commit it refers to. A weekly report has no tag: link the merge commit of the session's pull request on `main`.
- The English release notes (`docs/releases/vX.Y.Z.md`), the milestone file, the supervisor's last reply (summary in `docs/planning/supervisor-feedback.md`) and its open actions.

## Output

1. `docs/releases/status-emails/YYYY-MM-DD-<milestone or topic>.md` in Hungarian, following the README's template, with `Státusz: vázlat`, and a row in the README's index.
2. A short report in the reply: the claim–evidence table (below), the open actions from the supervisor's last reply and how the e-mail answers each, and anything the author must fill in.

## Prohibitions

- Never send the e-mail and never ask for the supervisor's e-mail address; the author sends it from Gmail.
- Never put an e-mail address, the Neptun code (it stays `<Neptun-kód>`), a password, a token or real financial data in the file.
- Never claim something that is not in the tagged commit: "elkészült" only for merged, tested work; planned work is written as planned.
- Never edit a sent e-mail (`Státusz: elküldve`); a correction is a new e-mail.
- Never quote the supervisor's letter verbatim in the repository; letters stay in the project files.
- No English sentences in the e-mail body, apart from names of files, commands and endpoints.

## Steps

1. **Collect the evidence.** For every planned point of the milestone and every open supervisor action: the commit or pull request, the test or result file that shows it, or "not done" with the reason.
2. **Answer the last reply first.** Each action of the supervisor's last reply gets a sentence in the e-mail: done (where to see it), partly done (what is missing), or moved (to when and why).
3. **Draft** from the README template, with [example-sent-email.md](example-sent-email.md) (the e-mail as actually sent) as the model for tone and layout. Subject: `Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - <téma>`, where the topic names the milestone or the report (`M2: <cím> (v0.3.0)`, `Heti jelentés (november 16–22.)`). Then one or two sentences on what the milestone contains, then *Elkészült*, *Hogyan ellenőrizhető* (commands such as `python -m unittest discover -s tests`, and links to result files), *Eltérések a tervtől, kockázatok* (late items honestly, with the new date), *Következő lépések* (next deadline). Use the full commit URL.
4. **Numbers** come from the result files, copied exactly, with the split (dev or test) named; nothing is rounded differently from the result file.
5. **Layout check** (the README's rule, as in the example): a blank line **above** each bold section heading and above the sign-off; **no** blank line below a heading, so the first item follows right under it; the bold greeting is followed directly by the first paragraph; the deadline after *Következő lépések* stands in brackets outside the bold.

## Self-check

```bash
git rev-parse <tag>^{commit}                                   # equals the commit id in the file and the URL
grep -nE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}' docs/releases/status-emails/<file> || echo "no e-mail address"
grep -n "Neptun" docs/releases/status-emails/<file>            # only the <Neptun-kód> placeholder
grep -n "Tárgy" docs/releases/status-emails/<file>             # Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - <téma>
grep -nA1 -E '^\*\*[^*]+\*\*( \(.*\))? *$' docs/releases/status-emails/<file> | grep -E '^[0-9]+-$'   # empty: no blank line right below a heading
```

Then go through the claim–evidence table once more: every *Elkészült* line has a commit, test or result file, and every number matches its result file.

## Human checkpoints

1. **Before** the draft is final: the author reads it and corrects tone and wording; the e-mail goes out in the author's name.
2. **After** sending: the author tells the date and pastes the sent text; the file is matched to it (wording, subject, commit link), gets `Státusz: elküldve (<dátum>)` and the README index is updated, in the next session's pull request. A lasting change of form the author made in Gmail goes into the README template and this skill.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-12 | First version, from the M0, interim and M1 e-mails. |
| 1.1 | 2026-11-14 | New subject format (`Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - <téma>`); blank line above headings, none below; the sent weekly report of 2026-11-14 kept as [example-sent-email.md](example-sent-email.md); weekly reports link the merge commit; the sent text is copied back into the repository file. |
