"""Read a web page as clean text."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import BaseTool, tool


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return f"{title}\n\n{text}" if title else text


def make_web_fetch_tools(max_chars: int = 12000) -> list[BaseTool]:
    @tool
    async def read_web_page(url: str) -> str:
        """Fetch a web page and return its readable text. Use after a search to read a promising result."""
        if not url.startswith(("http://", "https://")):
            return "Only http and https URLs are supported."
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (agent)"}) as client:
                res = await client.get(url)
        except httpx.HTTPError as exc:
            return f"Could not fetch {url}: {exc}"
        if res.status_code >= 400:
            return f"Could not fetch {url}: HTTP {res.status_code}"
        kind = res.headers.get("content-type", "")
        text = html_to_text(res.text) if "html" in kind else res.text
        return text[:max_chars] + ("\n\n[truncated]" if len(text) > max_chars else "")

    return [read_web_page]
