"""Custom step wrapper: runs your function from app/custom/nodes.py.

Sync and async functions both work. Any AIMessage your function returns without a
name is labelled with this step's id so the UI can show who said it.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage

from app.events import step
from app.nodes import AsyncNode
from app.state import AppState


def make_custom_step_node(
    *, node_id: str, label: str, fn: Callable[[AppState], Any]
) -> AsyncNode:
    async def run(state: AppState) -> dict[str, Any]:
        step(node_id, "start")
        result = fn(dict(state))
        if inspect.isawaitable(result):
            result = await result
        update = dict(result or {})
        if "messages" in update:
            update["messages"] = [
                AIMessage(content=m.content, name=node_id, id=m.id) if isinstance(m, AIMessage) and not m.name else m
                for m in update["messages"]
            ]
        step(node_id, "end")
        return update

    run.__name__ = node_id
    return run
