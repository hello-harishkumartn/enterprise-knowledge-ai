import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("ENV", "test")
os.environ.setdefault("LLM_PROVIDER_ORDER", "mock")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402


@pytest.fixture(scope="session")
def db_available() -> bool:
    """True iff a real Postgres+pgvector instance is reachable at DATABASE_URL.

    None of this sandbox's local runs have Docker/Postgres available, so
    DB-backed integration tests use this fixture to skip cleanly rather than
    fail. The exact same tests run for real in CI, which spins up a
    `pgvector/pgvector` service container (see .github/workflows/ci.yml).
    """
    from app.db.session import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


@pytest.fixture()
def require_db(db_available):
    if not db_available:
        pytest.skip("Postgres (with pgvector) is not reachable at DATABASE_URL — skipping DB-backed test")


@pytest.fixture()
def db_session(require_db):
    from app.db.bootstrap import init_db
    from app.db.session import SessionLocal

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
