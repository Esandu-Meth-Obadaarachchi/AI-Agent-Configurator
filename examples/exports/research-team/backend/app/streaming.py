"""Turn a LangGraph run into Server-Sent Events for the chat UI.

Events (each `data:` is JSON):
- step:      a block started or finished, with a short detail ("Branch: Billing")
- token:     a piece of streamed text from a block
- tool:      a tool call started or returned
- message:   a block's final reply (replaces its streamed tokens)
- interrupt: the run paused for human approval
- done / error
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from app.messages import text_of
from app.meta import NODE_LABELS, SPEAKING_NODES

log = logging.getLogger(__name__)


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _outer_node(ns: tuple[str, ...], meta: dict[str, Any]) -> str:
    if ns:
        return ns[0].split(":", 1)[0]
    return str(meta.get("langgraph_node", ""))


async def stream_run(graph: Any, payload: Any, config: dict[str, Any]) -> AsyncIterator[str]:
    thread_id = config["configurable"]["thread_id"]
    try:
        async for ns, mode, chunk in graph.astream(
            payload, config, stream_mode=["messages", "updates", "custom"], subgraphs=True
        ):
            if mode == "custom":
                node = chunk.get("node", "")
                yield sse(chunk.get("kind", "step"), {**chunk, "label": NODE_LABELS.get(node, node)})
            elif mode == "messages":
                msg, meta = chunk
                node = _outer_node(ns, meta)
                label = NODE_LABELS.get(node, node)
                if isinstance(msg, AIMessageChunk):
                    text = text_of(msg)
                    if text and node in SPEAKING_NODES:
                        yield sse("token", {"node": node, "label": label, "text": text})
                    for tc in msg.tool_call_chunks or []:
                        if tc.get("name"):
                            yield sse("tool", {"node": node, "label": label, "name": tc["name"], "status": "start"})
                elif isinstance(msg, ToolMessage):
                    preview = text_of(msg)[:400]
                    yield sse("tool", {"node": node, "label": label, "name": msg.name, "status": "end", "preview": preview})
                elif isinstance(msg, AIMessage) and ns:
                    # A complete (non-streamed) inner model reply, e.g. from a provider without streaming.
                    for call in msg.tool_calls or []:
                        yield sse("tool", {"node": node, "label": label, "name": call["name"], "status": "start", "args": call["args"]})
            elif mode == "updates" and not ns:
                if "__interrupt__" in chunk:
                    for intr in chunk["__interrupt__"]:
                        yield sse("interrupt", {"id": intr.id, **(intr.value or {})})
                    continue
                for node, update in chunk.items():
                    for m in (update or {}).get("messages", []) if isinstance(update, dict) else []:
                        if isinstance(m, AIMessage) and text_of(m).strip():
                            yield sse(
                                "message",
                                {"id": m.id, "node": node, "label": NODE_LABELS.get(node, node), "content": text_of(m)},
                            )
        yield sse("done", {"thread_id": thread_id})
    except Exception as exc:  # surface the failure in the chat instead of a dead stream
        log.exception("run failed")
        yield sse("error", {"message": f"{type(exc).__name__}: {exc}"})
