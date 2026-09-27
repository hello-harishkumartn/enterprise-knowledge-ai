from app.context.builder import build_context
from app.retrieval.types import RetrievedChunk


def make_chunk(chunk_id, document_id, content, score, page=1, section=None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"Doc {document_id}",
        content=content,
        section=section,
        page_number=page,
        document_type="policy",
        department="HR",
        category="hr_policy",
        allowed_roles=["admin", "employee"],
        rerank_score=score,
    )


def test_build_context_orders_by_relevance_and_numbers_citations():
    chunks = [
        make_chunk("a", "doc1", "Low relevance content.", score=0.1),
        make_chunk("b", "doc2", "High relevance content.", score=0.9),
    ]

    result = build_context(chunks, token_budget=3000, max_chunks_per_doc=3)

    assert len(result.chunks) == 2
    assert result.chunks[0].chunk.chunk_id == "b"
    assert "[1]" in result.context_text
    assert "High relevance content." in result.context_text.split("---")[0]


def test_build_context_deduplicates_identical_content():
    chunks = [
        make_chunk("a", "doc1", "Employees accrue 15 PTO days per year.", score=0.9),
        make_chunk("b", "doc2", "employees accrue 15 pto days per year.", score=0.8),
    ]

    result = build_context(chunks, token_budget=3000, max_chunks_per_doc=3)

    assert len(result.chunks) == 1
    assert result.dropped_as_duplicate == 1


def test_build_context_respects_max_chunks_per_doc():
    chunks = [make_chunk(str(i), "doc1", f"Content number {i}.", score=1.0 - i * 0.01) for i in range(5)]

    result = build_context(chunks, token_budget=3000, max_chunks_per_doc=2)

    assert len(result.chunks) == 2


def test_build_context_respects_token_budget():
    chunks = [
        make_chunk("a", "doc1", "alpha " * 500, score=0.9),  # ~500 tokens
        make_chunk("b", "doc2", "beta " * 500, score=0.8),  # ~500 tokens, distinct content
    ]

    result = build_context(chunks, token_budget=600, max_chunks_per_doc=3)

    assert len(result.chunks) == 1
    assert result.dropped_for_budget == 1
    assert result.total_tokens <= 600


def test_build_context_empty_input():
    result = build_context([], token_budget=3000, max_chunks_per_doc=3)
    assert result.chunks == []
    assert result.context_text == ""


def test_build_context_includes_page_and_document_metadata_in_header():
    chunks = [make_chunk("a", "doc1", "Some content.", score=0.9, page=4)]
    result = build_context(chunks, token_budget=3000, max_chunks_per_doc=3)
    assert "p.4" in result.context_text
    assert "Doc doc1" in result.context_text
