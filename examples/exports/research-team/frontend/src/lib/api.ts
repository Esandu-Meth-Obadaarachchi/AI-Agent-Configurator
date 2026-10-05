import type { AppInfo, ChatMessage, Pending, StreamEvent } from "./types";

/** Read a Server-Sent Events response and call `onEvent` for each event. */
export async function readEvents(res: Response, onEvent: (e: StreamEvent) => void): Promise<void> {
  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `Request failed with status ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split = buffer.indexOf("\n\n");
    while (split !== -1) {
      const block = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (data) onEvent({ event, data: JSON.parse(data) } as StreamEvent);
      split = buffer.indexOf("\n\n");
    }
  }
}

export async function getInfo(): Promise<AppInfo> {
  const res = await fetch("/api/info", { cache: "no-store" });
  if (!res.ok) throw new Error("The API is not reachable. Is the backend running on port 8000?");
  return res.json();
}

export async function getThread(threadId: string): Promise<{ messages: ChatMessage[]; pending: Pending[] }> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}`, { cache: "no-store" });
  if (!res.ok) return { messages: [], pending: [] };
  return res.json();
}

export function startTurn(message: string, threadId: string): Promise<Response> {
  return fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
}

export function resumeTurn(
  threadId: string,
  decision: { approved: boolean; edited?: string; feedback?: string },
): Promise<Response> {
  return fetch("/api/chat/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, ...decision }),
  });
}

export async function sendFeedback(threadId: string, messageId: string, score: -1 | 1): Promise<void> {
  await fetch("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message_id: messageId, score }),
  });
}

export async function uploadDocuments(kbId: string, files: FileList): Promise<number> {
  const form = new FormData();
  Array.from(files).forEach((f) => form.append("files", f));
  const res = await fetch(`/api/knowledge/${encodeURIComponent(kbId)}/upload`, { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ?? "Upload failed");
  return body.chunks_added ?? 0;
}
