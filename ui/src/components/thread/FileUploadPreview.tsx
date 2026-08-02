import { X } from "lucide-react";
import type { PendingUpload } from "@/lib/types";

export function FileUploadPreview({
  uploads,
  onRemove,
}: {
  uploads: PendingUpload[];
  onRemove: (fileId: string) => void;
}) {
  if (!uploads || uploads.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 px-4">
      {uploads.map((upload) => (
        <div
          key={upload.file_id}
          className="relative flex items-center gap-2 rounded-lg border bg-background px-3 py-2 shadow-sm"
        >
          <div className="flex flex-col max-w-[150px]">
            <span className="truncate text-sm font-medium">
              {upload.filename}
            </span>
            <span className="text-xs text-muted-foreground">
              {(upload.size_bytes / 1024).toFixed(1)} KB
            </span>
          </div>
          <button
            type="button"
            className="absolute -right-2 -top-2 rounded-full border bg-background p-1 hover:bg-muted"
            onClick={() => onRemove(upload.file_id)}
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ))}
    </div>
  );
}
