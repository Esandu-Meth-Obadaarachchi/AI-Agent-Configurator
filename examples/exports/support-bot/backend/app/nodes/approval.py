"""Human approval step: pause the run until a person approves or rejects.

Uses LangGraph's interrupt(). The paused run is saved by the checkpointer, and the
UI resumes it via POST /api/chat/resume with {"approved", "edited", "feedback"}.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from app.events import step
from app.messages import last_reply, text_of
from app.nodes import SyncNode
from app.state import AppState


def make_approval_node(
    *,
    node_id: str,
    label: str,
    prompt: str,
    allow_edit: bool = True,
    reject_ends: bool = True,
) -> SyncNode:
    def run(state: AppState) -> dict[str, Any]:
        draft = last_reply(state["messages"])
        step(node_id, "start", "Waiting for approval")
        answer = interrupt(
            {
                "type": "approval",
                "node": node_id,
                "label": label,
                "prompt": prompt,
                "content": text_of(draft) if draft else "",
                "allow_edit": allow_edit,
            }
        )
        decision = answer if isinstance(answer, dict) else {"approved": bool(answer)}
        if decision.get("approved"):
            step(node_id, "end", "Approved")
            update: dict[str, Any] = {"decisions": {node_id: "approved"}}
            edited = str(decision.get("edited") or "").strip()
            if allow_edit and edited and draft is not None and edited != text_of(draft).strip():
                # Same id replaces the draft in place.
                update["messages"] = [AIMessage(content=edited, name=draft.name, id=draft.id)]
            return update
        step(node_id, "end", "Rejected")
        notes = str(decision.get("feedback") or "").strip()
        messages: list[Any] = []
        if reject_ends:
            messages.append(AIMessage(content="A reviewer held this reply back." + (f" Note: {notes}" if notes else ""), name=node_id))
        else:
            messages.append(HumanMessage(content=f"A reviewer rejected the draft. {notes or 'Please try again.'}", name=node_id))
        return {"decisions": {node_id: "rejected"}, "messages": messages}

    run.__name__ = node_id
    return run
