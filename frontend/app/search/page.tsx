"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { SearchResponse, RetrievedChunk } from "@/lib/types";

const MODES = [
  { value: "hybrid", label: "Hybrid (BM25 + vector, RRF-fused, reranked)" },
  { value: "semantic", label: "Semantic (vector only)" },
  { value: "keyword", label: "Keyword (BM25 only)" },
];

function Score({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  return (
    <span className="badge bg-gray-100 text-gray-600" title={label}>
      {label}: {value.toFixed(3)}
    </span>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("How many PTO days can I carry over?");
  const [mode, setMode] = useState("hybrid");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.post<SearchResponse>("/search", { query, mode });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl px-8 py-8">
        <h1 className="text-2xl font-semibold text-gray-900">Search</h1>
        <p className="mt-1 text-sm text-gray-500">
          Inspect raw retrieval — no LLM generation. Useful for debugging retrieval quality directly.
        </p>

        <form onSubmit={onSubmit} className="card mt-6 space-y-3 p-5">
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about any Acme FS policy…"
          />
          <div className="flex items-center justify-between">
            <select className="input w-auto" value={mode} onChange={(e) => setMode(e.target.value)}>
              {MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Searching…" : "Search"}
            </button>
          </div>
        </form>

        {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        {result && (
          <div className="mt-6 space-y-3">
            <p className="text-xs text-gray-400">
              {result.results.length} result{result.results.length === 1 ? "" : "s"} · {result.latency_ms.toFixed(0)} ms · mode: {result.mode}
            </p>
            {result.results.map((chunk: RetrievedChunk, i) => (
              <div key={chunk.chunk_id} className="card p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium text-brand-700">#{i + 1} · {chunk.document_name}</p>
                    <p className="text-xs text-gray-400">
                      {chunk.page_number ? `Page ${chunk.page_number}` : chunk.section || "Full document"} · {chunk.department} / {chunk.category}
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-end gap-1">
                    <Score label="vector" value={chunk.vector_score} />
                    <Score label="bm25" value={chunk.keyword_score} />
                    <Score label="rrf" value={chunk.fused_score} />
                    <Score label="rerank" value={chunk.rerank_score} />
                  </div>
                </div>
                <p className={`mt-3 text-sm text-gray-700 ${expanded === chunk.chunk_id ? "" : "line-clamp-3"}`}>
                  {chunk.content}
                </p>
                <button
                  className="mt-2 text-xs font-medium text-brand-600 hover:underline"
                  onClick={() => setExpanded(expanded === chunk.chunk_id ? null : chunk.chunk_id)}
                >
                  {expanded === chunk.chunk_id ? "Show less" : "Show full passage"}
                </button>
              </div>
            ))}
            {result.results.length === 0 && (
              <p className="rounded-md bg-gray-50 p-4 text-sm text-gray-500">
                No results — either nothing matched or your role doesn&apos;t have access to any matching document.
              </p>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
