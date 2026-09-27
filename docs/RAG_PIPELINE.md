# RAG Pipeline

## End-to-end flow

```
Upload -> Parse (pdf/docx/txt/md) -> Clean -> Metadata extract -> Chunk
       -> Embed -> Store (Postgres+pgvector) -> Index (BM25 corpus rebuild)

Query -> query processing -> keyword retrieval + vector retrieval
      -> RRF fusion -> RBAC filter (already applied in both retrievers)
      -> cross-encoder rerank -> context construction -> LLM -> citations
```

## Ingestion

`app/ingestion/parsers.py` normalizes every supported format (PDF via
`pypdf`, DOCX via `python-docx`, Markdown via `markdown-it-py`, plain text)
into a common `ParsedBlock(text, section, page_number)` sequence:

- **PDF**: text extracted per page; short, punctuation-free, title-cased
  lines are heuristically treated as headings and set the running `section`
  for subsequent blocks on that page.
- **DOCX**: paragraphs styled `Heading`/`Title` set the section; DOCX has no
  fixed pagination, so `page_number` is `None`.
- **Markdown**: a real heading stack (`#`/`##`/...) tracked via
  `markdown-it-py` tokens, producing dotted section paths like
  `"Leave Policy > Carryover Rules"`.
- **TXT**: blank-line-delimited paragraphs, with the same heading heuristic
  as PDF.

### Chunking (`app/ingestion/chunking.py`)

Deliberately **not** a fixed-N-character splitter:

1. Blocks are grouped by their section heading — a chunk never straddles two
   different headings.
2. Within a section, paragraphs are greedily packed up to
   `CHUNK_TARGET_TOKENS` (default 300), splitting on paragraph boundaries.
3. A paragraph that alone exceeds the target is split on sentence boundaries
   instead of mid-sentence.
4. A short token overlap (`CHUNK_OVERLAP_TOKENS`, default 40) carries into
   the next chunk of the same section, so a fact sitting right at a chunk
   boundary isn't lost to either side.

Token counting uses `tiktoken`'s `cl100k_base` encoding throughout the
codebase (chunking, context budget, token-usage estimates) as a consistent,
good-enough proxy — it's not the exact tokenizer for every provider, but
using one consistent estimator everywhere is more useful than three
slightly-different "exact" ones.

## Retrieval — three real, independent modes

Configuration lives in `app/config.py` (`RETRIEVAL_*` settings) so tuning is
a one-line code change, not a buried magic number:

| Setting | Default | Meaning |
|---|---|---|
| `RETRIEVAL_TOP_K_VECTOR` | 20 | Vector candidates fetched from pgvector |
| `RETRIEVAL_TOP_K_KEYWORD` | 20 | BM25 candidates fetched |
| `RETRIEVAL_RRF_K` | 60 | RRF smoothing constant (standard value) |
| `RETRIEVAL_FUSED_TOP_N` | 15 | Candidates handed to the reranker |
| `RETRIEVAL_FINAL_TOP_N` | 6 | Chunks handed to the context builder |

### Semantic (`vector_search.py`)

Cosine distance via pgvector's `<=>` operator (exposed through
`Chunk.embedding.cosine_distance(...)` in SQLAlchemy), `ORDER BY` that
distance, RBAC-filtered in the same query via
`Document.allowed_roles.contains([role])` (a JSONB `@>` containment check).

### Keyword (`keyword_search.py`)

Real BM25 (`rank_bm25.BM25Okapi`), not a substring/ILIKE match. The
RBAC-filtered candidate set is loaded from Postgres first and BM25 is
computed only over already-authorized chunks — an unauthorized chunk is
never in the corpus the ranker can return, regardless of match quality.

> **Scale trade-off, stated plainly**: rebuilding BM25 per query is
> `O(corpus size)`. That's fine at this project's scale (a few hundred
> chunks across ~25 documents) and it keeps the RBAC guarantee trivially
> correct to reason about. At real enterprise scale you'd move this to
> Postgres full-text search (`tsvector`/`tsrank`) or an external index
> (OpenSearch/Elasticsearch) with the same role predicate pushed into that
> index's filter — not computed after the fact.

