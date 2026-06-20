"""One-shot script to populate sc_events from current source data.

Fetches all sources and directly stores results in Qdrant,
bypassing the Redis Stream pipeline.
"""

import asyncio
import logging
import os
import sys
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from verse_monitor.config import settings
from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.sources.devtracker import DevtrackerSource
from verse_monitor.sources.roadmap import RoadmapSource
from verse_monitor.sources.comm_links import CommLinksSource
from verse_monitor.storage.qdrant_store import QdrantStore
from verse_monitor.pipeline.classifier import classify_category, classify_priority, extract_keywords

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def ingest_source(store: QdrantStore, source, event_type_default: EventType):
    """Fetch a source and store all current items as events in Qdrant."""
    name = source.name
    try:
        data = await source.fetch()
    except Exception as exc:
        logger.error(f"{name}: fetch failed: {exc}")
        return 0

    count = 0
    for key, item in data.items():
        title = item.get("title", item.get("name", ""))
        url = item.get("url", "")

        # Determine event type
        etype = event_type_default
        if hasattr(source, '_detect_event_type'):
            try:
                detected = source._detect_event_type(title)
                if isinstance(detected, EventType):
                    etype = detected
            except Exception:
                pass

        # Build diff from item data
        diff = {k: v for k, v in item.items() if k not in ("title", "name", "url", "hash", "id")}

        event = SCEvent(
            id=uuid4().hex,
            type=etype,
            priority=Priority.MEDIUM,
            source=name,
            title=title,
            url=url,
            diff=diff,
        )
        text = title + str(diff)
        try:
            event.priority = classify_priority(etype, text)
        except Exception:
            pass
        try:
            event.category = classify_category(text)
        except Exception:
            pass
        try:
            event.keywords = extract_keywords(text)
        except Exception:
            pass

        try:
            await store.store_event(event)
            count += 1
        except Exception as exc:
            logger.error(f"Failed to store event {event.id}: {exc}")

    logger.info(f"{name}: stored {count} events in Qdrant")
    return count


async def main():
    logger.info(
        "Config: QDRANT_URL=%s collection=%s REDIS_URL=%s",
        settings.QDRANT_URL,
        settings.QDRANT_COLLECTION,
        settings.REDIS_URL,
    )

    store = QdrantStore()
    await store.ensure_collection()

    total = 0

    # Devtracker
    total += await ingest_source(store, DevtrackerSource(), EventType.DEVTRACKER_POST)

    # Roadmap
    total += await ingest_source(store, RoadmapSource(), EventType.ROADMAP_CARD_ADDED)

    # Comm-Links
    total += await ingest_source(store, CommLinksSource(), EventType.COMM_LINK_PUBLISHED)

    # Verify
    count_after = await store.count()
    logger.info(f"Total events stored: {total}")
    logger.info(f"Total points in sc_events: {count_after}")


if __name__ == "__main__":
    asyncio.run(main())
