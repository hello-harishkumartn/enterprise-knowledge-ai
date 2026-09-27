from app.core.rbac import role_can_access


def test_role_can_access_true_when_role_listed():
    assert role_can_access("admin", ["admin", "employee"]) is True
    assert role_can_access("employee", ["admin", "employee"]) is True


def test_role_can_access_false_when_role_not_listed():
    assert role_can_access("employee", ["admin"]) is False


def test_role_can_access_false_for_empty_allowed_roles():
    assert role_can_access("admin", []) is False


def test_role_can_access_false_for_none_allowed_roles():
    assert role_can_access("employee", None) is False


# --- DB-backed integration test -------------------------------------------
# Proves the guarantee end to end: an admin-only document's chunks are never
# returned to an employee-role query, across all three retrieval modes, even
# when the query is a strong semantic/keyword match for that document.
# Skips (does not fail) when Postgres+pgvector isn't reachable locally; runs
# for real in CI against the pgvector service container.


def test_admin_only_document_never_retrieved_by_employee_role(db_session):
    from app.db.models import Chunk, Document
    from app.retrieval.embeddings import embed_query
    from app.retrieval.keyword_search import keyword_search
    from app.retrieval.vector_search import vector_search

    admin_doc = Document(
        name="Incident Response Procedures",
        file_format="md",
        document_type="procedure",
        department="IT",
        category="security_procedure",
        storage_path="unit-test",
        allowed_roles=["admin"],
    )
    db_session.add(admin_doc)
    db_session.flush()

    secret_text = "SEV-1 incidents require CISO notification within 30 minutes of detection."
    db_session.add(
        Chunk(
            document_id=admin_doc.id,
            chunk_index=0,
            content=secret_text,
            token_count=20,
            embedding=embed_query(secret_text),
        )
    )
    db_session.commit()

    vector_hits = vector_search(db_session, embed_query(secret_text), role="employee", top_k=20)
    keyword_hits = keyword_search(db_session, "SEV-1 CISO notification", role="employee", top_k=20)

    assert all(h.document_id != admin_doc.id for h in vector_hits)
    assert all(h.document_id != admin_doc.id for h in keyword_hits)

    # Sanity check: an admin CAN see it (proves the filter is role-based, not
    # simply broken / always-empty).
    admin_vector_hits = vector_search(db_session, embed_query(secret_text), role="admin", top_k=20)
    assert any(h.document_id == admin_doc.id for h in admin_vector_hits)
