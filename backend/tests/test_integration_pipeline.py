"""End-to-end integration test: ingest a real document -> hybrid retrieve ->
RAG-generate a cited answer -> verify the citation resolves to real content.
Requires Postgres+pgvector (skips otherwise — see conftest.require_db).
"""
from app.ingestion.pipeline import ingest_document
from app.rag.pipeline import answer_question


def test_full_pipeline_ingest_to_cited_answer(require_db, tmp_path):
    doc_path = tmp_path / "sample_leave_policy.md"
    doc_path.write_text(
        "# Sample Leave Policy\n\n"
        "## Carryover Rules\n\n"
        "Employees may carry forward up to 10 unused PTO days into the following calendar year.\n\n"
        "## Sick Leave\n\n"
        "Employees receive 10 paid sick days per calendar year.\n",
        encoding="utf-8",
    )

    from app.db.bootstrap import init_db
    from app.db.session import SessionLocal

    init_db()
    db = SessionLocal()
    try:
        document = ingest_document(
            db,
            file_path=str(doc_path),
            file_format="md",
            name="Sample Leave Policy (integration test)",
            document_type="policy",
            department="HR",
            category="hr_policy",
            allowed_roles=["admin", "employee"],
        )
        assert document.status == "indexed"
        assert document.chunk_count == 2

        result = answer_question(db, "How many PTO days can I carry over to next year?", role="employee")

        assert "10" in result.answer_text
        assert len(result.citations) >= 1
        assert result.citations[0].document_id == document.id
        assert result.llm_provider == "mock"
    finally:
        from app.db.models import Chunk, Document

        db.query(Chunk).filter(Chunk.document_id == document.id).delete()
        db.query(Document).filter(Document.id == document.id).delete()
        db.commit()
        db.close()
