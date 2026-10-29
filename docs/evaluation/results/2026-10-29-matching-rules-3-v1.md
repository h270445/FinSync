# Matching evaluation

- Code: commit `c774208`, matcher `rules-3`
- Command: `python -m finsync.evaluation --dataset tests/data/matching_eval.csv`
- Dataset: `tests/data/matching_eval.csv` (sha256 `c0829a854f89`), 100 records, dev 49, test 51
- Fixed: review threshold 0.60, runner-up margin 0.10

Metric definitions are in [evaluation-plan.md](../evaluation-plan.md#1-transaction-matching). *Double counted* is the number of purchases that appear as more than one expense; a false merge hides a purchase inside another one's event and is listed separately below.

## 1. Auto-link threshold sweep (dev split, arrival order)

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| matcher@0.70 | arrival | 90.0% | 52.9% | 1 | 2.6% | 5.9% | 18.4% | 39 (32) | 8 |
| matcher@0.75 | arrival | 90.0% | 52.9% | 1 | 2.6% | 5.9% | 18.4% | 39 (32) | 8 |
| matcher@0.80 | arrival | 90.0% | 52.9% | 1 | 2.6% | 5.9% | 18.4% | 39 (32) | 8 |
| matcher@0.85 | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |
| matcher@0.90 | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |
| matcher@0.95 | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |

Chosen: **0.95** (fewest false merges, then highest recall, then lowest review rate; ties go to the higher threshold). The test split was not used for this choice.

## 2. Test split at 0.95

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| store-every-row | arrival | n/a | 0.0% | 0 | 0.0% | 100.0% | 0.0% | 51 (39) | 12 |
| matcher@0.95 | arrival | 100.0% | 66.7% | 0 | 0.0% | 0.0% | 11.8% | 43 (39) | 4 |
| matcher@0.95 | reverse | 100.0% | 66.7% | 0 | 0.0% | 0.0% | 13.7% | 43 (39) | 4 |

`reverse` replays the same records from the last arrival to the first, to show how much the result depends on arrival order.

## 3. False merges

| Run | Records | Scenarios | Purchases | Outcome per record | In review |
| --- | --- | --- | --- | --- | --- |
| matcher@0.70, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked | no |
| matcher@0.75, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked | no |
| matcher@0.80, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked | no |

## 4. Missed duplicates on the test split at 0.95

None.

## 5. Reverse-order options at 0.85

A: an information-poor pair (a date-only side, or a merchant score of 0.5) needs 0.95 to link automatically. B: a record whose channel is taken in an automatically linked event, and that fits the event as well as its weakest automatic link, opens that event for review; nothing is moved. Both are on in `rules-3`; `rules-2` had neither. They are compared at the `rules-2` threshold, because at the stricter-gate score or above option A changes nothing.

### Development split

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| neither (rules-2) | arrival | 100.0% | 64.7% | 0 | 0.0% | 5.9% | 16.3% | 38 (32) | 6 |
| neither (rules-2) | reverse | 100.0% | 64.7% | 0 | 0.0% | 5.9% | 18.4% | 38 (32) | 6 |
| A strict gate | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |
| A strict gate | reverse | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 22.4% | 40 (32) | 8 |
| B reopen | arrival | 100.0% | 64.7% | 0 | 0.0% | 5.9% | 16.3% | 38 (32) | 6 |
| B reopen | reverse | 100.0% | 64.7% | 0 | 0.0% | 5.9% | 18.4% | 38 (32) | 6 |
| A+B (rules-3) | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |
| A+B (rules-3) | reverse | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 22.4% | 40 (32) | 8 |

### Test split

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| neither (rules-2) | arrival | 100.0% | 91.7% | 0 | 0.0% | 0.0% | 3.9% | 40 (39) | 1 |
| neither (rules-2) | reverse | 84.6% | 91.7% | 1 | 2.6% | 8.3% | 3.9% | 39 (39) | 1 |
| A strict gate | arrival | 100.0% | 66.7% | 0 | 0.0% | 0.0% | 11.8% | 43 (39) | 4 |
| A strict gate | reverse | 100.0% | 66.7% | 0 | 0.0% | 0.0% | 13.7% | 43 (39) | 4 |
| B reopen | arrival | 100.0% | 91.7% | 0 | 0.0% | 0.0% | 5.9% | 40 (39) | 1 |
| B reopen | reverse | 84.6% | 91.7% | 1 | 2.6% | 0.0% | 5.9% | 39 (39) | 1 |
| A+B (rules-3) | arrival | 100.0% | 66.7% | 0 | 0.0% | 0.0% | 11.8% | 43 (39) | 4 |
| A+B (rules-3) | reverse | 100.0% | 66.7% | 0 | 0.0% | 0.0% | 13.7% | 43 (39) | 4 |

### False merges of the options

| Run | Records | Scenarios | Purchases | Outcome per record | In review |
| --- | --- | --- | --- | --- | --- |
| neither (rules-2), test, reverse | R0017, R0022, R0024 | late_manual, date_only_manual, date_only_manual | E0046, E0070 | auto_linked, auto_linked, separate | no |
| B reopen, test, reverse | R0017, R0022, R0024 | late_manual, date_only_manual, date_only_manual | E0046, E0070 | auto_linked, auto_linked, separate | yes |
