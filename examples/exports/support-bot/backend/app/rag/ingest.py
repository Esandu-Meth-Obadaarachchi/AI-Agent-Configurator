"""Add documents to a knowledge base.

From the command line (re-running is safe: a file's old chunks are replaced):

    python -m app.rag.ingest <knowledge_base_id> data/docs
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

from app.rag.chunking import split
from app.rag.loaders import EXTENSIONS, load_bytes
from app.rag.registry import KNOWLEDGE_BASES, get_knowledge_base
from app.rag.stores import Chunk

SUPPORTED = tuple(ext for exts in EXTENSIONS.values() for ext in exts)


def allowed_extensions(kb_id: str) -> tuple[str, ...]:
    cfg = KNOWLEDGE_BASES[kb_id]
    return tuple(ext for kind in cfg.sources for ext in EXTENSIONS[kind])


async def ingest_bytes(kb_id: str, name: str, data: bytes) -> int:
    kb = get_knowledge_base(kb_id)
    cfg = kb.cfg
    text = load_bytes(name, data)
    pieces = split(text, cfg.chunker, cfg.chunk_size, cfg.overlap)
    chunks = [
        Chunk(id=hashlib.sha1(f"{kb_id}:{name}:{i}".encode()).hexdigest(), content=p, source=name, metadata={"chunk": i})
        for i, p in enumerate(pieces)
    ]
    await kb.store.delete_source(name)
    if chunks:
        vectors = await kb.embedder.embed([c.content for c in chunks])
        await kb.store.add(chunks, vectors)
    return len(chunks)


async def ingest_paths(kb_id: str, paths: list[Path]) -> int:
    exts = allowed_extensions(kb_id)
    total = 0
    for root in paths:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for f in files:
            if f.suffix.lower() in exts:
                n = await ingest_bytes(kb_id, f.name, f.read_bytes())
                print(f"{f}: {n} chunks")
                total += n
    return total


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in KNOWLEDGE_BASES:
        print(f"usage: python -m app.rag.ingest <{'|'.join(KNOWLEDGE_BASES)}> [paths...]")
        raise SystemExit(2)
    kb_id = sys.argv[1]
    paths = [Path(p) for p in sys.argv[2:]] or [Path("data/docs")]
    total = asyncio.run(ingest_paths(kb_id, paths))
    print(f"Added {total} chunks to '{kb_id}'.")


if __name__ == "__main__":
    main()
