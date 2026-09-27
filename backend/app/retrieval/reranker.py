"""Cross-encoder reranker — scores (query, chunk) pairs jointly, which is far
more accurate than cosine similarity alone but too slow to run over an
entire corpus, so it only ever sees the small fused candidate set.
"""
from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_reranker():
    from sentence_transformers import CrossEncoder

    settings = get_settings()
    return CrossEncoder(settings.RERANKER_MODEL)


def rerank(query: str, candidates: list[str]) -> list[float]:
    if not candidates:
        return []
    model = get_reranker()
    pairs = [[query, c] for c in candidates]
    scores = model.predict(pairs)
    return [float(s) for s in scores]
