"""Review loop step: grade the latest answer and send it back for revision if weak.

On "revise" the reviewer's feedback is added to the conversation as a note, so the
step that redoes the work can see exactly what to fix. After `max_iterations`
revisions the answer passes regardless, which guarantees the loop ends.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.events import step
from app.llm import get_chat_model, structured
from app.messages import last_reply, last_user_text, text_of
from app.nodes import AsyncNode
from app.state import AppState


class Review(BaseModel):
    verdict: Literal["pass", "revise"] = Field(description="'pass' if the answer meets every criterion, else 'revise'.")
    feedback: str = Field(description="If revising: specific, actionable changes. If passing: empty.")

    @classmethod
    def demo(cls) -> Review:
        return cls(verdict="pass", feedback="")


def make_critic_node(
    *,
    node_id: str,
    label: str,
    criteria: str,
    max_iterations: int = 2,
    model: str | None = None,
    can_revise: bool = True,
) -> AsyncNode:
    system = (
        "You review answers before they reach the user. A good answer meets these criteria:\n"
        f"{criteria}\n\n"
        "Judge only the latest answer. Ask for a revision only for real problems, and say exactly what to change."
    )

    async def run(state: AppState) -> dict[str, Any]:
        rounds = (state.get("counters") or {}).get(node_id, 0)
        answer = last_reply(state["messages"])
        if not can_revise or rounds >= max_iterations or answer is None:
            step(node_id, "end", "Pass" if answer else "Nothing to review")
            return {"decisions": {node_id: "pass"}}
        step(node_id, "start", f"Attempt {rounds + 1} of {max_iterations}")
        llm = structured(get_chat_model(model, purpose=label), Review)
        question = last_user_text(state["messages"])
        review = await llm.ainvoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=f"Question:\n{question}\n\nAnswer to review:\n{text_of(answer)}"),
            ]
        )
        if review.verdict == "pass":
            step(node_id, "end", "Pass")
            return {"decisions": {node_id: "pass"}}
        step(node_id, "end", f"Revise: {review.feedback[:120]}")
        return {
            "decisions": {node_id: "revise"},
            "counters": {node_id: rounds + 1},
            "messages": [HumanMessage(content=f"Reviewer feedback, please revise:\n{review.feedback}", name=node_id)],
        }

    run.__name__ = node_id
    return run
