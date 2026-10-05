"use client";

import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type EdgeChange,
  type NodeChange,
} from "@xyflow/react";
import { create } from "zustand";

import { NODE_DEFS } from "./catalog";
import { connectionProblem } from "./connect";
import { defaultData, edgeKind, emptyProject, graphToSpec, ID_PATTERN, nextId, specToGraph } from "./spec";
import type { Analysis, BlockNode, FlowEdge, ProjectSettings, Spec } from "./types";

type View = "canvas" | "code" | "spec";

interface Snapshot {
  nodes: BlockNode[];
  edges: FlowEdge[];
  project: ProjectSettings;
}

interface Toast {
  id: number;
  text: string;
  tone: "info" | "error" | "success";
}

interface State {
  nodes: BlockNode[];
  edges: FlowEdge[];
  project: ProjectSettings;
  selectedId: string | null;
  view: View;
  past: Snapshot[];
  future: Snapshot[];
  revision: number;
  analysis: Analysis | null;
  engineOnline: boolean;
  trace: { playing: boolean; step: number };
  dialogs: { gallery: boolean; palette: boolean; settings: boolean; shortcuts: boolean };
  toast: Toast | null;
  fitRequest: number;

  onNodesChange: (changes: NodeChange<BlockNode>[]) => void;
  onEdgesChange: (changes: EdgeChange<FlowEdge>[]) => void;
  onConnect: (c: Connection) => void;
  addNode: (type: string, position?: { x: number; y: number }, attachTo?: string) => string | null;
  updateData: (id: string, patch: Record<string, unknown>) => void;
  renameNode: (id: string, newId: string) => string | null;
  duplicateNode: (id: string) => void;
  removeNode: (id: string) => void;
  setProject: (path: string, value: unknown) => void;
  loadSpec: (spec: Spec, opts?: { keepHistory?: boolean }) => void;
  select: (id: string | null) => void;
  syncSelection: (id: string | null) => void;
  setView: (view: View) => void;
  undo: () => void;
  redo: () => void;
  setAnalysis: (a: Analysis | null, online: boolean) => void;
  playTrace: () => void;
  stopTrace: () => void;
  stepTrace: (step: number) => void;
  openDialog: (name: keyof State["dialogs"], open: boolean) => void;
  notify: (text: string, tone?: Toast["tone"]) => void;
  spec: () => Spec;
}

const HISTORY_LIMIT = 100;
let lastDataCommit = { id: "", at: 0 };
let toastId = 0;

function snapshot(s: State): Snapshot {
  return { nodes: s.nodes, edges: s.edges, project: s.project };
}

function pushHistory(s: State): Partial<State> {
  return { past: [...s.past.slice(-HISTORY_LIMIT + 1), snapshot(s)], future: [], revision: s.revision + 1 };
}

function setIn(obj: Record<string, unknown>, path: string, value: unknown): Record<string, unknown> {
  const [head, ...rest] = path.split(".");
  if (!rest.length) return { ...obj, [head]: value };
  return { ...obj, [head]: setIn((obj[head] as Record<string, unknown>) ?? {}, rest.join("."), value) };
}

