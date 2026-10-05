"""Helpers for sharing one conversation between several agents."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.meta import NODE_LABELS


def text_of(message: Any) -> str:
    """Plain text of a message, skipping thinking and tool-use blocks."""
    if message is None:
        return ""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def last_user_text(messages: Sequence[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage) and not m.name:
            return text_of(m)
    return ""


def last_reply(messages: Sequence[BaseMessage]) -> AIMessage | None:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and text_of(m).strip():
            return m
    return None


def for_node(messages: Sequence[BaseMessage], node_id: str) -> list[BaseMessage]:
    """The conversation as one node should see it.

    - The user's messages stay as they are.
    - This node's own earlier replies stay as assistant turns.
    - Replies from other agents become labelled notes on the user side. Claude models
      reject a conversation that ends on an assistant turn, and a model shouldn't
      mistake another agent's words for its own.
    """
    out: list[BaseMessage] = []
    for m in messages:
        text = text_of(m).strip()
        if not text:
            continue
        if isinstance(m, HumanMessage):
            if m.name:
                label = NODE_LABELS.get(m.name, m.name)
                out.append(HumanMessage(content=f"[{label}]\n{text}"))
            else:
                out.append(HumanMessage(content=text))
        elif isinstance(m, AIMessage):
            if m.name == node_id:
                out.append(AIMessage(content=text))
            else:
                label = NODE_LABELS.get(m.name or "", m.name or "Assistant")
                out.append(HumanMessage(content=f"[Message from {label}, not from the user]\n{text}"))
    if not out or isinstance(out[-1], AIMessage):
        out.append(HumanMessage(content="Continue with your part of the task."))
    return out


def context_block(state: Mapping[str, Any]) -> str:
    """Retrieved passages from Retrieve steps, formatted for a system prompt."""
    passages = [p for docs in (state.get("context") or {}).values() for p in docs]
    if not passages:
        return ""
    lines = ["", "", "Relevant passages (cite them as [n]):"]
    for i, p in enumerate(passages, start=1):
        source = p.get("source", "unknown")
        lines.append(f"[{i}] ({source}) {p.get('content', '').strip()}")
    return "\n".join(lines)
