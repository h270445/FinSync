"""The hybrid categorizer's LLM layer: asked only when the deterministic layer gives nothing or only `low`.

The model sees one record's merchant, description and amount, never member names or group data
([design](../../docs/design/categorization.md#llm-rules)). It must answer with one allowed category or
`unknown`; anything else is rejected and counted as `unknown`.

**Confidence is computed, not asked for.** Current models take no `temperature` and expose no token
log-probabilities, so the layer draws `samples` answers (5 by default) and uses the share of the most
frequent real category as its confidence (`LlmVote.share`). Below the abstention threshold the answer is
"Bizonytalan" (uncertain): the record keeps a `low` suggestion and nothing is settled
(`combine()`). The threshold is tuned on the development split only (`finsync/evaluation/hybrid.py`).

Every answer is cached by model, prompt version, the record's text and the sample number
(`AnswerCache`), so the same text is never sent twice and a measurement re-run gives the same numbers.

The provider sits behind `LlmClient`. `AnthropicClient` is the measured one; `OpenAICompatibleClient`
talks to any server with the OpenAI chat-completions API, such as a local model in LM Studio
(`http://localhost:1234/v1`), so a self-hosted model needs no code change. The `anthropic` package is
imported only when that client is built, so the rest of FinSync and the tests run without it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Protocol, Sequence

from finsync.categorization.hybrid import HIGH, LOW, SOURCE_NONE, CategoryDecision
from finsync.categorization.merchant_rules import CATEGORIES

PROMPT_VERSION = "llm-1"
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_SAMPLES = 5
UNKNOWN = "unknown"
# The category of a record that no layer could decide ("Bizonytalan" in the web app).
UNCATEGORIZED = "uncategorized"
SOURCE_LLM = "llm"

# USD per million tokens, from the provider's price list (2026-11-03). Used for the cost report only.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
}

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": [*CATEGORIES, UNKNOWN]}},
    "required": ["category"],
    "additionalProperties": False,
}

# Written from general knowledge of Hungarian spending, not from the labelled dataset.
SYSTEM_PROMPT = f"""You categorize one purchase of a Hungarian household for a shared spending tracker.
The text comes from a bank notification, a bank export or a member's manual entry; it may be Hungarian or
English, abbreviated, without accents, or a payment processor's cryptic code.

Allowed categories:
- groceries: supermarkets, food shops, bakeries, markets, drugstore basics bought with food
- eating_out: restaurants, cafés, canteens, fast food, food delivery
- transport: public transport, train, taxi, ride hailing, fuel, parking, tolls, car service
- housing_utilities: rent, common costs, electricity, gas, water, heating, internet, phone bills
- health: pharmacy, doctor, dentist, optician, medical tests
- clothing: clothes, shoes, accessories
- entertainment: cinema, concerts, streaming, games, books, sport events, hobbies, travel fun
- household: furniture, home improvement, kitchenware, cleaning products, electronics for the home
- other: a purchase you understand that fits none of the above (fees, gifts, donations, services)
- {UNKNOWN}: you cannot tell what was bought

Rules:
- Answer "{UNKNOWN}" rather than guess. A wrong confident category is worse than "{UNKNOWN}".
- A shop that sells many kinds of goods (hypermarket, drugstore, marketplace, department store) with no
  detail about what was bought: give its usual category only if almost all purchases there belong to it,
  otherwise "{UNKNOWN}".
