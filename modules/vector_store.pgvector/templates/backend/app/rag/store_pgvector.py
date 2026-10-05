"""pgvector store: vectors and a full-text index in Postgres, one table per knowledge base."""

from __future__ import annotations

import json

import psycopg

from app.config import get_settings
from app.rag.stores import Chunk, Hit


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in v) + "]"


class PgVectorStore:
    def __init__(self, kb_id: str, dim: int) -> None:
        self.table = f"kb_{kb_id}"
        self.dim = dim
        self._ready = False

    async def _conn(self) -> psycopg.AsyncConnection:
        return await psycopg.AsyncConnection.connect(get_settings().database_url, autocommit=True)

    async def _setup(self) -> None:
        if self._ready:
            return
        async with await self._conn() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(
                f"""CREATE TABLE IF NOT EXISTS {self.table} (
                    id text PRIMARY KEY,
                    source text NOT NULL,
                    content text NOT NULL,
                    metadata jsonb NOT NULL DEFAULT '{{}}',
                    embedding vector({self.dim}) NOT NULL,
                    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
                )"""
            )
            await conn.execute(f"CREATE INDEX IF NOT EXISTS {self.table}_tsv ON {self.table} USING gin (tsv)")
            if self.dim <= 2000:  # HNSW indexes support up to 2,000 dimensions
                await conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {self.table}_hnsw ON {self.table} USING hnsw (embedding vector_cosine_ops)"
                )
        self._ready = True

    async def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        await self._setup()
        async with await self._conn() as conn, conn.cursor() as cur:
            await cur.executemany(
                f"""INSERT INTO {self.table} (id, source, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding""",
                [(c.id, c.source, c.content, json.dumps(c.metadata), _vec(v)) for c, v in zip(chunks, vectors, strict=True)],
            )

    async def delete_source(self, source: str) -> None:
        await self._setup()
        async with await self._conn() as conn:
            await conn.execute(f"DELETE FROM {self.table} WHERE source = %s", (source,))

    async def dense(self, vector: list[float], k: int) -> list[Hit]:
        await self._setup()
        async with await self._conn() as conn:
            cur = await conn.execute(
                f"""SELECT id, content, source, 1 - (embedding <=> %s::vector) AS score
                    FROM {self.table} ORDER BY embedding <=> %s::vector LIMIT %s""",
                (_vec(vector), _vec(vector), k),
            )
            rows = await cur.fetchall()
        return [Hit(id=r[0], content=r[1], source=r[2], score=float(r[3])) for r in rows]

    async def keyword(self, query: str, k: int) -> list[Hit]:
        await self._setup()
        async with await self._conn() as conn:
            cur = await conn.execute(
                f"""SELECT id, content, source, ts_rank_cd(tsv, q) AS score
                    FROM {self.table}, websearch_to_tsquery('english', %s) q
                    WHERE tsv @@ q ORDER BY score DESC LIMIT %s""",
                (query, k),
            )
            rows = await cur.fetchall()
        return [Hit(id=r[0], content=r[1], source=r[2], score=float(r[3])) for r in rows]

    async def count(self) -> int:
        await self._setup()
        async with await self._conn() as conn:
            cur = await conn.execute(f"SELECT count(*) FROM {self.table}")
            row = await cur.fetchone()
        return int(row[0]) if row else 0
