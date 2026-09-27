from app.context.builder import build_context
from app.rag.citations import extract_citations
from app.retrieval.types import RetrievedChunk


def make_chunk(chunk_id, document_id, content, score) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"Doc {document_id}",
        content=content,
        section="Carryover",
        page_number=4,
        document_type="policy",
        department="HR",
        category="hr_policy",
        allowed_roles=["admin", "employee"],
        rerank_score=score,
    )


def _context():
    chunks = [
        make_chunk("a", "doc1", "Employees may carry forward up to 10 leave days.", 0.9),
        make_chunk("b", "doc2", "Sick leave does not carry over.", 0.5),
    ]
    return build_context(chunks, token_budget=3000, max_chunks_per_doc=3)


def test_extract_citations_resolves_real_markers():
    context = _context()
    answer = "Employees may carry forward up to 10 leave days [1]."

    citations = extract_citations(answer, context)

    assert len(citations) == 1
    assert citations[0].document_id == "doc1"
    assert citations[0].page_number == 4


def test_extract_citations_ignores_out_of_range_marker():
    context = _context()
    answer = "This is a fabricated claim [99]."

    citations = extract_citations(answer, context)

    assert citations == []


def test_extract_citations_handles_multiple_markers_in_order():
    context = _context()
    answer = "Point one [1]. Point two [2]."

    citations = extract_citations(answer, context)

    assert [c.number for c in citations] == [1, 2]


def test_extract_citations_no_markers_returns_empty():
    context = _context()
    assert extract_citations("No citations here.", context) == []
