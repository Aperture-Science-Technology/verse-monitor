"""Source de données RSI : Comm-Links.

URL : https://robertsspaceindustries.com/en/comm-link
Structure : <a class="content-block2" href="/comm-link/{category}/{id}-{slug}">
⚠️ Format d'URL : /comm-link/{category}/{article_id}-{slug} (PAS /comm-link/{id}-{slug})
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.sources.base import BaseSource
from verse_monitor.sources.time_ago import parse_time_ago

logger = logging.getLogger(__name__)

COMM_LINKS_URL = "https://robertsspaceindustries.com/en/comm-link"
RSI_BASE_URL = "https://robertsspaceindustries.com"


class CommLinksSource(BaseSource):
    """Source comm-links RSI — parsing HTML des comm-links."""

    name = "comm_links"
    event_type_default = EventType.COMM_LINK_PUBLISHED

    @staticmethod
    def _detect_event_type(title: str) -> EventType:
        """Détecte le type d'événement selon le titre de l'article."""
        title_lower = title.lower()
        if re.search(r"alpha \d+\.\d+", title_lower) or "patch notes" in title_lower or "hotfix" in title_lower:
            return EventType.PATCH_NOTES_LIVE
        if "this week in star citizen" in title_lower:
            return EventType.TWISC_PUBLISHED
        if "monthly report" in title_lower:
            return EventType.MONTHLY_REPORT
        return EventType.COMM_LINK_PUBLISHED

    async def fetch(self) -> dict[str, Any]:
        """Récupère et parse le HTML des comm-links RSI.

        Retourne {article_id: {id, title, date, url, category, comments}}.
        L'article_id est le 4e segment de l'URL (avant le premier tiret).
        """
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(COMM_LINKS_URL)
                    resp.raise_for_status()
                    html = resp.text
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    logger.warning(f"comm_links fetch attempt {attempt + 1} failed: {exc}, retrying in 5s")
                    await asyncio.sleep(5)

        if last_exc is not None:
            logger.error(f"comm_links fetch failed after 3 attempts: {last_exc}")
            raise last_exc

        soup = BeautifulSoup(html, "html.parser")
        articles: dict[str, Any] = {}

        for a in soup.select("a.content-block2"):
            href = a.get("href", "")
            # Format : /comm-link/{category}/{article_id}-{slug}
            # Découpage : ["", "comm-link", "{category}", "{article_id}-{slug}"]
            segments = href.split("/")
            if len(segments) < 4:
                continue
            category = segments[2]   # 3e segment (index 2)
            id_slug = segments[3]    # 4e segment (index 3)
            article_id = id_slug.split("-")[0]
            if not article_id.isdigit():
                continue

            title_el = a.select_one("div.title")
            date_el = a.select_one("div.time_ago span.value")
            comments_el = a.select_one("div.comments")

            title = title_el.get_text(strip=True) if title_el else ""
            date = date_el.get_text(strip=True) if date_el else ""
            comments = comments_el.get_text(strip=True) if comments_el else "0"

            articles[article_id] = {
                "id": article_id,
                "title": title,
                "date": date,
                "url": f"{RSI_BASE_URL}{href}",
                "category": category,
                "comments": comments,
            }

        logger.debug(f"comm_links: {len(articles)} articles fetched")
        return articles

    def diff(self, old: dict[str, Any], new: dict[str, Any]) -> list[SCEvent]:
        """Retourne les nouveaux articles comme événements avec type détecté par titre."""
        events: list[SCEvent] = []
        for article_id, article in new.items():
            if article_id not in old:
                event_type = self._detect_event_type(article["title"])
                events.append(SCEvent(
                    id=uuid4().hex,
                    type=event_type,
                    priority=Priority.CRITICAL if event_type == EventType.PATCH_NOTES_LIVE else Priority.MEDIUM,
                    source=self.name,
                    title=article["title"],
                    url=article.get("url", ""),
                    published_at=parse_time_ago(article.get("date", "")),
                    diff={
                        "category": article.get("category", ""),
                        "date": article.get("date", ""),
                        "comments": article.get("comments", ""),
                    },
                ))
        logger.debug(f"comm_links diff: {len(events)} new articles")
        return events
