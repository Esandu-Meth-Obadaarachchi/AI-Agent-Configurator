"""Agent step: a model with tools, running its own think-act-observe loop.

Built on LangChain's create_agent. Only the agent's final answer goes into the shared
conversation; its tool calls stream to the UI but stay out of other agents' context.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError

from app.events import step
from app.llm import get_chat_model
from app.messages import context_block, for_node, text_of
from app.nodes import AsyncNode
from app.state import AppState


def make_agent_node(
    *,
    node_id: str,
    label: str,
    system_prompt: str,
    tools: Sequence[BaseTool],
    model: str | None = None,
    temperature: float | None = None,
    effort: str | None = None,
    max_steps: int = 8,
) -> AsyncNode:
    async def run(state: AppState) -> dict[str, Any]:
        step(node_id, "start", f"{len(tools)} tools" if tools else "")
        llm = get_chat_model(model, temperature=temperature, effort=effort, purpose=label)
        agent = create_agent(llm, tools=list(tools), system_prompt=system_prompt + context_block(state))
        try:
            inputs: Any = {"messages": for_node(state["messages"], node_id)}
            result = await agent.ainvoke(inputs, {"recursion_limit": max_steps * 2 + 1})
            answer = text_of(result["messages"][-1]).strip()
        except GraphRecursionError:
            answer = f"I couldn't finish within {max_steps} steps. Try a narrower request."
        step(node_id, "end")
        return {"messages": [AIMessage(content=answer or "(no answer)", name=node_id)]}

    run.__name__ = node_id
    return run
