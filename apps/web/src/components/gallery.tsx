"use client";

import { ArrowRight, Sparkle, X } from "@phosphor-icons/react";
import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { CATALOG, colorFor, isResource } from "@/lib/catalog";
import { emptyProject } from "@/lib/spec";
import { useStore } from "@/lib/store";
import type { Spec } from "@/lib/types";

import { Button } from "./ui";

const EXAMPLES = [
  "A support bot that answers from our help centre and asks a human before issuing refunds",
  "A research team that searches the web, checks the numbers and writes a cited report",
  "Answer questions about our Postgres warehouse in plain English, read-only",
];

/** A to-scale sketch of a blueprint's graph, drawn from its real node positions. */
function MiniGraph({ spec }: { spec: Spec }) {
  const nodes = spec.graph.nodes;
  const size = (t: string) => (isResource(t) ? { w: 168, h: 70 } : { w: 200, h: 92 });
  const xs = nodes.flatMap((n) => [n.position.x, n.position.x + size(n.type).w]);
  const ys = nodes.flatMap((n) => [n.position.y, n.position.y + size(n.type).h]);
  const minX = Math.min(...xs) - 40;
  const minY = Math.min(...ys) - 40;
  const w = Math.max(...xs) - minX + 40;
  const h = Math.max(...ys) - minY + 40;
  const at = Object.fromEntries(nodes.map((n) => [n.id, n]));
  return (
    <svg viewBox={`${minX} ${minY} ${w} ${h}`} className="h-full w-full" aria-hidden preserveAspectRatio="xMidYMid meet">
      {spec.graph.edges.map((e) => {
        const s = at[e.source];
        const t = at[e.target];
        if (!s || !t) return null;
        const attach = e.sourceHandle === "attach";
        const x1 = attach ? s.position.x + size(s.type).w / 2 : s.position.x + size(s.type).w;
        const y1 = attach ? s.position.y : s.position.y + 30;
        const x2 = attach ? t.position.x + size(t.type).w / 2 : t.position.x;
        const y2 = attach ? t.position.y + size(t.type).h : t.position.y + 30;
        const mid = (x1 + x2) / 2;
        const d = attach ? `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}` : `M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`;
        return (
          <path
            key={e.id}
            d={d}
            fill="none"
            stroke={attach ? colorFor(s.type) : "var(--line-strong)"}
            strokeWidth={attach ? 5 : 7}
            strokeDasharray={attach ? "14 12" : undefined}
            opacity={0.9}
          />
        );
      })}
      {nodes.map((n) => {
        const { w: nw, h: nh } = size(n.type);
        return (
          <g key={n.id}>
            <rect x={n.position.x} y={n.position.y} width={nw} height={nh} rx={18} fill="var(--surface)" stroke="var(--line-strong)" strokeWidth={5} />
            <rect x={n.position.x} y={n.position.y + 16} width={9} height={nh - 32} rx={4} fill={colorFor(n.type)} />
            <rect x={n.position.x + 34} y={n.position.y + 24} width={nw * 0.5} height={14} rx={7} fill="var(--line-strong)" />
            <rect x={n.position.x + 34} y={n.position.y + 48} width={nw * 0.32} height={10} rx={5} fill="var(--line)" />
          </g>
        );
      })}
    </svg>
  );
}

