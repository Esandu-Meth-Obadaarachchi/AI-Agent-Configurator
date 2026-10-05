import type { Analysis, Preview, Spec } from "./types";

const KEY_STORAGE = "configurator.anthropic-key";

/** The user's own Anthropic key, kept for this browser session only. */
export function sessionKey(): string | null {
  try {
    return window.sessionStorage.getItem(KEY_STORAGE);
  } catch {
    return null;
  }
}

export function setSessionKey(key: string | null): void {
  try {
    if (key) window.sessionStorage.setItem(KEY_STORAGE, key);
    else window.sessionStorage.removeItem(KEY_STORAGE);
  } catch {
    /* storage unavailable: key just won't persist */
  }
}

function headers(): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const key = typeof window === "undefined" ? null : sessionKey();
  if (key) h["X-Anthropic-Key"] = key;
  return h;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, { method: "POST", headers: headers(), body: JSON.stringify(body), signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("The engine isn't reachable. Start it with `make api`.", 0);
  }
  if (!res.ok) throw new ApiError(await errorText(res), res.status);
  return res.json() as Promise<T>;
}

async function errorText(res: Response): Promise<string> {
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) {
    const first = detail.problems?.[0];
    return first ? `${detail.message} ${first.path}: ${first.message}` : detail.message;
  }
  return body?.message ?? `Request failed (${res.status})`;
}

export const api = {
  validate: (spec: Spec, signal?: AbortSignal) => post<Analysis>("/validate", { spec }, signal),
  preview: (spec: Spec, signal?: AbortSignal) => post<Preview>("/preview", { spec }, signal),
  layout: (spec: Spec) => post<Spec>("/layout", { spec }),
  importSpec: (raw: unknown) => post<Spec>("/import", raw),
  async exportZip(spec: Spec): Promise<Blob> {
    const res = await fetch("/api/export", { method: "POST", headers: headers(), body: JSON.stringify({ spec }) });
    if (!res.ok) throw new ApiError(await errorText(res), res.status);
    return res.blob();
  },
  async aiStatus(): Promise<{ available: boolean; model: string; sandbox: boolean }> {
    const res = await fetch("/api/ai/status", { headers: headers() });
    if (!res.ok) throw new ApiError(await errorText(res), res.status);
    return res.json();
  },
  textToSpec: (description: string) =>
    post<{ spec: Spec; summary: string; source: "claude" | "blueprint"; notes: string[] }>("/ai/text-to-spec", { description }),
  generateCode: (spec: Spec, nodeId: string) =>
    post<{ ok: boolean; attempts: number; verified: string; message: string; data: Record<string, unknown> }>(
      "/ai/generate-code",
      { spec, node_id: nodeId },
    ),
  writePrompt: (body: { kind: string; label: string; role: string; context: string; tools: string[] }) =>
    post<{ prompt: string }>("/ai/write-prompt", body),
};

export function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
