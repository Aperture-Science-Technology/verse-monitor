"""Scheduler APScheduler : lance un job de polling par source RSI.

Utilise AsyncIOScheduler pour la compatibilité async-native.
Chaque job appelle source.poll(r) à intervalle configurable.
"""

from __future__ import annotations

import logging

import redis.asyncio as redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from verse_monitor.config import settings

logger = logging.getLogger(__name__)


def build_scheduler(r: redis.Redis) -> AsyncIOScheduler:
    """Construit et configure le scheduler avec les 3 sources RSI."""
    scheduler = AsyncIOScheduler()

    # TODO Phase 4 : instancier les sources réelles
    # from verse_monitor.sources.roadmap import RoadmapSource
    # from verse_monitor.sources.devtracker import DevtrackerSource
    # from verse_monitor.sources.comm_links import CommLinksSource
    #
    # roadmap = RoadmapSource()
    # devtracker = DevtrackerSource()
    # comm_links = CommLinksSource()
    #
    # scheduler.add_job(roadmap.poll, "interval", seconds=settings.POLL_ROADMAP_INTERVAL, args=[r], max_instances=1, id="roadmap")
    # scheduler.add_job(devtracker.poll, "interval", seconds=settings.POLL_DEVTRACKER_INTERVAL, args=[r], max_instances=1, id="devtracker")
    # scheduler.add_job(comm_links.poll, "interval", seconds=settings.POLL_COMMLINKS_INTERVAL, args=[r], max_instances=1, id="comm_links")

    logger.info(
        f"Scheduler configuré — roadmap:{settings.POLL_ROADMAP_INTERVAL}s "
        f"devtracker:{settings.POLL_DEVTRACKER_INTERVAL}s "
        f"commlinks:{settings.POLL_COMMLINKS_INTERVAL}s"
    )
    return scheduler
