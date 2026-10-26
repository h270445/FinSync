# Categorization of ambiguous purchases

- Status: **Proposed** (not implemented)
- Date: 2026-10-17

## Summary

A merchant name does not determine the category. "Tesco 12 000 Ft" can be food, clothing, a game or a mix of all three, and a bank notification carries nothing else. No categorizer, rule-based or LLM, can know the answer from that input, so FinSync does not pretend to: every category carries **where it came from** and **how sure it is**, an uncertain one is shown as a suggestion the member can fix in one tap, and a correction is remembered for the next purchase at that merchant.

## The problem in three cases

| Case | Example | Can it be decided from the record? |
| --- | --- | --- |
| **Clear merchant** | BKK, Netflix, MOL fuel | Yes: one category fits almost always |
| **Mixed-assortment merchant** | Tesco, Spar, Auchan, Rossmann, Amazon, eMAG | No: the usual category is a good guess, but often wrong |
| **Unknown or cryptic text** | "SUMUP *KJ BT", "PAYPAL *12345" | No: even the merchant is unclear |

Only the first case is a categorization problem in the usual sense. The other two are an information problem: the missing information is in the member's head or on the receipt.

## Data model

New fields on `events` (the category belongs to the purchase, not to one source record):

| Field | Values | Purpose |
| --- | --- | --- |
| `category` | one of the allowed categories, or `uncategorized` | The category used in totals |
| `category_source` | `user`, `source`, `merchant_memory`, `rule`, `llm`, `none` | Who decided |
| `category_confidence` | `high`, `low` | Whether it is shown as settled or as a suggestion |

A new `merchant_categories` table (per group): `merchant_key`, `category`, `times_confirmed`, `updated_at`. It is filled from member corrections and confirmations, never from LLM output alone.

Every change of category is logged (who, old, new, when), the same way match decisions are.

## Order of precedence

The first step that gives an answer wins:

1. **Member's choice** on any record of the event (manual entry, sheet column, correction in the web app). Never overwritten by automation.
2. **Category supplied by the source**, when the source has one (a bank export's category or MCC column, a sheet's category column), mapped to the allowed list. An unmappable value is not guessed; the mapping is asked once and remembered.
3. **Merchant memory** of the group: the category the group confirmed for this merchant. `high` once confirmed twice without a later correction.
4. **Keyword rules** (the current baseline). `high` for clear merchants, `low` for merchants on the mixed-assortment list.
5. **LLM**, only when the steps above give nothing or only `low`. It must answer with one allowed category or `unknown`; anything else is rejected. Its answer is always `low` unless it agrees with a rule.
6. Otherwise `uncategorized`.

When events are linked by matching, the event takes the highest-precedence category of its records, so a manual "clothing" beats the notification's guessed "groceries".

## LLM rules

- **Abstaining is a valid answer.** The prompt lists the allowed categories plus `unknown`, and states that a mixed-assortment merchant without further detail is `unknown` or the usual category marked uncertain. A wrong confident answer is the worst outcome, the same principle as false merges in matching.
- **Structured output, temperature 0**, validated against the allowed list ([security](../architecture/security-and-privacy.md)).
- **Only description, merchant and amount are sent**, never member names or group data.
- **The group's own corrections go into the prompt as examples** (few-shot), so the model learns household habits without fine-tuning.
- **Self-reported confidence is not trusted**; confidence comes from agreement with rules or memory.
- Results are cached by merchant key and description, so the same text is not sent twice.

## Per input platform

