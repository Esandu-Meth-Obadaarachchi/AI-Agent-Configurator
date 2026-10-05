"""Tool sets, keyed by the id of the block that provides them on the canvas.

An agent's tools are the union of the tool sets attached to it (see app/graph.py).
"""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

log = logging.getLogger(__name__)

Toolsets = dict[str, list[BaseTool]]


async def build_toolsets() -> Toolsets:
    sets: Toolsets = {}

    # Orders API
    from app.tools.http_orders import get_order

    sets["orders"] = [get_order]

    # Help centre (knowledge base, as a search tool)
    from app.tools.knowledge import make_knowledge_tool

    sets["helpdocs"] = [make_knowledge_tool("helpdocs")]
    log.info("tool sets ready: %s", {name: [t.name for t in tools] for name, tools in sets.items()})
    return sets
