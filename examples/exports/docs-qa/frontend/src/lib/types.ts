export type Role = "user" | "assistant" | "note";

export interface ChatMessage {
  id: string;
  role: Role;
  node?: string | null;
  label?: string;
  content: string;
  streaming?: boolean;
  superseded?: boolean;
  score?: -1 | 0 | 1;
}

export interface Step {
  key: string;
  node: string;
  label: string;
  status: "start" | "end";
  detail?: string;
  tools: { name: string; preview?: string; done: boolean }[];
}

export interface Pending {
  id?: string;
  node: string;
  label: string;
  prompt: string;
  content: string;
  allow_edit: boolean;
}

export interface Turn {
  id: string;
  user: ChatMessage;
  replies: ChatMessage[];
  steps: Step[];
  error?: string;
  running: boolean;
}

export interface AppInfo {
  title: string;
  greeting: string;
  nodes: Record<string, { label: string; kind: string }>;
  features: {
    approval: boolean;
    knowledge: { id: string; label: string }[];
    long_term_memory: boolean;
    feedback: boolean;
    show_steps: boolean;
    streaming: boolean;
  };
  demo: boolean;
  model: string;
}

export type StreamEvent =
  | { event: "token"; data: { node: string; label: string; text: string } }
  | { event: "message"; data: { id: string; node: string; label: string; content: string } }
  | { event: "step"; data: { node: string; label: string; status: "start" | "end"; detail?: string } }
  | { event: "tool"; data: { node: string; label: string; name: string; status: "start" | "end"; preview?: string } }
  | { event: "interrupt"; data: Pending }
  | { event: "done"; data: { thread_id: string } }
  | { event: "error"; data: { message: string } };