- Use the description when it says what was bought; it beats the shop's usual category.
- Never answer anything except one category from the list."""


@dataclass(frozen=True)
class LlmReply:
    """One raw answer of the provider, with the numbers the cost and latency report needs."""

    text: str
    input_tokens: int
    output_tokens: int
    seconds: float


class LlmClient(Protocol):
    model: str

    def complete(self, system: str, user: str) -> LlmReply: ...


class AnthropicClient:
    """`LlmClient` on the Anthropic Messages API with a JSON schema for the answer.

    Credentials come from the environment (`ANTHROPIC_API_KEY` or an `ant auth login` profile)."""

    def __init__(self, model: str = DEFAULT_MODEL, client=None) -> None:
        import anthropic  # imported here so FinSync runs without the package when the LLM layer is off

        self.model = model
        self._client = client if client is not None else anthropic.Anthropic()

    def complete(self, system: str, user: str) -> LlmReply:
        started = time.perf_counter()
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": ANSWER_SCHEMA}},
        )
        seconds = time.perf_counter() - started
        text = "" if response.stop_reason == "refusal" else next(
            (block.text for block in response.content if block.type == "text"), ""
        )
        return LlmReply(text, response.usage.input_tokens, response.usage.output_tokens, seconds)


class OpenAICompatibleClient:
    """`LlmClient` for a server with the OpenAI chat-completions API (LM Studio, llama.cpp, vLLM, Ollama).

    The answer is constrained by the same JSON schema where the server supports `response_format`;
    `parse_answer()` checks it either way. A local server keeps the default sampling temperature, so the
    five samples still vary and the share stays a usable confidence."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 60.0,
                 transport=None) -> None:
        import httpx

        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.model = model
        self._http = httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout,
                                  transport=transport)

    def complete(self, system: str, user: str) -> LlmReply:
        started = time.perf_counter()
        response = self._http.post("/chat/completions", json={
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "category", "strict": True, "schema": ANSWER_SCHEMA}},
            "max_tokens": 256,
        })
        response.raise_for_status()
        seconds = time.perf_counter() - started
        data = response.json()
        choices = data.get("choices") or [{}]
        text = (choices[0].get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        return LlmReply(text, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)), seconds)


def user_prompt(merchant: str | None, description: str | None, amount: str | None, currency: str | None) -> str:
    """The per-record message: only merchant, description and amount."""
    lines = [
        f"Merchant: {merchant or '(none)'}",
        f"Description: {description or '(none)'}",
        f"Amount: {amount} {currency or ''}".rstrip() if amount else "Amount: (none)",
    ]
    return "\n".join(lines) + '\n\nAnswer as JSON: {"category": "<one allowed category>"}'


def parse_answer(text: str) -> str:
    """The category in a raw answer, or `unknown` when the answer is not valid JSON naming an allowed one.

    The model's output is untrusted: a category outside the list is never used."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return UNKNOWN
    category = data.get("category") if isinstance(data, dict) else None
    return category if category in CATEGORIES else UNKNOWN


class AnswerCache:
    """Raw answers by request key, kept in a JSON file so a re-run makes no new calls."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.entries: dict[str, dict] = {}
        if path is not None and path.exists():
            self.entries = json.loads(path.read_text(encoding="utf-8"))

    def get(self, key: str) -> LlmReply | None:
        entry = self.entries.get(key)
        return None if entry is None else LlmReply(**entry)

    def put(self, key: str, reply: LlmReply) -> None:
        self.entries[key] = {
            "text": reply.text,
            "input_tokens": reply.input_tokens,
            "output_tokens": reply.output_tokens,
            "seconds": round(reply.seconds, 3),
        }

    def save(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self.entries, ensure_ascii=False, indent=1, sort_keys=True)
            self.path.write_text(text + "\n", encoding="utf-8")


