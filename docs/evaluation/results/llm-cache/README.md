# LLM answer cache

Answers of the LLM layer from paid measurement runs, one JSON file per model and prompt version (for example `categorization-<model>-llm-1.json`). The runner in `finsync/evaluation/hybrid.py` writes every answer here as it arrives and reads them back on a re-run, so a report can be reproduced without new calls and without paying twice.

The files hold only answers to the synthetic dataset `tests/data/categorization_eval.csv`; no real data and no API key. Like result files, they are not edited by hand.
