"""Step factories. Each make_*_node() returns an async function LangGraph can run."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from langgraph.graph import END

from app.state import AppState


class AsyncNode(Protocol):
    """What LangGraph runs for an async step. The parameter must be called `state`."""

    def __call__(self, state: AppState) -> Awaitable[dict[str, Any]]: ...


class SyncNode(Protocol):
    def __call__(self, state: AppState) -> dict[str, Any]: ...


def route(node_id: str, mapping: dict[str, list[str]]) -> Callable[[dict[str, Any]], list[str]]:
    """Follow the branch a step chose, by reading state["decisions"][node_id].

    An unknown or missing decision ends the run rather than guessing.
    """

    def pick(state: dict[str, Any]) -> list[str]:
        decision = (state.get("decisions") or {}).get(node_id, "")
        return mapping.get(decision) or [END]

    pick.__name__ = f"route_{node_id}"
    return pick
