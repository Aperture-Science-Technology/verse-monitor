"""Cache service (Redis)."""

import redis.asyncio as redis
from verse_mcp.constants import REDIS_TTL_SECONDS
from verse_monitor.config import settings

_redis_client: redis.Redis | None = None


async def init_redis() -> None:
    global _redis_client
    _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    # Test connection
    await _redis_client.ping()


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def get_cached_embedding(question: str) -> list[float] | None:
    if not _redis_client:
        raise RuntimeError("Redis not initialized")
    cached = await _redis_client.get(f"emb:{question}")
    if cached is None:
        return None
    import json
    return json.loads(cached)


async def set_cached_embedding(question: str, embedding: list[float]) -> None:
    if not _redis_client:
        raise RuntimeError("Redis not initialized")
    import json
    await _redis_client.set(
        f"emb:{question}",
        json.dumps(embedding),
        ex=REDIS_TTL_SECONDS,
    )