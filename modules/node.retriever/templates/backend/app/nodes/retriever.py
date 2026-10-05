"""Retrieve step: search the attached knowledge bases with the latest user message.

Results go into state["context"], which the next model steps add to their system
prompt as numbered passages.
"""

from __future__ import annotations

from typing import Any

from app.events import step
from app.messages import last_user_text
from app.nodes import AsyncNode
from app.rag.registry import get_knowledge_base
from app.state import AppState


def make_retriever_node(
    *,
    node_id: str,
    label: str,
    knowledge: list[str],
    top_k: int | None = None,
) -> AsyncNode:
    async def run(state: AppState) -> dict[str, Any]:
        query = last_user_text(state["messages"])
        step(node_id, "start", f"Searching for: {query[:80]}")
        passages: list[dict[str, Any]] = []
        for kb_id in knowledge:
            for hit in await get_knowledge_base(kb_id).search(query, top_k=top_k):
                passages.append({"content": hit.content, "source": hit.source, "score": round(hit.score, 4)})
        step(node_id, "end", f"{len(passages)} passages found")
        return {"context": {node_id: passages}}

    run.__name__ = node_id
    return run
