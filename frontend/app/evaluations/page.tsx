"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import type { EvalRun } from "@/lib/types";

type Metrics = {
  dataset_size: number;
  generation_mode: string;
  retrieval: Record<string, { recall_at_k: number; precision_at_k: number; mrr: number }>;
  generation: { avg_groundedness: number; avg_relevance: number; avg_citation_correctness: number };
  system: { avg_total_latency_ms: number; avg_prompt_tokens: number; avg_completion_tokens: number };
  rbac: { test_count: number; pass_rate: number };
  insufficient_evidence: { test_count: number; correct_refusal_rate: number };
};

export default function EvaluationsPage() {
  const { user } = useAuth();
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api.get<EvalRun[]>("/evaluations").then(setRuns).catch((e) => setError(e.message));
  }

  useEffect(refresh, []);

  async function triggerRun() {
    setRunning(true);
    setError(null);
    try {
      await api.post("/evaluations/run?mode=hybrid");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Eval run failed");
    } finally {
      setRunning(false);
    }
  }

  const latest = runs[0]?.metrics as unknown as Metrics | undefined;

  return (
    <AppShell>
      <div className="mx-auto max-w-5xl px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Evaluations</h1>
            <p className="mt-1 text-sm text-gray-500">
              Retrieval, generation, and system quality against evals/qa_dataset.json (57 grounded Q&amp;A pairs).
            </p>
          </div>
          {user?.role === "admin" && (
            <button className="btn-primary" onClick={triggerRun} disabled={running}>
              {running ? "Running evaluation…" : "Run evaluation"}
            </button>
          )}
        </div>

        {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        {!latest && (
          <p className="mt-6 rounded-md bg-gray-50 p-4 text-sm text-gray-500">
            No evaluation runs yet.{" "}
            {user?.role === "admin"
              ? "Click \"Run evaluation\" above, or run `python scripts/run_evals.py` from the CLI."
              : "Ask an admin to run one, or run `python scripts/run_evals.py` from the CLI."}
          </p>
        )}

        {latest && (
          <div className="mt-6 space-y-6">
            <div className="card p-5">
              <h2 className="font-medium text-gray-900">Retrieval quality by mode</h2>
              <table className="mt-3 w-full text-left text-sm">
                <thead className="text-xs uppercase text-gray-400">
                  <tr>
                    <th className="py-1">Mode</th>
                    <th className="py-1">Recall@K</th>
                    <th className="py-1">Precision@K</th>
                    <th className="py-1">MRR</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(latest.retrieval).map(([mode, m]) => (
                    <tr key={mode} className="border-t border-gray-100">
                      <td className="py-2 font-medium">{mode}</td>
                      <td className="py-2">{m.recall_at_k.toFixed(3)}</td>
                      <td className="py-2">{m.precision_at_k.toFixed(3)}</td>
                      <td className="py-2">{m.mrr.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <MetricCard label="Groundedness" value={latest.generation.avg_groundedness} />
              <MetricCard label="Answer relevance" value={latest.generation.avg_relevance} />
              <MetricCard label="Citation correctness" value={latest.generation.avg_citation_correctness} />
              <MetricCard label="RBAC pass rate" value={latest.rbac.pass_rate} sub={`${latest.rbac.test_count} tests`} />
            </div>

            <div className="card p-5">
              <h2 className="font-medium text-gray-900">System metrics</h2>
              <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                <div><p className="text-gray-400">Avg total latency</p><p className="font-medium">{latest.system.avg_total_latency_ms.toFixed(0)} ms</p></div>
                <div><p className="text-gray-400">Avg prompt tokens</p><p className="font-medium">{latest.system.avg_prompt_tokens.toFixed(0)}</p></div>
                <div><p className="text-gray-400">Avg completion tokens</p><p className="font-medium">{latest.system.avg_completion_tokens.toFixed(0)}</p></div>
              </div>
            </div>

            <div className="card p-5">
              <h2 className="font-medium text-gray-900">Insufficient-evidence handling</h2>
              <p className="mt-2 text-sm text-gray-600">
                Correct refusal rate: <span className="font-medium">{(latest.insufficient_evidence.correct_refusal_rate * 100).toFixed(0)}%</span>{" "}
                ({latest.insufficient_evidence.test_count} out-of-corpus questions)
              </p>
            </div>
          </div>
        )}

        <div className="card mt-8">
          <div className="border-b border-gray-100 px-5 py-3">
            <h2 className="font-medium text-gray-900">Run history</h2>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-gray-400">
              <tr><th className="px-5 py-2">Run</th><th className="px-5 py-2">Dataset size</th><th className="px-5 py-2">Date</th></tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t border-gray-100">
                  <td className="px-5 py-3 font-mono text-xs">{r.id.slice(0, 8)}</td>
                  <td className="px-5 py-3">{r.dataset_size}</td>
                  <td className="px-5 py-3">{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr><td colSpan={3} className="px-5 py-6 text-center text-gray-400">No runs recorded.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: number; sub?: string }) {
  return (
    <div className="card p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-gray-900">{(value * 100).toFixed(0)}%</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}
