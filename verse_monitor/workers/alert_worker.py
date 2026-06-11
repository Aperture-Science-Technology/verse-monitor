"""Alert worker : consumer du Redis Stream sc:events.

Lit les messages avec xreadgroup, stocke dans Qdrant, et envoie des alertes Discord
selon la priorité (CRITICAL, HIGH, MEDIUM).
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import redis.asyncio as redis

from verse_monitor.config import settings
from verse_monitor.models import SCEvent
from verse_monitor.alerts.formatter import format_discord_payload
from verse_monitor.webhook_portal.store import SubscriptionStore
from verse_monitor.webhook_portal.dispatcher import dispatch_event

logger = logging.getLogger(__name__)


async def run_alert_worker(r: redis.Redis) -> None:
    """Boucle infinie : lit le stream, stocke dans Qdrant, alerte Discord."""
    from verse_monitor.pipeline.publisher import ensure_consumer_group
    from verse_monitor.storage.qdrant_store import store_event

    def _get_webhook(priority) -> str | None:
        """Retourne l'URL du webhook Discord selon la priorité."""
        from verse_monitor.models import Priority
        if priority == Priority.CRITICAL:
            return settings.DISCORD_WEBHOOK_CRITICAL or None
        elif priority == Priority.HIGH:
            return settings.DISCORD_WEBHOOK_HIGH or None
        elif priority == Priority.MEDIUM:
            return settings.DISCORD_WEBHOOK_MEDIUM or None
        return None

    await ensure_consumer_group(r)
    store = SubscriptionStore(r)
    logger.info(f"Alert worker démarré — stream: {settings.STREAM_NAME}")

    while True:
        try:
            messages = await r.xreadgroup(
                groupname=settings.CONSUMER_GROUP,
                consumername=settings.CONSUMER_NAME,
                streams={settings.STREAM_NAME: ">"},
                count=10,
                block=2000,
            )
            if not messages:
                continue

            for stream_name, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    try:
                        event = SCEvent.from_redis_dict(msg_data)
                        await store_event(event)

                        active_subs = await store.get_all_active()
                        if active_subs:
                            results = await dispatch_event(event, store)
                            if results:
                                for sub_id, success in results:
                                    if not success:
                                        logger.warning(f"Webhook delivery failed for subscription {sub_id}")
                        else:
                            webhook = _get_webhook(event.priority)
                            if webhook:
                                async with httpx.AsyncClient() as client:
                                    payload = format_discord_payload(event)
                                    await client.post(webhook, json=payload, timeout=10)

                        await r.xack(settings.STREAM_NAME, settings.CONSUMER_GROUP, msg_id)
                    except Exception as e:
                        logger.error(f"Erreur traitement message {msg_id}: {e}")
                        await r.xack(settings.STREAM_NAME, settings.CONSUMER_GROUP, msg_id)

        except redis.exceptions.ConnectionError:
            logger.error("Redis injoignable — retry dans 5s")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Erreur alert worker: {e}")
            await asyncio.sleep(1)
