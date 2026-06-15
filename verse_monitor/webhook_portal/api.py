"""FastAPI REST API for webhook subscription management.

Endpoints for CRUD operations, testing, and stats.
Serves the frontend static files.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from verse_monitor.config import settings
from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.webhook_portal.formatters import get_formatter
from verse_monitor.webhook_portal.models import Subscription
from verse_monitor.webhook_portal.store import SubscriptionStore

logger = logging.getLogger(__name__)


# ===== Request/Response Models =====

class CreateSubscriptionRequest(BaseModel):
    name: str
    webhook_url: str
    format: str = "discord"
    priority_min: str = "MEDIUM"
    event_types: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    category: str | None = None
    rate_limit: int = 30


class UpdateSubscriptionRequest(BaseModel):
    name: str | None = None
    webhook_url: str | None = None
    format: str | None = None
    priority_min: str | None = None
    event_types: list[str] | None = None
    keywords: list[str] | None = None
    category: str | None = None
    rate_limit: int | None = None
    active: bool | None = None


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    webhook_url: str
    format: str
    active: bool
    priority_min: str
    event_types: list[str]
    keywords: list[str]
    category: str | None
    rate_limit: int
    created_at: str
    last_ping: str | None
    last_delivery: str | None
    failure_count: int
    total_deliveries: int


class CreateResponse(SubscriptionResponse):
    api_key: str


class TestResponse(BaseModel):
    status: str
    http_code: int | None = None
    message: str | None = None


class StatsResponse(BaseModel):
    total_deliveries: int
    failure_count: int
    last_delivery: str | None
    last_ping: str | None
    active: bool
    rate_limit: int


# ===== Helper Functions =====

def _get_store() -> SubscriptionStore:
    r = redis.from_url(
        settings.REDIS_URL,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True,
    )
    return SubscriptionStore(r)


def _sub_to_response(sub: Subscription, include_api_key: bool = False) -> dict[str, Any]:
    d = {
        "id": sub.id,
        "name": sub.name,
        "webhook_url": sub.webhook_url,
        "format": sub.format,
        "active": sub.active,
        "priority_min": sub.priority_min.value,
        "event_types": [et.value for et in sub.event_types],
        "keywords": sub.keywords,
        "category": sub.category,
        "rate_limit": sub.rate_limit,
        "created_at": sub.created_at.isoformat(),
        "last_ping": sub.last_ping.isoformat() if sub.last_ping else None,
        "last_delivery": sub.last_delivery.isoformat() if sub.last_delivery else None,
        "failure_count": sub.failure_count,
        "total_deliveries": sub.total_deliveries,
    }
    if include_api_key:
        d["api_key"] = sub.api_key
    return d


async def _send_test_ping(store: SubscriptionStore, sub: Subscription) -> tuple[bool, int]:
    """Send a test ping to the webhook. Returns (success, http_code)."""
    formatter = get_formatter(sub.format)
    test_event = SCEvent(
        id="test",
        type=EventType.PATCH_NOTES_LIVE,
        priority=Priority.MEDIUM,
        source="verse-monitor",
        title="🔧 Verse Monitor — Test Ping",
        url="https://verse-monitor.aperture-agency.org",
        diff={},
        keywords=[],
        timestamp=datetime.now(timezone.utc),
        content_hash="",
        patch_version=None,
        author="Verse Monitor",
        category=None,
    )
    payload = formatter(test_event)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(sub.webhook_url, json=payload)
            success = 200 <= resp.status_code < 300
            await store.record_delivery(sub.id, success)
            return success, resp.status_code
    except Exception as e:
        logger.warning(f"Test ping failed for {sub.id}: {e}")
        await store.record_delivery(sub.id, False)
        return False, 0


def _validate_create(req: CreateSubscriptionRequest) -> list[str]:
    errors = []
    if not req.name or len(req.name) < 2:
        errors.append("Name must be at least 2 characters")
    if not req.webhook_url.startswith("https://"):
        errors.append("Webhook URL must start with https://")
    valid_formats = {"discord", "slack", "telegram", "generic"}
    if req.format not in valid_formats:
        errors.append(f"Format must be one of: {', '.join(valid_formats)}")
    try:
        Priority(req.priority_min.upper())
    except ValueError:
        errors.append(f"Invalid priority_min: {req.priority_min}")
    for et in req.event_types:
        try:
            EventType(et)
        except ValueError:
            errors.append(f"Invalid event_type: {et}")
    if req.rate_limit < 1 or req.rate_limit > 100:
        errors.append("rate_limit must be between 1 and 100")
    return errors


# ===== App Factory =====

def create_app() -> FastAPI:
    app = FastAPI(
        title="Verse Monitor Webhook Portal",
        version="1.0.0",
        description="Self-service webhook subscription portal for Star Citizen event alerts",
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://verse-monitor.aperture-agency.org", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # ===== Endpoints =====

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        """Serve the main frontend page."""
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path) as f:
                return f.read()
        return HTMLResponse(content="<h1>Verse Monitor Portal</h1><p>Frontend not built yet.</p>")

    @app.post("/api/v1/subscriptions", status_code=201)
    async def create_subscription(req: CreateSubscriptionRequest):
        """Create a new webhook subscription."""
        errors = _validate_create(req)
        if errors:
            raise HTTPException(status_code=400, detail="; ".join(errors))

        store = _get_store()
        sub = Subscription(
            name=req.name,
            webhook_url=req.webhook_url,
            format=req.format,
            priority_min=Priority(req.priority_min.upper()),
            event_types=[EventType(et) for et in req.event_types],
            keywords=req.keywords,
            category=req.category,
            rate_limit=req.rate_limit,
        )
        await store.create(sub)

        # Send test ping in background
        success, code = await _send_test_ping(store, sub)

        resp_data = _sub_to_response(sub, include_api_key=True)
        resp_data["status"] = "active" if sub.active else "inactive"
        resp_data["test_ping"] = "sent" if success else "failed"
        resp_data["test_http_code"] = code
        resp_data["dashboard_url"] = f"/?key={sub.api_key}"
        return resp_data

    @app.get("/api/v1/subscriptions/{api_key}")
    async def get_subscription(api_key: str):
        """Get subscription details by API key."""
        store = _get_store()
        sub = await store.get_by_api_key(api_key)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return _sub_to_response(sub, include_api_key=True)

    @app.patch("/api/v1/subscriptions/{api_key}")
    async def update_subscription(api_key: str, req: UpdateSubscriptionRequest):
        """Update an existing subscription."""
        store = _get_store()
        sub = await store.get_by_api_key(api_key)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")

        update_data = req.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Validate
        if "format" in update_data and update_data["format"] not in {"discord", "slack", "telegram", "generic"}:
            raise HTTPException(status_code=400, detail=f"Invalid format: {update_data['format']}")
        if "webhook_url" in update_data and not update_data["webhook_url"].startswith("https://"):
            raise HTTPException(status_code=400, detail="Webhook URL must start with https://")
        if "priority_min" in update_data:
            try:
                update_data["priority_min"] = Priority(update_data["priority_min"].upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid priority_min")
        if "event_types" in update_data:
            try:
                update_data["event_types"] = [EventType(et) for et in update_data["event_types"]]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid event_type: {e}")
        if "rate_limit" in update_data and (update_data["rate_limit"] < 1 or update_data["rate_limit"] > 100):
            raise HTTPException(status_code=400, detail="rate_limit must be between 1 and 100")

        # Apply updates
        for field_name, value in update_data.items():
            if hasattr(sub, field_name):
                setattr(sub, field_name, value)

        await store.update(sub)
        return _sub_to_response(sub, include_api_key=True)

    @app.delete("/api/v1/subscriptions/{api_key}")
    async def delete_subscription(api_key: str):
        """Soft-delete a subscription (sets active=false)."""
        store = _get_store()
        sub = await store.get_by_api_key(api_key)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        sub.active = False
        await store.update(sub)
        return {"status": "deleted", "id": sub.id}

    @app.post("/api/v1/subscriptions/{api_key}/test")
    async def test_subscription(api_key: str):
        """Send a test ping to the webhook."""
        store = _get_store()
        sub = await store.get_by_api_key(api_key)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")

        success, code = await _send_test_ping(store, sub)
        if success:
            # Update last_ping
            sub.last_ping = datetime.now(timezone.utc)
            await store.update(sub)
            return {"status": "ok", "http_code": code, "message": "Test ping sent successfully"}
        else:
            return {"status": "error", "http_code": code, "message": f"Webhook returned HTTP {code}" if code else "Connection failed"}

    @app.get("/api/v1/subscriptions/{api_key}/stats")
    async def get_stats(api_key: str):
        """Get delivery statistics for a subscription."""
        store = _get_store()
        sub = await store.get_by_api_key(api_key)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return {
            "total_deliveries": sub.total_deliveries,
            "failure_count": sub.failure_count,
            "last_delivery": sub.last_delivery.isoformat() if sub.last_delivery else None,
            "last_ping": sub.last_ping.isoformat() if sub.last_ping else None,
            "active": sub.active,
            "rate_limit": sub.rate_limit,
        }

    @app.get("/api/v1/stats")
    async def get_global_stats():
        """Get global platform statistics for the documentation page."""
        try:
            store = _get_store()
            subs = await store.get_all_active()

            total_deliveries = sum(s.total_deliveries for s in subs)
            total_failures = sum(s.failure_count for s in subs)
            total_subs = len(subs)
        except Exception:
            logger.exception("Failed to fetch subscription stats")
            total_subs = 0
            total_deliveries = 0
            total_failures = 0

        # Get Qdrant event count if available
        qdrant_events = 0
        try:
            from verse_monitor.storage.qdrant_store import QdrantStore
            qstore = QdrantStore()
            qdrant_events = qstore.count()
        except Exception:
            pass

        return {
            "subscriptions": {
                "active": total_subs,
                "total_deliveries": total_deliveries,
                "total_failures": total_failures,
            },
            "sources": {
                "roadmap_cards_monitored": 798,
                "devtracker_posts_per_page": 18,
                "commlinks_per_page": 10,
            },
            "rag": {
                "total_documents": 3334,
                "categories": {
                    "ships": 548,
                    "lore": 437,
                    "equipment": 783,
                    "weapons": 783,
                    "armor": 783,
                },
            },
            "alerts_stored": qdrant_events,
        }

    return app


# ===== Entry point =====

app = create_app()
