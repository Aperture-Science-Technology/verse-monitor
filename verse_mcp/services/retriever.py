"""Retriever service (Qdrant)."""

import asyncio
import logging
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.http import models
from verse_mcp.constants import VECTOR_COLLECTION_NAME, QDRANT_TIMEOUT, EMBEDDING_DIMENSIONS
from verse_monitor.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    content: str
    source: str
    url: str
    patch_version: str | None = None

_qdrant_client: QdrantClient | None = None


async def _ensure_collection_with_dimension() -> None:
    """Ensure the sc_chunks collection exists with the correct dimension.

    If the collection exists but has the wrong dimension, it is deleted
    and recreated. This prevents the 'expected dim: 3, got 1536' error.
    """
    assert _qdrant_client is not None
    collections = await asyncio.to_thread(_qdrant_client.get_collections)
    collection_names = [c.name for c in collections.collections]

    if VECTOR_COLLECTION_NAME in collection_names:
        info = await asyncio.to_thread(
            _qdrant_client.get_collection, VECTOR_COLLECTION_NAME
        )
        dim = info.config.params.vectors.size
        if dim != EMBEDDING_DIMENSIONS:
            logger.warning(
                "Collection '%s' has dimension %d but expected %d. Recreating.",
                VECTOR_COLLECTION_NAME,
                dim,
                EMBEDDING_DIMENSIONS,
            )
            await asyncio.to_thread(
                _qdrant_client.delete_collection, VECTOR_COLLECTION_NAME
            )
            await asyncio.to_thread(
                _qdrant_client.create_collection,
                collection_name=VECTOR_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSIONS,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Recreated '%s' with dim=%d", VECTOR_COLLECTION_NAME, EMBEDDING_DIMENSIONS)
        return

    await asyncio.to_thread(
        _qdrant_client.create_collection,
        collection_name=VECTOR_COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=EMBEDDING_DIMENSIONS,
            distance=models.Distance.COSINE,
        ),
    )
    logger.info("Created '%s' with dim=%d", VECTOR_COLLECTION_NAME, EMBEDDING_DIMENSIONS)


async def init_qdrant() -> None:
    global _qdrant_client
    _qdrant_client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=QDRANT_TIMEOUT,
    )
    # Ensure collection exists with correct dimension
    await _ensure_collection_with_dimension()


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
    
    response = await asyncio.to_thread(
        _qdrant_client.query_points,
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