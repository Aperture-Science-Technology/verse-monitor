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
    score: float = 0.0

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
    import qdrant_client as _qd_mod
    _qdrant_client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=QDRANT_TIMEOUT,
    )
    # Early-fail explicite : la méthode .query_points (>=1.16) doit être présente
    if not hasattr(_qdrant_client, 'query_points'):
        raise RuntimeError(
            "qdrant-client version incompatible : .query_points introuvable. "
            ">=1.16 requis (API .search() supprimée)."
        )
    logger.info(
        "Qdrant client v%s initialisé (serveur: %s)",
        getattr(_qd_mod, '__version__', '?'),
        settings.QDRANT_URL,
    )
    # Ensure collection exists with correct dimension
    await _ensure_collection_with_dimension()


async def close_qdrant() -> None:
    global _qdrant_client
    if _qdrant_client:
        _qdrant_client.close()
        _qdrant_client = None


# Seuils de confiance par défaut — cosinus ∈ [0, 1]
# En dessous, le résultat est considéré comme hors-sujet forcé.
DEFAULT_SCORE_THRESHOLD = 0.4


async def search_chunks(
    embedding: list[float],
    top_k: int = 5,
    category: str | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> tuple[list, float]:
    """Search Qdrant for similar chunks, filtrés par seuil de score.

    Retourne (chunks_filtrés, max_score_vu).
    chunks_filtrés peut être vide si aucun point ne dépasse le seuil.
    Chaque Chunk a son .score renseigné.
    """
    if not _qdrant_client:
        raise RuntimeError("Qdrant not initialized")

    query_filter = None
    if category:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="category", match=models.MatchValue(value=category))]
        )

    # Récupérer un peu plus de candidates que top_k pour compenser le filtrage
    fetch_limit = max(top_k * 3, top_k + 5)

    response = await asyncio.to_thread(
        _qdrant_client.query_points,
        collection_name=VECTOR_COLLECTION_NAME,
        query=embedding,
        limit=fetch_limit,
        query_filter=query_filter,
        with_payload=True,
        with_vectors=False,
    )

    chunks = []
    max_seen = 0.0
    for point in response.points:
        max_seen = max(max_seen, point.score)
        if point.score < score_threshold:
            continue
        payload = point.payload
        chunks.append(
            Chunk(
                content=payload.get("content", ""),
                source=payload.get("source", ""),
                url=payload.get("url", ""),
                patch_version=payload.get("patch_version"),
                score=point.score,
            )
        )

    # Trier par score décroissant et limiter à top_k
    chunks.sort(key=lambda c: c.score, reverse=True)
    return chunks[:top_k], max_seen