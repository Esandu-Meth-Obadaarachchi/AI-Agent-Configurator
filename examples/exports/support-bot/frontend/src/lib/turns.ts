import type { ChatMessage, StreamEvent, Turn } from "./types";

export type Action =
  | { type: "reset"; turns: Turn[] }
  | { type: "start"; turnId: string; text: string }
  | { type: "resume"; turnId: string }
  | { type: "event"; turnId: string; e: StreamEvent }
  | { type: "fail"; turnId: string; message: string }
  | { type: "score"; messageId: string; score: -1 | 1 };

let draftCounter = 0;

function updateTurn(turns: Turn[], id: string, fn: (t: Turn) => Turn): Turn[] {
  return turns.map((t) => (t.id === id ? fn(t) : t));
}

function applyEvent(turn: Turn, e: StreamEvent): Turn {
  switch (e.event) {
    case "token": {
      const replies = [...turn.replies];
      const i = replies.findIndex((r) => r.streaming && r.node === e.data.node);
      if (i === -1) {
        draftCounter += 1;
        replies.push({
          id: `draft-${draftCounter}`,
          role: "assistant",
          node: e.data.node,
          label: e.data.label,
          content: e.data.text,
          streaming: true,
        });
      } else {
        replies[i] = { ...replies[i], content: replies[i].content + e.data.text };
      }
      return { ...turn, replies };
    }
    case "message": {
      const { id, node, label, content } = e.data;
      let replies = [...turn.replies];
      const same = replies.findIndex((r) => r.id === id);
      if (same !== -1) {
        replies[same] = { ...replies[same], content, streaming: false };
        return { ...turn, replies };
      }
      // An earlier finished reply from the same step is now an earlier draft.
      replies = replies.map((r) => (r.node === node && !r.streaming ? { ...r, superseded: true } : r));
      const draft = replies.findIndex((r) => r.streaming && r.node === node);
      const final: ChatMessage = { id, role: "assistant", node, label, content, streaming: false };
      if (draft === -1) replies.push(final);
      else replies[draft] = final;
      return { ...turn, replies };
    }
    case "step": {
      const steps = [...turn.steps];
      const { node, label, status, detail } = e.data;
      if (status === "start") {
        steps.push({ key: `${node}-${steps.length}`, node, label, status, detail, tools: [] });
      } else {
        let i = -1;
        for (let k = steps.length - 1; k >= 0; k -= 1) {
          if (steps[k].node === node && steps[k].status === "start") {
            i = k;
            break;
          }
        }
        if (i === -1) steps.push({ key: `${node}-${steps.length}`, node, label, status, detail, tools: [] });
        else steps[i] = { ...steps[i], status: "end", detail: detail || steps[i].detail };
      }
      return { ...turn, steps };
    }
    case "tool": {
      const steps = [...turn.steps];
      let i = -1;
      for (let k = steps.length - 1; k >= 0; k -= 1) {
        if (steps[k].node === e.data.node) {
          i = k;
          break;
        }
      }
      if (i === -1) {
        steps.push({ key: `${e.data.node}-${steps.length}`, node: e.data.node, label: e.data.label, status: "start", tools: [] });
        i = steps.length - 1;
      }
      const tools = [...steps[i].tools];
      if (e.data.status === "start") {
        tools.push({ name: e.data.name, done: false });
      } else {
        const t = tools.findIndex((x) => x.name === e.data.name && !x.done);
        if (t === -1) tools.push({ name: e.data.name, preview: e.data.preview, done: true });
        else tools[t] = { ...tools[t], preview: e.data.preview, done: true };
      }
      steps[i] = { ...steps[i], tools };
      return { ...turn, steps };
    }
    case "error":
      return { ...turn, error: e.data.message, running: false };
    case "done":
    case "interrupt":
      return {
        ...turn,
        running: false,
        replies: turn.replies.map((r) => (r.streaming ? { ...r, streaming: false } : r)),
      };
    default:
      return turn;
  }
}

export function turnsReducer(turns: Turn[], action: Action): Turn[] {
  switch (action.type) {
    case "reset":
      return action.turns;
    case "start":
      return [
        ...turns,
        {
          id: action.turnId,
          user: { id: `user-${action.turnId}`, role: "user", content: action.text },
          replies: [],
          steps: [],
          running: true,
        },
      ];
    case "resume":
      return updateTurn(turns, action.turnId, (t) => ({ ...t, running: true, error: undefined }));
    case "event":
      return updateTurn(turns, action.turnId, (t) => applyEvent(t, action.e));
    case "fail":
      return updateTurn(turns, action.turnId, (t) => ({ ...t, running: false, error: action.message }));
    case "score":
      return turns.map((t) => ({
        ...t,
        replies: t.replies.map((r) => (r.id === action.messageId ? { ...r, score: action.score } : r)),
      }));
    default:
      return turns;
  }
}

/** Rebuild turns from saved history: each user message starts a turn. */
export function turnsFromHistory(messages: ChatMessage[]): Turn[] {
  const turns: Turn[] = [];
  for (const m of messages) {
    if (m.role === "user") {
      turns.push({ id: `h-${m.id}`, user: m, replies: [], steps: [], running: false });
    } else if (turns.length) {
      const t = turns[turns.length - 1];
      if (m.role === "assistant") {
        t.replies = t.replies.map((r) => (r.node === m.node ? { ...r, superseded: true } : r));
        t.replies.push(m);
      } else {
        t.steps.push({ key: `${m.id}`, node: m.node ?? "", label: m.label ?? "", status: "end", detail: m.content, tools: [] });
      }
    }
  }
  return turns;
}