### Hybrid (the default)

Both retrievers run, then **Reciprocal Rank Fusion** (`fusion.py`) combines
them by *rank*, not raw score — sidestepping the "BM25 scores and cosine
similarities live on incomparable scales" problem entirely:

```
RRF(d) = Σ over rankings r containing d of  1 / (k + rank_r(d))
```

A chunk ranked highly by both signals wins; a chunk found by only one signal
still gets a chance to surface.

### Reranking

The fused top-`RETRIEVAL_FUSED_TOP_N` candidates are rescored by a real
cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`), which scores
`(query, passage)` pairs jointly — far more accurate than cosine similarity
alone, but too slow to run over an entire corpus, which is why it only ever
sees a small, pre-filtered candidate set.

## Context Engineering (`app/context/builder.py`)

Rules applied in order:

1. **Deduplicate** — identical/near-identical content (normalized
   whitespace + case) counted once.
2. **Prioritize by relevance** — rerank score, falling back to fusion score,
   then raw vector/keyword score.
3. **Cap chunks per document** (`CONTEXT_MAX_CHUNKS_PER_DOC`, default 3) so
   one long, well-matching document can't crowd out every other source.
4. **Respect a hard token budget** (`CONTEXT_TOKEN_BUDGET`, default 3000) —
   greedily add chunks in relevance order, *skipping* (not truncating) any
   chunk that would blow the budget, so smaller, still-relevant chunks
   further down the list still get a chance.
5. **Present grouped by document** for readability, while the *selection*
   above stays purely relevance-driven.

If nothing survives (empty retrieval, or nothing relevant), the builder
returns an empty context and `app/rag/pipeline.py` short-circuits: it never
calls the LLM at all, returning a fixed "insufficient evidence" response.
This is a deliberate choice — it's cheaper, faster, and removes any chance
of the LLM hallucinating an answer from its own training data when the
corpus genuinely has nothing relevant.

## Generation (`app/llm/`)

A minimal `LLMProvider` ABC (`base.py`) with one method,
`generate(system_prompt, user_prompt, max_tokens) -> LLMResult`. Three
implementations:

- **Gemini** (`gemini_provider.py`) — calls the REST API directly via
  `httpx` (no SDK dependency), so the integration is readable end to end.
  Raises immediately (no network call) if `GEMINI_API_KEY` isn't set.
- **Ollama** (`ollama_provider.py`) — local daemon REST API, short connect
  timeout so an absent daemon fails fast rather than hanging.
- **Mock** (`mock_provider.py`) — deterministic, offline. Does *real*
  extractive work: it parses the actual numbered context blocks the
  pipeline built, scores them by word overlap with the question, and
  returns the most relevant sentence(s) with correct `[n]` citations — or
  the same "insufficient evidence" text real providers are instructed to
  use, if nothing overlaps. This is what lets tests and CI exercise the full
  citation/insufficient-evidence logic with zero network access.

`app/llm/factory.py` walks `LLM_PROVIDER_ORDER` (default
`gemini,ollama,mock`) and returns the first provider that succeeds,
catching `LLMProviderError` specifically so a real bug elsewhere isn't
silently swallowed as "try the next provider."

### The system prompt

```
You are the internal knowledge assistant for Acme Financial Services.
Answer the employee's question using ONLY the information in the numbered
context blocks below. Every factual sentence in your answer MUST end with a
citation marker like [1] or [2] referencing the context block it came from.
Never invent a citation number that isn't shown in the context.
If the context does not contain enough information to answer confidently,
say so explicitly instead of guessing — do not use outside knowledge.
```

## Citations (`app/rag/citations.py`)

`[n]` markers in the model's answer are resolved **strictly** against the
context that was actually sent for that request — a citation number outside
the range the model was given is dropped, never guessed at or fabricated.
This is the mechanism that makes "never generate fake citations" an
enforced property of the code, not just a prompt instruction.
