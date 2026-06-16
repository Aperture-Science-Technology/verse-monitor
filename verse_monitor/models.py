"""Modèles Pydantic pour les événements Star Citizen.

SCEvent : événement de changement détecté sur une source RSI.
EventType : type d'événement (roadmap, patch notes, comm-link, etc.).
Priority : niveau de priorité (CRITICAL, HIGH, MEDIUM, LOW).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class Priority(str, Enum):
    """Niveau de priorité d'un événement."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EventType(str, Enum):
    """Type d'événement de changement."""
    ROADMAP_CARD_ADDED = "roadmap_card_added"
    ROADMAP_CARD_RELEASED = "roadmap_card_released"
    ROADMAP_CARD_DELAYED = "roadmap_card_delayed"
    ROADMAP_CARD_REMOVED = "roadmap_card_removed"
    ROADMAP_CARD_UPDATED = "roadmap_card_updated"
    PATCH_NOTES_LIVE = "patch_notes_live"
    COMM_LINK_PUBLISHED = "comm_link_published"
    TWISC_PUBLISHED = "twisc_published"
    MONTHLY_REPORT = "monthly_report"
    DEVTRACKER_POST = "devtracker_post"
    REDDIT_POST_NEW = "reddit_post_new"
    REDDIT_POST_TRENDING = "reddit_post_trending"


class SCEvent(BaseModel):
    """Événement de changement détecté sur une source RSI."""

    id: str = uuid4().hex
    type: EventType
    priority: Priority
    source: str
    title: str
    url: str = ""
    diff: dict[str, Any] = {}
    keywords: list[str] = []
    timestamp: datetime = datetime.now(timezone.utc)
    content_hash: str = ""
    patch_version: str | None = None
    author: str | None = None
    category: str | None = None

    def to_redis_dict(self) -> dict[str, str]:
        """Sérialise l'événement pour Redis Stream."""
        return {"data": json.dumps(self.model_dump(mode="json"))}

    @classmethod
    def from_redis_dict(cls, d: dict[str, str]) -> SCEvent:
        """Désérialise un événement depuis Redis Stream."""
        return cls.model_validate_json(d["data"])
