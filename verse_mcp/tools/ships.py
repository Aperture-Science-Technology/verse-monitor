"""Tool: sc_get_ship_stats and sc_compare_ships."""

from verse_mcp.models.inputs import GetShipStatsInput, CompareShipsInput
from verse_mcp.models.outputs import ShipStatsOutput, CompareShipsOutput
from verse_mcp.services.rag import run_rag_pipeline
import asyncio

async def sc_get_ship_stats(ship_name: str) -> ShipStatsOutput:
    """Full technical ship stats (Qdrant → fallback Wiki API)"""
    # First try to get from Qdrant via RAG pipeline for a specific question
    question = f"What are the technical specifications and statistics for the {ship_name}?"
    rag_result = await run_rag_pipeline(question=question, top_k=10)
    
    # For now, we return a placeholder. In a full implementation, we would parse the rag_result
    # to extract structured ship stats. This is a simplified version.
    return ShipStatsOutput(
        name=ship_name,
        manufacturer="Placeholder",
        role="Placeholder",
        size="Placeholder",
        length=0.0,
        beam=0.0,
        height=0.0,
        mass=0.0,
        cargo_capacity=0.0,
        max_speed=0.0,
        scm_speed=0.0,
        afterburner_speed=0.0,
        min_crew=0,
        max_crew=0,
        weapon_size="Placeholder",
        shield_size="Placeholder",
        armor_size="Placeholder",
        description=rag_result.answer[:500] if rag_result.answer else "No data available"
    )

async def sc_compare_ships(ship_a: str, ship_b: str) -> CompareShipsOutput:
    """Compare two ships — fetch **in parallel** via `asyncio.gather`"""
    # Fetch both ships in parallel
    ship_a_task = sc_get_ship_stats(ship_a)
    ship_b_task = sc_get_ship_stats(ship_b)
    ship_a_stats, ship_b_stats = await asyncio.gather(ship_a_task, ship_b_task)
    
    # Generate a simple comparison string
    comparison = f"{ship_a.name} vs {ship_b.name}: Basic comparison based on available data."
    
    return CompareShipsOutput(
        ship_a=ship_a_stats,
        ship_b=ship_b_stats,
        comparison=comparison
    )