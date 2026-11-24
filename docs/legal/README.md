# Legal documents for the family pilot

- Written: 2026-11-24
- Owner: Bence Varga
- Status: **draft**, not yet accepted by anyone

These documents are for the closed family pilot planned in [family-pilot-readiness.md](../planning/family-pilot-readiness.md). They are written **in Hungarian**, because the family members who accept them read Hungarian; this is the second exception to the English-only rule of [docs/](../README.md#conventions), next to the status e-mails.

> **Not legal advice.** The drafts were written with an AI tool (Claude Code) from the repository's actual state on 2026-11-24. They have not been reviewed by a lawyer. Before real use, have them checked by a lawyer or a data-protection expert, especially the liability clause, the legal bases and the transfer to the United States.

| File | What it is | Who accepts it |
| --- | --- | --- |
| [eula-hu.md](eula-hu.md) | *Végfelhasználói licencszerződés* (EULA): terms of use of the Android app, the web app and the server run by the author, for a free, closed test | Every family member, before installation |
| [adatkezelesi-tajekoztato-hu.md](adatkezelesi-tajekoztato-hu.md) | *Adatkezelési tájékoztató* (privacy notice under GDPR Art. 13–14): what data, why, on what legal basis, for how long, to whom, and the members' rights; includes the opt-in for AI categorization | Every family member reads it; the AI opt-in is a separate, optional consent |

## Why two documents

The EULA is a contract about using the software. A privacy notice is a separate legal duty under the GDPR (Art. 12–14): it must be concise, separate from contract terms, and consent to optional processing (here the AI categorization) must not be bundled with accepting the contract (Art. 7(2) and 7(4)). FinSync reads bank notifications on the phone, stores personal spending data and, when enabled, sends merchant text to the Anthropic API, so a privacy notice is needed in any case.

## Placeholders to fill before use

Both documents mark missing facts as **[KITÖLTENDŐ: …]** (to be filled) and statements to verify as **[ELLENŐRIZENDŐ: …]** (to be checked). Before anyone accepts them:

1. Contact details of the author (e-mail, postal address) — never committed to this repository; fill them in the copy handed to the family.
2. Hosting: where the server runs (home computer or a named EU provider), from blocker B1.
3. Anthropic's current commercial terms, data-processing addendum, retention period and transfer mechanism, checked on Anthropic's website on the day of acceptance.
4. The retention periods, once blocker B4 sets them.
5. Effective date and version number.

## How acceptance is recorded

Each family member gets the filled-in PDF of both documents, accepts the EULA and (optionally) gives the AI consent by signing a paper copy or by replying to an e-mail with the version number and date. The author keeps the acceptances outside the repository. A new version is sent again and accepted again before it applies.

## Relation to the source code licence

The source code in this repository is under the [MIT licence](../../LICENSE). The EULA does not restrict it: it covers the **service the author runs** (the author's server, the family's accounts and data) and the app build the author hands over. Anyone may still use the code under the MIT licence.
