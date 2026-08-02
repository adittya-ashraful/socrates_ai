"use client";

/**
 * ThreadProvider — manages the list of conversation threads.
 *
 * Replaced the LangGraph SDK Client dependency with the custom API client.
 */

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import { listThreads, deleteThread as apiDeleteThread } from "@/lib/api-client";
import type { ThreadInfo } from "@/lib/types";

interface ThreadContextType {
  getThreads: () => Promise<ThreadInfo[]>;
  threads: ThreadInfo[];
  setThreads: Dispatch<SetStateAction<ThreadInfo[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
  deleteThread: (threadId: string) => Promise<void>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<ThreadInfo[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);

  const getThreads = useCallback(async (): Promise<ThreadInfo[]> => {
    return listThreads(100, 0);
  }, []);

  const deleteThread = useCallback(
    async (threadId: string): Promise<void> => {
      await apiDeleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
    },
    [],
  );

  const value: ThreadContextType = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
    deleteThread,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}
