export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "employee";
  department: string;
}

export interface DocumentItem {
  id: string;
  name: string;
  file_format: string;
  document_type: string;
  department: string;
  category: string;
  allowed_roles: string[];
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  section: string | null;
  page_number: number | null;
  document_type: string;
  department: string;
  category: string;
  vector_score: number | null;
  keyword_score: number | null;
  fused_score: number | null;
  rerank_score: number | null;
}

export interface SearchResponse {
  query: string;
  mode: string;
  results: RetrievedChunk[];
  latency_ms: number;
}

export interface Citation {
  number: number;
  document_id: string;
  document_name: string;
  section: string | null;
  page_number: number | null;
  passage: string;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  retrieved_chunks: RetrievedChunk[];
  llm_provider: string;
  llm_model: string;
  prompt_tokens: number;
  completion_tokens: number;
  retrieval_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;
  warnings: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  retrieved_chunks?: RetrievedChunk[];
  meta?: {
    llm_provider: string;
    total_latency_ms: number;
  };
}

export interface ConversationSummary {
  id: string;
  title: string;
}

export interface DashboardSummary {
  documents_indexed: number;
  chunks_indexed: number;
  total_queries: number;
  avg_response_time_ms: number;
  avg_retrieval_score: number;
}

export interface QueryLogItem {
  id: string;
  query: string;
  mode: string;
  llm_provider: string;
  llm_model: string;
  prompt_tokens: number;
  completion_tokens: number;
  retrieval_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;
  avg_retrieval_score: number;
  created_at: string;
}

export interface AnalyticsResponse {
  summary: DashboardSummary;
  recent_queries: QueryLogItem[];
}

export interface EvalRun {
  id: string;
  dataset_size: number;
  metrics: Record<string, unknown>;
  results_path: string;
  created_at: string;
}
