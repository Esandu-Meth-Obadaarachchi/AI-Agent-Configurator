"use client";

import { ThumbsDown, ThumbsUp } from "@phosphor-icons/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ChatMessage } from "@/lib/types";

export function Reply({
  message,
  showLabel,
  feedback,
  onRate,
}: {
  message: ChatMessage;
  showLabel: boolean;
  feedback: boolean;
  onRate: (id: string, score: -1 | 1) => void;
}) {
  if (message.superseded) {
    return (
      <details className="enter rounded-xl border border-dashed border-line px-4 py-2 text-sm text-muted">
        <summary className="cursor-pointer select-none">Earlier draft from {message.label || "the assistant"}</summary>
        <div className="prose-chat mt-2">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      </details>
    );
  }
  return (
    <article className="enter group">
      {showLabel && message.label && (
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">{message.label}</p>
      )}
      <div className={`prose-chat text-[15px] leading-relaxed ${message.streaming ? "caret" : ""}`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
      </div>
      {feedback && (
        <div className="mt-2 flex gap-1 opacity-70 transition-opacity group-hover:opacity-100">
          <button
            type="button"
            aria-label="Good reply"
            aria-pressed={message.score === 1}
            onClick={() => onRate(message.id, 1)}
            className={`grid size-9 place-items-center rounded-lg transition-colors hover:bg-surface ${message.score === 1 ? "text-accent" : "text-muted"}`}
          >
            <ThumbsUp size={16} weight={message.score === 1 ? "fill" : "regular"} />
          </button>
          <button
            type="button"
            aria-label="Bad reply"
            aria-pressed={message.score === -1}
            onClick={() => onRate(message.id, -1)}
            className={`grid size-9 place-items-center rounded-lg transition-colors hover:bg-surface ${message.score === -1 ? "text-danger" : "text-muted"}`}
          >
            <ThumbsDown size={16} weight={message.score === -1 ? "fill" : "regular"} />
          </button>
        </div>
      )}
    </article>
  );
}
