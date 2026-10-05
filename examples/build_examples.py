"""Build the starter blueprints in examples/specs/.

Blueprints are written in Python so the schema validates them as they are built.
Run: python examples/build_examples.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from configurator_engine.layout import auto_layout
from configurator_spec import dump_spec, parse_spec

OUT = Path(__file__).parent / "specs"

COL = 300  # horizontal spacing between flow steps
FLOW_Y = 160
RES_Y = 440


class B:
    """Tiny builder so blueprints read like a description of the graph."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.extra: dict[str, Any] = {}

    def node(self, id_: str, type_: str, x: float, y: float = FLOW_Y, **data: Any) -> str:
        self.nodes.append({"id": id_, "type": type_, "position": {"x": x, "y": y}, "data": data})
        return id_

    def flow(self, src: str, dst: str, handle: str = "out") -> None:
        self.edges.append({"id": f"e-{src}-{handle}-{dst}", "source": src, "target": dst, "sourceHandle": handle, "targetHandle": "in"})

    def attach(self, res: str, dst: str, handle: str = "tools") -> None:
        self.edges.append({"id": f"a-{res}-{dst}", "source": res, "target": dst, "sourceHandle": "attach", "targetHandle": handle})

    def spec(self, **extra: Any) -> dict[str, Any]:
        raw = {
            "spec_version": "0.2",
            "project": {"name": self.name, "description": self.description},
            "graph": {"nodes": self.nodes, "edges": self.edges},
        }
        raw.update(extra)
        return raw


def docs_qa() -> dict[str, Any]:
    b = B("docs-qa", "Answer questions over your company PDFs and Markdown, with sources.")
    b.node("start", "input", 0, label="Chat input", greeting="Ask me anything about the docs.")
    b.node(
        "assistant",
        "agent",
        COL,
        label="Docs assistant",
        role="Answers questions using the company documents.",
        system_prompt=(
            "You answer questions about the company's documents.\n"
            "Always search the knowledge base before answering. Quote the source file for every claim.\n"
            "If the documents don't contain the answer, say so plainly instead of guessing."
        ),
    )
    b.node("reply", "output", COL * 2, label="Reply")
    b.node("docs", "knowledge", COL - 140, RES_Y, label="Company docs", description="Company policies, handbooks and product docs",
           vector_store="pgvector", retrieval="hybrid", embedding="local_bge_small", top_k=6)
    b.node("memory", "memory", COL + 140, RES_Y, label="Memory", short_term="postgres")
    b.flow("start", "assistant")
    b.flow("assistant", "reply")
    b.attach("docs", "assistant")
    b.attach("memory", "assistant")
    return b.spec()


def rag_pipeline() -> dict[str, Any]:
    b = B("rag-starter", "The classic RAG pipeline: always retrieve, then answer. Runs with one API key.")
    b.node("start", "input", 0, label="Chat input")
    b.node("retrieve", "retriever", COL, label="Find passages")
    b.node(
        "answer",
        "prompt",
        COL * 2,
        label="Answer from passages",
        instructions=(
            "Answer the user's question using only the retrieved passages. "
            "Cite passages as [1], [2]. If they don't answer the question, say you don't know."
        ),
    )
    b.node("reply", "output", COL * 3, label="Reply")
    b.node("kb", "knowledge", COL, RES_Y, label="Notes", description="Your notes and documents",
           vector_store="chroma", embedding="local_bge_small", retrieval="hybrid", reranker="cross_encoder", sources=["pdf", "markdown", "text"])
    b.flow("start", "retrieve")
    b.flow("retrieve", "answer")
    b.flow("answer", "reply")
    b.attach("kb", "retrieve", "knowledge")
    return b.spec()


