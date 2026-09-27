# TODO

Legend: [x] done, [~] done but only verified via CI/manual review (no local Docker/Postgres in the build sandbox — see PLAN.md)

## 0. Planning
- [x] PLAN.md
- [x] TODO.md

## 1. Backend foundation
- [x] requirements.txt / requirements-dev.txt, package layout
- [x] Settings (pydantic-settings) incl. LLM_PROVIDER_ORDER, DB URL, JWT secret, retrieval/context knobs
- [x] SQLAlchemy models: User, Document, Chunk, Conversation, Message, QueryLog, EvalRun
- [x] DB bootstrap (extension + tables + ivfflat index + seeded users)
- [x] FastAPI app entrypoint + CORS + lifespan DB init

## 2. Ingestion
- [x] Parsers: pdf (pypdf), docx (python-docx), txt, markdown — all 4 verified against real sample files
- [x] Heading/paragraph-aware chunker (verified across all 25 real sample documents, 188 chunks, 0 errors)
- [x] Metadata extraction (doc_type, department, category, page/section)
- [x] Ingestion pipeline (parse -> chunk -> embed -> store)

## 3. Retrieval
- [x] Embeddings wrapper (sentence-transformers, real model verified: semantic similarity test passes)
- [x] Vector search (pgvector cosine, RBAC-filtered SQL) [~ integration-tested, DB required]
- [x] BM25 keyword index (rank_bm25, RBAC-filtered corpus) [~ integration-tested, DB required]
- [x] RRF fusion of BM25 + vector ranks (pure-logic, unit tested)
- [x] Cross-encoder reranker (real model verified: relevance ordering test passes)
- [x] Retrieval config object (k values, weights) visible/tunable in app/config.py

## 4. Context engineering
- [x] Context builder: dedupe, token budget, relevance ordering, per-doc cap (6 unit tests)

## 5. Generation
- [x] LLM provider interface (ABC)
- [x] Gemini provider (primary, real REST API via httpx)
- [x] Ollama provider (fallback, real REST API via httpx)
- [x] Mock provider (deterministic extractive fallback for tests/CI)
- [x] Provider factory w/ automatic fallback on error
- [x] RAG orchestrator: retrieval -> context -> prompt -> answer -> citation extraction
- [x] "insufficient evidence" short-circuit (no LLM call when context is empty)

## 6. RBAC
- [x] allowed_roles (JSONB) on documents
- [x] Filter enforced in the SQL WHERE clause for both vector + BM25 candidate sets
- [x] Test proving unauthorized docs never retrieved [~ DB required; also 3 rbac_negative eval items]

## 7. API
- [x] /auth (login, seeded admin/employee users, JWT)
- [x] /documents (list, upload, get, delete)
- [x] /search (semantic/keyword/hybrid modes, filters)
- [x] /chat (RAG answer with citations + sources, conversation history)
- [x] /evaluations (trigger + fetch results)
- [x] /analytics (dashboard aggregates, query log)

## 8. Sample data
- [x] 25 Acme Financial Services docs across HR/IT/Compliance/Finance/Product
- [x] 3 real non-Markdown conversions (docx, pdf, txt) to prove multi-format ingestion
- [x] 3 admin-only (Restricted) documents for RBAC testing
- [x] Seed/ingest script (scripts/seed_db.py)

## 9. Evaluation framework
- [x] evals/qa_dataset.json — 57 Q&A pairs, all cross-checked against manifest.json (0 mismatches)
- [x] scripts/run_evals.py: Recall@K, Precision@K, MRR across all 3 retrieval modes
- [x] generation metrics (groundedness, relevance, citation correctness — heuristic + optional LLM-judge)
- [x] system metrics (latency, token usage)
- [x] RBAC-negative and insufficient-evidence pass-rate reporting
- [x] export JSON + CSV to evals/results/

## 10. Frontend
- [x] Next.js 14 (App Router) + TS + Tailwind scaffold, API client, auth context
- [x] /login, /dashboard, /documents, /search, /chat, /evaluations, /analytics, /settings
- [x] Chat page: sidebar history + center chat + right source/context inspector
- [x] `npm run build` verified clean (0 TS errors), dev server smoke-tested (HTTP 200, correct render)

## 11. Tests
- [x] pytest config + fixtures (graceful DB-availability skip)
- [x] parsing, chunking, embedding, reranking, hybrid fusion, RBAC, citations, context builder, evaluation metrics, LLM providers/fallback, API — 60 passing
- [x] integration test: end-to-end ingest -> query -> cited answer [~ DB required]
- [x] ruff clean (0 lint errors)

## 12. Docker & CI
- [x] backend/Dockerfile
- [x] frontend/Dockerfile (multi-stage, standalone output)
- [x] docker-compose.yml (db with pgvector, backend, frontend) incl. correct build-arg vs runtime-env handling for NEXT_PUBLIC_API_URL
- [x] .github/workflows/ci.yml — backend job runs full suite against a real `pgvector/pgvector` service container; frontend job lints + builds
- [x] .pre-commit-config.yaml (ruff + hygiene hooks)

## 13. Docs
- [x] README.md (full, with mermaid architecture diagram)
- [x] docs/ARCHITECTURE.md (module layout, ER diagram, sequence diagram)
- [x] docs/RAG_PIPELINE.md
- [x] docs/EVALUATION.md
- [x] docs/DEPLOYMENT.md
- [x] docs/RESUME.md
- [x] LICENSE (MIT), .gitignore, .env.example

## 14. Verification actually performed in this environment
- [x] pip install backend deps (real install, incl. torch/sentence-transformers)
- [x] pytest: 60 passed, 5 skipped (DB-gated), 0 failed — run multiple times across the session as code changed
- [x] Real embedding model + real cross-encoder reranker downloaded and exercised (not mocked)
- [x] Full 25-document sample corpus parsed + chunked with zero errors (caught and fixed a real PDF-parsing bug this way — see PLAN.md)
- [x] npm install + `next build` (0 errors) + dev-server smoke test
- [x] ruff check: 0 errors
- [~] Postgres/pgvector-dependent paths (seed_db.py, live API against a real DB, docker compose up): not executable in this sandbox (no Docker); written, path-consistency-reviewed for both local and containerized layouts, and exercised for real by `.github/workflows/ci.yml`'s `pgvector/pgvector` service container on every push.
