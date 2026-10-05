"""Upgrade older spec versions to the current one.

v0.1 is the flat format from the original brief (``agents.pattern``, ``rag``,
``tools`` at the top level). v0.2 expresses the same choices as a graph. Each
upgrade is a pure function so it can be unit tested and chained.
"""

from __future__ import annotations

from typing import Any

from .models import SPEC_VERSION


class MigrationError(ValueError):
    pass


def _v01_to_v02(old: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    def node(id_: str, type_: str, x: float, y: float, **data: Any) -> None:
        nodes.append({"id": id_, "type": type_, "position": {"x": x, "y": y}, "data": data})

    def edge(src: str, dst: str, sh: str | None = "out", th: str | None = "in") -> None:
        edges.append({"id": f"e_{src}_{sh}_{dst}_{th}", "source": src, "target": dst, "sourceHandle": sh, "targetHandle": th})

    agents = old.get("agents", {}) or {}
    pattern = agents.get("pattern", "single")
    tools = agents.get("tools", []) or []

    node("start", "input", 0, 120, label="Chat input")
    node("reply", "output", 900, 120, label="Reply")

    workers: list[str] = []
    if pattern == "orchestrator":
        node("supervisor", "supervisor", 260, 120, label="Supervisor")
        node("worker", "agent", 560, 300, label="Worker")
        edge("start", "supervisor")
        edge("supervisor", "worker", "delegate", "in")
        edge("supervisor", "reply", "done", "in")
        workers = ["worker"]
    else:
        node("assistant", "agent", 400, 120, label="Assistant")
        edge("start", "assistant")
        edge("assistant", "reply")
        workers = ["assistant"]

    tool_map = {"mcp_client": "mcp_server", "web_search": "web_search", "custom": "custom_tool"}
    for i, t in enumerate(tools):
        new_type = tool_map.get(t)
        if not new_type:
            raise MigrationError(f"unknown v0.1 tool '{t}'")
        tid = f"tool_{new_type}"
        node(tid, new_type, 300 + i * 200, 480)
        for w in workers:
            edge(tid, w, "attach", "tools")

    rag = old.get("rag") or {}
    if rag.get("enabled"):
        ing = rag.get("ingestion", {}) or {}
        emb = (rag.get("embedding", {}) or {}).get("model", "text-embedding-3-small")
        retrieval = rag.get("retrieval", {}) or {}
        reranker = retrieval.get("reranker", "none")
        node(
            "docs",
            "knowledge",
            200,
            480,
            label="Knowledge base",
            sources=[s for s in ing.get("sources", ["pdf", "markdown"]) if s in {"pdf", "markdown", "text", "html"}],
            chunker=ing.get("chunker", "recursive"),
            chunk_size=ing.get("chunk_size", 800),
            overlap=ing.get("overlap", 100),
            embedding="openai_large" if "large" in emb else ("local_bge_small" if "bge" in emb else "openai_small"),
            vector_store=rag.get("vector_store", "pgvector"),
            retrieval=retrieval.get("mode", "hybrid"),
            top_k=retrieval.get("top_k", 6),
            reranker=reranker if reranker in {"none", "cross_encoder", "cohere"} else "none",
        )
        for w in workers:
            edge("docs", w, "attach", "tools")

    memory = old.get("memory", {}) or {}
    if memory.get("short_term"):
        node("memory", "memory", 600, 480, label="Memory", short_term="postgres")

    approvals = (old.get("human_in_loop", {}) or {}).get("approval_nodes", []) or []
    if approvals:
        # One approval before the reply, matching the v0.1 behaviour.
        node("approve", "approval", 700, 120, label="Human approval")
        edges[:] = [e for e in edges if e["target"] != "reply"]
        last = "supervisor" if pattern == "orchestrator" else "assistant"
        sh = "done" if pattern == "orchestrator" else "out"
        edge(last, "approve", sh, "in")
        edge("approve", "reply", "approved", "in")

    llm = old.get("llm", {}) or {}
    ui = old.get("ui", {}) or {}
    deploy = old.get("deploy", {}) or {}
    return {
        "spec_version": "0.2",
        "project": old.get("project", {}),
        "llm": {k: v for k, v in llm.items() if k in {"provider", "model", "temperature", "max_tokens"}},
        "backend": {"language": "python"},
        "graph": {"nodes": nodes, "edges": edges},
        "ui": {"framework": ui.get("framework", "nextjs"), "streaming": ui.get("streaming", True)},
        "deploy": {"target": deploy.get("target", "docker_compose")},
    }


UPGRADES = {"0.1": _v01_to_v02}


def upgrade(raw: dict[str, Any]) -> dict[str, Any]:
    """Return ``raw`` upgraded to the current spec version (input is not mutated)."""
    data = dict(raw)
    version = str(data.get("spec_version", SPEC_VERSION))
    seen = set()
    while version != SPEC_VERSION:
        if version in seen or version not in UPGRADES:
            raise MigrationError(f"don't know how to upgrade spec_version {version!r} to {SPEC_VERSION}")
        seen.add(version)
        data = UPGRADES[version](data)
        version = str(data["spec_version"])
    return data
