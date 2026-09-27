from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Chunk, Document, QueryLog, User
from app.db.session import get_db
from app.schemas.analytics import AnalyticsResponse, DashboardSummary, QueryLogOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
def get_analytics(limit: int = 25, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AnalyticsResponse:
    documents_indexed = db.execute(select(func.count(Document.id))).scalar_one()
    chunks_indexed = db.execute(select(func.count(Chunk.id))).scalar_one()
    total_queries = db.execute(select(func.count(QueryLog.id))).scalar_one()
    avg_latency = db.execute(select(func.avg(QueryLog.total_latency_ms))).scalar_one() or 0.0
    avg_score = db.execute(select(func.avg(QueryLog.avg_retrieval_score))).scalar_one() or 0.0

    recent = (
        db.execute(select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit))
        .scalars()
        .all()
    )

    return AnalyticsResponse(
        summary=DashboardSummary(
            documents_indexed=documents_indexed,
            chunks_indexed=chunks_indexed,
            total_queries=total_queries,
            avg_response_time_ms=float(avg_latency),
            avg_retrieval_score=float(avg_score),
        ),
        recent_queries=[QueryLogOut.model_validate(q, from_attributes=True) for q in recent],
    )
