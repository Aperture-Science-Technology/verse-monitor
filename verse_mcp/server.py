from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from verse_mcp.services.cache import init_redis, close_redis
from verse_mcp.services.retriever import init_qdrant, close_qdrant

print("DEBUG: top of server.py")

@asynccontextmanager
async def lifespan(app):
    """Connections initialized once at startup — never inside tools."""
    await init_redis()
    await init_qdrant()
    # init_anthropic()  # Removed as per user requirement: client provides model
    yield
    await close_redis()
    await close_qdrant()

mcp = FastMCP("verse_mcp", lifespan=lifespan)

# Import after init to avoid circular imports
from verse_mcp.tools import ask, ships, guide, lore  # noqa

# Register tools
mcp.add_tool(ask.sc_ask, name="sc_ask", description=ask.sc_ask.__doc__)
mcp.add_tool(ships.sc_get_ship_stats, name="sc_get_ship_stats", description=ships.sc_get_ship_stats.__doc__)
mcp.add_tool(guide.sc_get_guide, name="sc_get_guide", description=guide.sc_get_guide.__doc__)
mcp.add_tool(lore.sc_search_lore, name="sc_search_lore", description=lore.sc_search_lore.__doc__)

if __name__ == "__main__":
    import os
    print("Starting VERSE MCP server...", flush=True)
    transport = os.getenv("TRANSPORT", "stdio")
    port = os.getenv("PORT", "8000")
    print(f"Transport: {transport}, Port: {port}", flush=True)
    mcp.run(transport=transport)