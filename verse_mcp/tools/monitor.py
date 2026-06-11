"""Outils MCP pour le monitoring des sources RSI.

4 outils :
- sc_get_events : événements récentes toutes sources
- sc_get_roadmap_diff : changements roadmap groupés par type
- sc_get_dev_posts : posts Devtracker récents
- sc_get_event_context : historique d'événements liés à un sujet
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from verse_monitor.config import settings
from verse_monitor.models import Priority
from verse_monitor.storage.qdrant_store import get_events

logger = logging.getLogger(__name__)


async def sc_get_events(
    hours: int = 24,
    priority_min: str = "MEDIUM",
    event_type: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> str:
    """Récupère les événements récentes de toutes les sources RSI.

    Args:
        hours: Nombre d'heures à remonter (défaut: 24)
        priority_min: Priorité minimale (LOW, MEDIUM, HIGH, CRITICAL)
        event_type: Filtrer par type d'événement (optionnel)
        category: Filtrer par catégorie (optionnel)
        limit: Nombre max de résultats (défaut: 20)
    """
    try:
        since_ts = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        priority = Priority(priority_min.upper())

        events = await get_events(
            since_ts=since_ts,
            priority_min=priority,
            event_type=event_type,
            category=category,
            limit=limit,
        )

        if not events:
            return json.dumps({"events": [], "count": 0, "message": "Aucun événement trouvé"})

        return json.dumps({"events": events, "count": len(events)}, default=str, indent=2)
    except Exception as e:
        logger.error(f"Erreur sc_get_events: {e}")
        return json.dumps({"error": str(e)})


async def sc_get_roadmap_diff(hours: int = 48) -> str:
    """Récupère uniquement les changements roadmap groupés par type.

    Args:
        hours: Nombre d'heures à remonter (défaut: 48)
    """
    try:
        since_ts = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        roadmap_types = [
            "roadmap_card_added",
            "roadmap_card_delayed",
            "roadmap_card_released",
            "roadmap_card_removed",
            "roadmap_card_updated",
        ]

        all_events = []
        for et in roadmap_types:
            events = await get_events(
                since_ts=since_ts,
                priority_min=Priority.LOW,
                event_type=et,
                limit=50,
            )
            all_events.extend(events)

        # Grouper par type
        grouped: dict[str, list] = {}
        for e in all_events:
            t = e.get("type", "unknown")
            grouped.setdefault(t, []).append(e)

        return json.dumps(
            {"grouped": grouped, "total": len(all_events), "hours": hours},
            default=str,
            indent=2,
        )
    except Exception as e:
        logger.error(f"Erreur sc_get_roadmap_diff: {e}")
        return json.dumps({"error": str(e)})


async def sc_get_dev_posts(hours: int = 72, limit: int = 15) -> str:
    """Récupère les posts Devtracker récents.

    Args:
        hours: Nombre d'heures à remonter (défaut: 72)
        limit: Nombre max de résultats (défaut: 15)
    """
    try:
        since_ts = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        events = await get_events(
            since_ts=since_ts,
            priority_min=Priority.LOW,
            event_type="devtracker_post",
            limit=limit,
        )

        return json.dumps(
            {"events": events, "count": len(events), "hours": hours},
            default=str,
            indent=2,
        )
    except Exception as e:
        logger.error(f"Erreur sc_get_dev_posts: {e}")
        return json.dumps({"error": str(e)})


async def sc_get_event_context(event_title: str, limit: int = 10) -> str:
    """Récupère l'historique d'événements liés à un sujet.

    Filtre par keyword dans le titre et les keywords de l'événement.
    Ce n'est PAS une recherche sémantique — c'est un filtre textuel exact.
    TODO v2: embedding search for semantic similarity.

    Args:
        event_title: Titre ou mot-clé à rechercher
        limit: Nombre max de résultats (défaut: 10)
    """
    try:
        from verse_monitor.storage.qdrant_store import get_qdrant_client, ensure_collection
        from qdrant_client.http import models

        client = get_qdrant_client()
        await ensure_collection(client)

        # Extraire les keywords du titre
        keywords = event_title.lower().split()

        from collections.abc import Sequence

        # Construire un filtre OR sur les keywords
        should_filters = [
            models.FieldCondition(
                key="title",
                match=models.MatchText(text=kw),
            )
            for kw in keywords
        ] + [
            models.FieldCondition(
                key="keywords",
                match=models.MatchAny(any=[kw]),
            )
            for kw in keywords
        ]

        result = await __import__("asyncio").to_thread(
            client.scroll,
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=models.Filter(should=should_filters) if should_filters else None,  # type: ignore[arg-type]
            limit=limit,
            with_payload=True,
            order_by=models.OrderBy(key="timestamp_ts", direction="desc"),  # type: ignore[arg-type]
        )

        events = [p.payload for p in result[0] if p.payload]

        return json.dumps(
            {"events": events, "count": len(events), "query": event_title},
            default=str,
            indent=2,
        )
    except Exception as e:
        logger.error(f"Erreur sc_get_event_context: {e}")
        return json.dumps({"error": str(e)})
