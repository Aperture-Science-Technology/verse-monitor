"""VERSE MCP Server — Star Citizen Q&A via RAG."""

import os, traceback, sys
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from verse_mcp.services.cache import init_redis, close_redis
from verse_mcp.services.retriever import init_qdrant, close_qdrant


@asynccontextmanager
async def lifespan(app):
    """Connections initialized once at startup — never inside tools."""
    await init_redis()
    await init_qdrant()
    yield
    await close_redis()
    await close_qdrant()


mcp = FastMCP("verse_mcp", lifespan=lifespan)

# Import after init to avoid circular imports
from verse_mcp.tools import ask, ships, guide, lore  # noqa

# Register tools — direct, no wrapper
mcp.add_tool(ask.sc_ask, name="sc_ask", description=ask.sc_ask.__doc__)
mcp.add_tool(ships.sc_get_ship_stats, name="sc_get_ship_stats", description=ships.sc_get_ship_stats.__doc__)
mcp.add_tool(guide.sc_get_guide, name="sc_get_guide", description=guide.sc_get_guide.__doc__)
mcp.add_tool(lore.sc_search_lore, name="sc_search_lore", description=lore.sc_search_lore.__doc__)

if __name__ == "__main__":
    transport = os.getenv("TRANSPORT", "stdio")
    port = int(os.getenv("PORT", "8000"))

    # When binding to 0.0.0.0 behind Traefik, disable DNS rebinding protection
    # so the proxy Host header is accepted. For localhost/stdio it's harmless.
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=[],
        allowed_origins=[],
    )

    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.settings.transport_security = security
    mcp.run(transport=transport)
