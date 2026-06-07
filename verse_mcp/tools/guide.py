"""Tools: sc_get_guide and sc_search_lore."""

from verse_mcp.services.rag import run_rag_pipeline


async def sc_get_guide(guide_title: str, player_level: str = "beginner") -> str:
    """Step-by-step guide for a Star Citizen topic."""
    question = f"Provide a step-by-step guide for {guide_title} suitable for {player_level} players."
    return await run_rag_pipeline(question=question, top_k=10)


async def sc_search_lore(query: str, top_k: int = 5) -> str:
    """Search lore/universe from Galactapedia and Comm-Links."""
    return await run_rag_pipeline(question=query, top_k=top_k)
