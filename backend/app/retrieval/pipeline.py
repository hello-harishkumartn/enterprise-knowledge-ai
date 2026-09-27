"""Retrieval orchestrator: query -> keyword/vector retrieval -> fusion ->
RBAC (already enforced upstream in both retrievers) -> rerank.

The three retrieval modes are all real, independent code paths (not the
same query with a flag) so each can be inspected/evaluated on its own —
see /evals and the `/search` API's `mode` parameter.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.retrieval.embeddings import embed_query
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.keyword_search import keyword_search
from app.retrieval.reranker import rerank
from app.retrieval.types import RetrievedChunk
from app.retrieval.vector_search import vector_search

settings = get_settings()

RetrievalMode = str  # "semantic" | "keyword" | "hybrid"


@dataclass
class RetrievalFilters:
    document_ids: list[str] | None = None
    category: str | None = None
    department: str | None = None


def retrieve(
    db: Session,
    query: str,
    role: str,
    mode: RetrievalMode = "hybrid",
    top_n: int | None = None,
    filters: RetrievalFilters | None = None,
    use_reranker: bool = True,
) -> list[RetrievedChunk]:
    filters = filters or RetrievalFilters()
    top_n = top_n or settings.RETRIEVAL_FINAL_TOP_N

    if mode == "semantic":
        query_embedding = embed_query(query)
        candidates = vector_search(
            db, query_embedding, role, top_k=settings.RETRIEVAL_TOP_K_VECTOR,
            document_ids=filters.document_ids, category=filters.category, department=filters.department,
        )
    elif mode == "keyword":
        candidates = keyword_search(
            db, query, role, top_k=settings.RETRIEVAL_TOP_K_KEYWORD,
            document_ids=filters.document_ids, category=filters.category, department=filters.department,
        )
    elif mode == "hybrid":
        query_embedding = embed_query(query)
        vector_results = vector_search(
            db, query_embedding, role, top_k=settings.RETRIEVAL_TOP_K_VECTOR,
            document_ids=filters.document_ids, category=filters.category, department=filters.department,
        )
        keyword_results = keyword_search(
            db, query, role, top_k=settings.RETRIEVAL_TOP_K_KEYWORD,
            document_ids=filters.document_ids, category=filters.category, department=filters.department,
        )
        fused = reciprocal_rank_fusion(vector_results, keyword_results, k=settings.RETRIEVAL_RRF_K)
        candidates = fused[: settings.RETRIEVAL_FUSED_TOP_N]
    else:
        raise ValueError(f"Unknown retrieval mode: {mode}")

    if not candidates:
        return []

    if use_reranker:
        scores = rerank(query, [c.content for c in candidates])
        for chunk, score in zip(candidates, scores, strict=False):
            chunk.rerank_score = score
        candidates = sorted(candidates, key=lambda c: c.rerank_score, reverse=True)

    return candidates[:top_n]
