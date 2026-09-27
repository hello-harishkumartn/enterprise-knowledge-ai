"""End-to-end RAG orchestration: retrieval -> context engineering ->
generation -> citation extraction. This is the module the /chat and /search
API routes call; nothing else touches retrieval/LLM internals directly.
"""
import time
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import get_settings
from app.context.builder import BuiltContext, build_context
from app.llm.base import LLMResult
from app.llm.factory import generate_with_fallback
from app.rag.citations import Citation, extract_citations
from app.retrieval.pipeline import RetrievalFilters, retrieve
from app.retrieval.types import RetrievedChunk

settings = get_settings()

SYSTEM_PROMPT = """You are the internal knowledge assistant for Acme Financial Services.
Answer the employee's question using ONLY the information in the numbered
context blocks below. Every factual sentence in your answer MUST end with a
citation marker like [1] or [2] referencing the context block it came from.
Never invent a citation number that isn't shown in the context.
If the context does not contain enough information to answer confidently,
say so explicitly instead of guessing — do not use outside knowledge."""

INSUFFICIENT_EVIDENCE_TEXT = (
    "I don't have enough information in the currently indexed documents to "
    "answer this question confidently. Try rephrasing, broadening the search "
    "filters, or asking a member of the relevant department."
)


@dataclass
class RAGAnswer:
    answer_text: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]
    context: BuiltContext
    llm_provider: str
    llm_model: str
    prompt_tokens: int
    completion_tokens: int
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    mode: str = "hybrid"
    warnings: list[str] = field(default_factory=list)


def answer_question(
    db: Session,
    query: str,
    role: str,
    mode: str = "hybrid",
    filters: RetrievalFilters | None = None,
) -> RAGAnswer:
    t_start = time.perf_counter()

    retrieved = retrieve(db, query, role, mode=mode, filters=filters)
    t_retrieved = time.perf_counter()
    retrieval_latency_ms = (t_retrieved - t_start) * 1000

    context = build_context(
        retrieved,
        token_budget=settings.CONTEXT_TOKEN_BUDGET,
        max_chunks_per_doc=settings.CONTEXT_MAX_CHUNKS_PER_DOC,
    )

    if not context.chunks:
        return RAGAnswer(
            answer_text=INSUFFICIENT_EVIDENCE_TEXT,
            citations=[],
            retrieved_chunks=retrieved,
            context=context,
            llm_provider="none",
            llm_model="none",
            prompt_tokens=0,
            completion_tokens=0,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=0.0,
            total_latency_ms=(time.perf_counter() - t_start) * 1000,
            mode=mode,
            warnings=["no_relevant_context_found"],
        )

    user_prompt = f"Context:\n{context.context_text}\n\nQuestion: {query}"

    t_gen_start = time.perf_counter()
    llm_result: LLMResult = generate_with_fallback(SYSTEM_PROMPT, user_prompt)
    generation_latency_ms = (time.perf_counter() - t_gen_start) * 1000

    citations = extract_citations(llm_result.text, context)

    return RAGAnswer(
        answer_text=llm_result.text,
        citations=citations,
        retrieved_chunks=retrieved,
        context=context,
        llm_provider=llm_result.provider,
        llm_model=llm_result.model,
        prompt_tokens=llm_result.prompt_tokens,
        completion_tokens=llm_result.completion_tokens,
        retrieval_latency_ms=retrieval_latency_ms,
        generation_latency_ms=generation_latency_ms,
        total_latency_ms=(time.perf_counter() - t_start) * 1000,
        mode=mode,
    )
