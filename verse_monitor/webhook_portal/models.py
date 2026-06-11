"""Subscription Pydantic model for the webhook portal."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from verse_monitor.models import EventType, Priority


class Subscription(BaseModel):
    """A webhook subscriber with filters and delivery settings."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    webhook_url: str
    api_key: str = Field(default_factory=lambda: uuid4().hex)
    format: Literal["discord", "slack", "telegram", "generic"] = "discord"
    active: bool = True
    priority_min: Priority = Priority.MEDIUM
    event_types: list[EventType] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    rate_limit: int = 30
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime | None = None
    last_delivery: datetime | None = None
    failure_count: int = 0
    total_deliveries: int = 0

    @field_validator("webhook_url")
    @classmethod
    def webhook_url_must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("webhook_url must start with https://")
        return v

    def to_redis_dict(self) -> dict[str, str]:
        """Serialize subscription to Redis hash fields (all values as strings)."""
        return {
            "id": self.id,
            "name": self.name,
            "webhook_url": self.webhook_url,
            "api_key": self.api_key,
            "format": self.format,
            "active": str(int(self.active)),
            "priority_min": self.priority_min.value,
            "event_types": json.dumps([et.value for et in self.event_types]),
            "keywords": json.dumps(self.keywords),
            "category": self.category or "",
            "rate_limit": str(self.rate_limit),
            "created_at": self.created_at.isoformat(),
            "last_ping": self.last_ping.isoformat() if self.last_ping else "",
            "last_delivery": self.last_delivery.isoformat() if self.last_delivery else "",
            "failure_count": str(self.failure_count),
            "total_deliveries": str(self.total_deliveries),
        }

    @classmethod
    def from_redis_dict(cls, data: dict[str, bytes]) -> Subscription:
        """Deserialize subscription from Redis hash fields, decoding bytes values."""
        d: dict[str, str] = {
            k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
            for k, v in data.items()
        }
        return cls(
            id=d["id"],
            name=d["name"],
            webhook_url=d["webhook_url"],
            api_key=d["api_key"],
            format=d.get("format", "discord"),  # type: ignore[arg-type]
            active=bool(int(d.get("active", "1"))),
            priority_min=Priority(d.get("priority_min", "MEDIUM")),
            event_types=[EventType(et) for et in json.loads(d.get("event_types", "[]"))],
            keywords=json.loads(d.get("keywords", "[]")),
            category=d.get("category") or None,
            rate_limit=int(d.get("rate_limit", "30")),
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(timezone.utc),
            last_ping=datetime.fromisoformat(d["last_ping"]) if d.get("last_ping") else None,
            last_delivery=datetime.fromisoformat(d["last_delivery"]) if d.get("last_delivery") else None,
            failure_count=int(d.get("failure_count", "0")),
            total_deliveries=int(d.get("total_deliveries", "0")),
        )

    def __repr__(self) -> str:
        return (
            f"Subscription(id={self.id!r}, name={self.name!r}, "
            f"format={self.format!r}, active={self.active}, "
            f"priority_min={self.priority_min.value!r}, "
            f"failure_count={self.failure_count}, total_deliveries={self.total_deliveries})"
        )
