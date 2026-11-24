# Runbook: the paid hybrid categorizer measurement

Everything the measurement needs is in place (2026-11-19). The only missing piece is the API key, which the author gives in the week of Nov 23. Decisions behind it: [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md). Protocol: [dev-test-evaluation skill](../../.claude/skills/dev-test-evaluation/SKILL.md).

Approved by the author on 2026-11-19: model `claude-haiku-5-5`, the 200-item dataset with five samples per record that needs the LLM (390 calls, estimated USD 0.04), a budget of USD 2, and the threshold rule (highest dev coverage with at most 5 % wrong settled answers, ties to the higher threshold).

## 1. Provide the key (author)

Either:

- **Cloud environment:** the project settings in Claude Code → Cloud environment → gear → environment variable `FINSYNC_ANTHROPIC_API_KEY`. Not `ANTHROPIC_API_KEY`: a cloud session does not pass that name on to its commands (found on 2026-11-24), and it points `ANTHROPIC_BASE_URL` at its own proxy, so the runner sends the FinSync-specific key to `https://api.anthropic.com` explicitly. Everyone who uses the environment, and commands in its sessions, can read it. Only a session started after the change sees it.
- **Own computer:** set `ANTHROPIC_API_KEY` in the shell (PowerShell: `$env:ANTHROPIC_API_KEY = "..."`) and run the steps below there.

Never commit the key or paste it into a chat.

## 2. Check, without spending anything

```bash
pip install -r requirements.txt
python -m finsync.evaluation.hybrid --preflight
```

It prints the provider, the dataset, the cache, the number of missing calls with the estimated cost, and `READY` or what is missing. It makes no call.

## 3. Run (one command, about USD 0.04, a few minutes)

```bash
python -m finsync.evaluation.hybrid --call-llm --out docs/evaluation/results/<YYYY-MM-DD>-categorization-hybrid.md
```

The runner categorizes the dev split, chooses the threshold from dev alone, then categorizes the test split once. Every answer is written to `docs/evaluation/results/llm-cache/categorization-claude-haiku-5-5-llm-1.json`, also when the run stops halfway, so a second run continues without paying twice.

## 4. Check reproducibility and commit

```bash
python -m finsync.evaluation.hybrid --out /tmp/again.md     # cache only, no calls
diff <(sed '/report date/d;/new calls/d' docs/evaluation/results/<date>-categorization-hybrid.md) <(sed '/report date/d;/new calls/d' /tmp/again.md)
python -m unittest discover -s tests
git add docs/evaluation/results/
```

The committed report must come from a clean tree (`git describe` without `-dirty`). Then add its row to [README.md](README.md), update the [thesis map](../thesis-map.md) row "Rules or LLM for categorization?", and let the author read the report before it is quoted (checkpoint 3 of the skill).

## A self-hosted model instead (optional)

Any server with the OpenAI chat-completions API works, for example LM Studio:

```bash
python -m finsync.evaluation.hybrid --base-url http://localhost:1234/v1 --model <model name> --preflight
python -m finsync.evaluation.hybrid --base-url http://localhost:1234/v1 --model <model name> --call-llm \
    --out docs/evaluation/results/<date>-categorization-hybrid-<model>.md
```

It gets its own cache file and its own report. Keep the LM Studio port on `localhost` or the home network: it has no authentication by default. `FINSYNC_LLM_API_KEY` is sent as a bearer token if the server needs one.
