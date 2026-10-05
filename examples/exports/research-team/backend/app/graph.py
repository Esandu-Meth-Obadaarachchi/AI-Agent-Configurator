"""The agent loop for research-team, as a LangGraph state graph.

Generated from spec.json by Agent Configurator. Change the loop on the canvas (or in
spec.json) and regenerate. Your own code belongs in app/custom/, which regeneration
never overwrites.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.nodes import route
from app.nodes.agent import make_agent_node
from app.nodes.critic import make_critic_node
from app.nodes.supervisor import make_supervisor_node
from app.prompts import prompt_for
from app.state import AppState
from app.tools import Toolsets


def build_graph(toolsets: Toolsets, checkpointer: Any = None, store: Any = None) -> Any:
    graph = StateGraph(AppState)

    # Research lead
    graph.add_node(
        "lead",
        make_supervisor_node(
            node_id="lead",
            label="Research lead",
            instructions=prompt_for("lead"),
            workers=[
                {"id": "researcher", "label": "Researcher", "role": "Finds and reads sources on the web."},
                {"id": "analyst", "label": "Analyst", "role": "Checks numbers and does calculations."},
                {"id": "writer", "label": "Writer", "role": "Writes the final report."},
            ],
            model=None,
            max_rounds=8,
        ),
    )

    # Researcher: Finds and reads sources on the web.
    graph.add_node(
        "researcher",
        make_agent_node(
            node_id="researcher",
            label="Researcher",
            system_prompt=prompt_for("researcher"),
            tools=[*toolsets["search"], *toolsets["read"]],
            model=None,
            temperature=None,
            effort=None,
            max_steps=8,
        ),
    )

    # Analyst: Checks numbers and does calculations.
    graph.add_node(
        "analyst",
        make_agent_node(
            node_id="analyst",
            label="Analyst",
            system_prompt=prompt_for("analyst"),
            tools=[*toolsets["calc"]],
            model=None,
            temperature=None,
            effort=None,
            max_steps=8,
        ),
    )

    # Writer: Writes the final report.
    graph.add_node(
        "writer",
        make_agent_node(
            node_id="writer",
            label="Writer",
            system_prompt=prompt_for("writer"),
            tools=[],
            model=None,
            temperature=None,
            effort=None,
            max_steps=8,
        ),
    )

    # Fact check
    graph.add_node(
        "review",
        make_critic_node(
            node_id="review",
            label="Fact check",
            criteria=prompt_for("review"),
            max_iterations=2,
            model=None,
            can_revise=True,
        ),
    )

    # ---- How the steps connect
    graph.add_edge(START, "lead")
    graph.add_conditional_edges(
        "lead",
        route(
            "lead",
            {
                "researcher": ["researcher"],
                "analyst": ["analyst"],
                "writer": ["writer"],
                "done": ["review"],
            },
        ),
        ["researcher", "analyst", "writer", "review"],
    )
    graph.add_edge("researcher", "lead")  # reports back to Research lead
    graph.add_edge("analyst", "lead")  # reports back to Research lead
    graph.add_edge("writer", "lead")  # reports back to Research lead
    graph.add_conditional_edges(
        "review",
        route(
            "review",
            {
                "pass": [END],
                "revise": ["lead"],
            },
        ),
        [END, "lead"],
    )

    return graph.compile(checkpointer=checkpointer, store=store)