def support_bot() -> dict[str, Any]:
    b = B("support-bot", "Triage support requests to billing or technical agents. Refunds need a human sign-off.")
    b.node("start", "input", 0, label="Chat input", greeting="Hi! How can we help today?")
    b.node("guard", "guardrail", COL, label="Screen message", redact_pii=True, block_prompt_injection=True)
    b.node(
        "triage",
        "router",
        COL * 2,
        label="Triage",
        mode="llm",
        routes=[
            {"id": "billing", "label": "Billing", "description": "Payments, invoices, refunds, plans", "keywords": ["refund", "invoice", "charge", "billing", "plan"]},
            {"id": "technical", "label": "Technical", "description": "Bugs, errors, how-to questions about the product", "keywords": ["error", "bug", "crash", "how do i"]},
            {"id": "other", "label": "Other", "description": "Greetings and anything else", "keywords": []},
        ],
    )
    b.node("billing", "agent", COL * 3, FLOW_Y - 170, label="Billing agent", role="Handles payments, invoices and refunds.",
           system_prompt="You handle billing questions. Look up the order before discussing it. Offer refunds only when the order qualifies, and explain why.")
    b.node("tech", "agent", COL * 3, FLOW_Y + 40, label="Technical agent", role="Solves product problems using the help centre.",
           system_prompt="You solve technical problems. Search the help centre first, then give numbered steps. Ask for the error message if you need it.")
    b.node("smalltalk", "prompt", COL * 3, FLOW_Y + 250, label="Friendly reply", instructions="Reply briefly and warmly, then ask how you can help with billing or a technical issue.")
    b.node("approve", "approval", COL * 4, FLOW_Y - 170, label="Approve refund", prompt="A billing reply is ready. Approve it before it reaches the customer?")
    b.node("reply", "output", COL * 5, FLOW_Y, label="Reply")
    b.node("orders", "http_api", COL * 3 - 160, RES_Y + 120, label="Orders API", tool_name="get_order", description="Look up an order by its id: status, amount and refund eligibility.",
           method="GET", base_url="https://api.example.com", path="/orders/{order_id}", params=[{"name": "order_id", "location": "path", "description": "The order id, e.g. ORD-1234"}])
    b.node("helpdocs", "knowledge", COL * 3 + 60, RES_Y + 120, label="Help centre", description="Product help-centre articles", vector_store="pgvector", retrieval="hybrid", embedding="local_bge_small")
    b.node("memory", "memory", COL * 4 + 200, RES_Y + 120, label="Memory", short_term="postgres")
    b.flow("start", "guard")
    b.flow("guard", "triage", "pass")
    b.flow("guard", "reply", "blocked")
    b.flow("triage", "billing", "route:billing")
    b.flow("triage", "tech", "route:technical")
    b.flow("triage", "smalltalk", "route:other")
    b.flow("billing", "approve")
    b.flow("approve", "reply", "approved")
    b.flow("approve", "billing", "rejected")
    b.flow("tech", "reply")
    b.flow("smalltalk", "reply")
    b.attach("orders", "billing")
    b.attach("helpdocs", "tech")
    b.attach("memory", "billing")
    return b.spec()


def research_team() -> dict[str, Any]:
    b = B("research-team", "A supervisor runs a researcher, an analyst and a writer, and a reviewer checks the report.")
    b.node("start", "input", 0, label="Chat input", greeting="What should the team research?")
    b.node("lead", "supervisor", COL, label="Research lead", max_rounds=8,
           instructions=(
               "You lead a small research team. Plan the work, then delegate one step at a time:\n"
               "- researcher: finds and reads sources on the web\n- analyst: checks numbers and does calculations\n- writer: drafts the final report\n"
               "Finish once the writer has produced a report that answers the question."
           ))
    b.node("researcher", "agent", COL * 2, FLOW_Y - 200, label="Researcher", role="Finds and reads sources on the web.",
           system_prompt="Search the web, open the most relevant pages and report key facts with their URLs. Prefer primary sources.")
    b.node("analyst", "agent", COL * 2, FLOW_Y, label="Analyst", role="Checks numbers and does calculations.",
           system_prompt="Verify every number the team relies on. Use the calculator for arithmetic. Flag anything that doesn't add up.")
    b.node("writer", "agent", COL * 2, FLOW_Y + 200, label="Writer", role="Writes the final report.",
           system_prompt="Write a clear, well-structured report from the team's findings. Use headings and cite sources inline.")
    b.node("review", "critic", COL * 3 + 80, FLOW_Y, label="Fact check", max_iterations=2,
           criteria="Every claim is supported by a cited source, numbers are consistent, and the report answers the original question.")
    b.node("reply", "output", COL * 4 + 80, FLOW_Y, label="Reply")
    b.node("search", "web_search", COL * 2 - 140, RES_Y + 160, label="Web search")
    b.node("read", "web_fetch", COL * 2 + 60, RES_Y + 160, label="Read web page")
    b.node("calc", "calculator", COL * 2 + 260, RES_Y + 160, label="Calculator")
    b.flow("start", "lead")
    for w in ("researcher", "analyst", "writer"):
        b.flow("lead", w, "delegate")
    b.flow("lead", "review", "done")
    b.flow("review", "reply", "pass")
    b.flow("review", "lead", "revise")
    b.attach("search", "researcher")
    b.attach("read", "researcher")
    b.attach("calc", "analyst")
    return b.spec()


def content_studio() -> dict[str, Any]:
    b = B("content-studio", "Draft, self-review in a loop, then a human approves before publishing.")
    b.node("start", "input", 0, label="Brief", greeting="Describe the piece you need.")
    b.node("writer", "agent", COL, label="Writer", role="Writes on-brand drafts.",
           system_prompt="Write the requested piece. Match the brand voice: plain, warm, specific. When you receive reviewer feedback, revise the whole draft.")
    b.node("editor", "critic", COL * 2, label="Editor review", max_iterations=3,
           criteria="Clear structure, no filler, a concrete call to action, under the requested length, no factual claims without support.")
    b.node("signoff", "approval", COL * 3, label="Publish sign-off", prompt="Approve this draft for publishing?", allow_edit=True)
    b.node("reply", "output", COL * 4, label="Publish")
    b.node("search", "web_search", COL - 100, RES_Y, label="Web search")
    b.flow("start", "writer")
    b.flow("writer", "editor")
    b.flow("editor", "writer", "revise")
    b.flow("editor", "signoff", "pass")
    b.flow("signoff", "reply", "approved")
    b.flow("signoff", "writer", "rejected")
    b.attach("search", "writer")
    return b.spec()


