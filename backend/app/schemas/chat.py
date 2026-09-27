from pydantic import BaseModel, Field

from app.schemas.search import RetrievedChunkOut


class ChatRequest(BaseModel):
    message: str
    mode: str = Field(default="hybrid", pattern="^(semantic|keyword|hybrid)$")
    conversation_id: str | None = None
    document_ids: list[str] | None = None
    category: str | None = None
    department: str | None = None


class CitationOut(BaseModel):
    number: int
    document_id: str
    document_name: str
    section: str | None
    page_number: int | None
    passage: str


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[CitationOut]
    retrieved_chunks: list[RetrievedChunkOut]
    llm_provider: str
    llm_model: str
    prompt_tokens: int
    completion_tokens: int
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    warnings: list[str] = []


class ConversationOut(BaseModel):
    id: str
    title: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict] | None = None
