# Matching evaluation

- Code: commit `daef066`, matcher `rules-2`
- Command: `python -m finsync.evaluation --dataset tests/data/matching_eval.csv`
- Dataset: `tests/data/matching_eval.csv` (sha256 `c0829a854f89`), 100 records, dev 49, test 51
- Fixed: review threshold 0.60, runner-up margin 0.10

Metric definitions are in [evaluation-plan.md](../evaluation-plan.md#1-transaction-matching). *Double counted* is the number of purchases that appear as more than one expense; a false merge hides a purchase inside another one's event and is listed separately below.

## 1. Auto-link threshold sweep (dev split, arrival order)

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| matcher@0.70 | arrival | 84.2% | 94.1% | 2 | 6.5% | 5.9% | 2.0% | 31 (32) | 1 |
| matcher@0.75 | arrival | 82.4% | 82.4% | 2 | 6.1% | 5.9% | 6.1% | 33 (32) | 3 |
| matcher@0.80 | arrival | 82.4% | 82.4% | 2 | 6.1% | 5.9% | 6.1% | 33 (32) | 3 |
| matcher@0.85 | arrival | 100.0% | 64.7% | 0 | 0.0% | 5.9% | 16.3% | 38 (32) | 6 |
| matcher@0.90 | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |
| matcher@0.95 | arrival | 100.0% | 52.9% | 0 | 0.0% | 5.9% | 20.4% | 40 (32) | 8 |

Chosen: **0.85** (fewest false merges, then highest recall, then lowest review rate; ties go to the higher threshold). The test split was not used for this choice.

## 2. Test split at 0.85

| System | Order | Precision | Recall | False merges | False merge rate | Missed rate | Review rate | Events (true) | Double counted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| store-every-row | arrival | n/a | 0.0% | 0 | 0.0% | 100.0% | 0.0% | 51 (39) | 12 |
| matcher@0.85 | arrival | 100.0% | 91.7% | 0 | 0.0% | 0.0% | 3.9% | 40 (39) | 1 |
| matcher@0.85 | reverse | 84.6% | 91.7% | 1 | 2.6% | 8.3% | 3.9% | 39 (39) | 1 |

`reverse` replays the same records from the last arrival to the first, to show how much the result depends on arrival order.

## 3. False merges

| Run | Records | Scenarios | Purchases | Outcome per record |
| --- | --- | --- | --- | --- |
| matcher@0.70, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked |
| matcher@0.70, dev, arrival | R0083, R0088, R0096 | late_manual, late_manual, very_late_manual | E0007, E0021 | separate, auto_linked, auto_linked |
| matcher@0.75, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked |
| matcher@0.75, dev, arrival | R0083, R0088, R0096 | late_manual, late_manual, very_late_manual | E0007, E0021 | separate, auto_linked, auto_linked |
| matcher@0.80, dev, arrival | R0020, R0030 | single_notification, single_manual | E0048, E0049 | separate, auto_linked |
| matcher@0.80, dev, arrival | R0083, R0088, R0096 | late_manual, late_manual, very_late_manual | E0007, E0021 | separate, auto_linked, auto_linked |
| matcher@0.85, test, reverse | R0017, R0022, R0024 | late_manual, date_only_manual, date_only_manual | E0046, E0070 | auto_linked, auto_linked, separate |

## 4. Missed duplicates on the test split at 0.85

| Order | Records | Scenario | Outcome per record |
| --- | --- | --- | --- |
| reverse | R0013, R0017 | late_manual | separate, auto_linked |

## 5. Findings

Written with the run above; the numbers are the generated part. Same dataset as [2026-10-18-matching.md](2026-10-18-matching.md); the only change is the merchant score (shared tokens over the shorter name instead of Jaccard overlap, matcher `rules-2`).

- **Threshold.** 0.85 is still the lowest dev threshold without a false merge, so it stays. Below it the same two Decathlon false merges appear as with `rules-1`; the merchant change adds no new false merge on dev or test.
- **The late Decathlon entry (R0096)** still goes to review at 0.85 instead of joining the other 8990 HUF Decathlon purchase; its real pair stays missed (five days apart, outside the window).
- **Against the baseline (test, arrival order).** Of the 12 purchases the baseline counts twice, the matcher now leaves 1 (with `rules-1`: 4), and that one (R0069, the rounded MOL entry) waits for review against its own notification. Recall rises from 66.7% to 91.7%, the missed-duplicate rate falls from 16.7% to 0%, the review rate from 11.8% to 3.9%, with no false merge.
- **Arrival order still matters.** The reverse-order IKEA false merge (R0017 joining R0022 + R0024) remains: linking is greedy, and a record is not moved when a better match arrives later.
