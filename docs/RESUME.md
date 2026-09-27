# Resume Evidence

## Project Title

**Enterprise Knowledge Intelligence Platform** — a RAG-based internal
knowledge search system with hybrid retrieval, RBAC-enforced generation, and
a built-in evaluation harness.

## Two-Line Description

Built a production-oriented RAG platform for enterprise document search:
hybrid (BM25 + vector) retrieval with cross-encoder reranking, grounded
generation with verifiable citations, and role-based access control enforced
at the SQL layer before any content reaches the LLM. Includes a 57-question
evaluation harness (retrieval + generation + RBAC metrics) and full
observability over every query.

## Resume Bullet Points

- Designed and built a hybrid retrieval pipeline (BM25 + pgvector semantic
  search, fused via Reciprocal Rank Fusion, reranked with a cross-encoder)
  for an enterprise RAG system, with retrieval mode selectable and
  independently evaluable at query time.
- Implemented document-level RBAC enforced at the database query layer
  (not post-filtered), proven with dedicated unit and evaluation tests that
  an unauthorized document can never reach the retrieval results or the LLM
  context, across all retrieval modes.
- Built a 57-question evaluation harness measuring Recall@K/Precision@K/MRR,
  groundedness, answer relevance, and citation correctness, with an optional
  LLM-as-judge mode and a lexical-heuristic offline fallback so evaluation
  runs deterministically in CI with zero external dependencies.

## Technical Skills Demonstrated

- **RAG systems**: hybrid retrieval, RRF fusion, cross-encoder reranking,
  context engineering (dedup/token-budget/per-doc capping), citation
  grounding.
- **LLM engineering**: provider-agnostic abstraction with automatic
  fallback (Gemini → Ollama → deterministic offline), prompt design for
  citation-forcing and hallucination avoidance.
- **Backend engineering**: FastAPI, SQLAlchemy 2.0, Pydantic v2, JWT auth,
  RBAC design, PostgreSQL + pgvector.
- **ML/NLP**: sentence-transformers embeddings, cross-encoder reranking,
  BM25, heading-aware document chunking, evaluation metric design.
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, building a
  multi-page enterprise UI with a live retrieval/citation inspector.
- **DevOps/testing**: Docker Compose multi-service orchestration, GitHub
  Actions CI with a real Postgres+pgvector service container, pytest
  (unit + integration), ruff linting.
- **Evaluation & observability**: offline eval harness design, LLM-as-judge
  pattern, per-query analytics (latency, token usage, retrieval scores).

## Metrics to Collect After Deployment

*(Placeholders — do not fabricate; fill in from your own `evals/results/latest.json` and analytics after running the system for real.)*

- Retrieval Recall@K / Precision@K / MRR by mode: `[[ RUN scripts/run_evals.py ]]`
- Generation groundedness / relevance / citation correctness: `[[ RUN scripts/run_evals.py --llm-judge ]]`
- RBAC test pass rate (must be 100%): `[[ RUN scripts/run_evals.py ]]`
- p50/p95 end-to-end query latency in production: `[[ FROM analytics after real usage ]]`
- Average tokens per query and estimated LLM cost per 1,000 queries: `[[ FROM analytics ]]`
- Document ingestion throughput (docs/min, chunks/min) at your real corpus size: `[[ MEASURE on your dataset ]]`

## Interview Talking Points

- **Why RRF instead of a weighted score blend?** BM25 and cosine similarity
  scores live on incomparable scales; RRF combines by *rank*, which is
  scale-free and trivially explainable ("a result ranked highly by both
  signals wins") — no tuning a magic blend weight.
- **Where exactly is RBAC enforced, and how do you know it holds?** In the
  SQL `WHERE` clause of both retrievers (`Document.allowed_roles.contains
  ([role])`), not as a post-filter — walk through
  `backend/tests/test_rbac.py` and the three `rbac_negative` eval questions
  that prove an admin-only document never surfaces for an employee-role
  query, even when it's the best semantic/lexical match.
- **What happens when the corpus has no answer?** The context builder
  returns empty, and the pipeline short-circuits *before* calling the LLM at
  all — cheaper, faster, and removes any chance of the model falling back
  on outside training-data knowledge. Trace `INSUFFICIENT_EVIDENCE_TEXT` in
  `app/rag/pipeline.py`.
- **How do you keep the system provider-agnostic?** A one-method
  `LLMProvider` ABC and a fallback-chain factory
  (`app/llm/factory.py`) — swapping or reordering providers is a config
  change, never a change to the RAG orchestration code.
- **How would this scale past ~25 documents?** BM25 is currently rebuilt
  per query over the RBAC-filtered set — fine at demo scale, explicitly
  called out in `docs/RAG_PIPELINE.md` as needing to move to Postgres
  full-text search or an external index (with the same role predicate
  pushed into it) at real enterprise scale.
- **How is evaluation kept honest?** The default groundedness/relevance
  scoring is a disclosed lexical-overlap heuristic, not dressed up as an
  LLM judgment; `--llm-judge` is opt-in, and the mock provider is explicitly
  barred from judging its own answers.