def data_analyst() -> dict[str, Any]:
    b = B("data-analyst", "Ask questions about your database in plain English. Read-only by default.")
    b.node("start", "input", 0, label="Chat input", greeting="What would you like to know about the data?")
    b.node("guard", "guardrail", COL, label="Screen message", blocked_terms=["drop table", "delete from"])
    b.node("analyst", "agent", COL * 2, label="SQL analyst", role="Answers questions by querying the database.",
           system_prompt="Explore the schema first, then write one careful SQL query. Show the query you ran. Never guess column names.")
    b.node("explain", "prompt", COL * 3, label="Explain simply", instructions="Rewrite the analyst's findings for a non-technical reader: the answer first, then two lines of context.")
    b.node("reply", "output", COL * 4, label="Reply")
    b.node("db", "sql_database", COL * 2 - 120, RES_Y, label="Warehouse", dialect="postgres", read_only=True)
    b.node("calc", "calculator", COL * 2 + 120, RES_Y, label="Calculator")
    b.flow("start", "guard")
    b.flow("guard", "analyst", "pass")
    b.flow("guard", "reply", "blocked")
    b.flow("analyst", "explain")
    b.flow("explain", "reply")
    b.attach("db", "analyst")
    b.attach("calc", "analyst")
    return b.spec()


def mcp_assistant() -> dict[str, Any]:
    b = B("mcp-assistant", "A personal assistant with MCP tools and long-term memory of what you tell it.")
    b.node("start", "input", 0, label="Chat input")
    b.node("assistant", "agent", COL, label="Assistant", role="General assistant with file access and memory.",
           system_prompt="You are a helpful assistant. Remember durable facts the user shares (preferences, names, projects) and recall them when relevant.")
    b.node("reply", "output", COL * 2, label="Reply")
    b.node("files", "mcp_server", COL - 200, RES_Y, label="Filesystem (MCP)", server_name="filesystem", transport="stdio",
           command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", "/data"])
    b.node("search", "web_search", COL, RES_Y, label="Web search")
    b.node("memory", "memory", COL + 200, RES_Y, label="Memory", short_term="sqlite", long_term=True)
    b.flow("start", "assistant")
    b.flow("assistant", "reply")
    b.attach("files", "assistant")
    b.attach("search", "assistant")
    b.attach("memory", "assistant")
    return b.spec()


def blank() -> dict[str, Any]:
    b = B("my-agent", "")
    b.node("start", "input", 0, label="Chat input")
    b.node("assistant", "agent", COL, label="Assistant")
    b.node("reply", "output", COL * 2, label="Reply")
    b.flow("start", "assistant")
    b.flow("assistant", "reply")
    return b.spec()


BLUEPRINTS = [
    ("blank", blank, "Single agent", "One agent, ready for tools. The smallest useful loop.", ["starter"], "beginner"),
    ("rag-starter", rag_pipeline, "RAG pipeline", "Always retrieve, then answer with citations. Local embeddings, no second key.", ["rag"], "beginner"),
    ("docs-qa", docs_qa, "Docs Q&A agent", "An agent that searches your documents when it needs to, with memory.", ["rag", "memory"], "beginner"),
    ("support-bot", support_bot, "Support desk", "Guardrail, router, two specialist agents and a human approval for refunds.", ["router", "approval", "rag"], "intermediate"),
    ("research-team", research_team, "Research team", "A supervisor delegates to three workers; a reviewer loops until the report holds up.", ["multi-agent", "loop"], "advanced"),
    ("content-studio", content_studio, "Content studio", "Writer and editor loop, then human sign-off before publishing.", ["loop", "approval"], "intermediate"),
    ("data-analyst", data_analyst, "SQL analyst", "Plain-English questions over your database, read-only, explained simply.", ["tools", "guardrail"], "intermediate"),
    ("mcp-assistant", mcp_assistant, "MCP assistant", "MCP filesystem tools, web search and long-term memory.", ["mcp", "memory"], "intermediate"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for slug, fn, title, blurb, tags, level in BLUEPRINTS:
        raw = fn()
        auto_layout(raw["graph"]["nodes"], raw["graph"]["edges"])
        spec = parse_spec(raw)
        (OUT / f"{slug}.json").write_text(dump_spec(spec), encoding="utf-8")
        index.append({"id": slug, "title": title, "blurb": blurb, "tags": tags, "level": level, "file": f"{slug}.json"})
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(index)} blueprints to {OUT}")


if __name__ == "__main__":
    main()
