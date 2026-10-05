"use client";

import { WarningCircle, XCircle } from "@phosphor-icons/react";
import { Handle, type NodeProps, Position, useUpdateNodeInternals } from "@xyflow/react";
import { memo, useEffect, useMemo } from "react";
import { useShallow } from "zustand/react/shallow";

import { colorFor, NODE_DEFS, outputsFor } from "@/lib/catalog";
import { useStore } from "@/lib/store";
import type { BlockNode as BlockNodeType, NodeData } from "@/lib/types";

import { BlockIcon } from "./icons";
import { Hint } from "./ui";

function summary(type: string, d: NodeData, defaultModel: string, workers: number): string {
  const model = (d.model as string) || defaultModel;
  switch (type) {
    case "input":
      return String(d.greeting ?? "");
    case "agent":
      return String(d.role ?? "");
    case "prompt":
      return String(d.instructions ?? "");
    case "supervisor":
      return `${workers} worker${workers === 1 ? "" : "s"} · up to ${d.max_rounds} rounds`;
    case "router":
      return `${(d.routes as unknown[])?.length ?? 0} branches · decides by ${d.mode === "keywords" ? "keywords" : "model"}`;
    case "critic":
      return `Up to ${d.max_iterations} revision${d.max_iterations === 1 ? "" : "s"}`;
    case "approval":
      return String(d.prompt ?? "");
    case "guardrail": {
      const checks = [d.redact_pii && "PII", d.block_prompt_injection && "injection", (d.blocked_terms as string[])?.length && "terms"].filter(Boolean);
      return checks.length ? `Checks ${checks.join(", ")}` : "Length check only";
    }
    case "retriever":
      return d.top_k ? `Top ${d.top_k} passages` : "Knowledge base defaults";
    case "custom_step":
      return d.code ? "Code ready" : "Needs code";
    case "knowledge":
      return `${d.vector_store === "pgvector" ? "pgvector" : "Chroma"} · ${d.retrieval === "hybrid" ? "hybrid" : "vector"}${d.reranker !== "none" ? " · rerank" : ""}`;
    case "memory":
      return `${String(d.short_term)}${d.long_term ? " · long-term" : ""}`;
    case "http_api":
      return `${d.method} ${d.path}`;
    case "mcp_server":
      return `${d.server_name} · ${d.transport === "stdio" ? "local" : String(d.transport)}`;
    case "sql_database":
      return `${d.dialect}${d.read_only ? " · read-only" : ""}`;
    case "custom_tool":
      return d.code ? `${d.tool_name}() · code ready` : `${d.tool_name}() · needs code`;
    case "web_search":
      return `Tavily · ${d.max_results} results`;
    default:
      return model && ["prompt", "supervisor"].includes(type) ? model : "";
  }
}

