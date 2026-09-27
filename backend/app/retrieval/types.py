from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    section: str | None
    page_number: int | None
    document_type: str
    department: str
    category: str
    allowed_roles: list[str] = field(default_factory=list)

    vector_score: float | None = None
    vector_rank: int | None = None
    keyword_score: float | None = None
    keyword_rank: int | None = None
    fused_score: float | None = None
    rerank_score: float | None = None

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "content": self.content,
            "section": self.section,
            "page_number": self.page_number,
            "document_type": self.document_type,
            "department": self.department,
            "category": self.category,
            "vector_score": self.vector_score,
            "keyword_score": self.keyword_score,
            "fused_score": self.fused_score,
            "rerank_score": self.rerank_score,
        }
