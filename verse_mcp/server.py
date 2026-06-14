"""VERSE MCP Server — Star Citizen Q&A via RAG.

Uses FastMCP standalone package (from fastmcp import FastMCP).
Transport: HTTP (Streamable HTTP) via mcp.run(transport="http").
Stateless mode: FASTMCP_STATELESS_HTTP env var.
"""

import os
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from verse_mcp.services.cache import init_redis, close_redis
from verse_mcp.services.retriever import init_qdrant, close_qdrant
from verse_mcp.tools.ask import sc_ask as _sc_ask
from verse_mcp.tools.ships import sc_get_ship_stats as _sc_get_ship_stats
from verse_mcp.tools.guide import sc_get_guide as _sc_get_guide, sc_search_lore as _sc_search_lore
from verse_mcp.tools.monitor import (
    sc_get_events as _sc_get_events,
    sc_get_roadmap_diff as _sc_get_roadmap_diff,
    sc_get_dev_posts as _sc_get_dev_posts,
    sc_get_event_context as _sc_get_event_context,
)


@asynccontextmanager
async def lifespan(app):
    await init_redis()
    await init_qdrant()
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
