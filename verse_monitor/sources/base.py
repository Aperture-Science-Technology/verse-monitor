"""Sources de données RSI : classe de base abstraite.

Cycle de poll : fetch → load state → compare → diff → classify → publish → save.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import redis.asyncio as redis

from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.pipeline.classifier import classify_category, classify_priority, extract_keywords
from verse_monitor.pipeline.publisher import publish_event

logger = logging.getLogger(__name__)


class BaseSource(ABC):
    """Classe de base abstraite pour les sources RSI."""

    name: str = ""
    event_type_default: EventType = EventType.COMM_LINK_PUBLISHED

    @abstractmethod
    async def fetch(self) -> dict[str, Any]:
        """Récupère l'état courant depuis la source. Retourne un dict sérialisable."""
        ...

    @abstractmethod
    def diff(self, old: dict[str, Any], new: dict[str, Any]) -> list[SCEvent]:
        """Compare deux états et retourne la liste des événements détectés."""
        ...

    async def poll(self, r: redis.Redis) -> list[SCEvent]:
        """Cycle complet : fetch → compare → diff → classify → publish → save."""
        new_state = await self.fetch()

        old_raw = await r.get(f"state:{self.name}")
        if old_raw is None:
            await r.set(f"state:{self.name}", json.dumps(new_state, sort_keys=True))
            logger.info(f"{self.name}: état initial sauvegardé")
            return []

        old_state = json.loads(old_raw)
        if json.dumps(new_state, sort_keys=True) == json.dumps(old_state, sort_keys=True):
            return []

        events = self.diff(old_state, new_state)
        for event in events:
            text = event.title + str(event.diff)
            event.priority = classify_priority(event.type, text)
            event.category = classify_category(text)
            event.keywords = extract_keywords(text)
            await publish_event(event, r)

        await r.set(f"state:{self.name}", json.dumps(new_state, sort_keys=True))
        logger.info(f"{self.name}: {len(events)} événement(s) détecté(s)")
        return events
