# Evaluation plan

All evaluation uses synthetic data. Each measurement is reproducible from a commit id and a single command.

## 1. Transaction matching

A test dataset will contain examples of duplicate transactions, distinct transactions with similar attributes, incomplete records, and conflicting input data.

**Dataset** (`tests/data/matching_eval.csv`; version 1 with 100 records exists, see [datasets.md](datasets.md)): 200–300 synthetic records in the final version, each with its channel, member, raw fields and a hand-assigned `true_event` label. Records are split 50/50 into development and test sets by `true_event`, so both records of a pair stay together. Thresholds are tuned on the development split only.

The evaluation will measure:

| Metric | Definition |
| --- | --- |
| Duplicate detection precision | Merged pairs that are true / all merged pairs |
| Duplicate detection recall | True pairs merged / all true pairs |
| False merge rate | Events containing records from two or more true events / all predicted events |
| Missed duplicate rate | True pairs left in different events and not flagged for review / all true pairs |
| Review rate (ambiguous case handling) | Records ending in `needs_review` / all records |

**Baseline:** the same metrics for a naive system that stores every incoming row separately (the current behaviour). The difference shows how many double-counted expenses matching removes and at what cost in false merges and review effort.

The runner (`python -m finsync.evaluation`) replays a split in arrival order through a fresh temporary SQLite database, sweeps the auto-link threshold on the development split from 0.70 to 0.95 in steps of 0.05, and picks the threshold with the fewest false merges, then the highest recall, then the lowest review rate (ties go to the higher threshold). It reports the test split at that threshold in arrival order and in reverse order, to show how much the result depends on arrival order. A true pair split across two events counts as caught, not missed, only when one record waits for review against the other record's event. Every false merge and every missed duplicate is listed by record id. The evaluation also considers the ability to trace and correct matching decisions.

## 2. Transaction categorization

The existing rule-based categorizer will serve as a baseline for comparison with a planned LLM-based approach.

Both approaches will be evaluated on the same manually labeled dataset using measures such as:

* Categorization accuracy.
* Performance on ambiguous or unfamiliar transaction descriptions.
* Consistency and error patterns.
* Response time and, where applicable, estimated operating cost.

The goal is to determine where an LLM provides a measurable benefit over deterministic rules, rather than assuming that an AI-based solution is inherently better.

Ambiguous merchants (for example a supermarket that also sells clothing) are labelled separately, and abstaining is scored as its own outcome; the details are in the [categorization design](../design/categorization.md#evaluation).

## 3. Security and privacy

Requirements are in [architecture/security-and-privacy.md](../architecture/security-and-privacy.md). They are verified with automated tests where possible:

| Property | Check |
| --- | --- |
| Group isolation | Every endpoint called with another group's ids returns 403/404 and writes nothing |
| Input validation | Malformed JSON, wrong types, non-finite amounts, oversized bodies are rejected with 400 |
| Atomicity | A failing bulk import stores nothing |
| Traceability | Every stored record and matching decision can be traced to its source and decider |
| Identity | Requests without valid credentials are rejected (after authentication is added) |
| AI boundary | LLM output outside the allowed categories is rejected |
