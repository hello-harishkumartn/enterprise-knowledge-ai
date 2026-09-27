"""Evaluation runner: replays evals/qa_dataset.json against the live
retrieval + generation pipeline and computes retrieval, generation, and
system metrics. Requires a DB with the sample_data corpus already ingested
(`python scripts/seed_db.py`) — this is an integration-level tool, not a
unit test.

    python scripts/run_evals.py [--mode hybrid] [--llm-judge]
"""
import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document
from app.evaluation.llm_judge import judge_answer
from app.evaluation.metrics import (
    answer_relevance_heuristic,
    citation_correctness,
    groundedness_heuristic,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)
from app.rag.pipeline import answer_question
from app.retrieval.pipeline import retrieve

settings = get_settings()

RETRIEVAL_MODES = ["semantic", "keyword", "hybrid"]


@dataclass
class QAItem:
    id: str
    role: str
    category: str
    question: str
    expected_document_names: list[str]
    forbidden_document_names: list[str] = field(default_factory=list)


@dataclass
class ItemResult:
    id: str
    category: str
    question: str
    role: str
    retrieval: dict  # mode -> {recall, precision, mrr}
    answer: str
    citations_count: int
    citation_correctness: float
    groundedness: float
    relevance: float
    judged_by_llm: bool
    rbac_pass: bool
    llm_provider: str
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    prompt_tokens: int
    completion_tokens: int


