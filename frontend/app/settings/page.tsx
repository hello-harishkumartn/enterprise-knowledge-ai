"use client";

import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl px-8 py-8">
        <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>

        <div className="card mt-6 p-5">
          <h2 className="font-medium text-gray-900">Account</h2>
          <dl className="mt-3 grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-gray-500">Name</dt><dd>{user?.full_name}</dd>
            <dt className="text-gray-500">Email</dt><dd>{user?.email}</dd>
            <dt className="text-gray-500">Role</dt><dd className="capitalize">{user?.role}</dd>
            <dt className="text-gray-500">Department</dt><dd>{user?.department}</dd>
          </dl>
        </div>

        <div className="card mt-6 p-5">
          <h2 className="font-medium text-gray-900">Retrieval configuration</h2>
          <p className="mt-1 text-xs text-gray-400">
            Read-only — set in backend/app/config.py, not editable per-user. Shown here for transparency.
          </p>
          <dl className="mt-3 grid grid-cols-2 gap-y-2 text-sm">
            <dt className="text-gray-500">Embedding model</dt><dd className="font-mono text-xs">all-MiniLM-L6-v2</dd>
            <dt className="text-gray-500">Reranker model</dt><dd className="font-mono text-xs">cross-encoder/ms-marco-MiniLM-L-6-v2</dd>
            <dt className="text-gray-500">Vector candidates (top-K)</dt><dd>20</dd>
            <dt className="text-gray-500">Keyword candidates (top-K)</dt><dd>20</dd>
            <dt className="text-gray-500">RRF constant (k)</dt><dd>60</dd>
            <dt className="text-gray-500">Reranked candidates</dt><dd>15</dd>
            <dt className="text-gray-500">Final chunks to LLM</dt><dd>6</dd>
            <dt className="text-gray-500">Context token budget</dt><dd>3000</dd>
            <dt className="text-gray-500">Max chunks per document</dt><dd>3</dd>
          </dl>
        </div>

        <div className="card mt-6 p-5">
          <h2 className="font-medium text-gray-900">LLM provider chain</h2>
          <p className="mt-1 text-xs text-gray-400">
            Tried in order until one succeeds — configured via LLM_PROVIDER_ORDER.
          </p>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-gray-700">
            <li>Gemini (gemini-1.5-flash, free tier)</li>
            <li>Ollama (local open-weight model, e.g. llama3.2)</li>
            <li>Deterministic offline fallback (used automatically in tests/CI)</li>
          </ol>
        </div>
      </div>
    </AppShell>
  );
}