export const useStore = create<State>((set, get) => ({
  nodes: [],
  edges: [],
  project: emptyProject(),
  selectedId: null,
  view: "canvas",
  past: [],
  future: [],
  revision: 0,
  analysis: null,
  engineOnline: true,
  trace: { playing: false, step: -1 },
  dialogs: { gallery: false, palette: false, settings: false, shortcuts: false },
  toast: null,
  fitRequest: 0,

  onNodesChange: (changes) => {
    const s = get();
    const structural = changes.some((c) => c.type === "remove" || (c.type === "position" && c.dragging === false));
    const removed = new Set(changes.filter((c) => c.type === "remove").map((c) => c.id));
    const nodes = applyNodeChanges(changes, s.nodes);
    const edges = removed.size ? s.edges.filter((e) => !removed.has(e.source) && !removed.has(e.target)) : s.edges;
    const selectedId = removed.has(s.selectedId ?? "") ? null : s.selectedId;
    set({ nodes, edges, selectedId, ...(structural ? pushHistory(s) : {}) });
  },

  onEdgesChange: (changes) => {
    const s = get();
    const structural = changes.some((c) => c.type === "remove");
    set({ edges: applyEdgeChanges(changes, s.edges), ...(structural ? pushHistory(s) : {}) });
  },

  onConnect: (c) => {
    const s = get();
    const typeOf = (id: string) => s.nodes.find((n) => n.id === id)?.type;
    const problem = connectionProblem(c, typeOf);
    if (problem) {
      get().notify(problem, "error");
      return;
    }
    const exists = s.edges.some(
      (e) => e.source === c.source && e.target === c.target && e.sourceHandle === c.sourceHandle && e.targetHandle === c.targetHandle,
    );
    if (exists) return;
    const id = `e-${c.source}-${c.sourceHandle ?? "out"}-${c.target}`;
    const edge: FlowEdge = { ...c, id, type: edgeKind(c.sourceHandle) } as FlowEdge;
    set({ edges: addEdge(edge, s.edges), ...pushHistory(s) });
  },

  addNode: (type, position, attachTo) => {
    const s = get();
    const def = NODE_DEFS[type];
    if (!def) return null;
    if (def.max && s.nodes.filter((n) => n.type === type).length >= def.max) {
      get().notify(`Only ${def.max} ${def.title} block allowed.`, "error");
      return null;
    }
    const id = nextId(type, new Set(s.nodes.map((n) => n.id)));
    const node: BlockNode = {
      id,
      type,
      position: position ?? { x: 200 + s.nodes.length * 24, y: 120 + s.nodes.length * 24 },
      data: defaultData(type),
      selected: true,
    };
    let edges = s.edges;
    if (attachTo) {
      const target = s.nodes.find((n) => n.id === attachTo);
      const handle = def.role === "resource" ? (target?.type === "retriever" ? "knowledge" : "tools") : null;
      if (handle && !connectionProblem({ source: id, target: attachTo, sourceHandle: "attach", targetHandle: handle }, (x) => (x === id ? type : s.nodes.find((n) => n.id === x)?.type))) {
        edges = [...edges, { id: `a-${id}-${attachTo}`, source: id, target: attachTo, sourceHandle: "attach", targetHandle: handle, type: "attach" }];
      }
    }
    set({
      nodes: [...s.nodes.map((n) => (n.selected ? { ...n, selected: false } : n)), node],
      edges,
      selectedId: id,
      ...pushHistory(s),
    });
    return id;
  },

  updateData: (id, patch) => {
    const s = get();
    const now = Date.now();
    // Typing in a field is one undo step per pause, not one per keystroke.
    const commit = lastDataCommit.id !== id || now - lastDataCommit.at > 800;
    lastDataCommit = { id, at: now };
    const nodes = s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n));
    set({ nodes, ...(commit ? pushHistory(s) : { revision: s.revision + 1 }) });
  },

  renameNode: (id, newId) => {
    const s = get();
    if (id === newId) return null;
    if (!ID_PATTERN.test(newId)) return "Use lower case letters, numbers and underscores, starting with a letter.";
    if (s.nodes.some((n) => n.id === newId)) return `'${newId}' is already used.`;
    const nodes = s.nodes.map((n) => (n.id === id ? { ...n, id: newId } : n));
    const edges = s.edges.map((e) => ({
      ...e,
      source: e.source === id ? newId : e.source,
      target: e.target === id ? newId : e.target,
    }));
    set({ nodes, edges, selectedId: newId, ...pushHistory(s) });
    return null;
  },

  duplicateNode: (id) => {
    const s = get();
    const src = s.nodes.find((n) => n.id === id);
    if (!src?.type) return;
    const newId = get().addNode(src.type, { x: src.position.x + 40, y: src.position.y + 40 });
    if (newId) {
      const data = structuredClone(src.data);
      data.label = `${String(src.data.label ?? "")} copy`.trim();
      set({ nodes: get().nodes.map((n) => (n.id === newId ? { ...n, data } : n)) });
    }
  },

  removeNode: (id) => {
    const s = get();
    set({
      nodes: s.nodes.filter((n) => n.id !== id),
      edges: s.edges.filter((e) => e.source !== id && e.target !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
      ...pushHistory(s),
    });
  },

  setProject: (path, value) => {
    const s = get();
    set({ project: setIn(s.project as unknown as Record<string, unknown>, path, value) as unknown as ProjectSettings, ...pushHistory(s) });
  },

  loadSpec: (spec, opts) => {
    const s = get();
    const { nodes, edges, project } = specToGraph(spec);
    set({
      nodes,
      edges,
      project,
      selectedId: null,
      trace: { playing: false, step: -1 },
      fitRequest: s.fitRequest + 1,
      ...(opts?.keepHistory ? pushHistory(s) : { past: [], future: [], revision: s.revision + 1 }),
    });
  },

  select: (id) => {
    const s = get();
    // Keep React Flow's own selection flags in step (only when they differ, to avoid loops).
    const mismatch = s.nodes.some((n) => Boolean(n.selected) !== (n.id === id));
    set({ selectedId: id, ...(mismatch ? { nodes: s.nodes.map((n) => ({ ...n, selected: n.id === id })) } : {}) });
  },
  syncSelection: (id) => set({ selectedId: id }),
  setView: (view) => set({ view }),

  undo: () => {
    const s = get();
    const prev = s.past[s.past.length - 1];
    if (!prev) return;
    set({ ...prev, past: s.past.slice(0, -1), future: [snapshot(s), ...s.future], revision: s.revision + 1 });
  },

  redo: () => {
    const s = get();
    const next = s.future[0];
    if (!next) return;
    set({ ...next, past: [...s.past, snapshot(s)], future: s.future.slice(1), revision: s.revision + 1 });
  },

  setAnalysis: (analysis, engineOnline) => set({ analysis, engineOnline }),
  playTrace: () => set({ trace: { playing: true, step: 0 }, view: "canvas" }),
  stopTrace: () => set({ trace: { playing: false, step: -1 } }),
  stepTrace: (step) => set((s) => ({ trace: { ...s.trace, step } })),
  openDialog: (name, open) => set((s) => ({ dialogs: { ...s.dialogs, [name]: open } })),
  notify: (text, tone = "info") => {
    toastId += 1;
    const id = toastId;
    set({ toast: { id, text, tone } });
    setTimeout(() => {
      if (get().toast?.id === id) set({ toast: null });
    }, 4200);
  },
  spec: () => {
    const s = get();
    return graphToSpec(s.nodes, s.edges, s.project);
  },
}));
