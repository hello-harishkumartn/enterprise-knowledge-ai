"""Reciprocal Rank Fusion (RRF) — combines two independently-ranked lists
(BM25 keyword rank, vector similarity rank) into one ranking using only each
result's *rank* in its own list, not its raw score. This sidesteps the
"BM25 scores and cosine similarities live on different scales" problem
entirely and is easy to explain: a chunk ranked highly by both signals wins.

    RRF(d) = sum over source rankings r that contain d of  1 / (k + rank_r(d))

`k` (default 60, the standard value from the original RRF paper) damps the
influence of very low ranks.
"""
from app.retrieval.types import RetrievedChunk


def reciprocal_rank_fusion(
    vector_results: list[RetrievedChunk],
    keyword_results: list[RetrievedChunk],
    k: int = 60,
) -> list[RetrievedChunk]:
    merged: dict[str, RetrievedChunk] = {}

    for chunk in vector_results:
        merged[chunk.chunk_id] = chunk

    for chunk in keyword_results:
        if chunk.chunk_id in merged:
            merged[chunk.chunk_id].keyword_score = chunk.keyword_score
            merged[chunk.chunk_id].keyword_rank = chunk.keyword_rank
        else:
            merged[chunk.chunk_id] = chunk

    for chunk in merged.values():
        score = 0.0
        if chunk.vector_rank is not None:
            score += 1.0 / (k + chunk.vector_rank)
        if chunk.keyword_rank is not None:
            score += 1.0 / (k + chunk.keyword_rank)
        chunk.fused_score = score

    return sorted(merged.values(), key=lambda c: c.fused_score, reverse=True)
