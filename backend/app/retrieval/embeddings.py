"""Local, free embedding model (sentence-transformers). Loaded lazily and
cached as a process-wide singleton so the ~90MB model is only downloaded /
loaded into memory once, not per request.
"""
from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
