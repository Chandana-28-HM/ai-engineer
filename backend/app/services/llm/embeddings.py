from __future__ import annotations

import re
import zlib
from abc import ABC, abstractmethod

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import settings

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_NGRAM_SIZES = (1, 2, 3)


class Embedder(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        ...


class GeminiEmbedder(Embedder):
    """Embeddings via Gemini's text-embedding model."""

    def __init__(self) -> None:
        self._client = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )
        self._dim = 768

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._client.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._client.aembed_query(text)

    @property
    def dim(self) -> int:
        return self._dim


class LocalEmbedder(Embedder):
    """Zero-dependency hashed word/ngram embeddings (stateless, deterministic).

    Used as a fallback when no embedding API key is configured so repository
    search still works locally. Vectors are consistent across processes, so
    indexed data remains searchable after a server restart.
    """

    def __init__(self, dim: int | None = None) -> None:
        self._dim = dim or settings.embedding_dim

    def _tokens(self, text: str) -> list[tuple[int, float]]:
        lower = text.lower()
        words = _WORD_RE.findall(lower)
        tokens: list[tuple[int, float]] = []
        for n in _NGRAM_SIZES:
            for i in range(max(0, len(words) - n + 1)):
                gram = " ".join(words[i : i + n])
                h = zlib.crc32(gram.encode("utf-8"))
                idx = h % self._dim
                sign = 1.0 if (h >> 31) & 1 else -1.0
                tokens.append((idx, sign))
        return tokens

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        import numpy as np

        vec = np.zeros(self._dim, dtype=np.float32)
        for idx, sign in self._tokens(text):
            vec[idx] += sign
        norm = float(np.linalg.norm(vec)) or 1.0
        return (vec / norm).tolist()

    @property
    def dim(self) -> int:
        return self._dim


def get_embedder() -> Embedder:
    provider = (settings.embedding_provider or "").lower()
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiEmbedder()
    return LocalEmbedder()


# Cache embedder instance across requests
_EMBEDDER: Embedder | None = None


def embedder() -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = get_embedder()
    return _EMBEDDER
