import pytest

from app.llm.base import LLMProviderError
from app.llm.factory import AllProvidersFailedError, generate_with_fallback
from app.llm.gemini_provider import GeminiProvider
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider

SYSTEM_PROMPT = "Answer using only the context. Cite with [n]."


def _user_prompt(context_blob: str, question: str) -> str:
    return f"Context:\n{context_blob}\n\nQuestion: {question}"


def test_mock_provider_answers_with_citation_from_relevant_block():
    context = (
        "[1] Leave Policy (p.4)\nEmployees may carry forward up to 10 unused PTO days into the following year.\n\n"
        "---\n\n"
        "[2] Travel Policy (p.1)\nEconomy class is standard for flights under 6 hours."
    )
    prompt = _user_prompt(context, "How many PTO days can I carry over?")

    result = MockProvider().generate(SYSTEM_PROMPT, prompt, max_tokens=200)

    assert "[1]" in result.text
    assert "10" in result.text
    assert result.provider == "mock"


def test_mock_provider_says_insufficient_evidence_when_context_empty():
    prompt = _user_prompt("", "What is the meaning of life?")

    result = MockProvider().generate(SYSTEM_PROMPT, prompt, max_tokens=200)

    assert "don't have enough information" in result.text.lower()


def test_mock_provider_says_insufficient_evidence_when_context_irrelevant():
    context = "[1] Travel Policy (p.1)\nEconomy class is standard for flights under 6 hours."
    prompt = _user_prompt(context, "What is our quantum encryption algorithm?")

    result = MockProvider().generate(SYSTEM_PROMPT, prompt, max_tokens=200)

    assert "don't have enough information" in result.text.lower()


def test_gemini_provider_raises_without_api_key():
    provider = GeminiProvider(api_key="", model="gemini-1.5-flash", base_url="https://example.com", timeout=1.0)
    with pytest.raises(LLMProviderError):
        provider.generate(SYSTEM_PROMPT, "hi", 100)


def test_ollama_provider_raises_when_unreachable():
    provider = OllamaProvider(base_url="http://localhost:1", model="llama3.2", timeout=1.0)
    with pytest.raises(LLMProviderError):
        provider.generate(SYSTEM_PROMPT, "hi", 100)


def test_fallback_chain_skips_failed_providers_and_uses_mock():
    result = generate_with_fallback(
        SYSTEM_PROMPT,
        _user_prompt("[1] Doc (p.1)\nSome content about leave.", "leave?"),
        provider_order=["gemini", "ollama", "mock"],
    )
    assert result.provider == "mock"


def test_fallback_chain_raises_when_all_providers_fail():
    with pytest.raises(AllProvidersFailedError):
        generate_with_fallback(SYSTEM_PROMPT, "hi", provider_order=["gemini", "ollama"])
