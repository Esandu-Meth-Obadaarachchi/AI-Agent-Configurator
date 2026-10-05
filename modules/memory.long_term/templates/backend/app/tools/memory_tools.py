"""Long-term memory tools: remember and recall facts per user, across conversations."""

from __future__ import annotations

import re
import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool

_store: Any = None


def set_store(store: Any) -> None:
    """Called once at startup with the LangGraph store (see app/persistence.py)."""
    global _store
    _store = store


def _namespace(config: RunnableConfig) -> tuple[str, str]:
    user = (config.get("configurable") or {}).get("user_id", "default")
    return ("memories", str(user))


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) > 2}


def make_memory_tools() -> list[BaseTool]:
    @tool
    async def remember(fact: str, config: RunnableConfig) -> str:
        """Save a durable fact about the user (a preference, a name, an ongoing project) for future conversations."""
        if _store is None:
            return "Memory is not available."
        await _store.aput(_namespace(config), uuid.uuid4().hex, {"fact": fact.strip()})
        return "Saved."

    @tool
    async def recall(query: str, config: RunnableConfig) -> str:
        """Look up facts saved about the user in earlier conversations."""
        if _store is None:
            return "Memory is not available."
        items = await _store.asearch(_namespace(config), limit=200)
        wanted = _words(query)
        scored = sorted(items, key=lambda it: -len(wanted & _words(it.value.get("fact", ""))))
        facts = [it.value.get("fact", "") for it in scored[:8] if it.value.get("fact")]
        return "\n".join(f"- {f}" for f in facts) if facts else "Nothing saved yet."

    return [remember, recall]
