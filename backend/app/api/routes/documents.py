import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.config import get_settings
from app.core.rbac import role_can_access
from app.db.models import Document, User
from app.db.session import get_db
from app.ingestion.pipeline import ingest_document
from app.schemas.documents import DocumentListResponse, DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()

SUPPORTED_FORMATS = {"pdf", "docx", "txt", "md"}


@router.get("", response_model=DocumentListResponse)
def list_documents(
    category: str | None = None,
    department: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    stmt = select(Document)
    if category:
        stmt = stmt.where(Document.category == category)
    if department:
        stmt = stmt.where(Document.department == department)

    docs = [d for d in db.execute(stmt).scalars().all() if role_can_access(user.role, d.allowed_roles)]
    return DocumentListResponse(
        documents=[DocumentOut.model_validate(d, from_attributes=True) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentOut:
    doc = db.get(Document, document_id)
    if doc is None or not role_can_access(user.role, doc.allowed_roles):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return DocumentOut.model_validate(doc, from_attributes=True)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    department: str = Form(...),
    category: str = Form(...),
    allowed_roles: str = Form("[\"admin\", \"employee\"]"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DocumentOut:
    file_format = (file.filename or "").rsplit(".", 1)[-1].lower()
    if file_format not in SUPPORTED_FORMATS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported format: {file_format}")

    try:
        roles = json.loads(allowed_roles)
        if not isinstance(roles, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "allowed_roles must be a JSON array of role names") from exc

    storage_dir = Path(settings.STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    dest = storage_dir / f"{uuid.uuid4()}_{file.filename}"
    dest.write_bytes(file.file.read())

    try:
        document = ingest_document(
            db,
            file_path=str(dest),
            file_format=file_format,
            name=file.filename or dest.name,
            document_type=document_type,
            department=department,
            category=category,
            allowed_roles=roles,
            uploaded_by=admin.id,
        )
    except Exception as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Ingestion failed: {exc}") from exc

    return DocumentOut.model_validate(document, from_attributes=True)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    db.delete(doc)
    db.commit()
