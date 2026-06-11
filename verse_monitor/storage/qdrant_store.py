"""Stockage Qdrant : collection sc_events pour les événements RSI.

Vecteurs dummy (dim=3) — la valeur est dans les payload/filtres, pas la similarité.
Index payload sur : type, priority, source, category, timestamp_ts, keywords.
"""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from verse_monitor.config import settings
from verse_monitor.models import Priority, SCEvent

logger = logging.getLogger(__name__)

DUMMY_VECTOR = [0.0, 0.0, 0.0]
COLLECTION = settings.QDRANT_COLLECTION


def get_qdrant_client() -> QdrantClient:
    """Crée un client Qdrant."""
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=10,
    )


async def ensure_collection(qdrant_client: QdrantClient) -> None:
    """Crée la collection sc_events si absente, vérifie la dimension si existante."""
    from qdrant_client.http import models as qm

    collections = [c.name for c in qdrant_client.get_collections().collections]
    if COLLECTION in collections:
        info = qdrant_client.get_collection(COLLECTION)
        dim = info.config.params.vectors.size
        if dim != len(DUMMY_VECTOR):
            logger.warning(
                f"Collection {COLLECTION} existe avec dim={dim}, attendu={len(DUMMY_VECTOR)}. "
                "Ne supprime pas automatiquement — l'opérateur doit décider."
            )
        return

    qdrant_client.create_collection(
        collection_name=COLLECTION,
        vectors_config=qm.VectorParams(size=len(DUMMY_VECTOR), distance=qm.Distance.COSINE),
    )
    qdrant_client.create_payload_index(COLLECTION, field_name="type", field_type="keyword")
    qdrant_client.create_payload_index(COLLECTION, field_name="priority", field_type="keyword")
    qdrant_client.create_payload_index(COLLECTION, field_name="source", field_type="keyword")
    qdrant_client.create_payload_index(COLLECTION, field_name="category", field_type="keyword")
    qdrant_client.create_payload_index(COLLECTION, field_name="timestamp_ts", field_type="float")
    qdrant_client.create_payload_index(COLLECTION, field_name="keywords", field_type="keyword")
    logger.info(f"Collection {COLLECTION} créée")


async def store_event(event: SCEvent) -> None:
    """Stocke un événement dans Qdrant (upsert)."""
    import asyncio
    from uuid import NAMESPACE_URL, uuid5

    client = get_qdrant_client()
    await ensure_collection(client)

    point_id = str(uuid5(NAMESPACE_URL, f"sc_event:{event.id}"))
    payload = event.model_dump(mode="json")
    payload["timestamp_ts"] = event.timestamp.timestamp()

    await asyncio.to_thread(
        client.upsert,
        collection_name=COLLECTION,
        points=[models.PointStruct(id=point_id, vector=DUMMY_VECTOR, payload=payload)],
    )


async def get_events(
    since_ts: float | None = None,
    priority_min: Priority | None = None,
    event_type: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Récupère des événements depuis Qdrant avec filtres combinés."""
    import asyncio

    client = get_qdrant_client()
    await ensure_collection(client)

    filters: list[models.Condition] = []

    if since_ts is not None:
        filters.append(models.FieldCondition(key="timestamp_ts", range=models.Range(gte=since_ts)))

    if priority_min is not None:
        priorities = _priorities_above(priority_min)
        filters.append(models.FieldCondition(key="priority", match=models.MatchAny(any=priorities)))

    if event_type is not None:
        filters.append(models.FieldCondition(key="type", match=models.MatchValue(value=event_type)))

    if category is not None:
        filters.append(models.FieldCondition(key="category", match=models.MatchValue(value=category)))

    result = await asyncio.to_thread(
        client.scroll,
        collection_name=COLLECTION,
        scroll_filter=models.Filter(must=filters) if filters else None,
        limit=limit,
        with_payload=True,
        order_by=models.OrderBy(key="timestamp_ts", direction="desc"),
    )

    return [point.payload for point in result[0] if point.payload]


def _priorities_above(min_priority: Priority) -> list[str]:
    """Retourne la liste des priorités >= min_priority."""
    order = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
    idx = order.index(min_priority)
    return [p.value for p in order[idx:]]
