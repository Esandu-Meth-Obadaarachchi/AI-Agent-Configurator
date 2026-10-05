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

    # Web search
    from app.tools.web_search import make_web_search_tools

    sets["search"] = make_web_search_tools(max_results=5)

    # Read web page
    from app.tools.web_fetch import make_web_fetch_tools

    sets["read"] = make_web_fetch_tools(max_chars=12000)

    # Calculator
    from app.tools.calculator import calculator

    sets["calc"] = [calculator]
    log.info("tool sets ready: %s", {name: [t.name for t in tools] for name, tools in sets.items()})
    return sets
