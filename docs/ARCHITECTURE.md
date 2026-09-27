# Architecture

## System Overview

```mermaid
flowchart TB
    subgraph Frontend["Next.js Frontend (:3000)"]
        Login
        Dashboard
        Documents
        Search
        Chat
        Evaluations
        Analytics
        Settings
    end

    subgraph Backend["FastAPI Backend (:8000)"]
        direction TB
        API["/api/* routes"]
        Ingestion["app.ingestion"]
        Retrieval["app.retrieval"]
        Context["app.context"]
        RAG["app.rag"]
        LLMLayer["app.llm"]
        Evaluation["app.evaluation"]
    end

    subgraph Storage
        PG[(PostgreSQL + pgvector)]
        FS[(Local filesystem\nbackend/storage)]
    end

    subgraph External
        Gemini[(Gemini API)]
        Ollama[(Local Ollama)]
    end

    Frontend -->|fetch, JWT bearer| API
    API --> Ingestion --> FS
    Ingestion --> PG
    API --> Retrieval --> PG
    API --> RAG
    RAG --> Retrieval
    RAG --> Context
    RAG --> LLMLayer
    LLMLayer -->|1st| Gemini
    LLMLayer -->|2nd| Ollama
    API --> Evaluation --> Retrieval
    Evaluation --> RAG
```

## Backend Module Layout

```
backend/app/
├── main.py                 FastAPI app, router wiring, lifespan (DB init + seed)
├── config.py                Settings (env-driven, single source of truth)
├── core/
│   ├── security.py          JWT issuance/verification, password hashing
│   └── rbac.py               role_can_access() — the one RBAC predicate
├── db/
│   ├── models.py             SQLAlchemy ORM models
│   ├── session.py            engine/session factory
│   └── bootstrap.py          init_db(), seed_users() — idempotent setup
├── ingestion/
│   ├── parsers.py            pdf/docx/txt/md -> ParsedBlock[]
│   ├── chunking.py           heading/paragraph-aware chunker
│   └── pipeline.py           parse -> chunk -> embed -> store
├── retrieval/
│   ├── embeddings.py         sentence-transformers wrapper (singleton)
│   ├── reranker.py            cross-encoder wrapper (singleton)
│   ├── vector_search.py       pgvector query, RBAC-filtered
│   ├── keyword_search.py      BM25 over RBAC-filtered candidate set
│   ├── fusion.py               Reciprocal Rank Fusion
│   └── pipeline.py             orchestrates the above into 3 retrieval modes
├── context/
│   └── builder.py              dedup, token budget, per-doc cap, citation numbering
├── llm/
│   ├── base.py                  LLMProvider ABC, LLMResult, LLMProviderError
│   ├── gemini_provider.py       Gemini REST API (httpx, no SDK)
│   ├── ollama_provider.py       Local Ollama REST API
│   ├── mock_provider.py         Deterministic extractive fallback (tests/CI)
│   └── factory.py                Fallback chain walker
├── rag/
│   ├── pipeline.py               retrieval -> context -> generation orchestration
│   └── citations.py              resolves [n] markers to real source chunks
├── evaluation/
│   ├── metrics.py                 pure retrieval/generation metric functions
│   ├── llm_judge.py                optional LLM-as-judge scoring
│   └── runner.py                    replays evals/qa_dataset.json end to end
├── schemas/                        Pydantic request/response models
└── api/routes/                     auth, documents, search, chat, evaluations, analytics
```

## Database Schema

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : has
    USERS ||--o{ QUERY_LOGS : issues
    USERS ||--o{ DOCUMENTS : uploads
    DOCUMENTS ||--o{ CHUNKS : "split into"
    CONVERSATIONS ||--o{ MESSAGES : contains

    USERS {
        string id PK
        string email
        string hashed_password
        string role "admin | employee"
        string department
    }
    DOCUMENTS {
        string id PK
        string name
        string file_format
        string document_type
        string department
        string category
        jsonb allowed_roles
        string status
        int chunk_count
    }
    CHUNKS {
        string id PK
        string document_id FK
        int chunk_index
        text content
        string section
        int page_number
        vector embedding "384-dim, pgvector"
    }
    CONVERSATIONS {
        string id PK
        string user_id FK
        string title
    }
    MESSAGES {
        string id PK
        string conversation_id FK
        string role
        text content
        jsonb citations
    }
    QUERY_LOGS {
        string id PK
        string user_id FK
        text query
        string mode
        jsonb retrieved_chunk_ids
        jsonb retrieval_scores
        jsonb rerank_scores
        float total_latency_ms
        string llm_provider
    }
    EVAL_RUNS {
        string id PK
        int dataset_size
        jsonb metrics
        string results_path
    }
```

`allowed_roles` is `JSONB` specifically so RBAC filtering can use Postgres's
`@>` containment operator directly in the retrieval `WHERE` clause (see
`app/retrieval/vector_search.py` and `keyword_search.py`) rather than
filtering rows in Python after they've already been fetched.

## Request Flow: Chat / RAG Query

```mermaid
sequenceDiagram
    participant U as User (browser)
    participant API as FastAPI /api/chat
    participant RET as Retrieval
    participant CTX as Context Builder
    participant LLM as LLM Provider Chain
    participant DB as Postgres

    U->>API: POST /chat {message, mode}
    API->>RET: retrieve(query, role, mode)
    RET->>DB: BM25 candidates (RBAC-filtered)
    RET->>DB: vector candidates (RBAC-filtered)
    RET->>RET: Reciprocal Rank Fusion
    RET->>RET: cross-encoder rerank
    RET-->>API: top-N RetrievedChunk[]
    API->>CTX: build_context(chunks, budget)
    CTX-->>API: BuiltContext (deduped, capped, numbered)
    alt context is empty
        API-->>U: "insufficient evidence" (no LLM call)
    else has context
        API->>LLM: generate(system_prompt, context+question)
        LLM->>LLM: try Gemini -> Ollama -> mock
        LLM-->>API: answer text
        API->>API: extract_citations(answer, context)
        API->>DB: log QueryLog row
        API-->>U: answer + citations + retrieved_chunks (for inspector)
    end
```

## Authentication

Local/Docker dev uses a self-contained JWT flow (`app/core/security.py`):
`POST /auth/login` verifies a bcrypt-hashed password and issues a JWT with
`{sub, role, email}` claims; every other route decodes that JWT via the
`get_current_user` dependency. The hosted deployment swaps this for Supabase
Auth, which issues JWTs verified against Supabase's JWKS — the claim shape
is compatible by design, so nothing downstream of `get_current_user` changes
(see `docs/DEPLOYMENT.md`).

## RBAC Enforcement Point

The critical design decision: RBAC is enforced as a `WHERE` predicate inside
`vector_search()` and `keyword_search()`, not as a filter applied to results
afterward. An employee-role query for content only an admin-only document
contains never causes that document's chunks to be fetched from Postgres,
let alone reach the context builder or the LLM. `backend/tests/test_rbac.py`
proves this directly, and `evals/qa_dataset.json` includes three
`rbac_negative` questions that assert the same thing end-to-end through the
full RAG pipeline.
