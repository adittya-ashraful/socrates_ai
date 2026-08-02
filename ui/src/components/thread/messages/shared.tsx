import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Copy, CopyCheck } from "lucide-react";
import { TooltipIconButton } from "../tooltip-icon-button";

function ContentCopyable({
  content,
  disabled,
}: {
  content: string;
  disabled: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e.stopPropagation();
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <TooltipIconButton
      onClick={(e) => handleCopy(e)}
      variant="ghost"
      tooltip="Copy content"
      disabled={disabled}
    >
      <AnimatePresence
        mode="wait"
        initial={false}
      >
        {copied ? (
          <motion.div
            key="check"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
          >
            <CopyCheck className="text-green-500 size-4" />
          </motion.div>
        ) : (
          <motion.div
            key="copy"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
          >
            <Copy className="size-4" />
          </motion.div>
        )}
      </AnimatePresence>
    </TooltipIconButton>
  );
}

export function CommandBar({
  content,
  isHumanMessage,
  isAiMessage,
  isLoading,
}: {
  content: string;
  isHumanMessage?: boolean;
  isAiMessage?: boolean;
  isLoading: boolean;
}) {
  if (isHumanMessage && isAiMessage) {
    throw new Error(
      "Can only set one of isHumanMessage or isAiMessage to true, not both.",
    );
  }

  if (!isHumanMessage && !isAiMessage) {
    throw new Error(
      "One of isHumanMessage or isAiMessage must be set to true.",
    );
  }

  return (
    <div className="flex items-center gap-1 h-6">
      <ContentCopyable
        content={content}
        disabled={isLoading}
      />
    </div>
  );
}
