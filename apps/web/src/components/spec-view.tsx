"use client";

import { Check, Copy, DownloadSimple, UploadSimple } from "@phosphor-icons/react";
import hljs from "highlight.js/lib/core";
import json from "highlight.js/lib/languages/json";
import { useMemo, useRef, useState } from "react";

import { api, ApiError, download } from "@/lib/api";
import { graphToSpec } from "@/lib/spec";
import { useStore } from "@/lib/store";

import { Button } from "./ui";

hljs.registerLanguage("json", json);

/** The spec as JSON: the single source of truth the canvas edits. */
export function SpecView() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const project = useStore((s) => s.project);
  const loadSpec = useStore((s) => s.loadSpec);
  const notify = useStore((s) => s.notify);
  const fileInput = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);

  const text = useMemo(() => JSON.stringify(graphToSpec(nodes, edges, project), null, 2), [nodes, edges, project]);
  const html = useMemo(() => hljs.highlight(text, { language: "json" }).value, [text]);

  const importFile = async (file: File | undefined) => {
    if (!file) return;
    try {
      const raw = JSON.parse(await file.text());
      const spec = await api.importSpec(raw);
      loadSpec(spec, { keepHistory: true });
      notify(`Imported ${file.name}.`, "success");
    } catch (err) {
      notify(err instanceof ApiError ? err.message : `Couldn't read ${file.name}: ${(err as Error).message}`, "error");
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <div className="flex size-full min-h-0 flex-col bg-surface-2">
      <header className="flex h-11 shrink-0 items-center gap-2 border-b border-line bg-surface px-4">
        <p className="font-mono text-[12.5px]">spec.json</p>
        <span className="text-[12px] text-muted">· v{project.spec_version} · the canvas and this file are the same thing</span>
        <div className="ml-auto flex gap-1">
          <input ref={fileInput} type="file" accept="application/json,.json" className="sr-only" aria-label="Import a spec file" onChange={(e) => void importFile(e.target.files?.[0])} />
          <Button size="sm" variant="ghost" onClick={() => fileInput.current?.click()}>
            <UploadSimple size={14} /> Import
          </Button>
          <Button size="sm" variant="ghost" onClick={() => download(new Blob([text + "\n"], { type: "application/json" }), "spec.json")}>
            <DownloadSimple size={14} /> Download
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              void navigator.clipboard.writeText(text);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
          >
            {copied ? <Check size={14} className="text-ok" /> : <Copy size={14} />} {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </header>
      <div className="scroll-thin min-h-0 flex-1 overflow-auto">
        <pre className="p-4 font-mono text-[12.5px] leading-[1.6]">
          <code dangerouslySetInnerHTML={{ __html: html }} />
        </pre>
      </div>
      <p className="border-t border-line bg-surface px-4 py-2.5 text-[12px] text-muted">
        Use it from the terminal: <code className="font-mono text-ink-2">configurator generate spec.json -o ./{project.project.name}</code>
      </p>
    </div>
  );
}
