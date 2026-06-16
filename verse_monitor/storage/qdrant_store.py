from __future__ import annotations

import asyncio
import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from verse_monitor.config import settings
from verse_monitor.models import Priority, SCEvent
from verse_mcp.services.embeddings import generate_embedding

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 1536
COLLECTION = settings.QDRANT_COLLECTION


def build_embedding_text(event: SCEvent) -> str:
    diff_lines = "\n".join(f"  {k}: {v}" for k, v in event.diff.items())
    return (
        f"Star Citizen {event.type.value} event:\n"
        f"Title: {event.title}\n"
        f"Category: {event.category or 'unknown'}\n"
        f"Priority: {event.priority.value}\n"
        f"Source: {event.source}\n"
        f"Author: {event.author or 'CIG'}\n"
        f"Keywords: {', '.join(event.keywords)}\n"
        f"Patch Version: {event.patch_version or 'N/A'}\n"
        f"Diff:\n{diff_lines}\n"
        f"URL: {event.url}"
    )


class QdrantStore:
    def __init__(self) -> None:
        self._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )

    def ensure_collection(self) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if COLLECTION in existing:
            info = self._client.get_collection(COLLECTION)
            dim = info.config.params.vectors.size
            if dim != EMBEDDING_DIMENSIONS:
                logger.warning(
                    "Collection '%s' has dimension %d but expected %d. "
                    "Please manually delete and recreate the collection to use real embeddings.",
                    COLLECTION,
                    dim,
                    EMBEDDING_DIMENSIONS,
                )
            return

        self._client.create_collection(
            collection_name=COLLECTION,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d)", COLLECTION, EMBEDDING_DIMENSIONS)

    async def store_event(self, event: SCEvent) -> None:
        text = build_embedding_text(event)
        vector = await generate_embedding(text)

        payload: dict[str, Any] = {
            "id": event.id,
            "type": event.type.value,
            "priority": event.priority.value,
            "source": event.source,
            "title": event.title,
            "url": event.url,
            "keywords": event.keywords,
            "timestamp": event.timestamp.isoformat(),
            "content_hash": event.content_hash,
            "patch_version": event.patch_version,
            "author": event.author,
            "category": event.category,
            "diff": event.diff,
        }

        await asyncio.to_thread(
            self._client.upsert,
            collection_name=COLLECTION,
            points=[
                models.PointStruct(
                    id=event.id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        logger.debug("Stored event %s (%s) in Qdrant", event.id, event.type.value)

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        vector = await generate_embedding(query)

        qdrant_filter: models.Filter | None = None
        if filters:
            conditions = [
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=value),
                )
                for key, value in filters.items()
            ]
            qdrant_filter = models.Filter(must=conditions)

        results = await asyncio.to_thread(
            self._client.query_points,
            collection_name=COLLECTION,
            query=vector,
            limit=limit,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            {"score": hit.score, **hit.payload}
            for hit in results.points
        ]

    async def delete_event(self, event_id: str) -> None:
        await asyncio.to_thread(
            self._client.delete,
            collection_name=COLLECTION,
            points_selector=models.PointIdsList(points=[event_id]),
        )
        logger.debug("Deleted event %s from Qdrant", event_id)

    async def count(self) -> int:
        result = await asyncio.to_thread(self._client.count, collection_name=COLLECTION, exact=True)
        return result.count


# --- Module-level convenience functions (backward compatibility) ---

_default_store = QdrantStore()


async def ensure_collection() -> None:
    """Module-level wrapper for backward compatibility."""
    _default_store.ensure_collection()


async def store_event(event: SCEvent) -> None:
    """Module-level wrapper for backward compatibility."""
    await _default_store.store_event(event)


async def get_events(
    since_ts: float | None = None,
    priority_min: Priority | None = None,
    event_type: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Module-level wrapper — uses QdrantStore.search with filters."""
    filters: dict[str, Any] = {}
    if event_type is not None:
        filters["type"] = event_type
    if priority_min is not None:
        filters["priority"] = priority_min.value if isinstance(priority_min, Priority) else priority_min
    if category is not None:
        filters["category"] = category
    return await _default_store.search(
        query="event",  # generic query for filtered search
        limit=limit,
        filters=filters if filters else None,
    )
