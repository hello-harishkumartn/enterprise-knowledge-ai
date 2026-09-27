"""Ties parsing -> chunking -> embedding -> storage into one call.

Used by both the `/documents` upload API route and `scripts/ingest_sample_data.py`
so there's exactly one ingestion code path, not one for "real" uploads and a
different ad hoc one for seeding demo data.
"""
import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Chunk, Document
from app.ingestion.chunking import chunk_blocks
from app.ingestion.parsers import parse_document
from app.retrieval.embeddings import embed_texts

logger = logging.getLogger(__name__)
settings = get_settings()


def ingest_document(
    db: Session,
    file_path: str,
    file_format: str,
    name: str,
    document_type: str,
    department: str,
    category: str,
    allowed_roles: list[str],
    uploaded_by: str | None = None,
) -> Document:
    document = Document(
        name=name,
        file_format=file_format,
        document_type=document_type,
        department=department,
        category=category,
        storage_path=file_path,
        allowed_roles=allowed_roles,
        uploaded_by=uploaded_by,
        status="processing",
    )
    db.add(document)
    db.flush()  # assign document.id without committing yet

    try:
        blocks = parse_document(file_path, file_format)
        chunks = chunk_blocks(
            blocks,
            target_tokens=settings.CHUNK_TARGET_TOKENS,
            overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
        )
        if not chunks:
            raise ValueError("Document produced zero chunks — is it empty or unparsable?")

        embeddings = embed_texts([c.content for c in chunks])

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            db.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=i,
                    content=chunk.content,
                    section=chunk.section,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                    embedding=embedding,
                )
            )

        document.status = "indexed"
        document.chunk_count = len(chunks)
    except Exception:
        document.status = "failed"
        logger.exception("Ingestion failed for %s", name)
        raise
    finally:
        db.commit()
        db.refresh(document)

    return document
