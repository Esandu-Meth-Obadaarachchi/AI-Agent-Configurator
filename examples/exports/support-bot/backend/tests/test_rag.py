"""Chunking, ingestion and search, using the in-memory store and fake embedder."""

from __future__ import annotations

from app.rag.chunking import fixed_split, recursive_split
from app.rag.ingest import ingest_bytes
from app.rag.registry import KNOWLEDGE_BASES, get_knowledge_base
from app.rag.retriever import reciprocal_rank_fusion
from app.rag.stores import Hit

TEXT = (
    "Refunds are available within 30 days of purchase.\n\n"
    "To reset your password, open Settings and choose Security.\n\n"
    "Our office is closed on public holidays."
)


def test_recursive_chunks_respect_size() -> None:
    chunks = recursive_split(TEXT * 20, size=200, overlap=40)
    assert chunks
    assert all(len(c) <= 260 for c in chunks)


def test_fixed_chunks_overlap() -> None:
    chunks = fixed_split("abcdefghij" * 10, size=30, overlap=10)
    assert chunks[0][-10:] == chunks[1][:10]


def test_rrf_rewards_agreement() -> None:
    a = [Hit("1", "x", "s", 1.0), Hit("2", "y", "s", 0.5)]
    b = [Hit("2", "y", "s", 9.0), Hit("3", "z", "s", 1.0)]
    assert reciprocal_rank_fusion([a, b])[0].id == "2"


async def test_ingest_then_search() -> None:
    kb_id = "helpdocs"
    added = await ingest_bytes(kb_id, "policy.md", TEXT.encode())
    assert added >= 1
    hits = await get_knowledge_base(kb_id).search("how do refunds work", top_k=2)
    assert hits and "Refunds" in hits[0].content
    assert set(KNOWLEDGE_BASES) == set(["helpdocs"])
