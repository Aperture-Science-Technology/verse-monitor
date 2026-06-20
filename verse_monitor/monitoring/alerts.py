"""Background monitoring for Qdrant collections.

Runs a periodic check on both sc_events and sc_chunks collections,
sends Discord alerts on degradation with cooldown to avoid spam.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import httpx

from verse_monitor.health.collection_check import check_all_collections

logger = logging.getLogger(__name__)

# Cooldown between duplicate alerts (seconds)
ALERT_COOLDOWN = 300  # 5 minutes

# Default check interval (seconds)
DEFAULT_CHECK_INTERVAL = 60


class AlertState:
    """Tracks last alert timestamps per collection to enforce cooldown."""

    def __init__(self) -> None:
        self._last_alert: dict[str, float] = {}

    def should_alert(self, key: str) -> bool:
        now = time.time()
        last = self._last_alert.get(key, 0)
        return (now - last) >= ALERT_COOLDOWN

    def record_alert(self, key: str) -> None:
        self._last_alert[key] = time.time()


async def send_discord_alert(webhook_url: str, message: str) -> bool:
    """Send an alert to a Discord webhook. Returns True on success."""
    if not webhook_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                webhook_url,
                json={"content": message[:2000]},  # Discord limit
            )
            return resp.status_code in (200, 204)
    except Exception as exc:
        logger.error("Failed to send Discord alert: %s", exc)
        return False


def format_alert(result: dict, collection_name: str, health: dict) -> str:
    """Format a Discord alert message for a collection health issue."""
    status = health.get("status", "unknown")
    error = health.get("error", "No details")
    emoji = {
        "missing": "🔴",
        "dimension_mismatch": "🟠",
        "empty": "🟡",
        "error": "🔴",
    }.get(status, "⚠️")

    return (
        f"{emoji} **Qdrant Alert — `{collection_name}`**\n"
        f"Status: **{status}**\n"
        f"Error: `{error}`\n"
        f"Time: <t:{int(time.time())}:F>"
    )


async def monitor_collections_loop(
    events_client: Any,
    chunks_client: Any,
    events_collection: str = "sc_events",
    chunks_collection: str = "sc_chunks",
    expected_dimension: int = 1536,
    check_interval: int = DEFAULT_CHECK_INTERVAL,
    discord_webhook: str | None = None,
    alert_on_empty: bool = True,
) -> None:
    """Background task: periodically check collection health and alert on issues.

    Runs indefinitely until cancelled. Designed to be used as an asyncio.Task.

    Args:
        events_client: QdrantClient for sc_events
        chunks_client: QdrantClient for sc_chunks
        events_collection: Name of the events collection
        chunks_collection: Name of the chunks collection
        expected_dimension: Expected vector dimension (1536)
        check_interval: Seconds between checks
        discord_webhook: Discord webhook URL for alerts (optional)
        alert_on_empty: Whether to alert on empty collections
    """
    state = AlertState()
    logger.info(
        "Starting Qdrant collection monitor (interval=%ds, collections=%s,%s)",
        check_interval,
        events_collection,
        chunks_collection,
    )

    while True:
        try:
            result = await check_all_collections(
                events_client,
                chunks_client,
                events_collection,
                chunks_collection,
                expected_dimension,
            )

            collections = result.get("collections", {})
            for coll_name, health in collections.items():
                status = health.get("status", "unknown")

                if status == "healthy":
                    continue
                if status == "empty" and not alert_on_empty:
                    continue

                alert_key = f"{coll_name}:{status}"
                if not state.should_alert(alert_key):
                    logger.debug(
                        "Alert for '%s' (%s) suppressed (cooldown)", coll_name, status
                    )
                    continue

                logger.warning(
                    "Collection '%s' unhealthy: %s — %s",
                    coll_name,
                    status,
                    health.get("error", ""),
                )

                if discord_webhook:
                    msg = format_alert(result, coll_name, health)
                    sent = await send_discord_alert(discord_webhook, msg)
                    if sent:
                        state.record_alert(alert_key)
                        logger.info("Discord alert sent for '%s'", coll_name)
            # ──────────────────────────────────────────────────────────
            # Empty-collection persistent alert
            # If a collection was empty at startup (fresh recreate),
            # the status is "empty" and we keep alerting every cooldown
            # cycle — this is intentional so the operator knows
            # re-indexing hasn't completed yet.
            # ──────────────────────────────────────────────────────────

        except asyncio.CancelledError:
            logger.info("Qdrant collection monitor cancelled")
            raise
        except Exception as exc:
            logger.error(
                "Error in collection monitor loop: %s", exc, exc_info=True
            )

        await asyncio.sleep(check_interval)