def request_key(model: str, user: str, sample: int) -> str:
    raw = json.dumps([model, PROMPT_VERSION, user, sample], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class LlmVote:
    """The answers for one record: the most frequent real category and its share of all samples."""

    answers: tuple[str, ...]
    replies: tuple[LlmReply, ...]
    new_calls: int

    @property
    def top(self) -> str:
        """The most frequent allowed category; `unknown` when no sample named one. Ties go to the
        category answered first, so the result does not depend on dictionary order."""
        real = [answer for answer in self.answers if answer != UNKNOWN]
        if not real:
            return UNKNOWN
        counts = Counter(real)
        best = max(counts.values())
        return next(answer for answer in real if counts[answer] == best)

    @property
    def share(self) -> float:
        """Share of all samples (`unknown` and rejected ones included) that gave `top`."""
        if self.top == UNKNOWN:
            return 0.0
        return self.answers.count(self.top) / len(self.answers)


class MissingAnswer(LookupError):
    """Raised in cache-only mode when an answer is not cached yet."""


class LlmCategorizer:
    """Draws `samples` answers per record through the cache. With `client=None` only cached answers are
    used and a missing one raises `MissingAnswer` (so a measurement never spends money by accident)."""

    def __init__(self, client: LlmClient | None, cache: AnswerCache, model: str = DEFAULT_MODEL,
                 samples: int = DEFAULT_SAMPLES) -> None:
        if client is not None:
            model = client.model
        self.client = client
        self.cache = cache
        self.model = model
        self.samples = samples
        self.used: set[str] = set()

    def distinct_replies(self) -> list[LlmReply]:
        """Each answer used so far, once: what the provider is billed for when the cache is in front."""
        return [reply for key in sorted(self.used) if (reply := self.cache.get(key)) is not None]

    def missing(self, merchant: str | None, description: str | None, amount: str | None,
                currency: str | None) -> int:
        """How many samples of this record are not cached."""
        user = user_prompt(merchant, description, amount, currency)
        return sum(self.cache.get(request_key(self.model, user, n)) is None for n in range(self.samples))

    def vote(self, merchant: str | None, description: str | None, amount: str | None = None,
             currency: str | None = None) -> LlmVote:
        user = user_prompt(merchant, description, amount, currency)
        replies: list[LlmReply] = []
        new_calls = 0
        for sample in range(self.samples):
            key = request_key(self.model, user, sample)
            reply = self.cache.get(key)
            if reply is None:
                if self.client is None:
                    raise MissingAnswer(f"no cached answer for {merchant or description!r}, sample {sample}")
                reply = self.client.complete(SYSTEM_PROMPT, user)
                self.cache.put(key, reply)
                new_calls += 1
            self.used.add(key)
            replies.append(reply)
        return LlmVote(tuple(parse_answer(r.text) for r in replies), tuple(replies), new_calls)


def needs_llm(decision: CategoryDecision) -> bool:
    """The LLM is asked only when the deterministic layer gave nothing or only a `low` answer."""
    return decision.confidence == LOW


def combine(decision: CategoryDecision, vote: LlmVote | None, threshold: float) -> CategoryDecision:
    """The hybrid answer from the deterministic decision and the LLM vote.

    - A `high` deterministic answer is kept; the LLM is not consulted.
    - An LLM category whose share reaches `threshold` is settled: source `llm`, `high`.
    - Otherwise the record is "Bizonytalan": the deterministic `low` suggestion is kept when there is one,
      else the LLM's top category as a `low` suggestion, else `uncategorized`."""
    if not needs_llm(decision):
        return decision
    if vote is not None and vote.top != UNKNOWN and vote.share >= threshold:
        return CategoryDecision(vote.top, SOURCE_LLM, HIGH)
    if decision.source != SOURCE_NONE:
        return decision
    if vote is not None and vote.top != UNKNOWN:
        return CategoryDecision(vote.top, SOURCE_LLM, LOW)
    return CategoryDecision(UNCATEGORIZED, SOURCE_NONE, LOW)


def cost_usd(model: str, replies: Sequence[LlmReply]) -> float | None:
    """The price of these replies, or None for a model without a known price."""
    prices = PRICES_PER_MTOK.get(model)
    if prices is None:
        return None
    tokens_in = sum(r.input_tokens for r in replies)
    tokens_out = sum(r.output_tokens for r in replies)
    return (tokens_in * prices[0] + tokens_out * prices[1]) / 1_000_000
