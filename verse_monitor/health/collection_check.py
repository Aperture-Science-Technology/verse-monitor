"""Collection health checks for Qdrant.

Verifies existence, vector dimension, and point count for both
sc_events (monitor) and sc_chunks (MCP RAG) collections.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class CollectionHealth:
    """Health status of a single Qdrant collection."""
    name: str
    exists: bool
    dimension: int | None = None
    expected_dimension: int | None = None
    point_count: int | None = None
    status: str = "unknown"  # "healthy", "missing", "dimension_mismatch", "empty", "error"
    error: str = ""

    @property
    def is_healthy(self) -> bool:
        if not self.exists:
            return False
        if self.dimension is not None and self.expected_dimension is not None:
            if self.dimension != self.expected_dimension:
                return False
        return self.status == "healthy"


async def check_collection(
    client,
    collection_name: str,
    expected_dimension: int,
) -> CollectionHealth:
    """Check a single Qdrant collection for existence, dimension, and point count.

    Args:
        client: QdrantClient instance (sync — will be called via asyncio.to_thread)
        collection_name: Name of the collection to check
        expected_dimension: Expected vector dimension

    Returns:
        CollectionHealth with full status
    """
    health = CollectionHealth(
        name=collection_name,
        exists=False,
        expected_dimension=expected_dimension,
    )

    try:
        # Check existence
        collections = await asyncio.to_thread(client.get_collections)
        collection_names = [c.name for c in collections.collections]

        if collection_name not in collection_names:
            health.status = "missing"
            health.error = f"Collection '{collection_name}' does not exist"
            logger.warning("Collection '%s' not found in Qdrant", collection_name)
            return health

        health.exists = True

        # Check dimension
        info = await asyncio.to_thread(client.get_collection, collection_name)
        dim = info.config.params.vectors.size
        health.dimension = dim

        if dim != expected_dimension:
            health.status = "dimension_mismatch"
            health.error = (
                f"Dimension mismatch: expected {expected_dimension}, got {dim}"
            )
            logger.error(
                "Collection '%s' dimension mismatch: expected %d, got %d",
                collection_name,
                expected_dimension,
                dim,
            )
            return health

        # Check point count
        count_result = await asyncio.to_thread(
            client.count,
            collection_name=collection_name,
            exact=True,
        )
        health.point_count = count_result.count

        if health.point_count == 0:
            health.status = "empty"
            logger.warning("Collection '%s' is empty (0 points)", collection_name)
        else:
            health.status = "healthy"
            logger.debug(
                "Collection '%s' healthy: %d points, dim=%d",
                collection_name,
                health.point_count,
                dim,
            )

    except Exception as exc:
        health.status = "error"
        health.error = str(exc)
        logger.error(
            "Error checking collection '%s': %s", collection_name, exc, exc_info=True
        )

    return health


async def check_all_collections(
    events_client,
    chunks_client,
    events_collection: str,
    chunks_collection: str,
    expected_dimension: int,
) -> dict:
    """Check both sc_events and sc_chunks collections concurrently.

    Returns a dict suitable for inclusion in the /health endpoint response.
    """
    events_health, chunks_health = await asyncio.gather(
        check_collection(events_client, events_collection, expected_dimension),
        check_collection(chunks_client, chunks_collection, expected_dimension),
    )

    overall = "healthy"
    for h in (events_health, chunks_health):
        if not h.is_healthy:
            overall = "degraded"
            break

    return {
        "status": overall,
        "collections": {
            events_collection: asdict(events_health),
            chunks_collection: asdict(chunks_health),
        },
    }
