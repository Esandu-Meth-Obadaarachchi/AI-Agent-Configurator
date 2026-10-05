import type { Edge, Node } from "@xyflow/react";

// ---------------------------------------------------------------- catalog

export type CategoryId = "flow" | "agents" | "logic" | "knowledge" | "tools" | "memory" | "safety";

export interface Option {
  value: string;
  label: string;
  hint?: string;
  disabled?: boolean;
}

export interface FieldDef {
  key: string;
  label: string;
  kind:
    | "text"
    | "textarea"
    | "prompt"
    | "number"
    | "toggle"
    | "select"
    | "segmented"
    | "multiselect"
    | "tags"
    | "model"
    | "routes"
    | "params"
    | "toolinputs"
    | "code";
  help?: string;
  placeholder?: string;
  options?: Option[];
  min?: number;
  max?: number;
  step?: number;
  rows?: number;
  mono?: boolean;
  advanced?: boolean;
  nullable?: boolean;
  ai?: "system_prompt" | "custom_tool" | "custom_step";
  language?: string;
  showIf?: Record<string, string | string[]>;
}

export interface HandleDef {
  id: string;
  kind: "flow" | "attach";
  label?: string;
}

export interface NodeTypeDef {
  type: string;
  category: CategoryId;
  title: string;
  icon: string;
  blurb: string;
  explain: string;
  tradeoff?: string;
  role: "flow" | "resource";
  kind?: "tool" | "knowledge" | "memory";
  max?: number;
  ai?: boolean;
  inputs: HandleDef[];
  outputs: HandleDef[] | "routes";
  accepts?: string[];
  fields: FieldDef[];
}

export interface Blueprint {
  id: string;
  title: string;
  blurb: string;
  tags: string[];
  level: string;
  spec: Spec;
}

export interface Catalog {
  categories: { id: CategoryId; title: string; blurb: string }[];
  nodes: NodeTypeDef[];
  models: Record<string, Option[]>;
  default_model: Record<string, string>;
  project_fields: FieldDef[];
  defaults: Record<string, Record<string, unknown>>;
  spec_defaults: Spec;
  blueprints: Blueprint[];
}

// ---------------------------------------------------------------- spec

export type NodeData = Record<string, unknown> & { label?: string };

export interface SpecNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: NodeData;
}

export interface SpecEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
}

export interface ProjectSettings {
  spec_version: string;
  project: { name: string; description: string };
  llm: { provider: string; model: string; temperature: number; max_tokens: number; effort: string | null };
  backend: { language: string };
  ui: { framework: string; streaming: boolean; feedback: boolean; show_steps: boolean; title: string };
  deploy: { target: string; backend_port: number; frontend_port: number };
  observability: { langsmith: boolean };
}

export interface Spec extends ProjectSettings {
  graph: { nodes: SpecNode[]; edges: SpecEdge[] };
}

// ---------------------------------------------------------------- canvas

export type BlockNode = Node<NodeData, string>;
export type FlowEdge = Edge<Record<string, unknown>>;

// ---------------------------------------------------------------- analysis

export interface Issue {
  level: "error" | "warning" | "info";
  code: string;
  message: string;
  node_id: string | null;
  fix: string | null;
}

export interface TraceStep {
  nodes: string[];
  edges: string[];
  note: string;
}

export interface Analysis {
  ok: boolean;
  issues: Issue[];
  modules: string[];
  gaps: { node_id: string; kind: string }[];
  trace: TraceStep[];
}

export interface PreviewFile {
  path: string;
  content: string;
  module: string;
  size: number;
}

export interface Decision {
  module: string;
  title: string;
  what?: string;
  why?: string;
  "trade-off"?: string;
}

export interface Preview extends Analysis {
  files: PreviewFile[];
  node_files: Record<string, string[]>;
  decisions: Decision[];
}
