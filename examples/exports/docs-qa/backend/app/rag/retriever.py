"""Search a knowledge base: vector search, optional keyword fusion, optional reranking."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings
from app.rag.embeddings import get_embedder
from app.rag.stores import Hit, MemoryStore, VectorStore

if TYPE_CHECKING:
    from app.rag.registry import KnowledgeConfig


def reciprocal_rank_fusion(rankings: list[list[Hit]], k: int = 60) -> list[Hit]:
    """Merge rankings: each hit scores sum(1 / (k + rank)). Robust to different score scales."""
    scores: dict[str, float] = {}
    first: dict[str, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank)
            first.setdefault(hit.id, hit)
    ordered = sorted(scores, key=lambda i: -scores[i])
    return [Hit(id=i, content=first[i].content, source=first[i].source, score=scores[i]) for i in ordered]


def make_store(cfg: KnowledgeConfig, dim: int) -> VectorStore:
    override = get_settings().vector_store_override
    if override == "memory":
        return MemoryStore()
    if cfg.vector_store == "pgvector":
        from app.rag.store_pgvector import PgVectorStore

        return PgVectorStore(cfg.id, dim)
    raise ValueError(f"Unknown vector store '{cfg.vector_store}'")


class KnowledgeBase:
    def __init__(self, cfg: KnowledgeConfig) -> None:
        self.cfg = cfg
        self.embedder = get_embedder(cfg.embedding)
        self.store = make_store(cfg, self.embedder.dim)

    async def search(self, query: str, top_k: int | None = None) -> list[Hit]:
        k = top_k or self.cfg.top_k
        if not query.strip():
            return []
        reranker = get_settings().reranker_override or self.cfg.reranker
        pool = k * 4 if (self.cfg.retrieval == "hybrid" or reranker != "none") else k
        (vector,) = await self.embedder.embed([query])
        hits = await self.store.dense(vector, pool)
        if self.cfg.retrieval == "hybrid":
            hits = reciprocal_rank_fusion([hits, await self.store.keyword(query, pool)])
        if hits and reranker != "none":
            hits = await self.rerank(reranker, query, hits[:pool])
        return hits[:k]

    async def rerank(self, reranker: str, query: str, hits: list[Hit]) -> list[Hit]:
        return hits

    async def count(self) -> int:
        return await self.store.count()
