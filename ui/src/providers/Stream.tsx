"use client";

/**
 * StreamProvider — replaces the LangGraph SDK useStream() hook.
 *
 * Talks directly to the custom FastAPI backend via /api/chat/stream (SSE).
 * Manages messages, loading state, active nodes, thread_id, and errors.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryState } from "nuqs";
import { v4 as uuidv4 } from "uuid";
import { streamChat, getThreadHistory, healthCheck } from "@/lib/api-client";
import type { ChatMessage, ChatResponse, SSEEvent } from "@/lib/types";
import { toast } from "sonner";
import { useThreads } from "@/providers/Thread";

// ── Context shape ─────────────────────────────────────────────────────────────

interface StreamContextType {
  /** All messages in the current thread (human + ai). */
  messages: ChatMessage[];
  /** Whether a request is in-flight. */
  isLoading: boolean;
  /** Error from the last request, if any. */
  error: Error | null;
  /** Nodes currently in-flight (from SSE node_start / node_end events). */
  activeNodes: string[];
  /** The last completed ChatResponse (contains chart, metadata, etc.). */
  lastResponse: ChatResponse | null;
  /** Submit a new human message. */
  submit: (message: string, files?: import("@/lib/types").PendingUpload[]) => Promise<void>;
  /** Abort the current stream. */
  stop: () => void;
  /** Load a thread by ID (replaces messages with thread history). */
  loadThread: (threadId: string) => Promise<void>;
  /** Clear messages and start a new thread. */
  clearThread: () => void;
  /** Current token stream for the AI message being generated. */
  streamingText: string;
}

const StreamContext = createContext<StreamContextType | undefined>(undefined);

// ── Provider ──────────────────────────────────────────────────────────────────

export function StreamProvider({ children }: { children: ReactNode }) {
  const [threadId, setThreadId] = useQueryState("threadId");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [activeNodes, setActiveNodes] = useState<string[]>([]);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [streamingText, setStreamingText] = useState("");
  
  const { getThreads, setThreads } = useThreads();

  const abortControllerRef = useRef<AbortController | null>(null);

  // ── Health check on mount ──────────────────────────────────────────────────
  React.useEffect(() => {
    healthCheck().catch(() => {
      toast.error("Cannot reach the Socrates AI API", {
        description: `Make sure the FastAPI server is running at ${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}.`,
        duration: 10_000,
        richColors: true,
        closeButton: true,
      });
    });
  }, []);

  // ── Actions ────────────────────────────────────────────────────────────────

  const loadThread = useCallback(async (id: string) => {
    try {
      const result = await getThreadHistory(id);
      const loaded: ChatMessage[] = result.messages.map((m: any) => ({
        id: uuidv4(),
        role: m.role,
        content: m.content,
        files: m.files,
      }));
      setMessages(loaded);
      setLastResponse(null);
    } catch (e) {
      console.error("Failed to load thread history:", e);
    }
  }, []);

  // ── Load thread history when threadId changes ──────────────────────────────
  React.useEffect(() => {
    if (!threadId) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadThread(threadId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId]);

  const clearThread = useCallback(() => {
    setThreadId(null);
    setMessages([]);
    setLastResponse(null);
    setError(null);
    setActiveNodes([]);
    setStreamingText("");
  }, [setThreadId]);

  const stop = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const submit = useCallback(
    async (message: string, files?: import("@/lib/types").PendingUpload[]) => {
      const hasMessage = message.trim().length > 0;
      const hasFiles = files && files.length > 0;
      if ((!hasMessage && !hasFiles) || isLoading) return;

      const fileIds = files ? files.map(f => f.file_id) : undefined;

      // Add human message optimistically
      const humanMsg: ChatMessage = {
        id: uuidv4(),
        role: "human",
        content: message.trim(),
        files: files,
      };
      
      setMessages((prev) => [...prev, humanMsg]);
      setIsLoading(true);
      setError(null);
      setActiveNodes([]);
      setStreamingText("");

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const gen = streamChat(
          message.trim(),
          threadId,
          fileIds,
          controller.signal,
        );

        let finalResponse: ChatResponse | null = null;

        for await (const event of gen) {
          if (controller.signal.aborted) break;

          const sseEvent = event as SSEEvent;

          if (sseEvent.event === "node_start") {
            const node = sseEvent.node;
            if (node) {
              setActiveNodes((prev) =>
                prev.includes(node) ? prev : [...prev, node],
              );
            }
          } else if (sseEvent.event === "node_end") {
            const node = sseEvent.node;
            if (node) {
              setActiveNodes((prev) => prev.filter((n) => n !== node));
            }
          } else if (sseEvent.event === "result") {
            const data = (sseEvent as any).data as ChatResponse;
            finalResponse = data;

            // Update thread ID from response
            if (data.thread_id && data.thread_id !== threadId) {
              setThreadId(data.thread_id);
              getThreads().then(setThreads).catch(console.error);
            }

            const aiMsg: ChatMessage = {
              id: uuidv4(),
              role: "ai",
              content: data.message,
            };
            setMessages((prev) => [...prev, aiMsg]);
            setLastResponse(data);
            setStreamingText("");
          } else if (sseEvent.event === "error") {
            const detail = ((sseEvent as any).data as { detail: string })
              .detail;
            throw new Error(detail);
          } else if (sseEvent.event === "token") {
            const tokenText = (sseEvent as any).data as string;
            setStreamingText((prev) => prev + tokenText);
          }
        }

        if (!finalResponse && !controller.signal.aborted) {
          throw new Error("No result received from the server.");
        }
      } catch (e) {
        if ((e as Error)?.name === "AbortError") {
          // User cancelled — no toast
        } else {
          const err = e instanceof Error ? e : new Error(String(e));
          setError(err);
          toast.error("An error occurred. Please try again.", {
            description: err.message,
            richColors: true,
            closeButton: true,
          });
        }
      } finally {
        setIsLoading(false);
        setActiveNodes([]);
        abortControllerRef.current = null;
      }
    },
    [isLoading, threadId, setThreadId, getThreads, setThreads],
  );

  const value: StreamContextType = {
    messages,
    isLoading,
    error,
    activeNodes,
    lastResponse,
    submit,
    stop,
    loadThread,
    clearThread,
    streamingText,
  };

  return (
    <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useStreamContext(): StreamContextType {
  const context = useContext(StreamContext);
  if (context === undefined) {
    throw new Error("useStreamContext must be used within a StreamProvider");
  }
  return context;
}

export default StreamContext;
