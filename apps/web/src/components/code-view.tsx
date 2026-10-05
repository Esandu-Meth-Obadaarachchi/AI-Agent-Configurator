"use client";

import { Check, Copy, FileCode, FolderSimple, Funnel } from "@phosphor-icons/react";
import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import css from "highlight.js/lib/languages/css";
import dockerfile from "highlight.js/lib/languages/dockerfile";
import ini from "highlight.js/lib/languages/ini";
import json from "highlight.js/lib/languages/json";
import makefile from "highlight.js/lib/languages/makefile";
import markdown from "highlight.js/lib/languages/markdown";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import yaml from "highlight.js/lib/languages/yaml";
import { useEffect, useMemo, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { useStore } from "@/lib/store";
import type { Preview } from "@/lib/types";

import { Button, Toggle } from "./ui";

hljs.registerLanguage("python", python);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("json", json);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("dockerfile", dockerfile);
hljs.registerLanguage("ini", ini);
hljs.registerLanguage("css", css);
hljs.registerLanguage("makefile", makefile);

function languageFor(path: string): string | null {
  const name = path.split("/").pop() ?? "";
  if (name === "Dockerfile") return "dockerfile";
  if (name === "Makefile") return "makefile";
  const ext = name.includes(".") ? name.split(".").pop() : "";
  return (
    { py: "python", ts: "typescript", tsx: "typescript", mjs: "typescript", json: "json", yml: "yaml", yaml: "yaml", md: "markdown", sh: "bash", toml: "ini", css: "css", example: "bash" } as Record<string, string>
  )[ext ?? ""] ?? null;
}

const PREFERRED = ["backend/app/graph.py", "README.md"];

export function CodeView() {
  const revision = useStore((s) => s.revision);
  const selectedId = useStore((s) => s.selectedId);
  const selectedLabel = useStore((s) => String(s.nodes.find((n) => n.id === s.selectedId)?.data.label ?? ""));
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [path, setPath] = useState<string>(PREFERRED[0]);
  const [onlySelected, setOnlySelected] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      try {
        const p = await api.preview(useStore.getState().spec(), ctrl.signal);
        setPreview(p);
        setError(null);
      } catch (err) {
        if ((err as Error).name !== "AbortError") setError(err instanceof ApiError ? err.message : "Preview failed.");
      }
    }, 350);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [revision]);

  const nodeFiles = useMemo(() => (selectedId && preview ? new Set(preview.node_files[selectedId] ?? []) : null), [selectedId, preview]);
  const files = useMemo(() => {
    const all = preview?.files ?? [];
    return nodeFiles && onlySelected ? all.filter((f) => nodeFiles.has(f.path)) : all;
  }, [preview, nodeFiles, onlySelected]);

  const current = files.find((f) => f.path === path) ?? files.find((f) => PREFERRED.includes(f.path)) ?? files[0];

  const html = useMemo(() => {
    if (!current) return "";
    const lang = languageFor(current.path);
    if (current.content.length > 200_000) return escapeHtml(current.content);
    return lang ? hljs.highlight(current.content, { language: lang }).value : escapeHtml(current.content);
  }, [current]);

  const tree = useMemo(() => {
    const groups = new Map<string, typeof files>();
    for (const f of files) {
      const dir = f.path.includes("/") ? f.path.slice(0, f.path.lastIndexOf("/")) : "";
      groups.set(dir, [...(groups.get(dir) ?? []), f]);
    }
    return [...groups.entries()].sort(([a], [b]) => (a === "" ? -1 : b === "" ? 1 : a.localeCompare(b)));
  }, [files]);

  if (error) {
    return <Placeholder title="Preview unavailable" body={error} />;
  }
  if (!preview) {
    return <Placeholder title="Rendering the project…" body="The engine is running your spec through the templates." />;
  }
  if (!preview.ok) {
    const errs = preview.issues.filter((i) => i.level === "error");
    return <Placeholder title="Fix these to see the code" body={errs.map((e) => `• ${e.message}`).join("\n")} />;
  }

  const lines = current ? current.content.split("\n").length : 0;
  const totalKb = (preview.files.reduce((n, f) => n + f.size, 0) / 1024).toFixed(0);

  return (
    <div className="flex size-full min-h-0">
      <nav aria-label="Generated files" className="scroll-thin flex w-[280px] shrink-0 flex-col overflow-y-auto border-r border-line bg-surface">
        <div className="sticky top-0 z-10 space-y-2 border-b border-line bg-surface px-3 py-2.5">
          <p className="text-[12.5px] font-medium">
            {preview.files.length} files <span className="text-muted">· {totalKb} KB · deterministic</span>
          </p>
          {nodeFiles && (
            <div className="flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5 text-[12px] text-muted">
                <Funnel size={13} /> <span className="truncate">Only files for {selectedLabel}</span>
              </span>
              <Toggle checked={onlySelected} onChange={setOnlySelected} label="Only files for the selected block" />
            </div>
          )}
        </div>
        <ul className="py-1.5">
          {tree.map(([dir, items]) => (
            <li key={dir || "root"}>
              {dir && (
                <p className="flex items-center gap-1.5 px-3 pt-2 pb-0.5 font-mono text-[11px] text-faint">
                  <FolderSimple size={12} /> {dir}/
                </p>
              )}
              <ul>
                {items.map((f) => {
                  const active = current?.path === f.path;
                  return (
                    <li key={f.path}>
                      <button
                        type="button"
                        onClick={() => setPath(f.path)}
                        aria-current={active}
                        className={`flex w-full cursor-pointer items-center gap-2 py-1 pr-3 pl-5 text-left font-mono text-[12px] transition-colors ${
                          active ? "bg-accent-soft text-accent-ink" : "text-ink-2 hover:bg-surface-2"
                        }`}
                      >
                        <FileCode size={13} className="shrink-0 opacity-60" />
                        <span className="truncate">{f.path.split("/").pop()}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ul>
      </nav>
      <section className="flex min-w-0 flex-1 flex-col bg-surface-2">
        {current && (
          <>
            <header className="flex h-11 shrink-0 items-center gap-3 border-b border-line bg-surface px-4">
              <p className="truncate font-mono text-[12.5px]">{current.path}</p>
              <span className="shrink-0 rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-[10.5px] text-muted">{current.module}</span>
              <span className="ml-auto shrink-0 font-mono text-[11px] text-faint">{lines} lines</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  void navigator.clipboard.writeText(current.content);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? <Check size={14} className="text-ok" /> : <Copy size={14} />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </header>
            <div className="scroll-thin min-h-0 flex-1 overflow-auto">
              <pre className="flex min-w-max py-3 font-mono text-[12.5px] leading-[1.6]">
                <code aria-hidden className="select-none px-4 text-right text-faint">
                  {Array.from({ length: lines }, (_, i) => i + 1).join("\n")}
                </code>
                <code className="pr-6" dangerouslySetInnerHTML={{ __html: html }} />
              </pre>
            </div>
          </>
        )}
        {!current && <Placeholder title="No files for this block" body="Turn off the filter to see the whole project." />}
      </section>
    </div>
  );
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function Placeholder({ title, body }: { title: string; body: string }) {
  return (
    <div className="grid size-full place-items-center p-8">
      <div className="max-w-md">
        <p className="font-display text-[18px] font-semibold tracking-[-0.01em]">{title}</p>
        <p className="mt-2 whitespace-pre-line text-muted">{body}</p>
      </div>
    </div>
  );
}
