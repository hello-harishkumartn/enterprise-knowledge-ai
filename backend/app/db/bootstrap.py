"""Idempotent DB setup: extension, tables, ANN index, seeded demo users.

Safe to call on every startup — used by `app.main` (dev convenience) and by
`scripts/seed_db.py` (explicit local/CI setup).
"""
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Base, User
from app.db.session import engine

logger = logging.getLogger(__name__)

SEED_USERS = [
    {"email": "admin@acmefs.com", "password": "AdminPass123!", "full_name": "Avery Admin", "role": "admin", "department": "IT"},
    {"email": "employee@acmefs.com", "password": "EmployeePass123!", "full_name": "Erin Employee", "role": "employee", "department": "Finance"},
]


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
                "ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
            )
        )
        conn.commit()


def seed_users(db: Session) -> None:
    for spec in SEED_USERS:
        existing = db.query(User).filter(User.email == spec["email"]).first()
        if existing:
            continue
        db.add(
            User(
                email=spec["email"],
                hashed_password=hash_password(spec["password"]),
                full_name=spec["full_name"],
                role=spec["role"],
                department=spec["department"],
            )
        )
    db.commit()
