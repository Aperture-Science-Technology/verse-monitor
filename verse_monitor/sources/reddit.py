"""Source de données Reddit : r/starcitizen.

URL : https://www.reddit.com/r/starcitizen/hot.json
API JSON publique (pas d'auth, pas PRAW).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

import httpx

from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.sources.base import BaseSource

logger = logging.getLogger(__name__)

REDDIT_URL = "https://www.reddit.com/r/starcitizen/hot.json?limit=50"
REDDIT_HEADERS = {"User-Agent": "VerseMonitor/1.0 (by ApertureScience)"}


class RedditSource(BaseSource):
    """Source Reddit — r/starcitizen via l'API JSON publique."""

    name = "reddit_starcitizen"
    event_type_default = EventType.REDDIT_POST_NEW

    async def fetch(self) -> dict[str, Any]:
        """Récupère les posts chauds de r/starcitizen.

        Retourne {post_id: {id, title, score, num_comments, url,
        selftext, created_utc, author, permalink}}.
        """
        last_exc: Exception | None = None
        data: dict[str, Any] = {}
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(REDDIT_URL, headers=REDDIT_HEADERS)
                    resp.raise_for_status()
                    data = resp.json()
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    logger.warning(
                        f"reddit fetch attempt {attempt + 1} failed: {exc}, retrying in 5s"
                    )
                    await asyncio.sleep(5)

        if last_exc is not None:
            logger.error(f"reddit fetch failed after 3 attempts: {last_exc}")
            raise last_exc

        posts: dict[str, Any] = {}
        children = data.get("data", {}).get("children", [])
        for child in children:
            post = child.get("data", {})
            post_id = post.get("id")
            if not post_id:
                continue
            permalink = post.get("permalink", "")
            posts[post_id] = {
                "id": post_id,
                "title": post.get("title", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "url": f"https://www.reddit.com{permalink}" if permalink else post.get("url", ""),
                "selftext": post.get("selftext", ""),
                "created_utc": post.get("created_utc", 0),
                "author": post.get("author", ""),
                "permalink": permalink,
            }

        logger.debug(f"reddit: {len(posts)} posts fetched")
        return posts

    def diff(self, old: dict[str, Any], new: dict[str, Any]) -> list[SCEvent]:
        """Détecte les nouveaux posts et les posts en tendance.

        - Nouveau post (id absent de old) → REDDIT_POST_NEW, LOW.
        - Post trending (score ×2 ou comments ×3) → REDDIT_POST_TRENDING, MEDIUM.
        """
        events: list[SCEvent] = []

        for post_id, post in new.items():
            if post_id not in old:
                events.append(SCEvent(
                    id=uuid4().hex,
                    type=EventType.REDDIT_POST_NEW,
                    priority=Priority.LOW,
                    source=self.name,
                    title=post["title"],
                    url=post["url"],
                    diff={
                        "score": {"old": 0, "new": post["score"]},
                        "num_comments": {"old": 0, "new": post["num_comments"]},
                    },
                ))
            else:
                old_post = old[post_id]
                old_score = old_post.get("score", 0)
                new_score = post.get("score", 0)
                old_comments = old_post.get("num_comments", 0)
                new_comments = post.get("num_comments", 0)

                is_trending = (
                    new_score > old_score * 2 or new_comments > old_comments * 3
                )
                if is_trending:
                    events.append(SCEvent(
                        id=uuid4().hex,
                        type=EventType.REDDIT_POST_TRENDING,
                        priority=Priority.MEDIUM,
                        source=self.name,
                        title=post["title"],
                        url=post["url"],
                        diff={
                            "score": {"old": old_score, "new": new_score},
                            "num_comments": {"old": old_comments, "new": new_comments},
                        },
                    ))

        logger.info(f"reddit diff: {len(events)} event(s) detected")
        return events
