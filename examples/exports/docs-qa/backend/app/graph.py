"""The agent loop for docs-qa, as a LangGraph state graph.

Generated from spec.json by Agent Configurator. Change the loop on the canvas (or in
spec.json) and regenerate. Your own code belongs in app/custom/, which regeneration
never overwrites.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.nodes.agent import make_agent_node
from app.prompts import prompt_for
from app.state import AppState
from app.tools import Toolsets


def build_graph(toolsets: Toolsets, checkpointer: Any = None, store: Any = None) -> Any:
    graph = StateGraph(AppState)

    # Docs assistant: Answers questions using the company documents.
    graph.add_node(
        "assistant",
        make_agent_node(
            node_id="assistant",
            label="Docs assistant",
            system_prompt=prompt_for("assistant"),
            tools=[*toolsets["docs"]],
            model=None,
            temperature=None,
            effort=None,
            max_steps=8,
        ),
    )

    # ---- How the steps connect
    graph.add_edge(START, "assistant")
    graph.add_edge("assistant", END)

    return graph.compile(checkpointer=checkpointer, store=store)
