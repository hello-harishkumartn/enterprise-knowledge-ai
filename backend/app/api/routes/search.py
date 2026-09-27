import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.retrieval.pipeline import RetrievalFilters, retrieve
from app.schemas.search import RetrievedChunkOut, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SearchResponse:
    start = time.perf_counter()
    filters = RetrievalFilters(
        document_ids=payload.document_ids,
        category=payload.category,
        department=payload.department,
    )
    results = retrieve(db, payload.query, user.role, mode=payload.mode, top_n=payload.top_n, filters=filters)
    latency_ms = (time.perf_counter() - start) * 1000

    return SearchResponse(
        query=payload.query,
        mode=payload.mode,
        results=[RetrievedChunkOut(**r.to_dict()) for r in results],
        latency_ms=latency_ms,
    )
