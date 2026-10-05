"""Chroma vector store: an embedded index in a local folder."""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.rag.stores import Chunk, Hit, bm25_rank


class ChromaStore:
    def __init__(self, kb_id: str) -> None:
        import chromadb

        client = chromadb.PersistentClient(path=get_settings().chroma_path)
        self.collection: Any = client.get_or_create_collection(name=f"kb_{kb_id}", metadata={"hnsw:space": "cosine"})
        self._corpus: list[tuple[str, str, str]] | None = None  # cached for keyword search

    async def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        await asyncio.to_thread(
            self.collection.upsert,
            ids=[c.id for c in chunks],
            embeddings=vectors,
            documents=[c.content for c in chunks],
            metadatas=[{"source": c.source, **{k: str(v) for k, v in c.metadata.items()}} for c in chunks],
        )
        self._corpus = None

    async def delete_source(self, source: str) -> None:
        await asyncio.to_thread(self.collection.delete, where={"source": source})
        self._corpus = None

    async def dense(self, vector: list[float], k: int) -> list[Hit]:
        res = await asyncio.to_thread(self.collection.query, query_embeddings=[vector], n_results=k)
        hits = []
        for id_, doc, meta, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0], strict=False):
            hits.append(Hit(id=id_, content=doc, source=str((meta or {}).get("source", "")), score=1.0 - float(dist)))
        return hits

    async def keyword(self, query: str, k: int) -> list[Hit]:
        if self._corpus is None:
            got = await asyncio.to_thread(self.collection.get, include=["documents", "metadatas"])
            self._corpus = [
                (i, d, str((m or {}).get("source", ""))) for i, d, m in zip(got["ids"], got["documents"], got["metadatas"], strict=False)
            ]
        return bm25_rank(query, self._corpus, k)

    async def count(self) -> int:
        return int(await asyncio.to_thread(self.collection.count))
