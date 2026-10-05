"""The knowledge bases in this app, as configured on the canvas."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.retriever import KnowledgeBase


@dataclass(frozen=True)
class KnowledgeConfig:
    id: str
    label: str
    description: str
    sources: tuple[str, ...]
    chunker: str
    chunk_size: int
    overlap: int
    embedding: str
    vector_store: str
    retrieval: str
    top_k: int
    reranker: str


KNOWLEDGE_BASES: dict[str, KnowledgeConfig] = {
    "docs": KnowledgeConfig(
        id="docs",
        label="Company docs",
        description="Company policies, handbooks and product docs",
        sources=("pdf", "markdown"),
        chunker="recursive",
        chunk_size=800,
        overlap=100,
        embedding="local_bge_small",
        vector_store="pgvector",
        retrieval="hybrid",
        top_k=6,
        reranker="none",
    ),
}

_instances: dict[str, KnowledgeBase] = {}


def get_knowledge_base(kb_id: str) -> KnowledgeBase:
    if kb_id not in _instances:
        _instances[kb_id] = KnowledgeBase(KNOWLEDGE_BASES[kb_id])
    return _instances[kb_id]
