# Matching evaluation

- Code: commit `c774208`, matcher `rules-3`
- Command: `python -m finsync.evaluation --dataset tests/data/matching_eval_v2.csv`
- Dataset: `tests/data/matching_eval_v2.csv` (sha256 `e0495a4f25ee`), 132 records, dev 77, test 55
- Fixed: review threshold 0.60, runner-up margin 0.10

Metric definitions are in [evaluation-plan.md](../evaluation-plan.md#1-transaction-matching). *Double counted* is the number of purchases that appear as more than one expense; a false merge hides a purchase inside another one's event and is listed separately below.

## 1. Auto-link threshold sweep (dev split, arrival order)

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| matcher@0.70 | arrival | 84.2% | 51.6% | 2 | 3.4% | 6.5% | 28.6% | 59 (46) | 15 |
| matcher@0.75 | arrival | 84.2% | 51.6% | 2 | 3.4% | 6.5% | 28.6% | 59 (46) | 15 |
| matcher@0.80 | arrival | 84.2% | 51.6% | 2 | 3.4% | 6.5% | 28.6% | 59 (46) | 15 |
| matcher@0.85 | arrival | 88.9% | 51.6% | 1 | 1.7% | 6.5% | 29.9% | 60 (46) | 15 |
| matcher@0.90 | arrival | 88.9% | 51.6% | 1 | 1.7% | 6.5% | 29.9% | 60 (46) | 15 |
| matcher@0.95 | arrival | 88.9% | 51.6% | 1 | 1.7% | 6.5% | 29.9% | 60 (46) | 15 |

Chosen: **0.95** (fewest false merges, then highest recall, then lowest review rate; ties go to the higher threshold). The test split was not used for this choice.

## 2. Test split at 0.95

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| store-every-row | arrival | n/a | 0.0% | 0 | 0.0% | 100.0% | 0.0% | 55 (41) | 14 |
| matcher@0.95 | arrival | 100.0% | 64.3% | 0 | 0.0% | 0.0% | 14.5% | 46 (41) | 5 |
| matcher@0.95 | reverse | 100.0% | 64.3% | 0 | 0.0% | 0.0% | 16.4% | 46 (41) | 5 |

`reverse` replays the same records from the last arrival to the first, to show how much the result depends on arrival order.

## 3. False merges

| Run | Records | Scenarios | Purchases | Outcome per record | In review |
| --- | --- | --- | --- | --- | --- |
| matcher@0.70, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked | no |
| matcher@0.70, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| matcher@0.75, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked | no |
| matcher@0.75, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| matcher@0.80, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked | no |
| matcher@0.80, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| matcher@0.85, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| matcher@0.90, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| matcher@0.95, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |

## 4. Missed duplicates on the test split at 0.95

None.

## 5. Reverse-order options at 0.85

A: an information-poor pair (a date-only side, or a merchant score of 0.5) needs 0.95 to link automatically. B: a record whose channel is taken in an automatically linked event, and that fits the event as well as its weakest automatic link, opens that event for review; nothing is moved. Both are on in `rules-3`; `rules-2` had neither. They are compared at the `rules-2` threshold, because at the stricter-gate score or above option A changes nothing.

### Development split

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| neither (rules-2) | arrival | 85.7% | 77.4% | 2 | 3.9% | 6.5% | 10.4% | 51 (46) | 7 |
| neither (rules-2) | reverse | 52.9% | 58.1% | 8 | 15.7% | 25.8% | 11.7% | 51 (46) | 13 |
| A strict gate | arrival | 88.9% | 51.6% | 1 | 1.7% | 6.5% | 29.9% | 60 (46) | 15 |
| A strict gate | reverse | 100.0% | 48.4% | 0 | 0.0% | 6.5% | 35.1% | 62 (46) | 16 |
| B reopen | arrival | 85.7% | 77.4% | 2 | 3.9% | 6.5% | 18.2% | 51 (46) | 7 |
| B reopen | reverse | 54.8% | 54.8% | 7 | 13.2% | 6.5% | 22.1% | 53 (46) | 14 |
| A+B (rules-3) | arrival | 88.9% | 51.6% | 1 | 1.7% | 6.5% | 29.9% | 60 (46) | 15 |
| A+B (rules-3) | reverse | 100.0% | 48.4% | 0 | 0.0% | 6.5% | 35.1% | 62 (46) | 16 |

### Test split

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| neither (rules-2) | arrival | 100.0% | 92.9% | 0 | 0.0% | 0.0% | 3.6% | 42 (41) | 1 |
| neither (rules-2) | reverse | 75.0% | 85.7% | 2 | 4.9% | 14.3% | 3.6% | 41 (41) | 2 |
| A strict gate | arrival | 100.0% | 64.3% | 0 | 0.0% | 0.0% | 14.5% | 46 (41) | 5 |
| A strict gate | reverse | 100.0% | 64.3% | 0 | 0.0% | 0.0% | 16.4% | 46 (41) | 5 |
| B reopen | arrival | 100.0% | 92.9% | 0 | 0.0% | 0.0% | 7.3% | 42 (41) | 1 |
| B reopen | reverse | 75.0% | 85.7% | 2 | 4.9% | 0.0% | 7.3% | 41 (41) | 2 |
| A+B (rules-3) | arrival | 100.0% | 64.3% | 0 | 0.0% | 0.0% | 14.5% | 46 (41) | 5 |
| A+B (rules-3) | reverse | 100.0% | 64.3% | 0 | 0.0% | 0.0% | 16.4% | 46 (41) | 5 |

### False merges of the options

| Run | Records | Scenarios | Purchases | Outcome per record | In review |
| --- | --- | --- | --- | --- | --- |
| neither (rules-2), dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| neither (rules-2), dev, arrival | R0114, R0115, R0116 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0080, E0081 | separate, auto_linked, auto_linked | no |
| neither (rules-2), dev, reverse | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | auto_linked, separate, auto_linked | no |
| neither (rules-2), dev, reverse | R0102, R0103, R0104 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0072, E0073 | auto_linked, auto_linked, separate | no |
| neither (rules-2), dev, reverse | R0107, R0110, R0112 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0082, E0083 | auto_linked, auto_linked, separate | no |
| neither (rules-2), dev, reverse | R0108, R0111, R0113 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0084, E0085 | auto_linked, auto_linked, separate | no |
| neither (rules-2), dev, reverse | R0114, R0115, R0116 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0080, E0081 | auto_linked, auto_linked, separate | no |
| neither (rules-2), dev, reverse | R0119, R0121, R0124 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0076, E0077 | auto_linked, auto_linked, separate | no |
| neither (rules-2), dev, reverse | R0120, R0122, R0123 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0086, E0087 | auto_linked, auto_linked, separate | no |
| neither (rules-2), dev, reverse | R0126, R0127, R0128 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0078, E0079 | auto_linked, auto_linked, separate | no |
| A strict gate, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| B reopen, dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| B reopen, dev, arrival | R0114, R0115, R0116 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0080, E0081 | separate, auto_linked, auto_linked | no |
| B reopen, dev, reverse | R0102, R0103, R0104 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0072, E0073 | auto_linked, auto_linked, separate | yes |
| B reopen, dev, reverse | R0107, R0110, R0112 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0082, E0083 | auto_linked, auto_linked, separate | yes |
| B reopen, dev, reverse | R0108, R0111, R0113 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0084, E0085 | auto_linked, auto_linked, separate | yes |
| B reopen, dev, reverse | R0114, R0115, R0116 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0080, E0081 | auto_linked, auto_linked, separate | no |
| B reopen, dev, reverse | R0119, R0121, R0124 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0076, E0077 | auto_linked, auto_linked, separate | yes |
| B reopen, dev, reverse | R0120, R0122, R0123 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0086, E0087 | auto_linked, auto_linked, separate | yes |
| B reopen, dev, reverse | R0126, R0127, R0128 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0078, E0079 | auto_linked, auto_linked, separate | yes |
| A+B (rules-3), dev, arrival | R0034, R0035, R0109 | two_members_same_purchase, two_members_same_purchase, same_amount_neighbour_days | E0034, E0080 | separate, auto_linked, auto_linked | no |
| neither (rules-2), test, reverse | R0017, R0022, R0024 | late_manual, date_only_manual, date_only_manual | E0046, E0070 | auto_linked, auto_linked, separate | no |
| neither (rules-2), test, reverse | R0130, R0131, R0132 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0074, E0075 | auto_linked, auto_linked, separate | no |
| B reopen, test, reverse | R0017, R0022, R0024 | late_manual, date_only_manual, date_only_manual | E0046, E0070 | auto_linked, auto_linked, separate | yes |
| B reopen, test, reverse | R0130, R0131, R0132 | same_amount_neighbour_days, same_amount_neighbour_days, same_amount_neighbour_days | E0074, E0075 | auto_linked, auto_linked, separate | yes |

## 6. Findings

Written with the run above; the numbers are the generated part. The supervisor asked on 2026-10-29 to compare two directions for the reverse-order false merge on the development split ([feedback](../../planning/supervisor-feedback.md#2026-10-29--reply-to-the-oct-28-interim-note)). Version 1 had that case only in its test split, so [dataset v2](../datasets.md#testsdatamatching_eval_v2csv--matching-version-2) adds 8 same-amount neighbour-day cases (7 of them in dev) and keeps every version 1 record.

- **Choice of option (dev, section 5).** At the `rules-2` threshold, `rules-2` merges 8 pairs of separate purchases in reverse order and 2 in arrival order, none of them visible for review. A (strict gate) leaves 0 in reverse and 1 in arrival order, at the cost of recall (77.4% → 51.6%) and review rate (10.4% → 29.9%). B (reopen) keeps recall but only flags merges: 7 remain in reverse order, 6 of them in review. By the evaluation plan's rule (fewest false merges first) A and A+B tie; the author chose A+B on 2026-10-29, keeping B as the safety net for a merge A lets through. On this data A+B and A give the same result.
- **Choice of threshold (dev, section 1).** With `rules-3`, 0.85, 0.90 and 0.95 give the same result; the rule takes the higher threshold on a tie, so the auto-link threshold is now **0.95** (author's decision, 2026-10-29). At 0.95 the strict gate adds nothing by itself; it matters again if the threshold is lowered.
- **Test split (section 2).** No false merge in either arrival order (with `rules-2` at 0.85: 2 in reverse order) and no missed duplicate: every true pair the matcher does not link waits for review against its partner. The price is recall 92.9% → 64.3%, 5 double counts instead of 1 (the store-every-row baseline has 14), and review rate 3.6% → 14.5%. All 5 double counts are pending reviews, not silent.
- **Version 1 with `rules-3`** ([result](2026-10-29-matching-rules-3-v1.md)), for comparison with the 2026-10-18 results: on the test split no false merge in either order (the IKEA case R0017 now goes to review), 4 double counts instead of 1 (baseline 12), recall 91.7% → 66.7%, review rate 3.9% → 11.8%.
- **Remaining false merge (dev, arrival, every option).** R0109, the notification of a Decathlon purchase, joins R0034 and R0035, two members' entries for another 11 990 HUF Decathlon purchase on the same day. The pair scores 1.0: same shop, amount and day, with no notification of the first purchase to tell them apart. Without a time on the manual entries this is not separable by rules; it stays a known limit.
- **Order dependence.** Arrival and reverse order now give the same number of events on the test split of both versions; only the review rate differs.
- **Limits of the comparison.** The added cases are deliberately frequent, so the review rate is higher than a household would see. B's contested review cannot be confirmed directly while the event holds a record from the same channel: the member splits the wrong record out first (W5 in M2 should offer this). The test-split numbers of the options were visible in exploratory runs before the choice, and one narrower variant of A was tried and discarded; the choice itself rests on the development split and the plan's rule.
