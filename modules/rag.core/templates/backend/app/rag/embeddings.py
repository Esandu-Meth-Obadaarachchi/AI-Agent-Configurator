"""Embedding models. Each turns text into vectors of a fixed size."""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
from functools import lru_cache
from typing import Any, Protocol

from app.config import get_settings


class Embedder(Protocol):
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(self, model: str, dim: int) -> None:
        self.model, self.dim = model, dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=get_settings().openai_api_key)
        out: list[list[float]] = []
        for i in range(0, len(texts), 256):
            res = await client.embeddings.create(model=self.model, input=texts[i : i + 256])
            out.extend(d.embedding for d in res.data)
        return out


class LocalEmbedder:
    """BAAI/bge-small-en-v1.5 on CPU via fastembed. Downloads ~130 MB on first use."""

    dim = 384

    def __init__(self) -> None:
        self._model: Any = None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def run() -> list[list[float]]:
            from fastembed import TextEmbedding

            if self._model is None:
                self._model = TextEmbedding("BAAI/bge-small-en-v1.5")
            return [v.tolist() for v in self._model.embed(texts)]

        return await asyncio.to_thread(run)


class FakeEmbedder:
    """Deterministic hashing embedder for tests and demo mode. Not for real use."""

    dim = 64

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for word in re.findall(r"\w+", text.lower()):
                h = int(hashlib.md5(word.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


@lru_cache
def get_embedder(name: str) -> Embedder:
    settings = get_settings()
    demo_without_key = settings.llm_provider == "fake" and name.startswith("openai") and not settings.openai_api_key
    if settings.embeddings_override == "fake" or demo_without_key:
        return FakeEmbedder()
    if name == "openai_small":
        return OpenAIEmbedder("text-embedding-3-small", 1536)
    if name == "openai_large":
        return OpenAIEmbedder("text-embedding-3-large", 3072)
    if name == "local_bge_small":
        return LocalEmbedder()
    raise ValueError(f"Unknown embedding '{name}'")
