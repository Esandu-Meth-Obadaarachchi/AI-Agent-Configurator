"use client";

import { CaretDown, MagnifyingGlass } from "@phosphor-icons/react";
import { useReactFlow } from "@xyflow/react";
import { type DragEvent, useMemo, useState } from "react";

import { CATALOG, colorFor, NODE_DEFS } from "@/lib/catalog";
import { useStore } from "@/lib/store";
import type { NodeTypeDef } from "@/lib/types";

import { DRAG_MIME } from "./canvas";
import { BlockIcon } from "./icons";
import { Hint, inputClass } from "./ui";

export function Toolkit() {
  const [query, setQuery] = useState("");
  const [closed, setClosed] = useState<Record<string, boolean>>({});
  const addNode = useStore((s) => s.addNode);
  const rf = useReactFlow();

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    return CATALOG.categories
      .map((c) => ({
        ...c,
        items: CATALOG.nodes.filter(
          (n) => n.category === c.id && (!q || `${n.title} ${n.blurb} ${n.explain} ${n.type}`.toLowerCase().includes(q)),
        ),
      }))
      .filter((g) => g.items.length);
  }, [query]);

  const add = (def: NodeTypeDef) => {
    const state = useStore.getState();
    const selected = state.nodes.find((n) => n.id === state.selectedId);
    const canAttach =
      def.role === "resource" && selected && (selected.type === "agent" || (def.type === "knowledge" && selected.type === "retriever"));
    if (canAttach && selected) {
      const siblings = state.edges.filter((e) => e.target === selected.id && e.sourceHandle === "attach").length;
      addNode(def.type, { x: selected.position.x - 10 + siblings * 200, y: selected.position.y + (selected.measured?.height ?? 130) + 90 }, selected.id);
      return;
    }
    const box = document.querySelector(".react-flow")?.getBoundingClientRect();
    const centre = box ? rf.screenToFlowPosition({ x: box.left + box.width / 2, y: box.top + box.height / 2 }) : { x: 0, y: 0 };
    const jitter = (state.nodes.length % 5) * 18;
    addNode(def.type, { x: centre.x - 110 + jitter, y: centre.y - 50 + jitter });
  };

  const onDragStart = (e: DragEvent, type: string) => {
    e.dataTransfer.setData(DRAG_MIME, type);
    e.dataTransfer.effectAllowed = "copy";
  };

  return (
    <aside aria-label="Toolkit" className="flex h-full w-full flex-col">
      <div className="px-3 pt-3 pb-2">
        <label className="relative block">
          <span className="sr-only">Search blocks</span>
          <MagnifyingGlass size={15} className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-faint" aria-hidden />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search blocks"
            className={`${inputClass} h-9 pl-8`}
          />
        </label>
      </div>
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {groups.length === 0 && <p className="px-2 py-6 text-center text-muted">No block matches &ldquo;{query}&rdquo;.</p>}
        {groups.map((g) => {
          const isClosed = closed[g.id] && !query;
          return (
            <section key={g.id} className="mt-1">
              <button
                type="button"
                onClick={() => setClosed((c) => ({ ...c, [g.id]: !c[g.id] }))}
                aria-expanded={!isClosed}
                className="flex w-full cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-surface-2"
              >
                <span className="size-2 rounded-[3px]" style={{ background: `var(--cat-${g.id})` }} aria-hidden />
                <span className="text-[12px] font-semibold tracking-[0.02em] text-ink-2">{g.title}</span>
                <span className="ml-auto font-mono text-[11px] text-faint">{g.items.length}</span>
                <CaretDown size={12} className={`text-faint transition-transform duration-200 ${isClosed ? "-rotate-90" : ""}`} aria-hidden />
              </button>
              {!isClosed && (
                <ul className="mt-0.5 mb-2 space-y-0.5">
                  {g.items.map((def) => (
                    <li key={def.type}>
                      <Hint
                        side="right"
                        label={
                          <span>
                            {def.explain}
                            {def.tradeoff && <span className="mt-1 block opacity-75">Trade-off: {def.tradeoff}</span>}
                          </span>
                        }
                      >
                        <button
                          type="button"
                          draggable
                          onDragStart={(e) => onDragStart(e, def.type)}
                          onClick={() => add(def)}
                          className="group flex w-full cursor-grab items-center gap-2.5 rounded-[10px] px-2 py-1.5 text-left transition-colors hover:bg-surface active:cursor-grabbing"
                        >
                          <span
                            className="grid size-8 shrink-0 place-items-center rounded-[9px] transition-transform duration-150 group-active:scale-95"
                            style={{ background: `color-mix(in srgb, ${colorFor(def.type)} 12%, transparent)`, color: colorFor(def.type) }}
                          >
                            <BlockIcon name={def.icon} size={17} />
                          </span>
                          <span className="min-w-0">
                            <span className="flex items-center gap-1.5 text-[13px] font-medium text-ink">
                              {def.title}
                              {def.ai && (
                                <span className="rounded-[4px] bg-accent-soft px-1 font-mono text-[9.5px] font-semibold tracking-wide text-accent-ink uppercase">
                                  AI
                                </span>
                              )}
                            </span>
                            <span className="block truncate text-[12px] text-muted">{def.blurb}</span>
                          </span>
                        </button>
                      </Hint>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
      <p className="border-t border-line px-4 py-3 text-[12px] leading-snug text-muted">
        Drag blocks onto the canvas. Drop a tool on an agent to attach it.
      </p>
    </aside>
  );
}

export function nodeTitle(type: string): string {
  return NODE_DEFS[type]?.title ?? type;
}
