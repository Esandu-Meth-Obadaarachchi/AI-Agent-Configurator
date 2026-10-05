"""Custom steps. This file is yours: regeneration never overwrites it.

Each function takes the current state (a dict with "messages", "decisions",
"counters" and "context") and returns the changes to apply, for example:

    from langchain_core.messages import AIMessage

    def my_step(state: dict[str, Any]) -> dict[str, Any]:
        return {"messages": [AIMessage(content="Done", name="my_step")]}

Return {} to change nothing.
"""

from __future__ import annotations

from typing import Any

__all__: list[str] = []


def _example(state: dict[str, Any]) -> dict[str, Any]:
    return {}
