from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import settings

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_NGRAM_SIZES = (2, 3)


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
    """Zero-dependency hashed n-gram TF-IDF embedder.

    Used as a fallback when no embedding API key is configured so the
    repository search still works locally. Deterministic and fast.
    """

    def __init__(self, dim: int = 4096) -> None:
        self._dim = dim
        self._df: dict[tuple[int, int], int] = {}
        self._n_docs = 0
        self._fitted = False

    def _tokens(self, text: str) -> list[tuple[int, int]]:
        lower = text.lower()
        words = _WORD_RE.findall(lower)
        tokens: list[tuple[int, int]] = []
        for n in _NGRAM_SIZES:
            for i in range(max(0, len(words) - n + 1)):
                gram = " ".join(words[i : i + n])
                tokens.append((n, hash(gram) % self._dim))
        return tokens

    def _fit(self, texts: list[str]) -> None:
        if self._fitted:
            return
        for text in texts:
            seen: set[tuple[int, int]] = set()
            for tok in self._tokens(text):
                if tok not in seen:
                    seen.add(tok)
                    self._df[tok] = self._df.get(tok, 0) + 1
            self._n_docs += 1
        self._fitted = True

    def _vector(self, text: str) -> list[float]:
        import numpy as np

        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = self._tokens(text)
        if not tokens:
            return vec.tolist()
        n = len(tokens)
        for tok in tokens:
            tf = 1.0 + math.log(n)
            idf = math.log((self._n_docs + 1) / (self._df.get(tok, 0) + 1)) + 1
            vec[tok[1]] += tf * idf
        norm = float(np.linalg.norm(vec)) or 1.0
        return (vec / norm).tolist()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self._fit(texts)
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        if not self._fitted:
            return self._vector(text)
        return self._vector(text)

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
