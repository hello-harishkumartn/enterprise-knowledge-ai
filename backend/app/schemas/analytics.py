from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    documents_indexed: int
    chunks_indexed: int
    total_queries: int
    avg_response_time_ms: float
    avg_retrieval_score: float


class QueryLogOut(BaseModel):
    id: str
    query: str
    mode: str
    llm_provider: str
    llm_model: str
    prompt_tokens: int
    completion_tokens: int
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    avg_retrieval_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsResponse(BaseModel):
    summary: DashboardSummary
    recent_queries: list[QueryLogOut]
