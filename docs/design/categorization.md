# Categorization of ambiguous purchases

- Status: **Implemented** except the per-platform items marked below: group merchant rules, transfers and the deterministic layer with the built-in Hungarian dictionary (2026-11-19); the LLM layer and its measurement runner (2026-11-19, [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md)); the measured run ([report](../evaluation/results/2026-11-24-categorization-hybrid.md), 2026-11-24); category correction with the "mixed" flag, category lines, transfer marking and the change log, in the API and the web app (W3, W4), and the LLM in the live flow with the author's schedule settings (2026-11-24). Open: the W8 screen for the LLM setting, the import preview's bulk fix, Sheets category mapping, the Android question with actions (stretch), few-shot examples from the group's corrections
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

A `merchant_categories` table (per group): `merchant_key`, `category`, `times_confirmed`, `updated_at`, plus the merchant as typed, who added it and when (Alembic revision 0002, 2026-11-19). Admins of the group add, change and delete rows on the W8 settings screen (every member reads them); later, corrections and confirmations add and confirm them, never LLM output alone.

**How a rule matches (implemented 2026-11-19, [`merchant_rules.py`](../../finsync/categorization/merchant_rules.py)).** The key is the merchant's words, lowercase, accent-free, without store numbers and company suffixes ("Spar 0123 Kft." → `spar`), the same normalisation as matching uses. A rule applies when every word of its key is a word of the record's merchant, or of its description when it has no merchant; the rule with the most words wins ("MOL Bubi" before "MOL"). A group has at most one rule per key. A rule applies to records stored after it; existing events are not recategorized (author's decision, 2026-11-19), that is the logged category correction's job.

Every change of category is logged (who, old, new, when), the same way match decisions are.

**Built 2026-11-24 (Alembic revision 0006, [`service.py`](../../finsync/core/service.py)).** Records and events carry `category_source` and `category_confidence`; the source names are the code's: `user`, `merchant_rule`, `dictionary`, `keyword`, `llm`, `own_account`, `none` (the table above is the plan; `rule` became `dictionary`/`keyword`, `merchant_memory` became `merchant_rule`, and `source` waits for the import's category column). The log is the append-only `category_changes` table (kind `category`, `mixed`, `lines` or `transfer`, old and new value as JSON). Rows stored before revision 0006 did not record their source: they show as `none`/`low` suggestions, transfers as `own_account`/`high`. **Income is never uncertain** (author's decision, 2026-11-24, after the demo showed a salary as an uncertain "Egyéb"): the categories describe spending, so an income event is not counted or listed as uncertain, gets no LLM due time and shows as "Bevétel" in the web list; a member may still give it a category on W4.

**"Always use this for …" (author's default, 2026-11-24, open to change).** Any member may teach the group a rule through a correction, because it only affects future categories of the group, not access: no rule yet creates one, the same category confirms it (`times_confirmed` + 1). Changing an existing rule to another category stays an admin's step, as on W8: a member's correction then stays on the event and the answer says the rule was `kept`.

## Order of precedence

The first step that gives an answer wins:

1. **Member's choice** on any record of the event (manual entry, sheet column, correction in the web app). Never overwritten by automation.
2. **Category supplied by the source**, when the source has one (a bank export's category or MCC column, a sheet's category column), mapped to the allowed list. An unmappable value is not guessed; the mapping is asked once and remembered.
3. **Merchant memory** of the group: the category the group confirmed for this merchant, editable as group merchant → category rules on the W8 settings screen; the first, deterministic layer of the hybrid categorizer. `high` once confirmed twice without a later correction.
4. **Keyword rules** (the current baseline). `high` for clear merchants, `low` for merchants on the mixed-assortment list.

   **Built 2026-11-19 ([`dictionary.py`](../../finsync/categorization/dictionary.py), [`hybrid.py`](../../finsync/categorization/hybrid.py)):** steps 3–4 as the hybrid categorizer's deterministic layer, `categorize_record()`. Below the group's rules it uses a built-in Hungarian dictionary (version `hu-1`): 96 merchant keys and 179 keywords (SPAR, Tesco, dm, MOL, MÁV-START, BKK, Wolt, MVM, Telekom, Benu, H&M, IKEA, …), where the mixed-assortment ones are marked, with the keywords in Hungarian and English, matched accent-free, with `*` as a word prefix for Hungarian suffixes ("étterem*" covers "étteremben"). Within the layer: a clear merchant (`high`) beats keywords; keywords naming one category are `high`, several are `low`; a mixed merchant's usual category comes last and is `low`, so "Tesco" with "zokni" is clothing. With no answer the result is `other` with source `none`, the case the LLM layer will take. The dictionary was written from general knowledge, not from the labelled dataset; because both name the common Hungarian chains, the measurement (Nov 23–27) reports this overlap next to the dictionary's numbers. The keyword baseline in `rules.py` is unchanged.
5. **LLM**, only when the steps above give nothing or only `low`. It must answer with one allowed category or `unknown`; anything else is rejected. Its answer is always `low` unless it agrees with a rule.

   **Built 2026-11-19 ([`llm.py`](../../finsync/categorization/llm.py), [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md)):** five answers per record; the share of the most frequent category is the confidence. At or above the abstention threshold (tuned on dev) the LLM category is settled (`llm`, `high`); below it the record is "Bizonytalan": the dictionary's `low` suggestion is kept, else the LLM's top answer as a `low` suggestion, else `uncategorized`. This replaces "always `low` unless it agrees with a rule" with a computed, measured confidence; agreement with a rule is not used as a bonus in the first measurement.
6. Otherwise `uncategorized`.

When events are linked by matching, the event takes the highest-precedence category of its records, so a manual "clothing" beats the notification's guessed "groceries".

## LLM rules

- **Abstaining is a valid answer.** The prompt lists the allowed categories plus `unknown`, and states that a mixed-assortment merchant without further detail is `unknown` or the usual category marked uncertain. A wrong confident answer is the worst outcome, the same principle as false merges in matching.
- **Structured output**, validated against the allowed list. (Temperature 0 was planned; current models no longer take a temperature, so the answer varies between calls and that variation is used as the confidence, see below.) ([security](../architecture/security-and-privacy.md)).
- **Only description, merchant and amount are sent**, never member names or group data.
- **The group's own corrections go into the prompt as examples** (few-shot), so the model learns household habits without fine-tuning.
- **Self-reported confidence is not trusted**; confidence comes from agreement with rules or memory.
- Results are cached by merchant key and description, so the same text is not sent twice.

## When the LLM is called (proposed by the author, 2026-11-19)

Before the LLM is asked, the members get the chance to set an uncertain category themselves; when the LLM runs is a setting. Details proposed on 2026-11-19 and confirmed by the author on 2026-11-24, scheduled for Nov 23–27 with the category correction:

- **Group setting, admins only (W8):** *never* (default, because data leaves the system), *X hours after the purchase* (24 by default), *daily at a set time*, *weekly on a set day and time*. A member only chooses whether to be notified about uncertain items.
- **"Ask for a suggestion now"** on selected uncertain items works in every mode.
- **Manual first:** the "uncertain categories" filter shows the dictionary's suggestion and two or three quick choices; a member's choice is `user`, never overwritten, and teaches merchant memory; a scheduled run skips items decided in the meantime.
- **Cost guard:** a monthly budget per group (the run stops and says so when it is used up); daily and weekly runs can use the provider's batch interface at half price; identical texts are sent once (cache); an optional small-amount limit below which the LLM is not asked.
- **Implementation:** each uncertain event gets a due time (`llm_due_at`) from the group setting; an in-process task processes due events every few minutes, so no external scheduler is needed. The measurement is unaffected: it measures the answers, not their timing.

**Built 2026-11-24 (Alembic revision 0007, [`llm_schedule.py`](../../finsync/core/llm_schedule.py), [API](../guides/api.md#get-v1llm-settings-put-v1llm-settings)).** Modes `never`, `after_arrival` (X hours after the record *arrived*, so an old imported purchase still gives the members X hours), `daily`, `weekly`, in Budapest time. Saving a setting gives every uncertain event of the group its due time, the backlog included (`never` clears them). The server starts the runner (every 5 minutes) only when `FINSYNC_ANTHROPIC_API_KEY` is set. The live flow uses the measured prompt (`llm-1`), five samples and the threshold chosen on dev (0.40) through `combine()`, so it behaves like the measured hybrid. Changing the setting is web-session only, like roles: it decides whether data leaves the system. Not built yet: the W8 screen (Thursday), the provider's batch interface for daily and weekly runs, the small-amount limit, member notifications, few-shot examples from the group's corrections, and a persistent answer cache (the cache lives in memory per server run). A synthetic end-to-end call with the real key on 2026-11-24 cost USD 0.0005 for five samples.

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

- the probability of the top category from token log-probabilities over the allowed list, where the provider exposes them, or the share of the top answer in five samples otherwise (the provider chosen in November exposes no log-probabilities, so five samples are used);
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

**Built 2026-11-24.** `PUT /v1/events/{id}/mixed` and `PUT /v1/events/{id}/category-lines` ([API](../guides/api.md#put-v1eventsevent_idcategory-lines)): two to 20 lines, each category once, exact sum, the event's sign; the event's `category` becomes the largest line's (as the member's decision) so the list shows the main category. Two decisions the design left open, taken as the safer reading: lines that no longer add up after a split are ignored by the overview (the whole amount counts under `category`) and flagged on the event (`lines_match_amount: false`) until a member fixes them; a transfer cannot be mixed or split, and an event with lines cannot be marked a transfer before its lines are removed. The overview reports `mixed_amount` (mixed without lines) and `uncertain_amount` (suggested categories) on the month total.

Automatic splitting from receipts (photo, e-receipt) is out of scope.

## Money transfers

Decided by the author on 2026-10-26; scheduled for M2 (Nov 23–27). The own-accounts list and the `transfer` direction were built on 2026-11-19 ([`own_accounts.py`](../../finsync/categorization/own_accounts.py), W8 screen, `/v1/own-accounts`): an entry with at least 8 digits matches on its digits, any other entry on its words; the list applies to records stored after it, and only an admin changes it. Marking or unmarking a single record as a transfer comes with the category correction.

A transfer between members of the same group (for example within a family, through mobile banking) is neither spending nor income for the group: today it is stored as an expense on the sender's side and as income on the receiver's side, which inflates the group's totals.

- Each group keeps a list of **own accounts and counterparties**: account numbers or IBANs and the names that appear in notifications and exports (for example the members' names as the bank prints them).
- A record whose counterparty matches the list gets the direction **`transfer`** instead of `expense` or `income`, and is left out of spending and income totals. Its category is `transfer`; the categorizer is not asked.
- A member can mark a record as a transfer, or undo it, in the web app; the correction is logged like a category correction.
- The two sides of one transfer (−X at one member, +X at another) stay two separate events this semester. Linking them into one event is a matching extension (opposite signs, two members) left for Szakdolgozat II.
- The matching direction gate treats `transfer` like a direction of its own, so a transfer is never linked to a purchase of the same amount.

**Marking built 2026-11-24** (`PUT /v1/events/{id}/transfer`): marking sets the direction and category of the event and all its records to `transfer` as the member's decision; undoing gives the records the direction of their amount's sign and the category the categorizer gives them, ignoring the own-accounts list the member has just overruled. Both are logged.

## Review in the web app

**UX principles for the category correction, the "mixed" flag and category lines** (supervisor, 2026-11-23; the same principle as the W2 overview, which says openly how much is still waiting for review):

1. **Show where a suggestion comes from and how sure it is.** Every suggested category carries its source (member, group rule, dictionary, model) and its uncertainty (`high`, `low` or "Bizonytalan", and for the model the share of agreeing samples) in Hungarian on the screen, so a member never mistakes a guess for a decision.
2. **Few clicks.** Confirming or changing a category is one tap from the event list or the event detail; marking an event as mixed is one more; a split into category lines opens pre-filled with the current category for the whole amount, and the last line takes the remainder.
3. **Merchant memory learns a final rule only for non-mixed merchants.** Changing a category at a clear merchant offers "always use this for …" and can create a group rule; at a merchant on the mixed-assortment list, or for an event marked mixed or split into lines, the correction stays on that event and no group rule is written.

Details:

- The event list shows `low` categories in a lighter style with a "suggestion" marker; one tap confirms or changes it.
- A filter "uncertain categories" lists them; there is no mandatory queue, because a wrong category is a smaller error than a wrong merge.
- Confirming or changing a category at a merchant offers "always use this for Tesco" only when the merchant is not on the mixed-assortment list.

**Built 2026-11-24 ([`category.tsx`](../../web/src/components/category.tsx), [`CategoryPanel.tsx`](../../web/src/components/CategoryPanel.tsx)).** W3 shows a suggestion lighter with a "javaslat" marker and its source on hover, a ✓ to confirm and a select to change it, on phones below each card; the "Csak bizonytalan kategóriák" filter lists suggestions. W4 has the category card: source and certainty in Hungarian ("Forrás: beépített szótár · bizonytalan, csak javaslat"; for the model "4/5 modellválasz egyezett"), confirm or change with the "Mindig ezt használd: …" checkbox only when the API offers it (`remember_merchant`), the "Vegyes vásárlás" checkbox, the line editor (pre-filled with the whole amount; every line but the last is typed, the last takes the remainder), the transfer button, "Kérj javaslatot a modelltől" with the scheduled time, and the category history. W2 says how much of the category split is a suggestion or mixed.

## Evaluation

Added to the [evaluation plan](../evaluation/evaluation-plan.md#2-transaction-categorization):

- The labelled dataset marks each item as clear or ambiguous. For ambiguous items the label records what the member actually bought, so a merchant-only guess can be scored honestly.
- Metrics per approach (rules, LLM, rules + memory): accuracy on clear items; on ambiguous items accuracy **and** abstention rate; wrong-and-`high` rate as the main error; corrections a member would have to make per 100 purchases; time and cost per item.
- The comparison shows where the LLM helps (cryptic text, unfamiliar merchants) and where it cannot (mixed baskets without detail).

## Open questions

1. Which mixed-assortment merchants go on the starting list (proposal: the large Hungarian grocery, drugstore and marketplace chains)?
2. Do the target bank's notifications or exports carry an MCC or a category? Check during the Android spike and with a sample export.
3. Final category list: the current four plus `other` is too short; proposal: groceries, eating out, transport, housing and utilities, health, clothing, entertainment, household, other.
