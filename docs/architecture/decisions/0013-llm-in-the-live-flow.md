# 0013. LLM in the live flow: off by default, members first, a monthly budget, only the record text leaves

- Status: Proposed (the scheduling rules were set by the author on 2026-11-19 and confirmed on 2026-11-24; built on 2026-11-24; to be accepted by the author)
- Date: 2026-11-24

## Context

[ADR 0011](0011-llm-categorization-layer.md) chose the provider, the five-sample confidence and the abstention rule, and used the LLM layer only in the measurement. The [measurement of 2026-11-24](../../evaluation/results/2026-11-24-categorization-hybrid.md) chose the threshold 0.40 on the dev split. The next step was to let the live system ask the model about the events that stay uncertain, which raises four questions the measurement did not answer:

- **When** is the model asked? Asking at once costs money for records a member would have categorized anyway, and the author wants the members to decide first ([categorization design](../../design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19)).
- **Who decides** that group data may leave the server at all?
- **What does it cost**, and what stops a runaway cost?
- **What leaves** the system, and where is that recorded?

The API runs as one process on one machine (ADR 0006, ADR 0007); there is no job queue or external scheduler.

## Decision

1. **Off by default, per group.** Each group has one setting in `group_llm_settings`: `never` (default; nothing is sent), `after_arrival` (X hours after the record arrived, 24 by default), `daily` (at a Budapest wall-clock time, 20:00 by default) or `weekly` (weekday and time, Sunday 20:00 by default). Only an admin changes it (ADR 0012's least-privilege rule: `PUT /v1/llm-settings` works only from a web session). Every member sees the setting, the month's spending and the model on W8.
2. **Members first.** An uncertain event gets an `llm_due_at` time from the setting. Until then, and at any time after, a member's decision (`category_source = user`) wins: the run skips an event that was decided in the meantime, a member's decision clears the due time, and the answer is written only if the event is still uncertain when the answer comes back (the model is called outside the database transaction). "Ask for a suggestion now" works in every mode, for one event a member chooses.
3. **Same rule as measured.** The answer is combined with the deterministic result by the measured rule and threshold (0.40): at or above it the event is settled (`llm`, `high`) and shows the share of agreeing samples; below it the event stays uncertain with a suggestion.
4. **A monthly budget per group.** `monthly_budget_usd` (USD 1.00 by default, at most 100) is compared with the sum of the month's logged costs (Budapest calendar month). When it is reached, scheduled runs stop for that group, "ask now" answers `409` with the reason, and W8 says so; the due times stay for the next month or a higher budget. Identical texts are answered from an in-memory cache and cost nothing again during one server run.
5. **Only the record text leaves.** For one event, the primary record's merchant, description and amount with currency are sent; no member, group, account or token data. Events settled by the deterministic layer (merchant rules, dictionary `high`, own-account transfers) are never sent.
6. **Every call is logged.** `llm_calls` records who asked (`schedule` or the member), the event, the model, the number of new calls, tokens and cost. It is both the budget's ledger and the record of what data left the system.
7. **An in-process runner, only with a key.** The API process starts a daemon thread that looks for due events every 5 minutes, only when `FINSYNC_ANTHROPIC_API_KEY` is set; a key named for another program (`ANTHROPIC_API_KEY`) never makes FinSync send data. A failed run is logged and retried at the next interval; the server stays up. Without a key the setting can be saved, nothing is sent and the UI says that the server has no model.

## Consequences

- A group that never opens W8 never sends anything to a model; the thesis can say that the external call is opt-in, by an admin, with a visible cost.
- The member's decision is the strongest source in every case, so a late or wrong model answer cannot overwrite a correction; the tests check this for the schedule, for "ask now" and for a decision made during the call.
- With the measured cost (about USD 0.0004 per record sent, [report](../../evaluation/results/2026-11-24-categorization-hybrid.md#5-latency-and-cost-of-the-llm-layer)) the default budget covers roughly 2 500 uncertain records a month, far more than a household produces.
- The runner is tied to the API process: with more than one process every process would run it. That is outside the thesis scope (one process, ADR 0007); a database lock or an external scheduler would be the change then.
- The cache lives in memory, so a restart may ask about the same text again; this costs fractions of a cent and keeps no record text on disk beyond the event itself.
- The description is bank text and may contain a shop owner's name (for example a sole trader's card terminal). It is sent as it is, like in the measurement; masking names is a possible later step, noted in the [security and privacy](../security-and-privacy.md) document.
- Design views 5 and 6 show the optional outbound call as a trust boundary with the rule of point 5 ([design views](../design-views.md)).
- Not built: notifications about due questions, a small-amount limit, batch calls and a persistent cache (later, [categorization design](../../design/categorization.md)).
