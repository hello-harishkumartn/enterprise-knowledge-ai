"""Lexical (BM25) retrieval.

BM25 needs an in-memory corpus, so the RBAC-filtered candidate set is loaded
from Postgres first (same `allowed_roles` filter as vector search) and BM25
is computed only over that already-authorized set. A chunk the caller's role
cannot see is never added to the corpus the ranker scores, so it cannot
surface here regardless of how well it matches the query.

Rebuilding BM25 per query is O(corpus size) — fine at this project's scale
(a few hundred chunks) and it keeps the RBAC guarantee trivially correct.
At real enterprise scale you'd move this to Postgres full-text search or an
external index (OpenSearch/Elastic) with the same role predicate pushed
into that index's filter, not computed after the fact.
"""
import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.retrieval.types import RetrievedChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def keyword_search(
    db: Session,
    query: str,
    role: str,
    top_k: int = 20,
    document_ids: list[str] | None = None,
    category: str | None = None,
    department: str | None = None,
) -> list[RetrievedChunk]:
    stmt = (
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.allowed_roles.contains([role]))
    )
    if document_ids:
        stmt = stmt.where(Document.id.in_(document_ids))
    if category:
        stmt = stmt.where(Document.category == category)
    if department:
        stmt = stmt.where(Document.department == department)

    rows = db.execute(stmt).all()
    if not rows:
        return []

    corpus_tokens = [_tokenize(chunk.content) for chunk, _ in rows]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(_tokenize(query))

    ranked = sorted(zip(rows, scores, strict=False), key=lambda pair: pair[1], reverse=True)

    results: list[RetrievedChunk] = []
    for rank, ((chunk, document), score) in enumerate(ranked[:top_k], start=1):
        if score <= 0:
            continue
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=document.id,
                document_name=document.name,
                content=chunk.content,
                section=chunk.section,
                page_number=chunk.page_number,
                document_type=document.document_type,
                department=document.department,
                category=document.category,
                allowed_roles=document.allowed_roles,
                keyword_score=float(score),
                keyword_rank=rank,
            )
        )
    return results
