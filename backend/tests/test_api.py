from fastapi.testclient import TestClient


def _client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_health_endpoint_requires_no_db():
    client = _client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_chat_requires_auth():
    client = _client()
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_documents_upload_requires_admin(require_db):
    from app.db.bootstrap import init_db, seed_users
    from app.db.session import SessionLocal

    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()

    client = _client()
    login = client.post(
        "/api/auth/login", json={"email": "employee@acmefs.com", "password": "EmployeePass123!"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    resp = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", b"hello world", "text/plain")},
        data={"document_type": "policy", "department": "HR", "category": "hr_policy"},
    )
    assert resp.status_code == 403


def test_login_rejects_wrong_password(require_db):
    from app.db.bootstrap import init_db, seed_users
    from app.db.session import SessionLocal

    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()

    client = _client()
    resp = client.post("/api/auth/login", json={"email": "admin@acmefs.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_and_me_roundtrip(require_db):
    from app.db.bootstrap import init_db, seed_users
    from app.db.session import SessionLocal

    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
    finally:
        db.close()

    client = _client()
    login = client.post("/api/auth/login", json={"email": "admin@acmefs.com", "password": "AdminPass123!"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
