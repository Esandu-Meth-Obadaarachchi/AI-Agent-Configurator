"""Web search tool, backed by the Tavily search API."""

from __future__ import annotations

import httpx
from langchain_core.tools import BaseTool, tool

from app.config import get_settings

TAVILY_URL = "https://api.tavily.com/search"


def format_results(results: list[dict]) -> str:
    if not results:
        return "No results."
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(f"[{i}] {r.get('title', '')}\n{r.get('url', '')}\n{(r.get('content') or '').strip()[:600]}")
    return "\n\n".join(lines)


def make_web_search_tools(max_results: int = 5) -> list[BaseTool]:
    @tool
    async def web_search(query: str) -> str:
        """Search the web. Returns titles, URLs and snippets. Use for current events or facts you aren't sure of."""
        key = get_settings().tavily_api_key
        if not key:
            return "Web search is not configured: set TAVILY_API_KEY in .env."
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                TAVILY_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={"query": query, "max_results": max_results},
            )
        if res.status_code != 200:
            return f"Search failed with HTTP {res.status_code}: {res.text[:200]}"
        return format_results(res.json().get("results", []))

    return [web_search]
