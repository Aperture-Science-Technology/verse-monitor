"""Source de données RSI : Spectrum (posts de la communauté/forum).

URL : https://robertsspaceindustries.com/en/community/spectrum
Structure : div.forum-thread ou div.thread-item (fallback selectors du devtracker)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from verse_monitor.models import EventType, Priority, SCEvent
from verse_monitor.sources.base import BaseSource

logger = logging.getLogger(__name__)

SPECTRUM_URL = "https://robertsspaceindustries.com/en/community/spectrum"


class SpectrumSource(BaseSource):
    """Source Spectrum RSI — parsing HTML des posts du forum communautaire."""

    name = "spectrum"
    event_type_default = EventType.DEVTRACKER_POST

    async def fetch(self) -> dict[str, Any]:
        """Récupère et parse le HTML de Spectrum RSI.

        Retourne {post_hash: {hash, author, title, date, preview, url}}.
        """
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(SPECTRUM_URL)
                    resp.raise_for_status()
                    html = resp.text
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    logger.warning(f"spectrum fetch attempt {attempt + 1} failed: {exc}, retrying in 5s")
                    await asyncio.sleep(5)

        if last_exc is not None:
            logger.error(f"spectrum fetch failed after 3 attempts: {last_exc}")
            raise last_exc

        soup = BeautifulSoup(html, "html.parser")
        posts: dict[str, Any] = {}

        # Try Spectrum-specific selectors first, fall back to devtracker-style selectors
        wrappers = soup.select("div.forum-thread") or soup.select("div.thread-item") or soup.select("div.devpost-wrapper")

        for wrapper in wrappers:
            author_el = (
                wrapper.select_one("div.poster div.nickname")
                or wrapper.select_one("span.author")
                or wrapper.select_one(".author")
            )
            title_el = (
                wrapper.select_one("div.topic span.thread")
                or wrapper.select_one("span.title")
                or wrapper.select_one(".thread-title")
            )
            date_el = (
                wrapper.select_one("div.date span.time")
                or wrapper.select_one("span.time")
                or wrapper.select_one("time")
            )
            preview_el = (
                wrapper.select_one("p.details")
                or wrapper.select_one("p.preview")
                or wrapper.select_one(".thread-preview")
            )

            author = author_el.get_text(strip=True) if author_el else ""
            title = title_el.get_text(strip=True) if title_el else ""
            date = date_el.get_text(strip=True) if date_el else ""
            preview = preview_el.get_text(strip=True) if preview_el else ""

            url = ""
            for a in wrapper.find_all("a", href=True):
                href = a["href"]
                if "/spectrum/" in href:
                    url = href
                    break

            if not title and not author:
                continue

            post_hash = hashlib.md5(f"{title}{author}".encode()).hexdigest()
            posts[post_hash] = {
                "hash": post_hash,
                "author": author,
                "title": title,
                "date": date,
                "preview": preview,
                "url": url,
            }

        logger.debug(f"spectrum: {len(posts)} posts fetched")
        return posts

    def diff(self, old: dict[str, Any], new: dict[str, Any]) -> list[SCEvent]:
        """Retourne les nouveaux posts comme événements DEVTRACKER_POST."""
        events: list[SCEvent] = []
        for post_hash, post in new.items():
            if post_hash not in old:
                events.append(SCEvent(
                    id=uuid4().hex,
                    type=EventType.DEVTRACKER_POST,
                    priority=Priority.MEDIUM,
                    source=self.name,
                    title=post["title"],
                    url=post.get("url", ""),
                    author=post.get("author"),
                    diff={
                        "preview": post.get("preview", ""),
                        "date": post.get("date", ""),
                    },
                ))
        logger.debug(f"spectrum diff: {len(events)} new posts")
        return events
