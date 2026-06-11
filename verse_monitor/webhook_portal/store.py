"""SubscriptionStore: Redis CRUD for webhook subscriptions.

Key conventions:
  verse:subscription:<id>           — Hash storing subscription fields
  verse:sub:key:<api_key>           — String mapping api_key -> subscription id
  verse:subscriptions:active        — Set of active subscription IDs
  verse:subscription:ratelimit:<id> — Sorted set for rate limiting (score=timestamp)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import redis.asyncio as redis

from verse_monitor.webhook_portal.models import Subscription


class SubscriptionStore:
    """Redis-backed store for webhook subscriptions."""

    def __init__(self, r: redis.Redis) -> None:
        self._r = r

    async def create(self, sub: Subscription) -> Subscription:
        """Store subscription hash, add to active set, and index api_key."""
        await self._r.hset(f"verse:subscription:{sub.id}", mapping=sub.to_redis_dict())
        await self._r.sadd("verse:subscriptions:active", sub.id)
        await self._r.set(f"verse:sub:key:{sub.api_key}", sub.id)
        return sub

    async def get_by_id(self, sub_id: str) -> Subscription | None:
        """Fetch subscription by ID from Redis hash."""
        data = await self._r.hgetall(f"verse:subscription:{sub_id}")
        if not data:
            return None
        return Subscription.from_redis_dict(data)

    async def get_by_api_key(self, api_key: str) -> Subscription | None:
        """Look up subscription via api_key index, then fetch by ID."""
        sub_id = await self._r.get(f"verse:sub:key:{api_key}")
        if not sub_id:
            return None
        if isinstance(sub_id, bytes):
            sub_id = sub_id.decode()
        return await self.get_by_id(sub_id)

    async def get_all_active(self) -> list[Subscription]:
        """Return all active subscriptions with failure_count <= 5."""
        member_ids = await self._r.smembers("verse:subscriptions:active")
        subs: list[Subscription] = []
        for sub_id in member_ids:
            if isinstance(sub_id, bytes):
                sub_id = sub_id.decode()
            sub = await self.get_by_id(sub_id)
            if sub and sub.active and sub.failure_count <= 5:
                subs.append(sub)
        return subs

    async def update(self, sub: Subscription) -> Subscription:
        """Persist updated subscription. Handles api_key change and active set membership."""
        old = await self.get_by_id(sub.id)
        if old and old.api_key != sub.api_key:
            await self._r.delete(f"verse:sub:key:{old.api_key}")
            await self._r.set(f"verse:sub:key:{sub.api_key}", sub.id)
        await self._r.hset(f"verse:subscription:{sub.id}", mapping=sub.to_redis_dict())
        if sub.active:
            await self._r.sadd("verse:subscriptions:active", sub.id)
        else:
            await self._r.srem("verse:subscriptions:active", sub.id)
        return sub

    async def delete(self, sub_id: str) -> bool:
        """Hard delete: remove hash, api_key index, active set entry, and rate limit key."""
        sub = await self.get_by_id(sub_id)
        if not sub:
            return False
        await self._r.delete(f"verse:subscription:{sub_id}")
        await self._r.delete(f"verse:sub:key:{sub.api_key}")
        await self._r.srem("verse:subscriptions:active", sub_id)
        await self._r.delete(f"verse:subscription:ratelimit:{sub_id}")
        return True

    async def is_rate_limited(self, sub_id: str, limit: int) -> bool:
        """Sliding window rate limit over a 1-hour window. True if limit exceeded."""
        key = f"verse:subscription:ratelimit:{sub_id}"
        now = time.time()
        hour_ago = now - 3600

        await self._r.zremrangebyscore(key, "-inf", hour_ago)
        count = await self._r.zcard(key)
        if count >= limit:
            return True

        await self._r.zadd(key, {str(now): now})
        await self._r.expire(key, 3600)
        return False

    async def record_delivery(self, sub_id: str, success: bool) -> None:
        """Update delivery stats. Resets or increments failure_count; auto-disables after 5 failures."""
        sub = await self.get_by_id(sub_id)
        if not sub:
            return
        sub.total_deliveries += 1
        sub.last_delivery = datetime.now(timezone.utc)
        if success:
            sub.failure_count = 0
        else:
            sub.failure_count += 1
            if sub.failure_count > 5:
                sub.active = False
        await self.update(sub)
