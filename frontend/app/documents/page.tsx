"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/components/AuthProvider";
import { api, ApiError } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  indexed: "bg-green-100 text-green-700",
  processing: "bg-yellow-100 text-yellow-700",
  failed: "bg-red-100 text-red-700",
};

export default function DocumentsPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  function refresh() {
    setLoading(true);
    api
      .get<{ documents: DocumentItem[]; total: number }>("/documents")
      .then((res) => setDocuments(res.documents))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Documents</h1>
            <p className="mt-1 text-sm text-gray-500">
              {documents.length} document{documents.length === 1 ? "" : "s"} visible to your role.
            </p>
          </div>
          {user?.role === "admin" && (
            <button className="btn-primary" onClick={() => setShowUpload((v) => !v)}>
              {showUpload ? "Close" : "Upload document"}
            </button>
          )}
        </div>

        {showUpload && (
          <UploadForm
            onUploaded={() => {
              setShowUpload(false);
              refresh();
            }}
          />
        )}

        {error && <p className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        <div className="card mt-6 overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-400">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Department</th>
                <th className="px-5 py-3">Category</th>
                <th className="px-5 py-3">Access</th>
                <th className="px-5 py-3">Chunks</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="px-5 py-6 text-center text-gray-400">Loading…</td>
                </tr>
              )}
              {!loading && documents.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-6 text-center text-gray-400">No documents indexed yet.</td>
                </tr>
              )}
              {documents.map((doc) => (
                <tr key={doc.id} className="border-t border-gray-100">
                  <td className="px-5 py-3 font-medium text-gray-900">{doc.name}</td>
                  <td className="px-5 py-3 text-gray-600">{doc.document_type}</td>
                  <td className="px-5 py-3 text-gray-600">{doc.department}</td>
                  <td className="px-5 py-3 text-gray-600">{doc.category}</td>
                  <td className="px-5 py-3">
                    {doc.allowed_roles.includes("employee") ? (
                      <span className="badge bg-gray-100 text-gray-700">All staff</span>
                    ) : (
                      <span className="badge bg-purple-100 text-purple-700">Admin only</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-gray-600">{doc.chunk_count}</td>
                  <td className="px-5 py-3">
                    <span className={`badge ${STATUS_STYLES[doc.status] || "bg-gray-100 text-gray-700"}`}>{doc.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState("policy");
  const [department, setDepartment] = useState("HR");
  const [category, setCategory] = useState("hr_policy");
  const [adminOnly, setAdminOnly] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_type", documentType);
      formData.append("department", department);
      formData.append("category", category);
      formData.append("allowed_roles", JSON.stringify(adminOnly ? ["admin"] : ["admin", "employee"]));
      await api.postForm("/documents", formData);
      onUploaded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card mt-4 grid grid-cols-1 gap-4 p-5 md:grid-cols-2">
      <div className="md:col-span-2">
        <label className="label">File (PDF, DOCX, TXT, or Markdown)</label>
        <input
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="input"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
      </div>
      <div>
        <label className="label">Document type</label>
        <input className="input" value={documentType} onChange={(e) => setDocumentType(e.target.value)} />
      </div>
      <div>
        <label className="label">Department</label>
        <input className="input" value={department} onChange={(e) => setDepartment(e.target.value)} />
      </div>
      <div>
        <label className="label">Category</label>
        <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} />
      </div>
      <div className="flex items-end gap-2">
        <input id="adminOnly" type="checkbox" checked={adminOnly} onChange={(e) => setAdminOnly(e.target.checked)} />
        <label htmlFor="adminOnly" className="text-sm text-gray-700">Restrict to admin role only</label>
      </div>
      {error && <p className="text-sm text-red-600 md:col-span-2">{error}</p>}
      <div className="md:col-span-2">
        <button type="submit" className="btn-primary" disabled={submitting || !file}>
          {submitting ? "Uploading and indexing…" : "Upload and index"}
        </button>
      </div>
    </form>
  );
}
