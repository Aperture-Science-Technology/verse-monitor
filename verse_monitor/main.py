"""Entry point du service verse-monitor.

Lance le scheduler (polling des sources RSI), l'alert worker (consumer Redis Stream),
et le monitoring loop pour sc_events uniquement (le MCP server gère sc_chunks de son côté).
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Point d'entrée principal : lance scheduler + alert worker + ingestion scheduler."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("verse-monitor démarré")

    from verse_monitor.config import settings
    from verse_monitor.pipeline.publisher import get_redis
    from verse_monitor.workers.scheduler import build_scheduler
    from verse_monitor.workers.alert_worker import run_alert_worker
    from verse_monitor.workers.ingestion_scheduler import IngestionScheduler
    from verse_monitor.monitoring.alerts import monitor_collections_loop
    from verse_monitor.storage.qdrant_store import _default_store

    r = get_redis()
    scheduler = build_scheduler(r)
    scheduler.start()

    ingestion_scheduler = IngestionScheduler(r, interval=settings.INGESTION_INTERVAL)
    await ingestion_scheduler.start()

    # Start background collection monitoring (non-blocking)
    # Only monitors sc_events — sc_chunks is monitored by the MCP server health endpoint
    monitor_task = asyncio.create_task(
        monitor_collections_loop(
            events_client=_default_store._client,
            chunks_client=None,  # Worker doesn't have access to sc_chunks client
            events_collection=settings.QDRANT_COLLECTION,
            chunks_collection="sc_chunks",
            expected_dimension=1536,
            check_interval=60,
            discord_webhook=settings.DISCORD_WEBHOOK_HIGH or None,
            alert_on_empty=False,  # Don't alert on empty — normal state before first ingestion
        ),
        name="collection-monitor",
    )

    await run_alert_worker(r)


if __name__ == "__main__":
    asyncio.run(main())
