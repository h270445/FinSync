# Thesis map

Where the material for the thesis, the report and the defence already lives in the repository (BSc thesis, written in Szakdolgozat II.). It points to evidence; it does not repeat it. Kept up to date with the [docs-and-comments skill](../.claude/skills/docs-and-comments/SKILL.md): a session that adds a decision, a measurement or a limitation adds its link here.

## Chapters and their evidence

| Chapter (working outline) | Evidence in the repository |
| --- | --- |
| Problem and goals | [Project overview](overview.md), [semester commitment (M0)](planning/milestones/m0-2026-10-09-semester-commitment.md) |
| Requirements and scope | [Roadmap: committed items and priority order](planning/roadmap.md), [user interface](design/user-interface.md), [supervisor feedback](planning/supervisor-feedback.md) |
| Architecture | [Architecture overview](architecture/overview.md), [technology stack](architecture/technology-stack.md), ADRs [0002](architecture/decisions/0002-python-stdlib-and-sqlite.md), [0003](architecture/decisions/0003-layered-package-layout.md), [0005](architecture/decisions/0005-web-client-first.md), [0006](architecture/decisions/0006-framework-based-stack.md), [0007](architecture/decisions/0007-how-external-clients-reach-the-api.md) |
| Main contribution: transaction matching | [Matching design](design/transaction-matching.md), [ADR 0004](architecture/decisions/0004-event-based-transaction-matching.md), [ADR 0008](architecture/decisions/0008-notification-time-and-calendar-day.md), code in [finsync/matching/](../finsync/matching/README.md) |
| Categorization | [Categorization design](design/categorization.md), [baseline result](evaluation/results/2026-11-08-categorization-rules.md) |
| Clients and data sources | [Android spike](design/android-notification-spike.md), [Android app](../clients/android/README.md), [web app](../web/README.md) |
| Security and privacy | [Security and privacy](architecture/security-and-privacy.md), ADRs [0009](architecture/decisions/0009-api-tokens.md) and [0010](architecture/decisions/0010-web-sign-in.md), [bank-notification-privacy skill](../.claude/skills/bank-notification-privacy/SKILL.md) |
| Evaluation method | [Evaluation plan](evaluation/evaluation-plan.md), [datasets](evaluation/datasets.md), [dev-test-evaluation skill](../.claude/skills/dev-test-evaluation/SKILL.md) |
| Results | [All result reports](evaluation/README.md), key ones: [matching rules-3 (Oct 29)](evaluation/results/2026-10-29-matching-rules-3.md), [regression check on dataset v3 (Nov 12)](evaluation/results/2026-11-12-matching-rules-3-v3.md) |
| Development method and AI use | [AI usage log, author decisions, skill usage](ai-usage.md), [agent skills](../.claude/skills/README.md), [time log](planning/time-log.md) |
| Limitations and future work | "Known limits" in [datasets](evaluation/datasets.md), "Consequences" of each ADR, [roadmap risks and Szakdolgozat II.](planning/roadmap.md) |

## Defence questions

Questions the committee is likely to ask, and where the answer is backed. A question without evidence yet is marked *open*.

| Question | Where the answer is backed |
| --- | --- |
| Why a rule-based, explainable matcher instead of machine learning? | [Matching design](design/transaction-matching.md#matching-approach), [ADR 0004](architecture/decisions/0004-event-based-transaction-matching.md) |
| How do you know the matcher does not merge separate purchases? | [Matching rules-3 results](evaluation/results/2026-10-29-matching-rules-3.md): 0 false merges on the test split in both arrival orders |
| Why can the results be trusted (no tuning on the test data)? | [Evaluation plan](evaluation/evaluation-plan.md#1-transaction-matching), [dev-test-evaluation skill](../.claude/skills/dev-test-evaluation/SKILL.md) |
| How are times and time zones handled? | [ADR 0008](architecture/decisions/0008-notification-time-and-calendar-day.md), `tests/test_local_time.py` |
| Why synthetic data, and how realistic is it? | [Datasets](evaluation/datasets.md), [Android spike](design/android-notification-spike.md) (masked real formats) |
| How is sensitive financial data protected? | [Security and privacy](architecture/security-and-privacy.md), ADRs [0009](architecture/decisions/0009-api-tokens.md), [0010](architecture/decisions/0010-web-sign-in.md); *open*: the December security evaluation |
| Why scrypt and not Argon2? | [ADR 0010](architecture/decisions/0010-web-sign-in.md) |
| Rules or LLM for categorization? | [Categorization design](design/categorization.md); *open*: the hybrid categorizer measurement (M2) |
| How was AI used, and how was its output checked? | [AI usage](ai-usage.md), [agent skills](../.claude/skills/README.md) |
| What does the system not do? | Scope in the [overview](overview.md), "Known limits" in [datasets](evaluation/datasets.md) |
