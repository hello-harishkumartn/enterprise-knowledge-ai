"""Context engineering: turns a ranked chunk list into the exact prompt
context sent to the LLM.

Rules, in order:
1. Deduplicate — identical/near-identical chunk content only counted once
   (documents get re-ingested, chunk overlap can repeat the same sentence).
2. Prioritize by relevance (rerank score, falling back to fusion/vector/
   keyword score) so the token budget is spent on the best evidence first.
3. Cap chunks-per-document so one long, well-matching document can't crowd
   out every other source.
4. Respect a hard token budget — greedily add chunks in relevance order,
   skipping (not truncating) any chunk that would blow the budget so later,
   smaller, still-relevant chunks get a chance.
5. Present the final context grouped by document (citations read better
   grouped) while the *selection* above stays relevance-driven.

Each included chunk gets a stable citation number. `insufficient evidence`
guidance is a prompt-level instruction (see app/rag/pipeline.py) but starts
here: if nothing clears the relevance bar, the builder returns an empty
context and the caller tells the LLM to say so.
"""
from dataclasses import dataclass

from app.ingestion.chunking import count_tokens
from app.retrieval.types import RetrievedChunk


@dataclass
class ContextChunk:
    citation_number: int
    chunk: RetrievedChunk


@dataclass
class BuiltContext:
    context_text: str
    chunks: list[ContextChunk]
    total_tokens: int
    dropped_for_budget: int
    dropped_as_duplicate: int


def _relevance_score(chunk: RetrievedChunk) -> float:
    for score in (chunk.rerank_score, chunk.fused_score, chunk.vector_score, chunk.keyword_score):
        if score is not None:
            return score
    return 0.0


def _normalize(text: str) -> str:
    return " ".join(text.split()).lower()


def build_context(
    chunks: list[RetrievedChunk],
    token_budget: int = 3000,
    max_chunks_per_doc: int = 3,
) -> BuiltContext:
    if not chunks:
        return BuiltContext(context_text="", chunks=[], total_tokens=0, dropped_for_budget=0, dropped_as_duplicate=0)

    ranked = sorted(chunks, key=_relevance_score, reverse=True)

    seen_content: set[str] = set()
    per_doc_count: dict[str, int] = {}
    selected: list[RetrievedChunk] = []
    dropped_duplicate = 0
    dropped_budget = 0
    running_tokens = 0

    for chunk in ranked:
        normalized = _normalize(chunk.content)
        if normalized in seen_content:
            dropped_duplicate += 1
            continue
        if per_doc_count.get(chunk.document_id, 0) >= max_chunks_per_doc:
            continue
        chunk_tokens = count_tokens(chunk.content)
        if running_tokens + chunk_tokens > token_budget:
            dropped_budget += 1
            continue
        seen_content.add(normalized)
        per_doc_count[chunk.document_id] = per_doc_count.get(chunk.document_id, 0) + 1
        running_tokens += chunk_tokens
        selected.append(chunk)

    # Present grouped by document, ordered by each document's best chunk,
    # while citation numbers are assigned in that same (final) order.
    best_score_by_doc: dict[str, float] = {}
    for c in selected:
        best_score_by_doc[c.document_id] = max(best_score_by_doc.get(c.document_id, -1e9), _relevance_score(c))
    selected.sort(key=lambda c: (-best_score_by_doc[c.document_id], -_relevance_score(c)))

    context_chunks: list[ContextChunk] = []
    parts: list[str] = []
    for i, chunk in enumerate(selected, start=1):
        context_chunks.append(ContextChunk(citation_number=i, chunk=chunk))
        location = f"p.{chunk.page_number}" if chunk.page_number else (chunk.section or "full document")
        header = f"[{i}] {chunk.document_name} ({location})"
        parts.append(f"{header}\n{chunk.content}")

    context_text = "\n\n---\n\n".join(parts)

    return BuiltContext(
        context_text=context_text,
        chunks=context_chunks,
        total_tokens=running_tokens,
        dropped_for_budget=dropped_budget,
        dropped_as_duplicate=dropped_duplicate,
    )
