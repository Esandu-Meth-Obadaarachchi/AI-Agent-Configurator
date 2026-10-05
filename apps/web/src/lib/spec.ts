import { CATALOG, NODE_DEFS } from "./catalog";
import type { BlockNode, FlowEdge, ProjectSettings, Spec, SpecEdge } from "./types";

export const ID_PATTERN = /^[a-z][a-z0-9_]{0,39}$/;

export function edgeKind(sourceHandle: string | null | undefined): "flow" | "attach" {
  return sourceHandle === "attach" ? "attach" : "flow";
}

export function specToGraph(spec: Spec): { nodes: BlockNode[]; edges: FlowEdge[]; project: ProjectSettings } {
  const { graph, ...project } = spec;
  const nodes: BlockNode[] = graph.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    position: { ...n.position },
    data: { ...n.data },
  }));
  const edges: FlowEdge[] = graph.edges.map((e) => toFlowEdge(e));
  return { nodes, edges, project: structuredClone(project) };
}

export function toFlowEdge(e: SpecEdge): FlowEdge {
  return {
    id: e.id,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle ?? null,
    targetHandle: e.targetHandle ?? null,
    type: edgeKind(e.sourceHandle),
  };
}

export function graphToSpec(nodes: BlockNode[], edges: FlowEdge[], project: ProjectSettings): Spec {
  return {
    ...project,
    graph: {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.type ?? "agent",
        position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
        data: stripEmpty(n.data),
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle ?? null,
        targetHandle: e.targetHandle ?? null,
      })),
    },
  };
}

/** Drop UI-only keys and turn "" into null for nullable fields so the schema accepts them. */
function stripEmpty(data: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(data)) {
    if (k.startsWith("_")) continue;
    out[k] = v === "" && (k === "model" || k === "effort" || k === "temperature" || k === "top_k" || k === "auth_env") ? null : v;
  }
  return out;
}

export function nextId(type: string, taken: Set<string>): string {
  const base = type.replace(/[^a-z0-9_]/g, "_");
  if (!taken.has(base)) return base;
  for (let i = 2; ; i += 1) {
    const id = `${base}_${i}`;
    if (!taken.has(id)) return id;
  }
}

export function defaultData(type: string): Record<string, unknown> {
  return structuredClone(CATALOG.defaults[type] ?? { label: NODE_DEFS[type]?.title ?? type });
}

export function emptyProject(): ProjectSettings {
  const { graph: _graph, ...rest } = structuredClone(CATALOG.spec_defaults);
  void _graph;
  return rest;
}

export function slugify(text: string): string {
  const s = text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return /^[a-z]/.test(s) ? s : `app-${s}`.slice(0, 48);
}
