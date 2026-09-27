import os
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.models import EvalRun, User
from app.db.session import get_db
from app.evaluation.runner import run_evaluation
from app.schemas.evaluations import EvalRunOut

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

# Local dev: backend/app/api/routes/evaluations.py -> parents[4] is the repo
# root, where evals/ sits next to backend/. Inside the backend Docker
# container the same relative layout doesn't hold (this file lives at
# /app/app/api/routes/evaluations.py while evals/ is mounted at /app/evals),
# so EVALS_DIR is env-var-overridable there (see docker-compose.yml).
_LOCAL_DEV_ROOT = Path(__file__).resolve().parents[4]
EVALS_DIR = Path(os.environ.get("EVALS_DIR", str(_LOCAL_DEV_ROOT / "evals")))
DATASET_PATH = EVALS_DIR / "qa_dataset.json"
RESULTS_DIR = EVALS_DIR / "results"


@router.get("", response_model=list[EvalRunOut])
def list_eval_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[EvalRunOut]:
    runs = db.execute(select(EvalRun).order_by(EvalRun.created_at.desc())).scalars().all()
    return [EvalRunOut.model_validate(r, from_attributes=True) for r in runs]


@router.post("/run", response_model=EvalRunOut)
def trigger_eval_run(
    mode: str = "hybrid",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EvalRunOut:
    summary = run_evaluation(db, dataset_path=DATASET_PATH, output_dir=RESULTS_DIR, generation_mode=mode)

    run = EvalRun(
        dataset_size=summary["dataset_size"],
        metrics=summary,
        results_path=str(Path("evals") / "results" / "latest.json"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return EvalRunOut.model_validate(run, from_attributes=True)
