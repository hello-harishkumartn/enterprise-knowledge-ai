# Implementation Plan — Enterprise Knowledge Intelligence Platform

## Goal
An internal enterprise knowledge search & RAG product for a fictional company
("Acme Financial Services") demonstrating: hybrid retrieval (BM25 + vector),
cross-encoder reranking, context engineering, grounded generation with real
citations, RBAC-filtered retrieval, an evaluation harness, and observability.
Built to be read by a hiring reviewer, so correctness and clarity beat feature
count.

## Architecture Summary
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind. Pages:
  login, dashboard, documents, search, chat, evaluations, analytics, settings.
- **Backend**: FastAPI (Python), SQLAlchemy Core/ORM, Pydantic v2.
- **DB**: PostgreSQL + pgvector extension (Docker for local dev; Supabase
  Postgres for hosted). One schema works for both.
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim, local
  CPU inference, no API key required).
- **Keyword retrieval**: BM25 (`rank_bm25`) over chunk text, rebuilt from DB.
- **Fusion**: Reciprocal Rank Fusion (RRF) combining BM25 rank + vector rank.
- **Reranker**: cross-encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **LLM**: provider-abstracted (`backend/app/llm/base.py`). Primary: Gemini
  (`gemini-1.5-flash` free tier). Fallback: Ollama (local open-weight model,
  e.g. `llama3.2`). Selected via `LLM_PROVIDER` env var, falls back
  automatically if the primary call fails.
- **Auth**: local JWT-based auth for Docker/local dev (two seeded roles:
  `admin`, `employee`) behind an `AuthProvider` abstraction; Supabase Auth is
  documented as the drop-in hosted replacement (same interface).
- **RBAC**: every document has `allowed_roles`; retrieval filters at the SQL
  query layer (vector search, BM25 candidate set, and hybrid fusion) before
  any chunk reaches the LLM context — never filtered post-hoc.

## RAG Pipeline
```
Upload -> Parse (pdf/docx/txt/md) -> Clean -> Metadata extract -> Chunk
       -> Embed -> Store (Postgres+pgvector) -> Index (BM25 corpus rebuild)

Query -> query processing -> [keyword retrieval] + [vector retrieval]
      -> RRF fusion -> RBAC filter -> cross-encoder rerank
      -> context builder (dedupe, token budget, grouping)
      -> LLM (with citation-forcing prompt) -> answer + citations
```

## Evaluation
`evals/qa_dataset.json` — 50+ hand-authored Q/A pairs grounded in
`sample_data/`, each with expected source doc(s)/chunk ids. Metrics:
Recall@K, Precision@K, MRR (retrieval); groundedness, answer relevance,
citation correctness (generation, LLM-judge based with heuristic fallback);
latency & token usage (system). `python scripts/run_evals.py` writes
`evals/results/*.json` and `*.csv`.

## Build Order (this session)
1. PLAN.md / TODO.md (this file + companion)
2. Backend foundation: config, DB models, DB init SQL (pgvector), app entrypoint
3. Ingestion: parsers (pdf/docx/txt/md), heading-aware chunker, pipeline
4. Retrieval: embeddings wrapper, vector search, BM25 index, RRF fusion, reranker
5. Context engineering: context builder module
6. Generation: LLM provider abstraction (Gemini + Ollama), RAG orchestrator, citations
7. RBAC enforcement in retrieval layer
8. API routes: auth, documents, search, chat, evaluations, analytics
9. Sample data: ~20 Acme Financial Services documents
10. Evaluation dataset (50+ QA) + run_evals.py + metrics
11. Frontend: Next.js pages wired to the API
12. Tests: pytest unit + integration (parsing, chunking, retrieval, RBAC, citations, API, context builder)
13. Docker: backend Dockerfile, frontend Dockerfile, docker-compose.yml (postgres+pgvector, backend, frontend)
14. CI: GitHub Actions (lint + test)
15. Docs: README, ARCHITECTURE.md, RAG_PIPELINE.md, EVALUATION.md, DEPLOYMENT.md, RESUME.md
16. Run backend tests + evals locally; fix failures; finalize docs

## Known Environment Constraints
- Dev machine had no Python or Docker preinstalled. Python 3.12 is being
  installed via `winget` so backend tests can actually run locally in this
  session. Docker is not available here, so `docker-compose` is written
  correctly but not executed in this session — noted in DEPLOYMENT.md as
  something to verify on a Docker-enabled machine.
- No live Gemini API key / Ollama daemon in this sandbox — the LLM layer is
  built with a `MockProvider` used automatically in tests/CI so the
  generation path is still fully exercised without network calls.

## Verification Log (this session)

Real verification performed despite the constraints above, in order:

1. Installed Python 3.12 (winget) and a backend virtualenv; installed all
   backend deps for real (including `torch`/`sentence-transformers`).
2. Ran the full pytest suite repeatedly as code was written — 60 passed, 5
   skipped (DB-gated), 0 failed at every checkpoint after the initial
   scaffolding stabilized.
3. Exercised the *real* embedding model and *real* cross-encoder reranker
   (not mocks) — `test_embeddings.py`/`test_reranker.py` assert genuine
   semantic-similarity and relevance-ordering behavior.
4. Ran ingestion (parse + chunk, no DB) against all 25 real sample
   documents. This caught a real bug: `pypdf`'s `extract_text()` returns
   one line per visual line, not blank-line-delimited paragraphs like
   DOCX/Markdown/TXT — the original PDF parser assumed `\n\n` paragraph
   breaks and collapsed the sample PDF's 9 sections into 2 oversized
   chunks. Fixed by rewriting `_parse_pdf` to accumulate lines into
   paragraphs and flush on heading-detection or blank line; re-verified
   the PDF now parses into 9 correctly-sectioned chunks matching its
   source content.
5. Found and fixed a real Docker-vs-local path-resolution bug before it
   could ship: `scripts/seed_db.py`, `scripts/run_evals.py`, and
   `app/api/routes/evaluations.py` all assumed the local dev filesystem
   layout (`<repo_root>/backend/app/...`, `<repo_root>/evals`), which does
   not hold inside the backend container (`/app/app/...` with `evals`
   bind-mounted at `/app/evals`). Fixed via `BACKEND_DIR`/`EVALS_DIR` env
   vars (set in `docker-compose.yml`) with local-dev-correct fallbacks, and
   mounted `scripts/` into the container.
6. Fixed a CORS misconfiguration (`allow_credentials=True` with a wildcard
   origin — invalid per the CORS spec and unnecessary since auth is a
   Bearer token, never a cookie).
7. `npm install` + `npm run build` (0 TypeScript/lint errors) + started the
   production server and confirmed the login page renders correctly via
   curl.
8. `ruff check .` clean (0 errors) after fixing real issues (B023 loop-
   variable-closure risks in the chunker/PDF parser, `zip()` without
   `strict=`) and suppressing one documented false-positive (B008 for
   FastAPI's `Depends(...)` default-argument idiom).
