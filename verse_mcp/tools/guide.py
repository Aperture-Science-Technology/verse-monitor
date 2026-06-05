"""Tool: sc_get_guide and sc_search_lore."""

from verse_mcp.models.inputs import GetGuideInput, SearchLoreInput
from verse_mcp.models.outputs import GuideOutput, LoreResult, SearchLoreOutput
from verse_mcp.services.rag import run_rag_pipeline
import asyncio

async def sc_get_guide(guide_title: str, player_level: str = "beginner") -> GuideOutput:
    """Step-by-step guide, `player_level` parameter (beginner/intermediate/advanced)"""
    question = f"Provide a step-by-step guide for {guide_title} suitable for {player_level} players."
    rag_result = await run_rag_pipeline(question=question, top_k=10)
    
    # For simplicity, we split the answer by lines and treat each line as a step.
    # In a real implementation, we would parse for actual steps.
    steps = [line.strip() for line in rag_result.answer.split('\n') if line.strip()]
    if not steps:
        steps = [rag_result.answer]  # fallback
    
    return GuideOutput(
        title=guide_title,
        steps=steps,
        player_level=player_level,
        tips=["Refer to the official Star Citizen wiki for more details."] if rag_result.answer else None
    )

async def sc_search_lore(query: str, top_k: int = 5) -> SearchLoreOutput:
    """Lore/universe from Galactapedia + Comm-Links, returns `related_topics`"""
    rag_result = await run_rag_pipeline(question=query, top_k=top_k)
    
    results = []
    for source in rag_result.sources:
        # We don't have the full content from the source, so we use the answer as content for simplicity.
        # In a real implementation, we would fetch the full content or store it in the chunk.
        results.append(
            LoreResult(
                title=source.label,
                content=rag_result.answer[:500],  # placeholder
                url=source.url,
                related_topics=[]  # placeholder
            )
        )
    
    return SearchLoreOutput(results=results)