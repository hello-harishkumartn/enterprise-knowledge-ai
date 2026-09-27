from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    mode: str = Field(default="hybrid", pattern="^(semantic|keyword|hybrid)$")
    document_ids: list[str] | None = None
    category: str | None = None
    department: str | None = None
    top_n: int | None = None


class RetrievedChunkOut(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    section: str | None
    page_number: int | None
    document_type: str
    department: str
    category: str
    vector_score: float | None
    keyword_score: float | None
    fused_score: float | None
    rerank_score: float | None


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[RetrievedChunkOut]
    latency_ms: float
