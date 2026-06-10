"""Tool: sc_get_ship_stats."""

from verse_mcp.services.rag import run_rag_pipeline


async def sc_get_ship_stats(ship_name: str) -> str:
    """Full technical ship stats from the knowledge base."""
    question = f"What are the technical specifications and statistics for the {ship_name}?"
    return await run_rag_pipeline(question=question, category="ships", top_k=10)
