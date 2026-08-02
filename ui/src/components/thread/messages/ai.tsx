import { MarkdownText } from "../markdown-text";
import { CommandBar } from "./shared";
import type { ChatMessage, ChatResponse } from "@/lib/types";
import { ChartDisplay } from "../ChartDisplay";
import { AlertCircle, CircleDashed, LoaderCircle } from "lucide-react";

const NODE_LABELS: Record<string, string> = {
  thinking: "Thinking",
  loading_context: "Loading context",
  searching: "Searching",
  analyzing: "Analyzing",
  generating: "Generating",
};

export function AssistantMessage({
  message,
  isLoading,
  response,
}: {
  message: ChatMessage;
  isLoading: boolean;
  response?: ChatResponse | null;
}) {
  const contentString = message.content ?? "";
  const hasErrors = response?.metadata?.errors && response.metadata.errors.length > 0;

  return (
    <div className="group mr-auto flex w-full items-start gap-2">
      <div className="flex w-full flex-col gap-2">
        {contentString.length > 0 && (
          <div className="py-1 w-full max-w-4xl overflow-hidden">
            <MarkdownText>{contentString}</MarkdownText>
          </div>
        )}

        {response?.chart && <ChartDisplay chart={response.chart} />}

        {hasErrors && (
          <div className="mt-2 rounded-md border border-red-200 bg-red-50 p-4 max-w-4xl">
            <div className="flex items-center gap-2 text-red-800 font-semibold mb-2">
              <AlertCircle className="size-5" />
              <span>Issues encountered during analysis</span>
            </div>
            <ul className="list-disc pl-5 text-sm text-red-700 space-y-1">
              {response.metadata!.errors!.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mr-auto flex items-center gap-2 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          <CommandBar
            content={contentString}
            isLoading={isLoading}
            isAiMessage={true}
          />
        </div>
      </div>
    </div>
  );
}

export function AssistantMessageLoading({ 
  activeNodes = [], 
  streamingText = "" 
}: { 
  activeNodes?: string[], 
  streamingText?: string 
}) {
  const currentNode = activeNodes.length > 0 ? activeNodes[activeNodes.length - 1] : null;

  return (
    <div className="mr-auto flex w-full flex-col items-start gap-4 max-w-4xl">
      {/* Streaming Text */}
      {streamingText && (
        <div className="py-1 w-full overflow-hidden">
          <MarkdownText>{streamingText}</MarkdownText>
          <span className="inline-block w-2 h-4 ml-1 bg-gray-400 animate-pulse" />
        </div>
      )}

      {/* Progress Stepper */}
      <div className="flex flex-col gap-2 bg-gray-50 rounded-xl p-4 border border-gray-100 min-w-[280px]">
        {currentNode ? (
          <div className="flex items-center gap-3">
            <LoaderCircle className="size-4 animate-spin text-blue-500" />
            <span className="text-sm font-medium text-gray-700">
              {NODE_LABELS[currentNode] || currentNode.replace(/_/g, " ")}...
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <CircleDashed className="size-4 animate-spin text-gray-400" />
            <span className="text-sm font-medium text-gray-500">Thinking...</span>
          </div>
        )}
      </div>
    </div>
  );
}
