"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { StatCard } from "@/components/StatCard";
import { api } from "@/lib/api";
import type { AnalyticsResponse } from "@/lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<AnalyticsResponse>("/analytics?limit=8")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-8 py-8">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Live snapshot of the knowledge base and query activity.</p>

        {error && (
          <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            Could not load analytics: {error}
          </p>
        )}

        {data && (
          <>
            <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-5">
              <StatCard label="Documents indexed" value={String(data.summary.documents_indexed)} />
              <StatCard label="Chunks indexed" value={String(data.summary.chunks_indexed)} />
              <StatCard label="Total queries" value={String(data.summary.total_queries)} />
              <StatCard label="Avg response time" value={`${data.summary.avg_response_time_ms.toFixed(0)} ms`} />
              <StatCard label="Avg retrieval score" value={data.summary.avg_retrieval_score.toFixed(3)} />
            </div>

            <div className="card mt-8">
              <div className="border-b border-gray-100 px-5 py-4">
                <h2 className="font-medium text-gray-900">Recent queries</h2>
              </div>
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-gray-400">
                  <tr>
                    <th className="px-5 py-2">Query</th>
                    <th className="px-5 py-2">Mode</th>
                    <th className="px-5 py-2">Provider</th>
                    <th className="px-5 py-2">Latency</th>
                    <th className="px-5 py-2">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_queries.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-5 py-6 text-center text-gray-400">
                        No queries yet — try the Search or Chat pages.
                      </td>
                    </tr>
                  )}
                  {data.recent_queries.map((q) => (
                    <tr key={q.id} className="border-t border-gray-100">
                      <td className="max-w-xs truncate px-5 py-3">{q.query}</td>
                      <td className="px-5 py-3">
                        <span className="badge bg-gray-100 text-gray-700">{q.mode}</span>
                      </td>
                      <td className="px-5 py-3">{q.llm_provider}</td>
                      <td className="px-5 py-3">{q.total_latency_ms.toFixed(0)} ms</td>
                      <td className="px-5 py-3">{q.prompt_tokens + q.completion_tokens}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
