# Matching evaluation

- Code: commit `v0.2.0-42-g47122b2`, matcher `rules-3`
- Command: `python -m finsync.evaluation --dataset tests/data/matching_eval_v3.csv`
- Dataset: `tests/data/matching_eval_v3.csv` (sha256 `f2de390ec464`), 132 records, dev 77, test 55
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

Written with the run above; the numbers are the generated part. This is a regression check, not a new measurement: no threshold or option was chosen from it.

- **Same numbers as on 2026-10-29.** Every generated table and line above equals the [2026-10-29 result on version 2](2026-10-29-matching-rules-3.md) (checked with `diff`), so reading times without an offset as Europe/Budapest ([ADR 0008](../../architecture/decisions/0008-notification-time-and-calendar-day.md)) changes no result once the data prints local time, as [version 3](../datasets.md#testsdatamatching_eval_v3csv--matching-version-3) does.
- **Why version 2 alone was not enough.** Run with the new parser, version 2's UTC texts are read two hours early. One dev-split row of the threshold sweep then differs (0.80: one false merge fewer), and the test split is unchanged. The chosen threshold and every reported test number stay the same either way.