function BlockNodeImpl({ id, type, data, selected }: NodeProps<BlockNodeType>) {
  const def = NODE_DEFS[type];
  const updateInternals = useUpdateNodeInternals();
  // Select primitives only: fresh arrays from a selector would re-render forever.
  const { issueKey, tracing, toolCount, workers, defaultModel } = useStore(
    useShallow((s) => ({
      issueKey: (s.analysis?.issues ?? [])
        .filter((i) => i.node_id === id && i.level !== "info")
        .map((i) => `${i.level}\u0000${i.message}`)
        .join("\u0001"),
      tracing: s.trace.step >= 0 && (s.analysis?.trace[s.trace.step]?.nodes.includes(id) ?? false),
      toolCount: s.edges.filter((e) => e.target === id && e.sourceHandle === "attach").length,
      workers: s.edges.filter((e) => e.source === id && e.sourceHandle === "delegate").length,
      defaultModel: s.project.llm.model,
    })),
  );
  const issues = useMemo(
    () => (issueKey ? issueKey.split("\u0001").map((x) => ({ level: x.split("\u0000")[0], message: x.split("\u0000")[1] })) : []),
    [issueKey],
  );
  const outputs = useMemo(() => outputsFor(type, data), [type, data]);
  const routeKey = outputs.map((o) => o.id).join("|");

  // Router branches change the node's handles; tell React Flow to re-measure.
  useEffect(() => {
    updateInternals(id);
  }, [id, routeKey, updateInternals]);

  if (!def) return null;
  const color = colorFor(type);
  const resource = def.role === "resource";
  const errors = issues.filter((i) => i.level === "error");
  const branching = !resource && (outputs.length > 1 || (outputs.length === 1 && outputs[0].id !== "out"));
  const text = summary(type, data, defaultModel, workers);
  const accepts = def.accepts ?? [];
  const attachHandle = accepts.includes("tool") ? "tools" : accepts.includes("knowledge") ? "knowledge" : null;

  return (
    <div
      className={`group relative rounded-[14px] border bg-surface text-left transition-[border-color,box-shadow] duration-150 ${
        resource ? "w-[168px]" : "w-[200px]"
      } ${selected ? "border-accent shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_20%,transparent),var(--shadow-md)]" : "border-line shadow-[var(--shadow-sm)] hover:border-line-strong hover:shadow-[var(--shadow-md)]"} ${
        tracing ? "tracing" : ""
      }`}
      style={{ ["--cat" as string]: color }}
    >
      {/* Category tab: the module's colour, like the label strip on a patch-bay module. */}
      <span aria-hidden className="absolute top-3 bottom-3 left-0 w-[3px] rounded-r-full" style={{ background: color }} />

      {def.inputs.length > 0 && (
        <Handle type="target" position={Position.Left} id="in" className="!-left-[7px]" style={{ top: 30 }} aria-label="Input" />
      )}
      {resource && (
        <Handle
          type="source"
          position={Position.Top}
          id="attach"
          className="!-top-[7px] !rounded-[4px]"
          style={{ background: color, borderColor: color }}
          aria-label="Attach to an agent"
        />
      )}

      <div className="flex items-start gap-2.5 px-3.5 pt-3 pb-2.5">
        <span
          className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-[8px]"
          style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}
        >
          <BlockIcon name={def.icon} size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <p className="truncate text-[13.5px] font-semibold tracking-[-0.01em] text-ink">{String(data.label || def.title)}</p>
            {issues.length > 0 && (
              <Hint label={issues.map((i) => i.message).join(" ")} side="top">
                <span
                  className={`ml-auto inline-flex shrink-0 items-center gap-0.5 rounded-full px-1.5 text-[11px] font-semibold ${errors.length ? "bg-error-soft text-error" : "bg-warn-soft text-warn"}`}
                >
                  {errors.length ? <XCircle size={12} weight="fill" /> : <WarningCircle size={12} weight="fill" />}
                  {issues.length}
                </span>
              </Hint>
            )}
          </div>
          <p className="truncate font-mono text-[11px] text-faint">
            {def.title}
            {["agent", "prompt", "supervisor", "router", "critic"].includes(type) && (
              <span> · {(data.model as string) || defaultModel}</span>
            )}
          </p>
          {text && <p className="mt-1 line-clamp-2 text-[12px] leading-[1.35] text-muted">{text}</p>}
        </div>
      </div>

      {/* Outputs. A plain step has one port on the right; branching steps label each branch. */}
      {!resource && !branching && outputs.length === 1 && (
        <Handle type="source" position={Position.Right} id="out" className="!-right-[7px]" style={{ top: 30 }} aria-label="Output" />
      )}
      {branching && (
        <div className="border-t border-line pt-1 pb-1.5">
          {outputs.map((o) => (
            <div key={o.id} className="relative flex h-6 items-center justify-end pr-4 text-[11.5px] font-medium text-muted">
              <span className="truncate">{o.label}</span>
              <Handle
                type="source"
                position={Position.Right}
                id={o.id}
                className="!-right-[7px]"
                style={{ top: "50%" }}
                aria-label={`${o.label} branch`}
              />
            </div>
          ))}
        </div>
      )}

      {attachHandle && (
        <div className="relative flex justify-center border-t border-dashed border-line py-1.5">
          <span className="inline-flex items-center gap-1 font-mono text-[10.5px] uppercase tracking-[0.06em] text-faint">
            {attachHandle === "tools" ? "Tools" : "Knowledge"}
            {toolCount > 0 && <span className="text-muted">· {toolCount}</span>}
          </span>
          <Handle
            type="target"
            position={Position.Bottom}
            id={attachHandle}
            className="!-bottom-[7px] !rounded-[4px] !border-dashed"
            aria-label={attachHandle === "tools" ? "Attach tools here" : "Attach a knowledge base here"}
          />
        </div>
      )}
    </div>
  );
}

export const BlockNode = memo(BlockNodeImpl);
