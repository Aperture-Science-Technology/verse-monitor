"""Retriever service (Qdrant)."""

import os
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.http import models
from verse_mcp.constants import VECTOR_COLLECTION_NAME, QDRANT_TIMEOUT


@dataclass
class Chunk:
    content: str
    source: str
    url: str
    patch_version: str | None = None

_qdrant_client: QdrantClient | None = None


async def init_qdrant() -> None:
    global _qdrant_client
    qdrant_url = os.getenv("QDRANT_URL")
    if not qdrant_url:
        raise RuntimeError("QDRANT_URL not set")
    _qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=QDRANT_TIMEOUT,
    )
    # Ensure collection exists
    collections = _qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]
    if VECTOR_COLLECTION_NAME not in collection_names:
        _qdrant_client.create_collection(
            collection_name=VECTOR_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=1536,  # from constants.EMBEDDING_DIMENSIONS
                distance=models.Distance.COSINE,
            ),
        )


async def close_qdrant() -> None:
    global _qdrant_client
    if _qdrant_client:
        _qdrant_client.close()
        _qdrant_client = None


async def search_chunks(
    embedding: list[float],
    top_k: int = 5,
    category: str | None = None,
) -> list:
    """Search Qdrant for similar chunks."""
    if not _qdrant_client:
        raise RuntimeError("Qdrant not initialized")
    
    query_filter = None
    if category:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="category", match=models.MatchValue(value=category))]
        )
    
    response = _qdrant_client.query_points(
        collection_name=VECTOR_COLLECTION_NAME,
        query=embedding,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    chunks = []
    for point in response.points:
        payload = point.payload
        chunks.append(
            Chunk(
                content=payload.get("content", ""),
                source=payload.get("source", ""),
                url=payload.get("url", ""),
                patch_version=payload.get("patch_version"),
            )
        )
    return chunks