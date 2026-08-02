/**
 * API client for the Socrates AI FastAPI backend.
 *
 * All functions talk directly to the custom REST/SSE endpoints.
 * The base URL is configured via NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 */

import type {
  ChatResponse,
  ThreadInfo,
  UploadedFile,
  SSEEvent,
} from "./types";

function getBaseUrl(): string {
  if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

// ── Helper ────────────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const res = await fetch(url, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/api/health");
}

// ── File Upload ───────────────────────────────────────────────────────────────

export async function uploadFile(file: File): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<UploadedFile>("/api/upload", {
    method: "POST",
    body: formData,
  });
}

// ── Chat (full response) ──────────────────────────────────────────────────────

export async function sendChat(
  message: string,
  threadId?: string | null,
  fileIds?: string[],
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      thread_id: threadId ?? undefined,
      file_ids: fileIds?.length ? fileIds : undefined,
    }),
  });
}

// ── Chat Stream (SSE) ─────────────────────────────────────────────────────────

/**
 * Opens a streaming SSE connection to /api/chat/stream.
 *
 * Yields parsed SSE event objects. The caller should read events until the
 * "result" or "error" event is received, then break the loop.
 *
 * Pass an AbortSignal to cancel the stream.
 */
export async function* streamChat(
  message: string,
  threadId?: string | null,
  fileIds?: string[],
  signal?: AbortSignal,
): AsyncGenerator<SSEEvent> {
  const url = `${getBaseUrl()}/api/chat/stream`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      thread_id: threadId ?? undefined,
      file_ids: fileIds?.length ? fileIds : undefined,
    }),
    signal,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(`Stream error ${res.status}: ${detail}`);
  }

  if (!res.body) {
    throw new Error("Response body is null");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE messages are separated by double newlines
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const lines = part.split("\n");
        let dataLine = "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            dataLine = line.slice(6).trim();
          }
        }

        if (!dataLine) continue;

        try {
          const parsed = JSON.parse(dataLine) as SSEEvent;
          yield parsed;
        } catch {
          // Malformed JSON — skip
        }
      }
    }
  } finally {
    reader.cancel().catch(() => undefined);
  }
}

// ── Threads ───────────────────────────────────────────────────────────────────

export async function listThreads(
  limit = 50,
  offset = 0,
): Promise<ThreadInfo[]> {
  return apiFetch<ThreadInfo[]>(
    `/api/threads?limit=${limit}&offset=${offset}`,
  );
}

export interface ThreadHistoryMessage {
  role: "human" | "ai";
  content: string;
}

export async function getThreadHistory(
  threadId: string,
): Promise<{ thread_id: string; messages: ThreadHistoryMessage[] }> {
  return apiFetch(`/api/threads/${encodeURIComponent(threadId)}/history`);
}

export async function deleteThread(threadId: string): Promise<void> {
  await apiFetch(`/api/threads/${encodeURIComponent(threadId)}`, {
    method: "DELETE",
  });
}

export async function getThreadFiles(
  threadId: string,
): Promise<{ thread_id: string; files: UploadedFile[] }> {
  return apiFetch(`/api/threads/${encodeURIComponent(threadId)}/files`);
}
