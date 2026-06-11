"""Entry point du service verse-monitor.

Lance le scheduler (polling des sources RSI) et l'alert worker (consumer Redis Stream).
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def main() -> None:
    """Point d'entrée principal : lance scheduler + alert worker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("verse-monitor démarré")

    from verse_monitor.pipeline.publisher import get_redis
    from verse_monitor.workers.scheduler import build_scheduler
    from verse_monitor.workers.alert_worker import run_alert_worker

    r = get_redis()
    scheduler = build_scheduler(r)
    scheduler.start()
    await run_alert_worker(r)


if __name__ == "__main__":
    asyncio.run(main())