export function Gallery({ aiAvailable }: { aiAvailable: boolean }) {
  const open = useStore((s) => s.dialogs.gallery);
  const openDialog = useStore((s) => s.openDialog);
  const loadSpec = useStore((s) => s.loadSpec);
  const notify = useStore((s) => s.notify);
  const hasNodes = useStore((s) => s.nodes.length > 0);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const start = (spec: Spec, message?: string) => {
    loadSpec(structuredClone(spec), { keepHistory: hasNodes });
    openDialog("gallery", false);
    if (message) notify(message, "success");
  };

  const draft = async () => {
    if (description.trim().length < 3) return;
    setBusy(true);
    try {
      const res = await api.textToSpec(description.trim());
      start(res.spec, res.source === "claude" ? `Drafted by Claude: ${res.summary}` : res.summary);
    } catch (err) {
      notify(err instanceof ApiError ? err.message : "Couldn't draft that. Try rephrasing.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => openDialog("gallery", v)}>
      <Dialog.Portal>
        <Dialog.Overlay className="fade-in fixed inset-0 z-40 bg-[rgb(8_12_18/0.45)] backdrop-blur-[2px]" />
        <Dialog.Content
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            document.getElementById("describe")?.focus();
          }}
          className="enter-up fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100dvh-32px)] w-[min(1080px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-[20px] border border-line bg-canvas shadow-[var(--shadow-lg)] focus:outline-none">
          <div className="flex items-start gap-4 border-b border-line bg-surface px-6 pt-5 pb-4">
            <div>
              <Dialog.Title className="font-display text-[24px] font-bold tracking-[-0.025em]">Start a loop</Dialog.Title>
              <Dialog.Description className="mt-1 text-muted">
                Describe what you&apos;re building, or open a blueprint that already runs. Everything stays editable.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button type="button" aria-label="Close" className="ml-auto grid size-9 cursor-pointer place-items-center rounded-[9px] text-muted hover:bg-surface-2 hover:text-ink">
                <X size={18} />
              </button>
            </Dialog.Close>
          </div>

          <div className="scroll-thin overflow-y-auto px-6 py-5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void draft();
              }}
              className="rounded-[16px] border border-line bg-surface p-3 shadow-[var(--shadow-sm)] focus-within:border-accent"
            >
              <label htmlFor="describe" className="flex items-center gap-1.5 px-1 text-[12.5px] font-medium text-ink-2">
                <Sparkle size={14} weight="fill" className="text-accent" /> Describe your app
              </label>
              <textarea
                id="describe"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void draft();
                }}
                rows={2}
                placeholder={EXAMPLES[0]}
                className="mt-1 w-full resize-none bg-transparent px-1 text-[15px] leading-relaxed outline-none placeholder:text-faint"
              />
              <div className="flex flex-wrap items-center gap-2">
                {EXAMPLES.slice(1).map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => setDescription(ex)}
                    className="max-w-[340px] cursor-pointer truncate rounded-full border border-line px-2.5 py-1 text-[12px] text-muted hover:border-line-strong hover:text-ink"
                  >
                    {ex}
                  </button>
                ))}
                <Button type="submit" variant="primary" size="sm" className="ml-auto" disabled={busy || description.trim().length < 3}>
                  {busy ? "Drafting…" : aiAvailable ? "Draft with Claude" : "Find closest blueprint"}
                  <ArrowRight size={14} weight="bold" />
                </Button>
              </div>
              {!aiAvailable && (
                <p className="mt-2 px-1 text-[12px] text-muted">Add an Anthropic key in Settings and Claude will design a custom graph instead.</p>
              )}
            </form>

            <h3 className="mt-6 mb-3 text-[12.5px] font-semibold text-ink-2">Blueprints</h3>
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {CATALOG.blueprints.map((b, i) => (
                <li key={b.id} className="enter-up" style={{ animationDelay: `${i * 35}ms`, animationFillMode: "backwards" }}>
                  <button
                    type="button"
                    onClick={() => start(b.spec)}
                    className="group flex h-full w-full cursor-pointer flex-col overflow-hidden rounded-[16px] border border-line bg-surface text-left shadow-[var(--shadow-sm)] transition-[border-color,box-shadow,transform] duration-200 hover:border-line-strong hover:shadow-[var(--shadow-md)] active:scale-[0.99]"
                  >
                    <div className="h-[132px] border-b border-line bg-canvas p-3 [background-image:radial-gradient(var(--grid)_1px,transparent_1px)] [background-size:14px_14px]">
                      <MiniGraph spec={b.spec} />
                    </div>
                    <div className="flex flex-1 flex-col p-3.5">
                      <div className="flex items-center gap-2">
                        <p className="text-[14px] font-semibold tracking-[-0.01em]">{b.title}</p>
                        <span className="ml-auto font-mono text-[10.5px] text-faint">{b.level}</span>
                      </div>
                      <p className="mt-1 text-[12.5px] leading-snug text-muted">{b.blurb}</p>
                      <p className="mt-auto pt-2.5 font-mono text-[10.5px] text-faint">
                        {b.spec.graph.nodes.length} blocks · {b.tags.join(" · ")}
                      </p>
                    </div>
                  </button>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  onClick={() => start({ ...emptyProject(), graph: { nodes: [], edges: [] } })}
                  className="grid h-full min-h-[200px] w-full cursor-pointer place-items-center rounded-[16px] border border-dashed border-line-strong text-muted transition-colors hover:border-accent hover:text-ink"
                >
                  <span className="text-center">
                    <span className="block text-[14px] font-semibold">Empty canvas</span>
                    <span className="mt-1 block text-[12.5px]">Build from scratch with the toolkit</span>
                  </span>
                </button>
              </li>
            </ul>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
