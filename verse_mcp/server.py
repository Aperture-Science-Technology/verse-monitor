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


@asynccontextmanager
async def lifespan(app):
    await init_redis()
    await init_qdrant()
    yield
    await close_redis()
    await close_qdrant()


mcp = FastMCP(
    "verse-mcp",
    lifespan=lifespan,
)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.tool()
async def sc_ask(question: str) -> str:
    """Ask a question about Star Citizen. Returns relevant lore, ship info, and game mechanics from the knowledge base."""
    return await _sc_ask(question)


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
