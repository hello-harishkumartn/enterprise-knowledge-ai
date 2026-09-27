"""LLM provider abstraction.

Nothing outside `app/llm/` knows or cares whether an answer came from
Gemini, Ollama, or the deterministic mock — every provider returns the same
`LLMResult` shape. This is what lets `app/rag/pipeline.py` stay provider-
agnostic and lets the factory fall back from a cloud API to a local model
without the caller changing at all.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class LLMProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a request (bad config, network,
    timeout, non-2xx). Callers (the fallback chain) catch this specifically
    so a real bug elsewhere doesn't get silently treated as "try the next
    provider"."""


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResult: ...
