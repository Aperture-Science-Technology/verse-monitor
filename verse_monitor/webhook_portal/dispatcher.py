"""Event dispatcher: match SCEvents to subscriptions and deliver webhooks."""

from __future__ import annotations

import httpx

from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.webhook_portal.formatters import get_formatter
from verse_monitor.webhook_portal.models import Subscription
from verse_monitor.webhook_portal.store import SubscriptionStore

_PRIORITY_ORDER: dict[Priority, int] = {
    Priority.LOW: 0,
    Priority.MEDIUM: 1,
    Priority.HIGH: 2,
    Priority.CRITICAL: 3,
}


def _priority_value(p: Priority) -> int:
    """Numeric value for priority comparison (LOW=0 … CRITICAL=3)."""
    return _PRIORITY_ORDER[p]


async def get_matching_subscriptions(
    event: SCEvent, store: SubscriptionStore
) -> list[Subscription]:
    """Return active subscriptions whose filters match the given event."""
    subs = await store.get_all_active()
    matched: list[Subscription] = []
    for sub in subs:
        if _priority_value(event.priority) < _priority_value(sub.priority_min):
            continue
        if sub.event_types and event.type not in sub.event_types:
            continue
        if sub.keywords:
            text = (event.title + " " + " ".join(event.keywords)).lower()
            if not any(kw.lower() in text for kw in sub.keywords):
                continue
        if sub.category and event.category != sub.category:
            continue
        matched.append(sub)
    return matched


async def dispatch_event(
    event: SCEvent, store: SubscriptionStore
) -> list[tuple[str, bool]]:
    """Send event to all matching subscriptions; return list of (sub_id, success)."""
    subs = await get_matching_subscriptions(event, store)
    results: list[tuple[str, bool]] = []

    for sub in subs:
        if await store.is_rate_limited(sub.id, sub.rate_limit):
            continue

        formatter = get_formatter(sub.format)
        payload = formatter(event)

        success = False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(sub.webhook_url, json=payload)
                success = resp.status_code < 400
        except Exception:
            success = False

        await store.record_delivery(sub.id, success)
        results.append((sub.id, success))

    return results
