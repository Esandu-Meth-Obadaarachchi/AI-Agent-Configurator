"use client";

import { HandPalm } from "@phosphor-icons/react";
import { useId, useState } from "react";

import type { Pending } from "@/lib/types";

/** A paused run waiting for a person. Approve (optionally after editing) or reject with a note. */
export function ApprovalCard({
  pending,
  onDecide,
}: {
  pending: Pending;
  onDecide: (d: { approved: boolean; edited?: string; feedback?: string }) => void;
}) {
  const [text, setText] = useState(pending.content);
  const [note, setNote] = useState("");
  const editId = useId();
  const noteId = useId();

  return (
    <section aria-label="Approval needed" className="enter rounded-2xl border border-warn/40 bg-warn-soft p-4">
      <header className="flex items-center gap-2 text-sm font-medium">
        <HandPalm size={18} className="text-warn" aria-hidden />
        {pending.label}: {pending.prompt}
      </header>
      {pending.allow_edit ? (
        <div className="mt-3">
          <label htmlFor={editId} className="text-xs font-medium text-muted">
            Reply to send (you can edit it)
          </label>
          <textarea
            id={editId}
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={Math.min(14, Math.max(4, text.split("\n").length + 1))}
            className="mt-1 w-full resize-y rounded-xl border border-line bg-surface p-3 text-[15px] leading-relaxed"
          />
        </div>
      ) : (
        <div className="mt-3 whitespace-pre-wrap rounded-xl border border-line bg-surface p-3 text-[15px]">{pending.content}</div>
      )}
      <div className="mt-3">
        <label htmlFor={noteId} className="text-xs font-medium text-muted">
          Note if rejecting (optional)
        </label>
        <input
          id={noteId}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="What should change?"
          className="mt-1 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm"
        />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onDecide({ approved: true, edited: text !== pending.content ? text : undefined })}
          className="h-10 rounded-lg bg-accent px-4 text-sm font-medium text-white transition-transform active:scale-[0.98]"
        >
          Approve and send
        </button>
        <button
          type="button"
          onClick={() => onDecide({ approved: false, feedback: note || undefined })}
          className="h-10 rounded-lg border border-line bg-surface px-4 text-sm font-medium transition-transform active:scale-[0.98]"
        >
          Reject
        </button>
      </div>
    </section>
  );
}
