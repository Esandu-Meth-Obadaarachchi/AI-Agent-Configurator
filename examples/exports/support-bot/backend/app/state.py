"""Shared state for the agent loop.

`messages` is the conversation every step reads and appends to. The three dicts hold
per-turn bookkeeping keyed by node id: branch decisions, loop counters and retrieved
passages. They merge (so parallel branches don't collide) and reset at the start of
each user turn.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph import MessagesState

RESET = "__reset__"


def merge(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    if right and RESET in right:
        return {k: v for k, v in right.items() if k != RESET}
    return {**(left or {}), **(right or {})}


class AppState(MessagesState):
    decisions: Annotated[dict[str, str], merge]
    counters: Annotated[dict[str, int], merge]
    context: Annotated[dict[str, list[dict[str, Any]]], merge]


def new_turn(message: str) -> dict[str, Any]:
    """Input payload for a fresh user message."""
    return {
        "messages": [{"role": "user", "content": message}],
        "decisions": {RESET: True},
        "counters": {RESET: True},
        "context": {RESET: True},
    }
