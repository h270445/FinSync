"""A scripted stand-in for the language model, so no test ever makes a paid call.

`fake_categorizer("groceries")` answers every sample with that category; a list cycles through its
answers sample by sample (["clothing", "groceries", ...]), so a test sets the share of agreeing answers.
"""

from __future__ import annotations

import json

from finsync.categorization.llm import AnswerCache, LlmCategorizer, LlmReply


class ScriptedClient:
    model = "claude-haiku-5-5"  # a model with a known price, so the cost guard has something to count

    def __init__(self, answers: str | list[str]) -> None:
        self.answers = [answers] if isinstance(answers, str) else list(answers)
        self.calls = 0
        self.prompts: list[str] = []

    def complete(self, system: str, user: str) -> LlmReply:
        answer = self.answers[self.calls % len(self.answers)]
        self.calls += 1
        self.prompts.append(user)
        return LlmReply(json.dumps({"category": answer}), input_tokens=1000, output_tokens=10, seconds=0.01)


def fake_categorizer(answers: str | list[str]) -> LlmCategorizer:
    return LlmCategorizer(ScriptedClient(answers), AnswerCache())
