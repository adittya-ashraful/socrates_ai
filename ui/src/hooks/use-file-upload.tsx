import { useState, useRef, useEffect, ChangeEvent } from "react";
import { toast } from "sonner";
import { uploadFile } from "@/lib/api-client";
import type { PendingUpload } from "@/lib/types";

export const SUPPORTED_FILE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "application/pdf",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // xlsx
];

export function useFileUpload() {
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const dropRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const dragCounter = useRef(0);

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const fileArray = Array.from(files);
    await processFiles(fileArray);
    e.target.value = "";
  };

  const processFiles = async (files: File[]) => {
    const validFiles = files.filter((file) =>
      SUPPORTED_FILE_TYPES.includes(file.type),
    );
    const invalidFiles = files.filter(
      (file) => !SUPPORTED_FILE_TYPES.includes(file.type),
    );

    if (invalidFiles.length > 0) {
      toast.error(
        "You have uploaded an invalid file type. Supported types: Images, PDFs, CSV, Excel.",
      );
    }

    for (const file of validFiles) {
      // Check if already uploaded
      if (pendingUploads.some((p) => p.filename === file.name && p.size_bytes === file.size)) {
        toast.warning(`File ${file.name} is already attached.`);
        continue;
      }

      try {
        toast.info(`Uploading ${file.name}...`);
        const result = await uploadFile(file);
        setPendingUploads((prev) => [...prev, result]);
        toast.success(`${file.name} uploaded successfully.`);
      } catch (err) {
        toast.error(`Failed to upload ${file.name}`, {
          description: String(err),
        });
      }
    }
  };

  // Drag and drop handlers
  useEffect(() => {
    if (!dropRef.current) return;

    const handleWindowDragEnter = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        dragCounter.current += 1;
        setDragOver(true);
      }
    };
    const handleWindowDragLeave = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        dragCounter.current -= 1;
        if (dragCounter.current <= 0) {
          setDragOver(false);
          dragCounter.current = 0;
        }
      }
    };
    const handleWindowDrop = async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setDragOver(false);

      if (!e.dataTransfer) return;
      const files = Array.from(e.dataTransfer.files);
      await processFiles(files);
    };
    const handleWindowDragEnd = () => {
      dragCounter.current = 0;
      setDragOver(false);
    };

    window.addEventListener("dragenter", handleWindowDragEnter);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);
    window.addEventListener("dragend", handleWindowDragEnd);

    const handleWindowDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("dragover", handleWindowDragOver);

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(true);
    };
    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(true);
    };
    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
    };
    const element = dropRef.current;
    element.addEventListener("dragover", handleDragOver);
    element.addEventListener("dragenter", handleDragEnter);
    element.addEventListener("dragleave", handleDragLeave);

    return () => {
      element.removeEventListener("dragover", handleDragOver);
      element.removeEventListener("dragenter", handleDragEnter);
      element.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("dragenter", handleWindowDragEnter);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
      window.removeEventListener("dragover", handleWindowDragOver);
      dragCounter.current = 0;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const removeUpload = (fileId: string) => {
    setPendingUploads((prev) => prev.filter((p) => p.file_id !== fileId));
  };

  const resetUploads = () => setPendingUploads([]);

  const handlePaste = async (
    e: React.ClipboardEvent<HTMLTextAreaElement | HTMLInputElement>,
  ) => {
    const items = e.clipboardData.items;
    if (!items) return;
    const files: File[] = [];
    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length === 0) return;
    
    e.preventDefault();
    await processFiles(files);
  };

  return {
    pendingUploads,
    setPendingUploads,
    handleFileUpload,
    dropRef,
    removeUpload,
    resetUploads,
    dragOver,
    handlePaste,
  };
}
