"""Parseur simple pour les formats 'time_ago' type '3 '2 weeks ago'.

Utilisé par comm_links/roadmap/devtracker pour peupler published_at
(date de publication réelle ≠ date d'ingestion).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


# Patterns courants (EN et FR)
_PATTERNS = [
    # "X seconds/minutes/hours ago"
    (r"(\d+)\s*(seconds?|secs?)\s*ago", "seconds"),
    (r"(\d+)\s*(minutes?|mins?)\s*ago", "minutes"),
    (r"(\d+)\s*(hours?|hrs?)\s*ago", "hours"),
    # "X days/weeks/months/years ago"
    (r"(\d+)\s*(days?)\s*ago", "days"),
    (r"(\d+)\s*(weeks?)\s*ago", "weeks"),
    (r"(\d+)\s*(months?)\s*ago", "months"),
    (r"(\d+)\s*(years?)\s*ago", "years"),
    # "YYYY-MM-DD" / "YYYY-MM-DD HH:MM:SS"
    (r"(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)", "iso"),
    # "Month DD, YYYY" (January 5, 2026)
    (r"(\w+\s+\d{1,2},?\s+\d{4})", "month_day_year"),
]

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_time_ago(text: str) -> datetime | None:
    """Parse un fragment de temps relatif ou absolu en datetime UTC.

    Retourne None si parsing impossible.
    """
    if not text:
        return None

    text = text.strip().lower()

    for pattern, kind in _PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue

        if kind == "iso":
            raw = m.group(1)
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            return None

        if kind == "month_day_year":
            raw = m.group(1).replace(",", "")
            try:
                return datetime.strptime(raw, "%B %d %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    return datetime.strptime(raw, "%b %d %Y").replace(tzinfo=timezone.utc)
                except ValueError:
                    return None

        # X unit ago
        amount = int(m.group(1))
        now = datetime.now(timezone.utc)
        if kind == "seconds":
            return now - timedelta(seconds=amount)
        if kind == "minutes":
            return now - timedelta(minutes=amount)
        if kind == "hours":
            return now - timedelta(hours=amount)
        if kind == "days":
            return now - timedelta(days=amount)
        if kind == "weeks":
            return now - timedelta(weeks=amount)
        if kind == "months":
            return now - timedelta(days=amount * 30)
        if kind == "years":
            return now - timedelta(days=amount * 365)

    return None
