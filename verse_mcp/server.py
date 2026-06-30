"""VERSE MCP Server — Star Citizen Q&A via RAG.

Uses FastMCP standalone package (from fastmcp import FastMCP).
Transport: HTTP (Streamable HTTP) via mcp.run(transport="http").
Stateless mode: FASTMCP_STATELESS_HTTP env var.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

import verse_mcp.services.cache as _cache_svc
import verse_mcp.services.retriever as _retriever_svc
from verse_mcp.constants import VECTOR_COLLECTION_NAME
from verse_mcp.services.cache import init_redis, close_redis
from verse_mcp.services.retriever import init_qdrant, close_qdrant
from verse_monitor.storage.qdrant_store import _default_store as _events_store
from verse_mcp.tools.ask import sc_ask as _sc_ask
from verse_mcp.tools.ships import sc_get_ship_stats as _sc_get_ship_stats
from verse_mcp.tools.guide import sc_get_guide as _sc_get_guide, sc_search_lore as _sc_search_lore
from verse_mcp.tools.monitor import (
    sc_get_events as _sc_get_events,
    sc_get_roadmap_diff as _sc_get_roadmap_diff,
    sc_get_dev_posts as _sc_get_dev_posts,
    sc_get_event_context as _sc_get_event_context,
)
from verse_mcp.tools.sc_search_community import sc_search_community as _sc_search_community

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    # Check version qdrant-client dès le départ
    from importlib.metadata import version as _pkg_version
    _qd_version = _pkg_version('qdrant-client')
    logger.info("qdrant-client version: %s", _qd_version)

    await init_redis()
    await init_qdrant()
    # Also ensure the events collection exists (sc_events)
    try:
        await _events_store.ensure_collection()
    except Exception as exc:
        logger.warning("Could not ensure sc_events collection: %s", exc)

    # Log structuré de startup
    try:
        _redis_ok = getattr(_cache_svc, '_redis_client', None) is not None
        _qdrant_ok = getattr(_retriever_svc, '_qdrant_client', None) is not None
        logger.info(
            "VERSE MCP startup: redis=%s qdrant=%s ready=%s",
            "ok" if _redis_ok else "missing",
            "ok" if _qdrant_ok else "missing",
            _redis_ok and _qdrant_ok,
        )
    except Exception:
        pass

    yield
    await close_redis()
    await close_qdrant()


mcp = FastMCP(
    "verse-monitor",
    lifespan=lifespan,
)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.custom_route("/healthz-light", methods=["GET"])
async def healthz_light(request: Request) -> PlainTextResponse:
    """Lightweight health check for Traefik — no DB calls."""
    return PlainTextResponse("OK")


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    now = datetime.now(timezone.utc)
    services: dict = {}

    # Redis health
    redis_client = _cache_svc._redis_client
    if redis_client is None:
        services["redis"] = "error: not initialized"
    else:
        try:
            await redis_client.ping()
            services["redis"] = "ok"
        except Exception as exc:
            services["redis"] = f"error: {exc}"

    # Qdrant health
    qdrant_client = _retriever_svc._qdrant_client
    if qdrant_client is None:
        services["qdrant"] = "error: not initialized"
    else:
        try:
            await asyncio.to_thread(qdrant_client.get_collections)
            services["qdrant"] = "ok"
        except Exception as exc:
            services["qdrant"] = f"error: {exc}"

    # Metrics: total chunks and breakdown by category
    total_chunks: int | str | None = None
    chunks_by_category: dict = {}
    if qdrant_client is not None:
        try:
            result = await asyncio.to_thread(
                qdrant_client.count,
                collection_name=VECTOR_COLLECTION_NAME,
                exact=True,
            )
            total_chunks = result.count
        except Exception as exc:
            total_chunks = f"error: {exc}"

        try:
            offset = None
            while True:
                records, next_offset = await asyncio.to_thread(
                    qdrant_client.scroll,
                    collection_name=VECTOR_COLLECTION_NAME,
                    limit=1000,
                    offset=offset,
                    with_payload=["category"],
                    with_vectors=False,
                )
                for record in records:
                    cat = (record.payload or {}).get("category") or "unknown"
                    chunks_by_category[cat] = chunks_by_category.get(cat, 0) + 1
                if next_offset is None:
                    break
                offset = next_offset
        except Exception:
            chunks_by_category = {}

    # Metrics: events stored in sc_events collection
    events_stored: int | str | None = None
    try:
        events_stored = await _events_store.count()
    except Exception as exc:
        events_stored = f"error: {exc}"

    # Metrics: last ingestion stats from Redis
    last_ingestion: str | None = None
    ingestion_stats: dict | None = None
    if redis_client is not None and services.get("redis") == "ok":
        try:
            raw = await redis_client.get("ingestion:last_run")
            if raw:
                data = json.loads(raw)
                ingestion_stats = data
                started_at = data.get("started_at")
                if started_at is not None:
                    last_ingestion = datetime.fromtimestamp(
                        float(started_at), tz=timezone.utc
                    ).isoformat()
        except Exception:
            pass

    overall_status = "healthy" if all(v == "ok" for v in services.values()) else "degraded"

    return JSONResponse({
        "status": overall_status,
        "timestamp": now.isoformat(),
        "services": services,
        "metrics": {
            "total_chunks": total_chunks,
            "chunks_by_category": chunks_by_category,
            "last_ingestion": last_ingestion,
            "ingestion_stats": ingestion_stats,
            "events_stored": events_stored,
            "uptime_sources": ["comm_links", "devtracker", "roadmap_release_view", "reddit_starcitizen"],
        },
    })


@mcp.tool()
async def sc_ask(question: str, category: str | None = None) -> str:
    """Ask a question about Star Citizen. Returns relevant lore, ship info, and game mechanics from the knowledge base."""
    return await _sc_ask(question, category=category)


@mcp.tool()
async def sc_get_ship_stats(ship_name: str) -> str:
    """Get detailed technical stats for a specific Star Citizen ship."""
    return await _sc_get_ship_stats(ship_name)


@mcp.tool()
async def sc_get_guide(topic: str) -> str:
    """Get a step-by-step guide or tutorial for a specific Star Citizen topic."""
    return await _sc_get_guide(topic)


@mcp.tool()
async def sc_search_lore(query: str) -> str:
    """Search the Star Citizen lore database (Galactapedia, Comm-Links) for specific terms or characters."""
    return await _sc_search_lore(query)


# --- Monitor tools (Phase 7) ---

@mcp.tool()
async def sc_get_events(
    hours: int = 24,
    priority_min: str = "MEDIUM",
    event_type: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> str:
    """Get recent events from all RSI sources (roadmap, devtracker, comm-links)."""
    return await _sc_get_events(hours, priority_min, event_type, category, limit)


@mcp.tool()
async def sc_get_roadmap_diff(hours: int = 48) -> str:
    """Get recent roadmap changes grouped by type (delays, additions, releases, removals)."""
    return await _sc_get_roadmap_diff(hours)


@mcp.tool()
async def sc_get_dev_posts(hours: int = 72, limit: int = 15) -> str:
    """Get recent Devtracker posts from Spectrum."""
    return await _sc_get_dev_posts(hours, limit)


@mcp.tool()
async def sc_get_event_context(event_title: str, limit: int = 10) -> str:
    """Get historical events related to a subject (keyword search, not semantic)."""
    return await _sc_get_event_context(event_title, limit)


# --- Community tools (Reddit) ---

@mcp.tool()
async def sc_search_community(query: str, top_k: int = 5) -> str:
    """Search community discussions from r/starcitizen (Reddit posts and comments)."""
    return await _sc_search_community(query, top_k=top_k)


if __name__ == "__main__":
    import asyncio
    transport = os.getenv("TRANSPORT", "http")
    if transport == "http":
        asyncio.run(mcp.run_http_async(
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
            stateless_http=True,
        ))
    else:
        mcp.run(transport=transport)
