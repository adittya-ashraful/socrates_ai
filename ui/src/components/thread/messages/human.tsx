import type { ChatMessage } from "@/lib/types";
import { CommandBar } from "./shared";
export function HumanMessage({
  message,
  isLoading,
}: {
  message: ChatMessage;
  isLoading: boolean;
}) {
  const contentString = message.content ?? "";

  return (
    <div className="group ml-auto flex items-center gap-2">
      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-2 items-end">
          {contentString ? (
            <p className="bg-muted ml-auto w-fit rounded-3xl px-4 py-2 text-right whitespace-pre-wrap max-w-[85vw] break-words">
              {contentString}
            </p>
          ) : null}

          {message.files && message.files.length > 0 && (
            <div className="flex flex-wrap items-center justify-end gap-2 mt-1">
              {message.files.map((file) => (
                <div
                  key={file.file_id}
                  className="flex items-center gap-2 rounded-lg border bg-white px-3 py-2 shadow-sm max-w-[200px]"
                >
                  <div className="flex flex-col items-end">
                    <span className="truncate text-sm font-medium text-gray-800">
                      {file.filename}
                    </span>
                    <span className="text-xs text-gray-500">
                      {(file.size_bytes / 1024).toFixed(1)} KB
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          <CommandBar
            isLoading={isLoading}
            content={contentString}
            isHumanMessage={true}
          />
        </div>
      </div>
    </div>
  );
}
