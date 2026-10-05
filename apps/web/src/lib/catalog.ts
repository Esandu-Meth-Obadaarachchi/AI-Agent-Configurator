import raw from "./catalog.json";
import type { Catalog, HandleDef, NodeTypeDef } from "./types";

/** Snapshot of the engine's catalog (scripts/export_catalog.py). Loaded instantly, works offline. */
export const CATALOG = raw as unknown as Catalog;

export const NODE_DEFS: Record<string, NodeTypeDef> = Object.fromEntries(CATALOG.nodes.map((n) => [n.type, n]));

export const CATEGORY_COLOR: Record<string, string> = {
  flow: "var(--cat-flow)",
  agents: "var(--cat-agents)",
  logic: "var(--cat-logic)",
  knowledge: "var(--cat-knowledge)",
  tools: "var(--cat-tools)",
  memory: "var(--cat-memory)",
  safety: "var(--cat-safety)",
};

export function colorFor(type: string): string {
  return CATEGORY_COLOR[NODE_DEFS[type]?.category ?? "flow"];
}

export function isResource(type: string): boolean {
  return NODE_DEFS[type]?.role === "resource";
}

/** Output handles for a node, resolving routers' dynamic branches. */
export function outputsFor(type: string, data: Record<string, unknown>): HandleDef[] {
  const def = NODE_DEFS[type];
  if (!def) return [];
  if (def.outputs === "routes") {
    const routes = (data.routes as { id: string; label?: string }[] | undefined) ?? [];
    return routes.map((r) => ({ id: `route:${r.id}`, kind: "flow", label: r.label || r.id }));
  }
  return def.outputs;
}
