"""Builds the provider fallback chain from `Settings.LLM_PROVIDER_ORDER` and
walks it until one provider succeeds.

This is the actual "do NOT tightly couple to one LLM provider" requirement:
swapping providers, reordering the fallback, or adding a third provider is a
one-line config/class change, never a change to `app/rag/pipeline.py`.
"""
import logging

from app.config import Settings, get_settings
from app.llm.base import LLMProvider, LLMProviderError, LLMResult
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def build_provider(name: str, settings: Settings) -> LLMProvider:
    if name == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            base_url=settings.GEMINI_BASE_URL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if name == "ollama":
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    if name == "mock":
        return MockProvider()
    raise ValueError(f"Unknown LLM provider: {name}")


class AllProvidersFailedError(RuntimeError):
    pass


def generate_with_fallback(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
    provider_order: list[str] | None = None,
) -> LLMResult:
    settings = get_settings()
    order = provider_order or settings.llm_provider_order
    max_tokens = max_tokens or settings.LLM_MAX_OUTPUT_TOKENS

    errors: list[str] = []
    for name in order:
        provider = build_provider(name, settings)
        try:
            return provider.generate(system_prompt, user_prompt, max_tokens)
        except LLMProviderError as exc:
            logger.warning("LLM provider %s failed, trying next: %s", name, exc)
            errors.append(f"{name}: {exc}")

    raise AllProvidersFailedError(
        f"All configured LLM providers failed: {'; '.join(errors)}"
    )
