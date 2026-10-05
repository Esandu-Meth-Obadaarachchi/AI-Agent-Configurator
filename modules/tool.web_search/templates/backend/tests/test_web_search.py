from __future__ import annotations

from app.tools.web_search import format_results, make_web_search_tools


def test_format_results() -> None:
    out = format_results([{"title": "LangGraph", "url": "https://example.com", "content": "Graphs for agents"}])
    assert "[1] LangGraph" in out and "https://example.com" in out


async def test_missing_key_is_explained() -> None:
    (tool,) = make_web_search_tools()
    assert "TAVILY_API_KEY" in await tool.ainvoke({"query": "hello"})
