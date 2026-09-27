"""Primary LLM provider: Google Gemini free-tier REST API, called directly
over HTTP (no SDK dependency) so the integration is easy to read end to end.
"""
import time

import httpx

from app.llm.base import LLMProvider, LLMProviderError, LLMResult


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResult:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured")

        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens},
        }

        start = time.perf_counter()
        try:
            resp = httpx.post(
                url, params={"key": self.api_key}, json=payload, timeout=self.timeout
            )
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Gemini request failed: {exc}") from exc
        latency_ms = (time.perf_counter() - start) * 1000

        if resp.status_code != 200:
            raise LLMProviderError(f"Gemini returned {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMProviderError(f"Unexpected Gemini response shape: {data}") from exc

        usage = data.get("usageMetadata", {})
        return LLMResult(
            text=text.strip(),
            provider=self.name,
            model=self.model,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            latency_ms=latency_ms,
        )
