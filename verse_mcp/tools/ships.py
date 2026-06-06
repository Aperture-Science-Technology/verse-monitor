"""Tool: sc_get_ship_stats."""

from verse_mcp.services.rag import run_rag_pipeline
from verse_mcp.models.outputs import ShipStatsOutput


async def sc_get_ship_stats(ship_name: str) -> ShipStatsOutput:
    """Full technical ship stats (Qdrant → fallback Wiki API)"""
    question = f"What are the technical specifications and statistics for the {ship_name}?"
    text = await run_rag_pipeline(question=question, top_k=10)
    return ShipStatsOutput(ship_name=ship_name, description=text)