| Platform | What it knows | Handling |
| --- | --- | --- |
| **Android notification** | Merchant and amount only | Automatic category by the order above; when it is uncertain, a question on the phone ([Asking the member](#asking-the-member-proposed-by-the-author-2026-10-17)), otherwise a suggestion in the web app's list. |
| **Manual entry (web)** | The member is present | The category field is pre-filled with the suggestion; the member's choice is stored as `user`. Changing a suggested category teaches merchant memory. |
| **File import (bank export)** | Often a bank category or MCC column | Used as `source` through a mapping table. The import preview lists the `low` and `uncategorized` rows so they can be fixed in bulk before saving. |
| **Google Sheets** | A category column the member typed | Taken as `user` after mapping; an unknown value such as "kaja" is mapped once and remembered. |

## Asking the member (proposed by the author, 2026-10-17)

When the category is uncertain, the member is asked with a short reason and the two or three most likely categories plus "Other" (and "Later"), for example: "Tesco sells food and clothing too. What was this?" On Android this is a notification with action buttons (Android allows three, so two categories plus "Other"); in the web app the same chooser appears on the event.

**When to ask.** A model's self-reported percentage is not calibrated, so it is not used directly. Confidence is computed instead:

- the probability of the top category from token log-probabilities over the allowed list, where the provider exposes them, or the share of the top answer in five samples otherwise;
- **ask when the top category is below 0.80, or the gap to the second is below 0.20**, or the merchant is on the mixed-assortment list without a group memory entry, or rules and LLM disagree.

0.80 and 0.20 are starting values. Like the matching thresholds they are tuned on the development split: the target is at most 5 % wrong answers among the categories set without asking, with as few questions as that allows; both rates are reported.

**Against question fatigue:** never ask for a merchant the group has confirmed; a small-amount limit (starting at 2 000 Ft) below which the suggestion is kept silently; an optional daily question limit in the member's settings, off by default (author's decision, 2026-10-17), with questions over the limit collected in the web app's "uncertain categories" filter; the reason text comes from a template, not free LLM text. An unanswered question leaves the suggestion `low`, nothing is blocked.

**Scope:** the web chooser is part of the review UI this semester; the Android notification with actions is a stretch goal of the reduced Android app.

## Mixed baskets

One Tesco receipt with food and a T-shirt is really two categories. **Decided by the author (2026-10-17): all three levels below are built this semester, so the data model does not have to be reworked in the second semester.**

1. **One category per event** by default: the usual category, marked `low` for a mixed-assortment merchant, corrected in one tap.
2. **A "mixed" flag** a member can set without giving amounts: the whole amount stays under the main category, and reports show how much of a total may be inaccurate.
3. **Category lines:** the member splits an event into lines, for example 12 000 Ft = 9 000 Ft groceries + 3 000 Ft clothing.

Data model for lines: a new `event_category_lines` table (`event_id`, `category`, `amount`, `created_by`, `created_at`). An event without lines counts its whole amount under `events.category`; an event with lines counts each line instead. The lines must add up to the event amount exactly (checked on write; the last line takes the remainder of a rounded split), and they must have the event's sign. Saving lines replaces the previous set as one logged change.

Interaction with matching: lines belong to the event, not to a source record, so linking or confirming does not touch them. When a split moves a record to a new event, the lines stay on the original event, and the new event starts without lines; the member is shown that the old lines may need checking.

Totals: category totals sum the lines of split events and the whole amount of the others, so the overview and the evaluation use one rule.

Automatic splitting from receipts (photo, e-receipt) is out of scope.

## Money transfers

Decided by the author on 2026-10-26; scheduled for M2 (Nov 23–27).

A transfer between members of the same group (for example within a family, through mobile banking) is neither spending nor income for the group: today it is stored as an expense on the sender's side and as income on the receiver's side, which inflates the group's totals.

- Each group keeps a list of **own accounts and counterparties**: account numbers or IBANs and the names that appear in notifications and exports (for example the members' names as the bank prints them).
- A record whose counterparty matches the list gets the direction **`transfer`** instead of `expense` or `income`, and is left out of spending and income totals. Its category is `transfer`; the categorizer is not asked.
- A member can mark a record as a transfer, or undo it, in the web app; the correction is logged like a category correction.
- The two sides of one transfer (−X at one member, +X at another) stay two separate events this semester. Linking them into one event is a matching extension (opposite signs, two members) left for Szakdolgozat II.
- The matching direction gate treats `transfer` like a direction of its own, so a transfer is never linked to a purchase of the same amount.

## Review in the web app

- The event list shows `low` categories in a lighter style with a "suggestion" marker; one tap confirms or changes it.
- A filter "uncertain categories" lists them; there is no mandatory queue, because a wrong category is a smaller error than a wrong merge.
- Confirming or changing a category at a merchant offers "always use this for Tesco" only when the merchant is not on the mixed-assortment list.

## Evaluation

Added to the [evaluation plan](../evaluation/evaluation-plan.md#2-transaction-categorization):

- The labelled dataset marks each item as clear or ambiguous. For ambiguous items the label records what the member actually bought, so a merchant-only guess can be scored honestly.
- Metrics per approach (rules, LLM, rules + memory): accuracy on clear items; on ambiguous items accuracy **and** abstention rate; wrong-and-`high` rate as the main error; corrections a member would have to make per 100 purchases; time and cost per item.
- The comparison shows where the LLM helps (cryptic text, unfamiliar merchants) and where it cannot (mixed baskets without detail).

## Open questions

1. Which mixed-assortment merchants go on the starting list (proposal: the large Hungarian grocery, drugstore and marketplace chains)?
2. Do the target bank's notifications or exports carry an MCC or a category? Check during the Android spike and with a sample export.
3. Final category list: the current four plus `other` is too short; proposal: groceries, eating out, transport, housing and utilities, health, clothing, entertainment, household, other.
