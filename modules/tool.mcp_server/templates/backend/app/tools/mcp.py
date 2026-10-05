"""Load every tool an MCP (Model Context Protocol) server offers."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

log = logging.getLogger(__name__)


async def load_mcp_tools(name: str, connection: dict[str, Any]) -> list[BaseTool]:
    """Connect to one MCP server and return its tools.

    A server that can't be reached is logged and skipped, so one broken server
    doesn't stop the whole app from starting.
    """
    try:
        client = MultiServerMCPClient({name: connection})  # type: ignore[dict-item]
        tools = await client.get_tools()
    except Exception as exc:
        log.warning("MCP server '%s' unavailable, continuing without it: %s", name, exc)
        return []
    log.info("MCP server '%s': %d tools", name, len(tools))
    return list(tools)
