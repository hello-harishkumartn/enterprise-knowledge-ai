"""Pure, dependency-free metric functions — deliberately separated from the
runner (which needs a live DB + retrieval pipeline) so they can be unit
tested directly against hand-constructed inputs.

Retrieval metrics compare at the *document* level (a question is "about"
one or more expected source documents) rather than exact chunk id, which is
more robust to chunking-parameter changes and simpler to hand-author ground
truth for.
"""
import re

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "is", "are", "of", "to", "and", "in", "for", "on", "what",
    "how", "do", "does", "can", "i", "my", "it", "this", "that", "be", "was",
    "were", "with", "as", "at", "by", "or", "if", "when", "who", "not",
}
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_CITATION_RE = re.compile(r"\[(\d+)\]")


def _words(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


def recall_at_k(retrieved_doc_ids: list[str], expected_doc_ids: list[str], k: int) -> float:
    if not expected_doc_ids:
        return 1.0
    top_k = set(retrieved_doc_ids[:k])
    hit = len(top_k & set(expected_doc_ids))
    return hit / len(set(expected_doc_ids))


def precision_at_k(retrieved_doc_ids: list[str], expected_doc_ids: list[str], k: int) -> float:
    top_k = retrieved_doc_ids[:k]
    if not top_k:
        return 0.0
    hit = len(set(top_k) & set(expected_doc_ids))
    return hit / len(top_k)


def mean_reciprocal_rank(retrieved_doc_ids: list[str], expected_doc_ids: list[str]) -> float:
    expected = set(expected_doc_ids)
    for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
        if doc_id in expected:
            return 1.0 / rank
    return 0.0


def citation_correctness(cited_document_ids: list[str], expected_doc_ids: list[str]) -> float:
    """Fraction of citations in the answer that point to an expected source.
    An answer with zero citations scores 0 (it should have cited something)
    unless the question also expects no answer (empty expected set -> 1.0,
    handled by the caller for the insufficient-evidence case).
    """
    if not cited_document_ids:
        return 0.0
    expected = set(expected_doc_ids)
    correct = sum(1 for d in cited_document_ids if d in expected)
    return correct / len(cited_document_ids)


def groundedness_heuristic(answer_text: str, context_text: str) -> float:
    """Lexical-overlap proxy for groundedness: for each answer sentence,
    what fraction of its (non-stopword) words also appear somewhere in the
    retrieved context? Averaged across sentences. A cheap, offline stand-in
    for an LLM-judge groundedness score — see `llm_judge.py` for the richer
    version used when a real provider is configured.
    """
    sentences = [s for s in _SENTENCE_RE.split(answer_text) if _words(s)]
    if not sentences:
        return 0.0
    context_words = _words(context_text)
    if not context_words:
        return 0.0

    scores = []
    for sentence in sentences:
        sentence_words = _words(sentence)
        if not sentence_words:
            continue
        overlap = len(sentence_words & context_words) / len(sentence_words)
        scores.append(overlap)
    return sum(scores) / len(scores) if scores else 0.0


def answer_relevance_heuristic(answer_text: str, question: str) -> float:
    """Lexical-overlap proxy for "does the answer address the question" —
    fraction of the question's key words that reappear in the answer."""
    question_words = _words(question)
    if not question_words:
        return 0.0
    answer_words = _words(answer_text)
    return len(question_words & answer_words) / len(question_words)


def extract_cited_numbers(answer_text: str) -> list[int]:
    return sorted({int(n) for n in _CITATION_RE.findall(answer_text)})