def _load_dataset(path: Path) -> list[QAItem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [QAItem(**item) for item in raw]


def _resolve_document_ids(db: Session, names: list[str]) -> list[str]:
    if not names:
        return []
    docs = db.query(Document).filter(Document.name.in_(names)).all()
    return [d.id for d in docs]


def run_evaluation(
    db: Session,
    dataset_path: Path,
    output_dir: Path,
    generation_mode: str = "hybrid",
    top_k: int | None = None,
    use_llm_judge: bool = False,
) -> dict:
    top_k = top_k or settings.RETRIEVAL_FINAL_TOP_N
    items = _load_dataset(dataset_path)
    results: list[ItemResult] = []

    for item in items:
        expected_ids = _resolve_document_ids(db, item.expected_document_names)
        forbidden_ids = _resolve_document_ids(db, item.forbidden_document_names)

        retrieval_metrics: dict[str, dict[str, float]] = {}
        for mode in RETRIEVAL_MODES:
            chunks = retrieve(db, item.question, item.role, mode=mode, top_n=top_k)
            seen: list[str] = []
            for c in chunks:
                if c.document_id not in seen:
                    seen.append(c.document_id)
            retrieval_metrics[mode] = {
                "recall_at_k": recall_at_k(seen, expected_ids, top_k),
                "precision_at_k": precision_at_k(seen, expected_ids, top_k),
                "mrr": mean_reciprocal_rank(seen, expected_ids),
            }

        t0 = time.perf_counter()
        rag_result = answer_question(db, item.question, item.role, mode=generation_mode)
        _ = time.perf_counter() - t0  # already captured inside rag_result

        cited_doc_ids = [c.document_id for c in rag_result.citations]
        retrieved_doc_ids = {c.document_id for c in rag_result.retrieved_chunks}

        if expected_ids:
            citation_score = citation_correctness(cited_doc_ids, expected_ids)
        else:
            # Nothing should have been cited (insufficient-evidence / RBAC-negative case).
            citation_score = 1.0 if not cited_doc_ids else 0.0

        judged = None
        if use_llm_judge:
            judged = judge_answer(item.question, rag_result.answer_text, rag_result.context.context_text)

        groundedness = judged["groundedness"] if judged else groundedness_heuristic(
            rag_result.answer_text, rag_result.context.context_text
        )
        relevance = judged["relevance"] if judged else answer_relevance_heuristic(
            rag_result.answer_text, item.question
        )

        rbac_pass = not any(fid in retrieved_doc_ids for fid in forbidden_ids) and not any(
            fid in cited_doc_ids for fid in forbidden_ids
        )

        results.append(
            ItemResult(
                id=item.id,
                category=item.category,
                question=item.question,
                role=item.role,
                retrieval=retrieval_metrics,
                answer=rag_result.answer_text,
                citations_count=len(rag_result.citations),
                citation_correctness=citation_score,
                groundedness=groundedness,
                relevance=relevance,
                judged_by_llm=judged is not None,
                rbac_pass=rbac_pass,
                llm_provider=rag_result.llm_provider,
                retrieval_latency_ms=rag_result.retrieval_latency_ms,
                generation_latency_ms=rag_result.generation_latency_ms,
                total_latency_ms=rag_result.total_latency_ms,
                prompt_tokens=rag_result.prompt_tokens,
                completion_tokens=rag_result.completion_tokens,
            )
        )

    summary = _summarize(results, generation_mode)
    _export(results, summary, output_dir)
    return summary


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summarize(results: list[ItemResult], generation_mode: str) -> dict:
    n = len(results)
    retrieval_summary = {
        mode: {
            metric: _avg([r.retrieval[mode][metric] for r in results])
            for metric in ("recall_at_k", "precision_at_k", "mrr")
        }
        for mode in RETRIEVAL_MODES
    }

    rbac_items = [r for r in results if r.category == "rbac_negative"]
    insufficient_items = [r for r in results if r.category == "insufficient_evidence"]

    return {
        "dataset_size": n,
        "generation_mode": generation_mode,
        "retrieval": retrieval_summary,
        "generation": {
            "avg_groundedness": _avg([r.groundedness for r in results]),
            "avg_relevance": _avg([r.relevance for r in results]),
            "avg_citation_correctness": _avg([r.citation_correctness for r in results]),
            "llm_judge_used_for_fraction": _avg([1.0 if r.judged_by_llm else 0.0 for r in results]),
        },
        "system": {
            "avg_retrieval_latency_ms": _avg([r.retrieval_latency_ms for r in results]),
            "avg_generation_latency_ms": _avg([r.generation_latency_ms for r in results]),
            "avg_total_latency_ms": _avg([r.total_latency_ms for r in results]),
            "avg_prompt_tokens": _avg([r.prompt_tokens for r in results]),
            "avg_completion_tokens": _avg([r.completion_tokens for r in results]),
        },
        "rbac": {
            "test_count": len(rbac_items),
            "pass_rate": _avg([1.0 if r.rbac_pass else 0.0 for r in rbac_items]),
        },
        "insufficient_evidence": {
            "test_count": len(insufficient_items),
            "correct_refusal_rate": _avg([1.0 if r.citations_count == 0 else 0.0 for r in insufficient_items]),
        },
    }


def _export(results: list[ItemResult], summary: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"eval_run_{timestamp}.json"
    json_path.write_text(
        json.dumps({"summary": summary, "results": [asdict(r) for r in results]}, indent=2),
        encoding="utf-8",
    )

    csv_path = output_dir / f"eval_run_{timestamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "category", "role", "question", "hybrid_recall_at_k", "hybrid_precision_at_k", "hybrid_mrr",
            "citations_count", "citation_correctness", "groundedness", "relevance", "rbac_pass",
            "llm_provider", "total_latency_ms", "prompt_tokens", "completion_tokens",
        ])
        for r in results:
            hybrid = r.retrieval["hybrid"]
            writer.writerow([
                r.id, r.category, r.role, r.question, hybrid["recall_at_k"], hybrid["precision_at_k"], hybrid["mrr"],
                r.citations_count, r.citation_correctness, r.groundedness, r.relevance, r.rbac_pass,
                r.llm_provider, r.total_latency_ms, r.prompt_tokens, r.completion_tokens,
            ])

    latest_path = output_dir / "latest.json"
    latest_path.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Wrote {json_path.name} and {csv_path.name}")
