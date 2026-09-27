from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    name: str
    file_format: str
    document_type: str
    department: str
    category: str
    allowed_roles: list[str]
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int
