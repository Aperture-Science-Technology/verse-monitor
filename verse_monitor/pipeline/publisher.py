"""Publisher : publication d'événements dans Redis Stream avec déduplication.

Utilise redis.asyncio pour la compatibilité async-native.
Déduplication par hash SHA-256 avec TTL configurable.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis
from redis import exceptions as redis_exceptions

from verse_monitor.config import settings
from verse_monitor.models import SCEvent

logger = logging.getLogger(__name__)


def get_redis() -> redis.Redis:
    """Crée une connexion Redis avec auth si password configuré."""
    return redis.from_url(
        settings.REDIS_URL,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
    )


def _content_hash(event: SCEvent) -> str:
    """Calcule un hash SHA-256 unique pour l'événement (type + diff + url)."""
    payload = json.dumps(
        {"type": event.type.value, "diff": event.diff, "url": event.url},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


async def publish_event(event: SCEvent, r: redis.Redis | None = None) -> bool:
    """Publie un événement dans le Redis Stream.

    Retourne True si l'événement a été publié, False s'il est un doublon.
    """
    if r is None:
        r = get_redis()

    h = _content_hash(event)
    dedup_key = f"dedup:{event.type.value}:{h}"

    if await r.exists(dedup_key):
        logger.debug(f"Doublon ignoré: {dedup_key}")
        return False

    await r.xadd(
        settings.STREAM_NAME,
        event.to_redis_dict(),
        maxlen=settings.STREAM_MAXLEN,
        approximate=True,
    )
    await r.set(dedup_key, "1", ex=settings.DEDUP_TTL)
    logger.info(f"Événement publié: {event.type.value} — {event.title[:60]}")
    return True


async def ensure_consumer_group(r: redis.Redis) -> None:
    """Crée le consumer group Redis si absent (ignore BUSYGROUP)."""
    try:
        await r.xgroup_create(
            settings.STREAM_NAME,
            settings.CONSUMER_GROUP,
            id="0",
            mkstream=True,
        )
    except redis_exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            pass  # Le groupe existe déjà
        else:
            raise
