"""Idempotent local/CI setup: creates the schema, seeds demo users, and
ingests every document in sample_data/manifest.json.

    python scripts/seed_db.py [--reset]

--reset drops and recreates all documents/chunks first (users are left
alone) so re-running during development doesn't pile up duplicates.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# ROOT is "wherever this script's parent directory's parent is" — the repo
# root locally (scripts/ sits directly under it), or /app when this file is
# bind-mounted to /app/scripts inside the backend container (docker-compose.yml),
# in which case ROOT resolves to /app and lines up with the sample_data/evals
# mounts there. BACKEND_DIR can't be inferred the same way since the backend
# package lives at <repo_root>/backend locally but *is* /app in the
# container — so that one is env-var-driven with a local-dev fallback.
ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(os.environ.get("BACKEND_DIR", str(ROOT / "backend")))
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete  # noqa: E402

from app.db.bootstrap import init_db, seed_users  # noqa: E402
from app.db.models import Chunk, Document  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.pipeline import ingest_document  # noqa: E402

MANIFEST_PATH = ROOT / "sample_data" / "manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete existing documents/chunks first")
    args = parser.parse_args()

    print("Initializing schema...")
    init_db()

    db = SessionLocal()
    try:
        print("Seeding demo users (admin@acmefs.com / employee@acmefs.com)...")
        seed_users(db)

        if args.reset:
            print("Resetting existing documents/chunks...")
            db.execute(delete(Chunk))
            db.execute(delete(Document))
            db.commit()

        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        existing_names = {d.name for d in db.query(Document).all()}

        for entry in manifest:
            if entry["name"] in existing_names:
                print(f"  skip (already ingested): {entry['name']}")
                continue
            file_path = ROOT / "sample_data" / entry["path"]
            file_format = file_path.suffix.lstrip(".")
            print(f"  ingesting: {entry['name']} ({file_format})...")
            ingest_document(
                db,
                file_path=str(file_path),
                file_format=file_format,
                name=entry["name"],
                document_type=entry["document_type"],
                department=entry["department"],
                category=entry["category"],
                allowed_roles=entry["allowed_roles"],
            )

        total_docs = db.query(Document).count()
        total_chunks = db.query(Chunk).count()
        print(f"Done. {total_docs} documents, {total_chunks} chunks indexed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
