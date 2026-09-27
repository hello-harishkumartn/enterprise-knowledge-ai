"""Semantic (vector) retrieval over pgvector.

RBAC is enforced here, in the SQL WHERE clause, not after the rows come
back — an unauthorized chunk is never fetched from the database in the
first place, let alone handed to an LLM.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.retrieval.types import RetrievedChunk


def vector_search(
    db: Session,
    query_embedding: list[float],
    role: str,
    top_k: int = 20,
    document_ids: list[str] | None = None,
    category: str | None = None,
    department: str | None = None,
) -> list[RetrievedChunk]:
    distance = Chunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(Chunk, Document, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.allowed_roles.contains([role]))
        .where(Chunk.embedding.is_not(None))
    )
    if document_ids:
        stmt = stmt.where(Document.id.in_(document_ids))
    if category:
        stmt = stmt.where(Document.category == category)
    if department:
        stmt = stmt.where(Document.department == department)

    stmt = stmt.order_by(distance).limit(top_k)

    results: list[RetrievedChunk] = []
    for rank, (chunk, document, dist) in enumerate(db.execute(stmt).all(), start=1):
        similarity = 1.0 - float(dist)
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
                vector_score=similarity,
                vector_rank=rank,
            )
        )
    return results
