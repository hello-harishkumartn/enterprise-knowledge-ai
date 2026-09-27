"""Deterministic, offline provider used in tests/CI and as the guaranteed
last resort in the fallback chain.

It does real extractive work (word-overlap scoring against the actual
context blocks the RAG pipeline built) rather than returning a canned
string, so it exercises the full citation/insufficient-evidence logic
without needing network access, an API key, or a running Ollama daemon.
"""
import re
import time

from app.llm.base import LLMProvider, LLMResult

_BLOCK_RE = re.compile(r"\[(\d+)\]\s+(.+?)\n([\s\S]*?)(?=\n\n---\n\n|\Z)")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "and", "in", "for", "on", "what",
    "how", "do", "does", "can", "i", "my", "it", "this", "that", "be", "was",
    "were", "with", "as", "at", "by", "or", "if", "when", "who",
}
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


class MockProvider(LLMProvider):
    name = "mock"

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> LLMResult:
        start = time.perf_counter()
        match = re.search(r"Context:\n([\s\S]*?)\n\nQuestion:", user_prompt)
        question_match = re.search(r"Question:\s*(.+)", user_prompt)
        question = question_match.group(1).strip() if question_match else user_prompt
        context_blob = match.group(1) if match else ""

        blocks = _BLOCK_RE.findall(context_blob)
        question_words = _words(question)

        if not blocks or not question_words:
            text = (
                "I don't have enough information in the currently indexed documents "
                "to answer this question confidently."
            )
            return self._result(text, start)

        scored = []
        for number, _header, body in blocks:
            body = body.strip()
            overlap = len(question_words & _words(body))
            scored.append((overlap, int(number), body))
        scored.sort(key=lambda t: t[0], reverse=True)

        top = [s for s in scored if s[0] > 0][:2] or scored[:1]
        if top[0][0] == 0:
            text = (
                "I don't have enough information in the currently indexed documents "
                "to answer this question confidently."
            )
            return self._result(text, start)

        sentences_out = []
        for _overlap, number, body in top:
            sentences = _SENTENCE_RE.split(body)
            best_sentence = max(sentences, key=lambda s: len(question_words & _words(s)), default=body)
            sentences_out.append(f"{best_sentence.strip()} [{number}]")

        text = "Based on the available documents: " + " ".join(sentences_out)
        return self._result(text, start)

    def _result(self, text: str, start: float) -> LLMResult:
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResult(
            text=text,
            provider=self.name,
            model="extractive-mock-v1",
            prompt_tokens=0,
            completion_tokens=len(text.split()),
            latency_ms=latency_ms,
        )
