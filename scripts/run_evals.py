"""CLI entrypoint for the evaluation harness.

    python scripts/run_evals.py
    python scripts/run_evals.py --mode semantic --llm-judge

Requires the DB to already contain the ingested sample_data corpus —
run `python scripts/seed_db.py` first (see docs/EVALUATION.md).
"""
import argparse
import json
import os
import sys
from pathlib import Path

# See the matching comment in scripts/seed_db.py: ROOT tracks this file's
# own mount point (repo root locally, /app in the backend container), while
# BACKEND_DIR (where the `app` package lives) differs between the two and is
# therefore resolved via an env var with a local-dev fallback.
ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(os.environ.get("BACKEND_DIR", str(ROOT / "backend")))
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.evaluation.runner import run_evaluation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="hybrid", choices=["semantic", "keyword", "hybrid"])
    parser.add_argument("--llm-judge", action="store_true", help="use an LLM judge for groundedness/relevance instead of the lexical heuristic")
    parser.add_argument("--dataset", default=str(ROOT / "evals" / "qa_dataset.json"))
    parser.add_argument("--output-dir", default=str(ROOT / "evals" / "results"))
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = run_evaluation(
            db,
            dataset_path=Path(args.dataset),
            output_dir=Path(args.output_dir),
            generation_mode=args.mode,
            use_llm_judge=args.llm_judge,
        )
    finally:
        db.close()

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
