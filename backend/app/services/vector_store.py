from __future__ import annotations

import asyncio
from uuid import uuid4

from qdrant_client import QdrantClient, models

from app.config import settings

COLLECTION = "code_chunks"


class VectorStore:
    """Qdrant-backed vector store (local disk mode when no server is configured)."""

    def __init__(self) -> None:
        self.client = QdrantClient(path=str(settings.qdrant_path))
        self._ensure_collection(settings.embedding_dim)

    def _ensure_collection(self, dim: int) -> None:
        collections = [c.name for c in self.client.get_collections().collections]
        if COLLECTION not in collections:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
            )

    async def upsert(self, repo_id: int, vectors: list[list[float]], payloads: list[dict]) -> int:
        points = [
            models.PointStruct(
                id=str(uuid4()),
                vector=vec,
                payload={**payload, "repo_id": repo_id},
            )
            for vec, payload in zip(vectors, payloads, strict=False)
        ]
        await asyncio.to_thread(
            self.client.upsert,
            collection_name=COLLECTION,
            points=points,
        )
        return len(points)

    async def search(self, repo_id: int, vector: list[float], limit: int = 5) -> list[dict]:
        hits = await asyncio.to_thread(
            self.client.search,
            collection_name=COLLECTION,
            query_vector=vector,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
            ),
            limit=limit,
            with_payload=True,
        )
        results: list[dict] = []
        for hit in hits:
            results.append(
                {
                    "file_path": hit.payload.get("file_path", ""),
                    "language": hit.payload.get("language", ""),
                    "content": hit.payload.get("content", ""),
                    "start_line": hit.payload.get("start_line", 0),
                    "score": round(float(hit.score), 4),
                }
            )
        return results

    async def delete_repo(self, repo_id: int) -> None:
        await asyncio.to_thread(
            self.client.delete,
            collection_name=COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
                )
            ),
        )

    async def count(self, repo_id: int) -> int:
        result = await asyncio.to_thread(
            self.client.count,
            collection_name=COLLECTION,
            count_filter=models.Filter(
                must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
            ),
        )
        return result.count


vector_store = VectorStore()
