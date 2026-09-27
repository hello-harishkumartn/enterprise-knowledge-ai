"""Fallback LLM provider: a local Ollama daemon running an open-weight model
(e.g. llama3.2). Used when Gemini is unavailable/unconfigured/rate-limited,
so the app keeps working with zero cloud dependency.
"""
import time

import httpx

from app.llm.base import LLMProvider, LLMProviderError, LLMResult


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResult:
        payload = {
            "model": self.model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.2},
        }
        start = time.perf_counter()
        try:
            # Short connect timeout: if no local Ollama daemon is running we
            # want to fail fast and move to the next provider, not hang.
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=httpx.Timeout(self.timeout, connect=2.0),
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code != 200:
            raise LLMProviderError(f"Ollama returned {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        return LLMResult(
            text=data.get("response", "").strip(),
            provider=self.name,
            model=self.model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )
