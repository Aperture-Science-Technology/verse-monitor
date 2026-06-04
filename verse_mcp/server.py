from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from verse_mcp.services.cache import init_redis, close_redis
from verse_mcp.services.retriever import init_qdrant, close_qdrant

print("DEBUG: top of server.py")

@asynccontextmanager
async def lifespan(app):
    """Connexions initialisées une seule fois au démarrage — jamais dans les tools."""
    await init_redis()
    await init_qdrant()
    # init_anthropic()  # Removed as per user requirement: client provides model
    yield
    await close_redis()
    await close_qdrant()

mcp = FastMCP("verse_mcp", lifespan=lifespan)

# Import après init pour éviter les imports circulaires
from verse_mcp.tools import ask, ships, guide, lore  # noqa

if __name__ == "__main__":
    import os
    print("Starting VERSE MCP server...", flush=True)
    transport = os.getenv("TRANSPORT", "stdio")
    port = os.getenv("PORT", "8000")
    print(f"Transport: {transport}, Port: {port}", flush=True)
    mcp.run(transport=transport)