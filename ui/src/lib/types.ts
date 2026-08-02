/**
 * Custom type definitions for the Socrates AI UI.
 * These replace the LangGraph SDK types which are not compatible
 * with the custom FastAPI backend.
 */

// ── Messages ────────────────────────────────────────────────────────────────

export type MessageRole = "human" | "ai";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  files?: PendingUpload[];
}

// ── Threads ──────────────────────────────────────────────────────────────────

export interface ThreadInfo {
  thread_id: string;
  title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  last_message?: string | null;
}

// ── API Response shapes ──────────────────────────────────────────────────────

export interface ChartInfo {
  title: string;
  type: string;
  path?: string | null;
  b64?: string | null;
}

export interface ChatResponse {
  message: string;
  thread_id: string;
  intent?: string;
  chart?: ChartInfo | null;
  files_used?: string[];
  metadata?: {
    evaluation?: Record<string, unknown>;
    errors?: string[];
  } | null;
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  size_bytes: number;
  content_type: string;
}

// ── SSE Event shapes ─────────────────────────────────────────────────────────

export interface SSEEvent {
  event: "node_start" | "node_end" | "result" | "error" | "token";
  node: string | null;
  data: unknown;
}

export interface NodeStartData {
  event: "node_start";
  node: string;
  data: null;
}

export interface NodeEndData {
  event: "node_end";
  node: string;
  data: { output_keys: string[] };
}

export interface ResultData {
  event: "result";
  node: null;
  data: ChatResponse;
}

export interface ErrorData {
  event: "error";
  node: null;
  data: { detail: string };
}

export interface TokenData {
  event: "token";
  node: string | null;
  data: string;
}

// ── Upload state ─────────────────────────────────────────────────────────────

export interface PendingUpload {
  /** The file_id returned by /api/upload */
  file_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
}
