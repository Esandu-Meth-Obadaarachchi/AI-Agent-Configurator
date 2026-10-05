"""LLM step: one model call with fixed instructions and no tools."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, SystemMessage

from app.events import step
from app.llm import get_chat_model
from app.messages import context_block, for_node, text_of
from app.nodes import AsyncNode
from app.state import AppState


def make_prompt_node(
    *,
    node_id: str,
    label: str,
    instructions: str,
    model: str | None = None,
    temperature: float | None = None,
) -> AsyncNode:
    async def run(state: AppState) -> dict[str, Any]:
        step(node_id, "start")
        llm = get_chat_model(model, temperature=temperature, purpose=label)
        system = SystemMessage(content=instructions + context_block(state))
        reply = await llm.ainvoke([system, *for_node(state["messages"], node_id)])
        step(node_id, "end")
        return {"messages": [AIMessage(content=text_of(reply).strip() or "(no answer)", name=node_id)]}

    run.__name__ = node_id
    return run
