from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Conversation, Message, QueryLog, User
from app.db.session import get_db
from app.rag.pipeline import answer_question
from app.retrieval.pipeline import RetrievalFilters
from app.schemas.chat import ChatRequest, ChatResponse, CitationOut, ConversationOut, MessageOut
from app.schemas.search import RetrievedChunkOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ConversationOut]:
    stmt = select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at.desc())
    return [ConversationOut(id=c.id, title=c.title) for c in db.execute(stmt).scalars().all()]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MessageOut]:
    convo = db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return [MessageOut(id=m.id, role=m.role, content=m.content, citations=m.citations) for m in convo.messages]


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ChatResponse:
    if payload.conversation_id:
        convo = db.get(Conversation, payload.conversation_id)
        if convo is None or convo.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    else:
        convo = Conversation(user_id=user.id, title=payload.message[:60])
        db.add(convo)
        db.flush()

    db.add(Message(conversation_id=convo.id, role="user", content=payload.message))

    filters = RetrievalFilters(
        document_ids=payload.document_ids,
        category=payload.category,
        department=payload.department,
    )
    result = answer_question(db, payload.message, user.role, mode=payload.mode, filters=filters)

    db.add(
        Message(
            conversation_id=convo.id,
            role="assistant",
            content=result.answer_text,
            citations=[c.to_dict() for c in result.citations],
        )
    )

    avg_score = 0.0
    scored = [c.rerank_score or c.fused_score or c.vector_score or c.keyword_score or 0.0 for c in result.retrieved_chunks]
    if scored:
        avg_score = sum(scored) / len(scored)

    db.add(
        QueryLog(
            user_id=user.id,
            query=payload.message,
            mode=payload.mode,
            retrieved_chunk_ids=[c.chunk_id for c in result.retrieved_chunks],
            retrieval_scores={c.chunk_id: (c.vector_score or c.keyword_score or 0.0) for c in result.retrieved_chunks},
            rerank_scores={c.chunk_id: (c.rerank_score or 0.0) for c in result.retrieved_chunks},
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            retrieval_latency_ms=result.retrieval_latency_ms,
            generation_latency_ms=result.generation_latency_ms,
            total_latency_ms=result.total_latency_ms,
            llm_provider=result.llm_provider,
            llm_model=result.llm_model,
            avg_retrieval_score=avg_score,
        )
    )
    db.commit()

    return ChatResponse(
        conversation_id=convo.id,
        answer=result.answer_text,
        citations=[CitationOut(**c.to_dict()) for c in result.citations],
        retrieved_chunks=[RetrievedChunkOut(**c.to_dict()) for c in result.retrieved_chunks],
        llm_provider=result.llm_provider,
        llm_model=result.llm_model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        retrieval_latency_ms=result.retrieval_latency_ms,
        generation_latency_ms=result.generation_latency_ms,
        total_latency_ms=result.total_latency_ms,
        warnings=result.warnings,
    )
