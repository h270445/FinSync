# 0004. Event-based, rule-scored transaction matching

- Status: Proposed
- Date: 2026-10-09

## Context

The same purchase can arrive from a banking notification, a manual entry and another member's entry. Merging rows destroys traceability; comparing only amount and time causes false merges of separate purchases.

## Decision

- Keep every incoming record unchanged and link records describing the same purchase to one shared **event**.
- An event holds at most one original record per **channel** (source type plus submitting member); this rule prevents most false merges. Exact re-deliveries are stored with a link to the record they repeat and do not count as originals.
- Score candidates with a transparent weighted rule score (amount, time, merchant) and two thresholds: auto-link, review, or keep separate.
- Write every decision, automatic or human, to an append-only `match_decisions` log with a `matcher_version`.

Full design: [design/transaction-matching.md](../../design/transaction-matching.md).

## Consequences

- Every decision can be explained, confirmed or undone (`split`).
- Thresholds are tuned on a labelled development split and reported on a held-out test split.
- Requires a schema migration (`events`, `match_decisions`, new `transactions` columns).
- An LLM matcher, if tried later, is evaluated only as a comparison against this baseline.
