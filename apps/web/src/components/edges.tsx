"use client";

import { ArrowsClockwise, X } from "@phosphor-icons/react";
import { BaseEdge, EdgeLabelRenderer, type EdgeProps, getBezierPath, useReactFlow } from "@xyflow/react";
import { memo } from "react";

import { colorFor, NODE_DEFS } from "@/lib/catalog";
import { useStore } from "@/lib/store";

function usePulse(id: string, source: string, target: string, kind: "flow" | "attach"): boolean {
  return useStore((s) => {
    if (s.trace.step < 0) return false;
    const step = s.analysis?.trace[s.trace.step];
    if (!step) return false;
    if (kind === "attach") return step.nodes.includes(target);
    return step.edges.includes(id);
  });
}

function DeleteButton({ id, x, y }: { id: string; x: number; y: number }) {
  const { deleteElements } = useReactFlow();
  return (
    <EdgeLabelRenderer>
      <button
        type="button"
        aria-label="Remove connection"
        onClick={() => void deleteElements({ edges: [{ id }] })}
        className="nodrag nopan pointer-events-auto absolute grid size-6 cursor-pointer place-items-center rounded-full border border-line bg-surface text-muted shadow-[var(--shadow-sm)] transition-colors hover:border-error hover:text-error"
        style={{ transform: `translate(-50%, -50%) translate(${x}px, ${y}px)` }}
      >
        <X size={12} weight="bold" />
      </button>
    </EdgeLabelRenderer>
  );
}

/**
 * A loop (an edge that goes back to an earlier step) runs in a lane under the blocks
 * instead of a curve tangled behind them, so every loop on the canvas reads at a glance.
 */
function loopPath(sx: number, sy: number, tx: number, ty: number, floor: number): [string, number, number] {
  const lane = Math.max(sy + 40, ty + 40, floor);
  const r = 12;
  const out = sx + 22;
  const back = tx - 22;
  const d = [
    `M ${sx} ${sy}`,
    `H ${out - r}`,
    `Q ${out} ${sy} ${out} ${sy + r}`,
    `V ${lane - r}`,
    `Q ${out} ${lane} ${out - r} ${lane}`,
    `H ${back + r}`,
    `Q ${back} ${lane} ${back} ${lane - r}`,
    `V ${ty + r}`,
    `Q ${back} ${ty} ${back + r} ${ty}`,
    `H ${tx}`,
  ].join(" ");
  return [d, (out + back) / 2, lane];
}

function FlowEdgeImpl(props: EdgeProps) {
  const { id, source, target, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected, sourceHandleId } = props;
  const isLoop = targetX < sourceX - 30 && sourceHandleId !== "delegate";
  // Run the lane under the lowest step it passes, staggered so parallel loops don't overlap.
  const floor = useStore((s) => {
    if (!isLoop) return 0;
    let lowest = 0;
    for (const n of s.nodes) {
      if (NODE_DEFS[n.type ?? ""]?.role !== "flow") continue;
      const w = n.measured?.width ?? 200;
      if (n.position.x + w >= targetX - 30 && n.position.x <= sourceX + 30) {
        lowest = Math.max(lowest, n.position.y + (n.measured?.height ?? 110));
      }
    }
    return lowest;
  });
  const stagger = isLoop ? 28 + (Array.from(id).reduce((h, c) => h + c.charCodeAt(0), 0) % 3) * 14 : 0;
  const [path, labelX, labelY] = isLoop
    ? loopPath(sourceX, sourceY, targetX, targetY, floor + stagger)
    : getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.35 });
  const pulsing = usePulse(id, source, target, "flow");
  const delegate = sourceHandleId === "delegate";
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        className={pulsing ? "trace-edge" : ""}
        markerEnd={pulsing ? "url(#cfg-arrow-accent)" : "url(#cfg-arrow)"}
        markerStart={delegate ? (pulsing ? "url(#cfg-arrow-accent-start)" : "url(#cfg-arrow-start)") : undefined}
        style={delegate ? { strokeDasharray: "6 4" } : undefined}
      />
      {pulsing && (
        <circle r="4.5" fill="var(--accent)" className="motion-reduce:hidden">
          <animateMotion dur="0.9s" repeatCount="indefinite" path={path} />
        </circle>
      )}
      {isLoop && !selected && (
        <EdgeLabelRenderer>
          <span
            aria-hidden
            className={`absolute grid size-5 place-items-center rounded-full border bg-surface ${pulsing ? "border-accent text-accent" : "border-line-strong text-muted"}`}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            <ArrowsClockwise size={11} weight="bold" />
          </span>
        </EdgeLabelRenderer>
      )}
      {selected && <DeleteButton id={id} x={labelX} y={labelY} />}
    </>
  );
}

function AttachEdgeImpl(props: EdgeProps) {
  const { id, source, target, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected } = props;
  const type = useStore((s) => s.nodes.find((n) => n.id === source)?.type ?? "web_search");
  const [path, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.3 });
  const pulsing = usePulse(id, source, target, "attach");
  const color = colorFor(type);
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        style={{ stroke: pulsing ? "var(--accent)" : color, strokeDasharray: "4 4", strokeWidth: pulsing ? 2.25 : 1.5, opacity: pulsing ? 1 : 0.75 }}
      />
      {selected && <DeleteButton id={id} x={labelX} y={labelY} />}
    </>
  );
}

export const EDGE_TYPES = { flow: memo(FlowEdgeImpl), attach: memo(AttachEdgeImpl) };

/** Arrowheads shared by every edge. */
export function EdgeMarkers() {
  return (
    <svg aria-hidden className="absolute size-0">
      <defs>
        {[
          ["cfg-arrow", "var(--line-strong)", "auto"],
          ["cfg-arrow-accent", "var(--accent)", "auto"],
          ["cfg-arrow-start", "var(--line-strong)", "auto-start-reverse"],
          ["cfg-arrow-accent-start", "var(--accent)", "auto-start-reverse"],
        ].map(([markerId, fill, orient]) => (
          <marker key={markerId} id={markerId} viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient={orient}>
            <path d="M 0 0 L 10 5 L 0 10 z" fill={fill} />
          </marker>
        ))}
      </defs>
    </svg>
  );
}
