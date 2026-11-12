---
name: bank-notification-privacy
description: Use when working with real bank notifications in FinSync, for example adding or changing a bank format in the Android app or the server parser, analysing captures from the phone, or writing parser tests and fixtures. Guarantees that no real personal or financial data reaches the agent, the tests or the docs.
---

# Bank notification privacy and parser check

- Version: 1.0 (2026-11-12)
- Owner: Bence Varga
- Why it exists: the Android client reads real banking notifications on the author's phone. Their formats are needed for the parser, their content must never leave the phone (GDPR, author's decision 2026-10-24). In the spike this was done by hand ([android-notification-spike.md](../../../docs/design/android-notification-spike.md)); this skill makes it a fixed procedure. The supervisor named "a bank-notification anonymiser and parser checker" as a skill candidate (2026-10-29).

## Input

- A masked format description produced by the author with `mask_captures.py` on their own machine, or a format the author describes in words.
- The bank and notification kind to support (currently OTP Bank outgoing transfer and card purchase; Revolut and K&H only seen, not supported).

## Output

1. Parser patterns (server: `finsync/ingestion/`; phone: the Android app's filter) and tests whose fixtures are **made up** but follow the masked shape exactly.
2. A masked format table in `docs/design/android-notification-spike.md` (or the Android app's README) for every new format, in the existing style.
3. A short report in the reply: which formats are covered, which masked shapes the fixtures follow, the gate results.

## Prohibitions

- **The agent never reads a raw capture.** It never opens, stages, uploads or asks for `captures.jsonl`, an export from the phone, a screenshot of a bank notification or a copied notification text. If one is offered, it declines and points to step 1.
- Never run `mask_captures.py` on a cloud or shared machine; it runs on the author's computer, and only its output is shared.
- Never commit a capture, an export, a log with notification text, a real `key` or `tag`, a real amount, merchant, counterparty name, account number or transaction id.
- Never "unmask" a format by guessing the real words (for example writing the real Hungarian title back into a fixture). Titles and sentence parts in fixtures are invented text with the same structure; where the parser must match a fixed keyword, the author supplies that keyword (checkpoint 1).
- Never log or store notification text, `key` or `tag` on the phone or the server beyond what the design allows: transactions only after a known pattern matched, everything else as counts per bank and channel.
- Never widen a pattern to "accept anything with an amount": the known-pattern (allow-list) rule decides what is forwarded (2026-10-28).

## Steps

1. **Masking on the author's machine.** The author exports captures on the phone, copies them to their computer and runs

   ```bash
   python .claude/skills/bank-notification-privacy/mask_captures.py captures.jsonl > masked.md
   ```

   Every letter becomes `a`/`A`, every digit `9`, absolute times are dropped, and the script refuses to print anything still unmasked. The author reads `masked.md` and shares only that.
2. **Describe the shape.** From the masked table, write down per kind: which field carries what (title = kind, text = signed amount, currency, merchant or counterparty), separators (space as thousands separator, comma before the counterparty), what is constant across records and what varies, and the `source_ref` candidate (for OTP the nine-digit number at the end of the tag).
3. **Ask for fixed keywords.** A pattern that must recognise a constant word (the title of a card purchase, the currency text) needs the real word. Ask the author to type only those constant words (checkpoint 1); never variable parts.
4. **Write fixtures.** Made-up merchant (`PELDABOLT KFT`), made-up counterparty (`Minta Anna`), round made-up amounts (`-4 990 Ft`), made-up transaction ids (`OTP-Tranzakcio:000000001`). Each fixture names the masked shape it follows in a comment.
5. **Tests.** For every kind: the positive case, a near miss that must be rejected (marketing text with an amount, a group summary without text, another bank's text), and a re-delivery (same `key` and `post_time_ms`) that must not create a second record.
6. **Document** the masked table, the date and the device, in the existing style of the spike document.

## Self-check

```bash
python -m unittest discover -s tests          # all OK
git status --short                            # no capture, export or masked.md file staged
git diff origin/main...HEAD | grep -nE '^\+.*(captures\.jsonl|masked\.md)' || echo "clean"
git diff origin/main...HEAD | grep -nE '^\+.*[0-9]{8}-[0-9]{8}|^\+.*:[1-9][0-9]{8}\b' || echo "clean"   # account numbers, real-looking transaction ids
```

Then read every new fixture and doc line and ask: could this string have come from the author's phone? If it could, replace it with an obviously invented value.

## Human checkpoints

1. **Before** writing a pattern that needs a constant word: the author types that word.
2. **Before** committing a new masked format table: the author confirms it shows no content (a short name or a rare amount can identify a person even when masked; shorten such fields to their shape).
3. **After**: the author tests the app on the phone with a real notification and reports only the outcome (matched, dropped, sent, status code), not the text.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-12 | First version, from the spike's masking practice (Oct 26–28), with `mask_captures.py`. |
