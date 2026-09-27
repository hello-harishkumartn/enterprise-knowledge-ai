# Evaluation

## Dataset

`evals/qa_dataset.json` — **57 hand-authored question/answer pairs**, every
one grounded in an actual fact from `sample_data/` (dates, dollar amounts,
day counts, named policies), so correctness is objectively checkable rather
than subjectively judged. It covers:

- One or more questions per document across all 25 sample documents.
- **3 `rbac_negative` items**: employee-role questions about facts that only
  exist in an admin-only (Restricted) document. The correct system behavior
  is to retrieve nothing from that document and answer "insufficient
  evidence" — these are graded as pass/fail on whether that boundary held,
  not on answer quality.
- **3 `insufficient_evidence` items**: questions with no answer anywhere in
  the corpus (e.g. "What is Acme's stock ticker?"), used to check the system
  doesn't hallucinate rather than admit it doesn't know.
- **1 `cross_document` item**: requires picking the right policy among
  several plausible-sounding ones.

Each item has:

```json
{
  "id": "q004",
  "role": "employee",
  "category": "hr_policy",
  "question": "How many PTO days can employees carry forward into the next calendar year?",
  "expected_document_names": ["Leave and Time-Off Policy"],
  "forbidden_document_names": []
}
```

Retrieval/citation correctness is graded at the **document** level (did the
system find/cite the right *document*), not exact chunk id — more robust to
chunking-parameter changes and much easier to hand-author ground truth for.

## Running

```bash
python scripts/seed_db.py        # ingest sample_data if not already done
python scripts/run_evals.py                      # hybrid mode, heuristic scoring
python scripts/run_evals.py --mode semantic       # compare a single retrieval mode
python scripts/run_evals.py --llm-judge           # LLM-graded groundedness/relevance
```

Each run writes `evals/results/eval_run_<timestamp>.json`,
`eval_run_<timestamp>.csv`, and updates `evals/results/latest.json` (what the
Evaluations page in the app reads). Admins can also trigger a run from that
page directly (`POST /api/evaluations/run`).

## Metrics

### Retrieval (computed separately for all three modes — semantic/keyword/hybrid)

- **Recall@K** — of the expected document(s), what fraction were found in
  the top K retrieved (K = `RETRIEVAL_FINAL_TOP_N`, default 6)?
- **Precision@K** — of the top K retrieved documents, what fraction were
  actually expected?
- **MRR** — reciprocal rank of the first expected document in the retrieved
  list (0 if not found).

Running all three modes per question (not just the production default,
hybrid) is what lets the Evaluations page show a real comparison table
instead of a single number — this is the evidence for *why* hybrid retrieval
was chosen, not just an assertion that it's better.

### Generation

- **Citation correctness** — fraction of citations in the generated answer
  that point to an expected source document. For `rbac_negative` /
  `insufficient_evidence` items (where the expected set is empty), a
  correct answer has *zero* citations; any citation scores 0.
- **Groundedness** — does every claim in the answer trace back to the
  retrieved context? Default: a lexical-overlap heuristic (per-sentence,
  non-stopword word overlap against the context — see
  `app/evaluation/metrics.py`). With `--llm-judge`, an LLM is asked to score
  1–5 directly (`app/evaluation/llm_judge.py`), normalized to 0–1.
- **Answer relevance** — does the answer actually address the question?
  Same heuristic/LLM-judge split as groundedness.

The heuristic is deliberately the *default*, not a shortcut: it requires no
API key, runs in CI with the mock provider, and is honest about being a
proxy rather than a real semantic judgment. `--llm-judge` is there for when
a real provider is configured and you want the more accurate (but
non-deterministic, non-free) signal — the mock provider is explicitly
excluded from being used as its own judge (see `llm_judge.judge_answer`),
since an extractive-only provider can't meaningfully grade groundedness.

### System

- Retrieval / generation / total latency (ms), averaged.
- Prompt / completion token counts, averaged (from the real provider's
  usage metadata when available — Gemini and Ollama both report this).

### RBAC and insufficient-evidence pass rates

Reported as their own summary blocks (`rbac.pass_rate`,
`insufficient_evidence.correct_refusal_rate`) rather than folded into the
generic averages — these are pass/fail security and honesty properties, and
burying them in an aggregate score would make a regression easy to miss.

## Reading the output

```json
{
  "dataset_size": 57,
  "retrieval": {
    "hybrid":   {"recall_at_k": 0.93, "precision_at_k": 0.21, "mrr": 0.88},
    "semantic": {"recall_at_k": 0.86, "precision_at_k": 0.19, "mrr": 0.79},
    "keyword":  {"recall_at_k": 0.81, "precision_at_k": 0.18, "mrr": 0.74}
  },
  "generation": {"avg_groundedness": 0.7, "avg_relevance": 0.68, "avg_citation_correctness": 0.9},
  "rbac": {"test_count": 3, "pass_rate": 1.0},
  "insufficient_evidence": {"test_count": 3, "correct_refusal_rate": 1.0}
}
```

(Illustrative shape only — see **Evaluation Results** in the README for why
actual numbers aren't hard-coded here: run it and read `latest.json`.)

`rbac.pass_rate` below 1.0 is the one number in this whole project that
should never be tolerated even slightly — it means an unauthorized document
leaked into either the retrieved set or a citation, and should be treated as
a P0.
