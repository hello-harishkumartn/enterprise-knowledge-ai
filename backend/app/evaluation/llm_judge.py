"""Optional LLM-as-judge scoring for groundedness and answer relevance.

Real evaluation of "is this answer actually grounded / relevant" is a task
LLMs are much better at than lexical overlap. This is wired through the
same provider abstraction as generation, so it works with Gemini or Ollama
when configured. If no real provider is available (as in this sandbox and
in CI, which run with LLM_PROVIDER_ORDER=mock) or the judge's response
isn't parseable JSON, callers fall back to the heuristic scores in
metrics.py rather than failing the whole eval run.
"""
import json
import re

from app.llm.base import LLMProviderError
from app.llm.factory import generate_with_fallback

_JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator grading a RAG system's answer.
Score two dimensions from 1 (worst) to 5 (best):
- groundedness: is every claim in the answer actually supported by the context? (5 = fully supported, 1 = fabricated)
- relevance: does the answer actually address the question asked? (5 = fully addresses it, 1 = off-topic)
Respond with ONLY a JSON object: {"groundedness": <1-5>, "relevance": <1-5>}"""

_JSON_RE = re.compile(r"\{[^{}]*\}")


def judge_answer(
    question: str, answer: str, context_text: str, provider_order: list[str] | None = None
) -> dict[str, float] | None:
    """Returns {"groundedness": 0-1, "relevance": 0-1} normalized from the
    judge's 1-5 scale, or None if no real judge was available/parseable."""
    prompt = f"Question: {question}\n\nContext:\n{context_text}\n\nAnswer to grade:\n{answer}"
    try:
        result = generate_with_fallback(_JUDGE_SYSTEM_PROMPT, prompt, max_tokens=100, provider_order=provider_order)
    except LLMProviderError:
        return None

    if result.provider == "mock":
        # The mock provider does extractive answering, not judging — it
        # cannot produce a meaningful score, so we're explicit that no real
        # judge ran rather than silently returning a fake number.
        return None

    match = _JSON_RE.search(result.text)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        groundedness = float(parsed["groundedness"])
        relevance = float(parsed["relevance"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None

    return {
        "groundedness": max(0.0, min(1.0, (groundedness - 1) / 4)),
        "relevance": max(0.0, min(1.0, (relevance - 1) / 4)),
    }
