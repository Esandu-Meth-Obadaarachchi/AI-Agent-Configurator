"use client";

import { CircleNotch, Paperclip, PaperPlaneRight } from "@phosphor-icons/react";
import { useRef, useState } from "react";

import { uploadDocuments } from "@/lib/api";

export function Composer({
  disabled,
  hint,
  knowledge,
  onSend,
}: {
  disabled: boolean;
  hint?: string;
  knowledge: { id: string; label: string }[];
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  };

  const upload = async (files: FileList | null) => {
    if (!files?.length || !knowledge.length) return;
    setUploading(true);
    setStatus(null);
    try {
      const chunks = await uploadDocuments(knowledge[0].id, files);
      setStatus(`Added ${files.length} file${files.length === 1 ? "" : "s"} (${chunks} passages) to ${knowledge[0].label}.`);
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <div className="sticky bottom-0 -mx-4 bg-gradient-to-t from-canvas from-70% to-transparent px-4 pb-4 pt-6">
      {(hint || status) && <p className="mb-2 text-sm text-muted" role="status">{hint ?? status}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-end gap-2 rounded-2xl border border-line bg-surface p-2 shadow-[0_8px_30px_-12px_rgb(0_0_0/0.18)]"
      >
        {knowledge.length > 0 && (
          <>
            <input
              ref={fileInput}
              type="file"
              multiple
              accept=".pdf,.md,.markdown,.txt,.html,.htm"
              className="sr-only"
              aria-label={`Add documents to ${knowledge[0].label}`}
              onChange={(e) => void upload(e.target.files)}
            />
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              disabled={uploading}
              aria-label={`Add documents to ${knowledge[0].label}`}
              className="grid size-10 shrink-0 place-items-center rounded-xl text-muted transition-colors hover:bg-canvas hover:text-ink disabled:opacity-50"
            >
              {uploading ? <CircleNotch size={18} className="animate-spin" /> : <Paperclip size={18} />}
            </button>
          </>
        )}
        <label htmlFor="message" className="sr-only">
          Message
        </label>
        <textarea
          id="message"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          rows={Math.min(8, Math.max(1, text.split("\n").length))}
          placeholder="Message"
          className="max-h-60 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-[15px] leading-relaxed outline-none placeholder:text-muted"
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          aria-label="Send"
          className="grid size-10 shrink-0 place-items-center rounded-xl bg-accent text-white transition-[transform,opacity] active:scale-95 disabled:opacity-40"
        >
          <PaperPlaneRight size={18} weight="fill" />
        </button>
      </form>
    </div>
  );
}
