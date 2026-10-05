"""A knowledge base exposed to an agent as a search tool."""

from __future__ import annotations

import re

from langchain_core.tools import BaseTool, StructuredTool

from app.rag.registry import KNOWLEDGE_BASES, get_knowledge_base


def make_knowledge_tool(kb_id: str) -> BaseTool:
    cfg = KNOWLEDGE_BASES[kb_id]

    async def search(query: str) -> str:
        hits = await get_knowledge_base(kb_id).search(query)
        if not hits:
            return "No matching passages."
        return "\n\n".join(f"[{i}] (source: {h.source})\n{h.content}" for i, h in enumerate(hits, start=1))

    name = "search_" + re.sub(r"[^a-z0-9_]", "_", kb_id.lower())
    return StructuredTool.from_function(
        coroutine=search,
        name=name,
        description=f"Search {cfg.label}: {cfg.description}. Returns numbered passages with their source file.",
    )
