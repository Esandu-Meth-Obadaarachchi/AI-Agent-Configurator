"""Router step: classify the latest user message and pick one branch.

mode="llm" asks the model for a structured choice. mode="keywords" is free and
instant: the first branch whose keyword appears wins, otherwise the last branch.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, create_model

from app.events import step
from app.llm import get_chat_model, structured
from app.messages import last_user_text
from app.nodes import AsyncNode
from app.state import AppState


def pick_by_keywords(text: str, routes: list[dict[str, Any]]) -> str:
    lowered = text.lower()
    for r in routes:
        if any(k.lower() in lowered for k in r.get("keywords", []) if k.strip()):
            return str(r["id"])
    return str(routes[-1]["id"])


def make_router_node(
    *,
    node_id: str,
    label: str,
    mode: str,
    instructions: str,
    routes: list[dict[str, Any]],
    model: str | None = None,
) -> AsyncNode:
    ids = [r["id"] for r in routes]
    labels = {r["id"]: r["label"] for r in routes}
    Choice: type[BaseModel] = create_model(  # noqa: N806
        "Choice",
        route=(Literal[tuple(ids)], Field(description="The id of the best matching branch.")),  # type: ignore[valid-type]
        reason=(str, Field(description="One short sentence explaining the choice.")),
    )
    Choice.demo = classmethod(lambda cls: cls(route=ids[0], reason="demo"))  # type: ignore[attr-defined]
    menu = "\n".join(f"- {r['id']}: {r['label']}. {r['description']}" for r in routes)
    system = f"{instructions}\n\nBranches:\n{menu}\n\nAnswer with the id of exactly one branch."

    async def run(state: AppState) -> dict[str, Any]:
        step(node_id, "start")
        text = last_user_text(state["messages"])
        if mode == "keywords":
            chosen = pick_by_keywords(text, routes)
        else:
            llm = structured(get_chat_model(model, purpose=label), Choice)
            result = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=text or "(empty message)")])
            chosen = str(result.route) if result.route in ids else ids[-1]
        step(node_id, "end", f"Branch: {labels.get(chosen, chosen)}")
        return {"decisions": {node_id: chosen}}

    run.__name__ = node_id
    return run
