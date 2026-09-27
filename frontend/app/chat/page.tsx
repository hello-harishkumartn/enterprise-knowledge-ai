"use client";

import { useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage, ChatResponse, ConversationSummary, RetrievedChunk } from "@/lib/types";

const MODES = ["hybrid", "semantic", "keyword"];

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("hybrid");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inspectorIndex, setInspectorIndex] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  function refreshConversations() {
    api.get<ConversationSummary[]>("/chat/conversations").then(setConversations).catch(() => {});
  }

  useEffect(refreshConversations, []);
  useEffect(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), [messages]);

  async function openConversation(id: string) {
    setConversationId(id);
    setInspectorIndex(null);
    try {
      const msgs = await api.get<{ id: string; role: "user" | "assistant"; content: string; citations: unknown }[]>(
        `/chat/conversations/${id}/messages`
      );
      setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
    } catch {
      setMessages([]);
    }
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([]);
    setInspectorIndex(null);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || sending) return;
    const question = input.trim();
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setSending(true);

    try {
      const res = await api.post<ChatResponse>("/chat", {
        message: question,
        mode,
        conversation_id: conversationId,
      });
      setConversationId(res.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer,
          citations: res.citations,
          retrieved_chunks: res.retrieved_chunks,
          meta: { llm_provider: res.llm_provider, total_latency_ms: res.total_latency_ms },
        },
      ]);
      setInspectorIndex(messages.length + 1);
      refreshConversations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to get a response");
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setSending(false);
    }
  }

  const inspectorMessage = inspectorIndex !== null ? messages[inspectorIndex] : undefined;

  return (
    <AppShell>
      <div className="flex h-screen">
        {/* Conversation history sidebar */}
        <div className="flex w-56 flex-col border-r border-gray-200 bg-white">
          <div className="p-3">
            <button className="btn-secondary w-full text-sm" onClick={startNewConversation}>+ New chat</button>
          </div>
          <div className="flex-1 overflow-y-auto px-2">
            {conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => openConversation(c.id)}
                className={`mb-1 block w-full truncate rounded-md px-3 py-2 text-left text-sm ${
                  conversationId === c.id ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {c.title}
              </button>
            ))}
          </div>
        </div>

        {/* Chat center */}
        <div className="flex flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
            <h1 className="font-medium text-gray-900">Ask Acme Knowledge</h1>
            <select className="input w-auto text-sm" value={mode} onChange={(e) => setMode(e.target.value)}>
              {MODES.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
            {messages.length === 0 && (
              <p className="text-sm text-gray-400">
                Ask about leave policy, security requirements, expense limits, or anything else in the Acme FS
                knowledge base. Answers are grounded in retrieved documents with citations.
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-2xl rounded-lg px-4 py-3 text-sm ${
                    m.role === "user" ? "bg-brand-600 text-white" : "card cursor-pointer hover:border-brand-300"
                  }`}
                  onClick={() => m.role === "assistant" && setInspectorIndex(i)}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.role === "assistant" && m.citations && m.citations.length > 0 && (
                    <p className="mt-2 text-xs text-brand-600">
                      {m.citations.length} citation{m.citations.length === 1 ? "" : "s"} · click to inspect sources →
                    </p>
                  )}
                  {m.meta && (
                    <p className="mt-1 text-xs text-gray-400">{m.meta.llm_provider} · {m.meta.total_latency_ms.toFixed(0)}ms</p>
                  )}
                </div>
              </div>
            ))}
            {sending && <p className="text-sm text-gray-400">Retrieving context and generating an answer…</p>}
            {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={onSubmit} className="flex gap-2 border-t border-gray-200 bg-white p-4">
            <input
              className="input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question…"
            />
            <button type="submit" className="btn-primary" disabled={sending}>Send</button>
          </form>
        </div>

        {/* Sources / context inspector */}
        <div className="w-96 overflow-y-auto border-l border-gray-200 bg-white p-5">
          <h2 className="font-medium text-gray-900">Sources & context inspector</h2>
          {!inspectorMessage && (
            <p className="mt-3 text-sm text-gray-400">Select an assistant reply to inspect the retrieved chunks and scores behind it.</p>
          )}
          {inspectorMessage?.citations && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold uppercase text-gray-400">Citations</h3>
              <div className="mt-2 space-y-2">
                {inspectorMessage.citations.map((c) => (
                  <div key={c.number} className="rounded-md border border-gray-200 p-3 text-xs">
                    <p className="font-medium text-brand-700">[{c.number}] {c.document_name}</p>
                    <p className="text-gray-400">{c.page_number ? `Page ${c.page_number}` : c.section || "Full document"}</p>
                    <p className="mt-1 text-gray-600">{c.passage}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {inspectorMessage?.retrieved_chunks && (
            <div className="mt-5">
              <h3 className="text-xs font-semibold uppercase text-gray-400">All retrieved chunks</h3>
              <div className="mt-2 space-y-2">
                {inspectorMessage.retrieved_chunks.map((chunk: RetrievedChunk) => (
                  <details key={chunk.chunk_id} className="rounded-md border border-gray-200 p-3 text-xs">
                    <summary className="cursor-pointer font-medium text-gray-700">{chunk.document_name}</summary>
                    <p className="mt-1 text-gray-400">
                      vector: {chunk.vector_score?.toFixed(3) ?? "—"} · bm25: {chunk.keyword_score?.toFixed(3) ?? "—"} ·
                      rerank: {chunk.rerank_score?.toFixed(3) ?? "—"}
                    </p>
                    <p className="mt-1 text-gray-600">{chunk.content}</p>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
