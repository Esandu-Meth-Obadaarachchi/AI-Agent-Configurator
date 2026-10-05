"""Supervisor step: decides which worker acts next, or that the job is done.

Each round it reads the conversation (including what workers reported) and returns a
structured decision. Workers always report back here (see app/graph.py). The run
stops after `max_rounds` delegations even if the supervisor wants more.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field, create_model

from app.config import get_settings
from app.events import step
from app.llm import get_chat_model, structured
from app.messages import for_node, last_reply, text_of
from app.nodes import AsyncNode
from app.state import AppState


def make_supervisor_node(
    *,
    node_id: str,
    label: str,
    instructions: str,
    workers: list[dict[str, str]],
    model: str | None = None,
    max_rounds: int = 6,
) -> AsyncNode:
    worker_ids = [w["id"] for w in workers]
    names = {w["id"]: w["label"] for w in workers}
    choice = Literal[tuple(worker_ids + ["done"])]  # type: ignore[valid-type]

    Decision: type[BaseModel] = create_model(  # noqa: N806
        "Decision",
        next=(choice, Field(description="The worker to act next, or 'done' when the request is fully handled.")),
        task=(str, Field(description="Instructions for that worker. Empty when done.")),
        final_answer=(str, Field(description="When done: the complete answer for the user. Otherwise empty.")),
    )
    team = "\n".join(f"- {w['id']}: {w['label']}. {w['role']}" for w in workers)
    system = (
        f"{instructions}\n\nYour team:\n{team}\n\n"
        "Delegate one step at a time. When the work is complete, choose 'done' and write the final answer "
        "for the user, combining what the team found."
    )

    async def run(state: AppState) -> dict[str, Any]:
        counters = state.get("counters") or {}
        rounds = counters.get(node_id, 0)
        if rounds >= max_rounds:
            step(node_id, "end", "Round limit reached")
            return {"decisions": {node_id: "done"}}

        if get_settings().llm_provider == "fake":
            # Demo mode: call each worker once, in order, then finish.
            used = counters.get(f"{node_id}.used", 0)
            if used < len(worker_ids):
                decision: Any = Decision(next=worker_ids[used], task="(demo task)", final_answer="")
            else:
                last = last_reply(state["messages"])
                decision = Decision(next="done", task="", final_answer=text_of(last) if last else "Done.")
        else:
            step(node_id, "start", "Planning")
            llm = structured(get_chat_model(model, purpose=label), Decision)
            decision = await llm.ainvoke([SystemMessage(content=system), *for_node(state["messages"], node_id)])

        if decision.next == "done":
            step(node_id, "end", "Done")
            update: dict[str, Any] = {"decisions": {node_id: "done"}}
            if decision.final_answer.strip():
                update["messages"] = [AIMessage(content=decision.final_answer.strip(), name=node_id)]
            return update

        worker = str(decision.next)
        step(node_id, "end", f"Delegates to {names.get(worker, worker)}")
        used = counters.get(f"{node_id}.used", 0)
        return {
            "decisions": {node_id: worker},
            "counters": {node_id: rounds + 1, f"{node_id}.used": used + 1},
            "messages": [HumanMessage(content=f"Task for {names.get(worker, worker)}: {decision.task}", name=node_id)],
        }

    run.__name__ = node_id
    return run
