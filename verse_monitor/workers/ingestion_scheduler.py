"""Periodic ingestion scheduler for the Star Citizen wiki pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import time

import redis.asyncio as redis_lib

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Runs run_ingestion_cycle() at a fixed interval and persists stats to Redis."""

    def __init__(self, r: redis_lib.Redis, interval: int = 86400) -> None:
        self._redis = r
        self._interval = interval
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Schedule the ingestion loop as a non-blocking background task."""
        self._task = asyncio.create_task(self._loop(), name="ingestion-scheduler")

    async def _loop(self) -> None:
        while True:
            await self._run_once()
            await asyncio.sleep(self._interval)

    async def _run_once(self) -> None:
        from ingestion.wiki_ingest import run_ingestion_cycle

        started_at = time.time()
        logger.info("Ingestion cycle starting")
        try:
            result = await run_ingestion_cycle()
            result["started_at"] = started_at
            await self._redis.set("ingestion:last_run", json.dumps(result))
            logger.info(
                "Ingestion cycle complete — %d items, %d chunks, %d errors, %.1fs",
                result["items_fetched"],
                result["chunks_created"],
                result["errors"],
                result["elapsed_seconds"],
            )
        except Exception as exc:
            logger.error("Ingestion cycle failed: %s", exc, exc_info=True)
            await self._redis.set(
                "ingestion:last_run",
                json.dumps({"error": str(exc), "started_at": started_at}),
            )
