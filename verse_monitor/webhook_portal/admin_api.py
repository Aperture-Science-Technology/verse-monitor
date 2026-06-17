"""Admin API endpoints for the webhook portal dashboard."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from verse_monitor.config import settings
from verse_monitor.webhook_portal.store import SubscriptionStore

logger = logging.getLogger(__name__)

VALID_SOURCES = {"roadmap", "devtracker", "comm_links", "reddit"}

_PROTECTED_PREFIXES = (
    "verse:subscription:",
    "verse:sub:",
    "verse:subscriptions:",
)

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")


def _verify_admin_key(x_admin_key: str | None = None) -> None:
    """Verify the admin API key. Raises HTTPException if invalid or not configured."""
    if not ADMIN_API_KEY:
        logger.warning("ADMIN_API_KEY not set — admin endpoints are disabled")
        raise HTTPException(status_code=503, detail="Admin API key not configured on server")
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


async def _verify_admin_key_dependency(x_admin_key: str | None = Header(None, alias="X-Admin-Key")) -> None:
    """FastAPI dependency that extracts the admin key from the X-Admin-Key header."""
    _verify_admin_key(x_admin_key)


class RagSearchRequest(BaseModel):
    query: str
    limit: int = 5


def _get_redis() -> redis.Redis:
    return redis.from_url(
        settings.REDIS_URL,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
    )


def _get_store(r: redis.Redis) -> SubscriptionStore:
    return SubscriptionStore(r)


def create_admin_router() -> APIRouter:
    router = APIRouter(dependencies=[Depends(_verify_admin_key_dependency)])

    @router.get("/sources/status")
    async def sources_status() -> dict[str, Any]:
        r = _get_redis()
        sources = []
        for source_id in ["roadmap", "devtracker", "comm_links", "reddit"]:
            last_fetch = await r.get(f"sc:source:{source_id}:last_fetch")
            error_count_raw = await r.get(f"sc:source:{source_id}:error_count")
            paused_raw = await r.get(f"sc:source:{source_id}:paused")
            sources.append({
                "id": source_id,
                "name": source_id.replace("_", " ").title(),
                "last_fetch": last_fetch,
                "error_count": int(error_count_raw) if error_count_raw else 0,
                "is_active": paused_raw != "1",
            })
        return {"sources": sources}

    @router.post("/sources/{source_id}/crawl")
    async def trigger_crawl(source_id: str) -> dict[str, Any]:
        if source_id not in VALID_SOURCES:
            return {"error": f"Unknown source: {source_id}"}
        r = _get_redis()
        await r.set(f"sc:source:{source_id}:trigger_crawl", "1", ex=60)
        return {"status": "triggered", "source": source_id}

    @router.post("/sources/{source_id}/pause")
    async def toggle_pause(source_id: str) -> dict[str, Any]:
        if source_id not in VALID_SOURCES:
            return {"error": f"Unknown source: {source_id}"}
        r = _get_redis()
        paused = await r.get(f"sc:source:{source_id}:paused")
        new_state = "0" if paused == "1" else "1"
        await r.set(f"sc:source:{source_id}:paused", new_state)
        return {"status": "paused" if new_state == "1" else "resumed", "source": source_id}

    @router.get("/activity")
    async def recent_activity() -> dict[str, Any]:
        r = _get_redis()
        events: list[dict[str, Any]] = []
        try:
            entries = await r.xrevrange("sc:events", count=10)
            for entry_id, fields in (entries or []):
                events.append({"id": entry_id, **fields})
        except Exception as exc:
            logger.debug("Could not read sc:events stream: %s", exc)
        return {"events": events}

    @router.get("/system")
    async def system_status() -> dict[str, Any]:
        import psutil

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load = psutil.getloadavg()
        uptime_seconds = int(time.time() - psutil.boot_time())

        r = _get_redis()
        redis_ok = False
        try:
            await r.ping()
            redis_ok = True
        except Exception:
            pass

        qdrant_ok = False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{settings.QDRANT_URL}/healthz")
                qdrant_ok = resp.status_code == 200
        except Exception:
            pass

        containers: list[dict[str, str]] = []
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        containers.append({"name": parts[0], "status": parts[1]})
        except Exception:
            pass

        ingestion: dict[str, Any] = {}
        try:
            raw = await r.get("ingestion:last_run")
            if raw:
                ingestion = json.loads(raw)
        except Exception:
            pass

        return {
            "uptime_seconds": uptime_seconds,
            "memory": {
                "total_mb": mem.total // (1024 * 1024),
                "used_mb": mem.used // (1024 * 1024),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "used_gb": round(disk.used / (1024 ** 3), 1),
                "percent": disk.percent,
            },
            "load": {"1m": round(load[0], 2), "5m": round(load[1], 2), "15m": round(load[2], 2)},
            "redis": {"ok": redis_ok},
            "qdrant": {"ok": qdrant_ok},
            "scheduler": {"status": "running" if redis_ok else "unknown"},
            "docker_containers": containers,
            "ingestion": ingestion,
        }

    @router.post("/ingest")
    async def trigger_ingest() -> dict[str, str]:
        r = _get_redis()
        await r.set("ingestion:trigger", "1", ex=300)
        return {"status": "triggered"}

    @router.post("/cache/flush")
    async def flush_cache() -> dict[str, Any]:
        r = _get_redis()
        keys_removed = 0
        try:
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor=cursor, match="verse:*", count=200)
                to_delete = [
                    k for k in keys
                    if not any(k.startswith(p) for p in _PROTECTED_PREFIXES)
                ]
                if to_delete:
                    await r.delete(*to_delete)
                    keys_removed += len(to_delete)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.error("Cache flush error: %s", exc)
        return {"status": "flushed", "keys_removed": keys_removed}

    @router.get("/subscriptions")
    async def list_all_subscriptions() -> dict[str, Any]:
        r = _get_redis()
        store = _get_store(r)
        result: list[dict[str, Any]] = []
        try:
            cursor = 0
            sub_ids: set[str] = set()
            while True:
                cursor, keys = await r.scan(cursor=cursor, match="verse:subscription:*", count=200)
                for k in keys:
                    if not k.startswith("verse:subscription:ratelimit:"):
                        parts = k.split(":", 2)
                        if len(parts) == 3:
                            sub_ids.add(parts[2])
                if cursor == 0:
                    break
            for sub_id in sub_ids:
                sub = await store.get_by_id(sub_id)
                if sub:
                    result.append({
                        "id": sub.id,
                        "name": sub.name,
                        "webhook_url": sub.webhook_url,
                        "format": sub.format,
                        "active": sub.active,
                        "priority_min": sub.priority_min.value,
                        "event_types": [et.value for et in sub.event_types],
                        "keywords": sub.keywords,
                        "category": sub.category,
                        "rate_limit": sub.rate_limit,
                        "created_at": sub.created_at.isoformat(),
                        "last_ping": sub.last_ping.isoformat() if sub.last_ping else None,
                        "last_delivery": sub.last_delivery.isoformat() if sub.last_delivery else None,
                        "failure_count": sub.failure_count,
                        "total_deliveries": sub.total_deliveries,
                        "api_key": sub.api_key,
                    })
        except Exception as exc:
            logger.error("Failed to list subscriptions: %s", exc)
        return {"subscriptions": result, "total": len(result)}

    @router.post("/rag/search")
    async def rag_search(body: RagSearchRequest) -> dict[str, Any]:
        limit = max(1, min(body.limit, 20))
        try:
            from verse_monitor.storage.qdrant_store import QdrantStore
            qstore = QdrantStore()
            hits = await qstore.search(query=body.query, limit=limit)
            return {"results": hits, "query": body.query}
        except Exception as exc:
            logger.warning("RAG search failed: %s", exc)
            return {"results": [], "query": body.query, "error": str(exc)}

    return router
