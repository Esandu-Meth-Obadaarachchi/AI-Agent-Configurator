"use client";

import {
  ArrowsClockwise,
  CaretDown,
  CheckCircle,
  CircleNotch,
  Code,
  GitFork,
  HandPalm,
  MagnifyingGlass,
  type Icon,
  Robot,
  ShieldCheck,
  Sparkle,
  UsersThree,
  Wrench,
} from "@phosphor-icons/react";
import { useState } from "react";

import type { Step } from "@/lib/types";

const ICONS: Record<string, Icon> = {
  agent: Robot,
  supervisor: UsersThree,
  prompt: Sparkle,
  router: GitFork,
  critic: ArrowsClockwise,
  approval: HandPalm,
  guardrail: ShieldCheck,
  retriever: MagnifyingGlass,
  custom_step: Code,
};

/** What the loop did this turn: each step, its decision and the tools it called. */
export function Activity({
  steps,
  nodes,
  running,
}: {
  steps: Step[];
  nodes: Record<string, { label: string; kind: string }>;
  running: boolean;
}) {
  const [open, setOpen] = useState(false);
  const toolCount = steps.reduce((n, s) => n + s.tools.length, 0);
  const current = [...steps].reverse().find((s) => s.status === "start");
  const summary = running
    ? `${current?.label ?? "Working"}${current?.detail ? `: ${current.detail}` : "…"}`
    : `${steps.length} step${steps.length === 1 ? "" : "s"}${toolCount ? `, ${toolCount} tool call${toolCount === 1 ? "" : "s"}` : ""}`;

  return (
    <div className="enter text-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="inline-flex min-h-9 items-center gap-2 rounded-lg px-2 text-muted transition-colors hover:bg-surface hover:text-ink"
      >
        {running ? (
          <CircleNotch size={16} className="animate-spin text-accent motion-reduce:animate-none" aria-hidden />
        ) : (
          <CheckCircle size={16} className="text-accent" aria-hidden />
        )}
        <span className="max-w-[60ch] truncate">{summary}</span>
        <CaretDown size={12} aria-hidden className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ol className="mt-2 space-y-1.5 border-l border-line pl-4">
          {steps.map((s) => {
            const IconFor = ICONS[nodes[s.node]?.kind ?? ""] ?? Wrench;
            return (
              <li key={s.key} className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <IconFor size={14} className="shrink-0 text-muted" aria-hidden />
                  <span className="font-medium">{s.label || s.node}</span>
                  {s.detail && <span className="truncate text-muted">{s.detail}</span>}
                  {s.status === "start" && running && <CircleNotch size={12} className="animate-spin text-muted motion-reduce:animate-none" aria-label="running" />}
                </div>
                {s.tools.length > 0 && (
                  <ul className="ml-6 flex flex-wrap gap-1.5">
                    {s.tools.map((t, i) => (
                      <li
                        key={`${t.name}-${i}`}
                        title={t.preview}
                        className="rounded-md border border-line bg-surface px-1.5 py-0.5 font-mono text-xs text-muted"
                      >
                        {t.name}
                        {!t.done && "…"}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
