"""The agent loop for support-bot, as a LangGraph state graph.

Generated from spec.json by Agent Configurator. Change the loop on the canvas (or in
spec.json) and regenerate. Your own code belongs in app/custom/, which regeneration
never overwrites.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.nodes import route
from app.nodes.agent import make_agent_node
from app.nodes.approval import make_approval_node
from app.nodes.guardrail import make_guardrail_node
from app.nodes.prompt_step import make_prompt_node
from app.nodes.router import make_router_node
from app.prompts import prompt_for
from app.state import AppState
from app.tools import Toolsets


def build_graph(toolsets: Toolsets, checkpointer: Any = None, store: Any = None) -> Any:
    graph = StateGraph(AppState)

    # Screen message
    graph.add_node(
        "guard",
        make_guardrail_node(
            node_id="guard",
            label="Screen message",
            redact_pii=True,
            block_prompt_injection=True,
            max_input_chars=8000,
            blocked_terms=[],
            blocked_message="Sorry, I can't help with that request.",
        ),
    )

    # Triage
    graph.add_node(
        "triage",
        make_router_node(
            node_id="triage",
            label="Triage",
            mode="llm",
            instructions=prompt_for("triage"),
            routes=[
                {"id": "billing", "label": "Billing", "description": "Payments, invoices, refunds, plans", "keywords": ["refund", "invoice", "charge", "billing", "plan"]},
                {"id": "technical", "label": "Technical", "description": "Bugs, errors, how-to questions about the product", "keywords": ["error", "bug", "crash", "how do i"]},
                {"id": "other", "label": "Other", "description": "Greetings and anything else", "keywords": []},
            ],
            model=None,
        ),
    )

    # Billing agent: Handles payments, invoices and refunds.
    graph.add_node(
        "billing",
        make_agent_node(
            node_id="billing",
            label="Billing agent",
            system_prompt=prompt_for("billing"),
            tools=[*toolsets["orders"]],
            model=None,
            temperature=None,
            effort=None,
            max_steps=8,
        ),
    )

    # Technical agent: Solves product problems using the help centre.
    graph.add_node(
        "tech",
        make_agent_node(
            node_id="tech",
            label="Technical agent",
            system_prompt=prompt_for("tech"),
            tools=[*toolsets["helpdocs"]],
            model=None,
            temperature=None,
            effort=None,
            max_steps=8,
        ),
    )

    # Friendly reply
    graph.add_node(
        "smalltalk",
        make_prompt_node(
            node_id="smalltalk",
            label="Friendly reply",
            instructions=prompt_for("smalltalk"),
            model=None,
            temperature=None,
        ),
    )

    # Approve refund
    graph.add_node(
        "approve",
        make_approval_node(
            node_id="approve",
            label="Approve refund",
            prompt=prompt_for("approve"),
            allow_edit=True,
            reject_ends=False,
        ),
    )

    # ---- How the steps connect
    graph.add_edge(START, "guard")
    graph.add_conditional_edges(
        "guard",
        route(
            "guard",
            {
                "pass": ["triage"],
                "blocked": [END],
            },
        ),
        ["triage", END],
    )
    graph.add_conditional_edges(
        "triage",
        route(
            "triage",
            {
                "billing": ["billing"],
                "technical": ["tech"],
                "other": ["smalltalk"],
            },
        ),
        ["billing", "tech", "smalltalk"],
    )
    graph.add_edge("billing", "approve")
    graph.add_edge("tech", END)
    graph.add_edge("smalltalk", END)
    graph.add_conditional_edges(
        "approve",
        route(
            "approve",
            {
                "approved": [END],
                "rejected": ["billing"],
            },
        ),
        [END, "billing"],
    )

    return graph.compile(checkpointer=checkpointer, store=store)
