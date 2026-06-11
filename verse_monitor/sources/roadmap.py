"""Source de données RSI : API Roadmap Release View.

URL : https://robertsspaceindustries.com/api/roadmap/v1/boards/1
Structure : data.releases[].cards[]
Status observés : "Released", "Tentative"
⚠️ Pas de category.name dans l'API, seulement category_id (int).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from uuid import uuid4

import httpx

from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.sources.base import BaseSource

logger = logging.getLogger(__name__)

ROADMAP_API_URL = "https://robertsspaceindustries.com/api/roadmap/v1/boards/1"


class RoadmapSource(BaseSource):
    """Source roadmap RSI — polling de l'API roadmap."""

    name = "roadmap_release_view"
    event_type_default = EventType.ROADMAP_CARD_ADDED

    @staticmethod
    def _version_number(release_name: str) -> float:
        """Extrait le numéro de version d'un nom de release (ex: 'Alpha 4.1' → 4.1)."""
        match = re.search(r"(\d+\.\d+)", release_name)
        if match:
            return float(match.group(1))
        return 0.0

    async def fetch(self) -> dict[str, Any]:
        """Récupère l'état courant depuis l'API roadmap RSI.

        Retourne {card_id: {id, name, status, release_id, release_name, category_id, description}}.
        """
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(ROADMAP_API_URL)
                    resp.raise_for_status()
                    data = resp.json()
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    logger.warning(f"roadmap fetch attempt {attempt + 1} failed: {exc}, retrying in 5s")
                    await asyncio.sleep(5)

        if last_exc is not None:
            logger.error(f"roadmap fetch failed after 3 attempts: {last_exc}")
            raise last_exc

        releases = data.get("data", {}).get("releases", [])
        cards: dict[str, Any] = {}

        for release in releases:
            release_id = release.get("id")
            release_name = release.get("name", "")
            for card in release.get("cards", []):
                card_id = str(card.get("id"))
                cards[card_id] = {
                    "id": card_id,
                    "name": card.get("name", ""),
                    "status": card.get("status", ""),
                    "release_id": release_id,
                    "release_name": release_name,
                    "category_id": card.get("category_id"),
                    "description": card.get("description") or card.get("body") or "",
                }

        logger.debug(f"roadmap: {len(cards)} cards fetched across {len(releases)} releases")
        return cards

    def diff(self, old: dict[str, Any], new: dict[str, Any]) -> list[SCEvent]:
        """Compare deux états roadmap et retourne les événements détectés."""
        events: list[SCEvent] = []
        old_ids = set(old.keys())
        new_ids = set(new.keys())

        for card_id in old_ids - new_ids:
            card = old[card_id]
            events.append(SCEvent(
                id=uuid4().hex,
                type=EventType.ROADMAP_CARD_REMOVED,
                priority=Priority.HIGH,
                source=self.name,
                title=card["name"],
                diff={"removed": card},
            ))

        for card_id in new_ids - old_ids:
            card = new[card_id]
            events.append(SCEvent(
                id=uuid4().hex,
                type=EventType.ROADMAP_CARD_ADDED,
                priority=Priority.MEDIUM,
                source=self.name,
                title=card["name"],
                diff={"added": card},
            ))

        for card_id in old_ids & new_ids:
            old_card = old[card_id]
            new_card = new[card_id]

            # Status passé à "Released" — prioritaire sur le changement de release
            if old_card["status"] != "Released" and new_card["status"] == "Released":
                events.append(SCEvent(
                    id=uuid4().hex,
                    type=EventType.ROADMAP_CARD_RELEASED,
                    priority=Priority.HIGH,
                    source=self.name,
                    title=new_card["name"],
                    diff={
                        "old_status": old_card["status"],
                        "new_status": "Released",
                        "release_name": new_card["release_name"],
                    },
                ))
                continue

            # Changement de release (déplacement dans le temps)
            if old_card["release_name"] != new_card["release_name"]:
                old_ver = self._version_number(old_card["release_name"])
                new_ver = self._version_number(new_card["release_name"])
                event_type = EventType.ROADMAP_CARD_DELAYED if new_ver > old_ver else EventType.ROADMAP_CARD_UPDATED
                events.append(SCEvent(
                    id=uuid4().hex,
                    type=event_type,
                    priority=Priority.HIGH if event_type == EventType.ROADMAP_CARD_DELAYED else Priority.LOW,
                    source=self.name,
                    title=new_card["name"],
                    diff={
                        "old_release": old_card["release_name"],
                        "new_release": new_card["release_name"],
                    },
                ))

        logger.debug(f"roadmap diff: {len(events)} events detected")
        return events
