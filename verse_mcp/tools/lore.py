"""Tool: sc_search_lore (lore.py)"""

from verse_mcp.models.inputs import SearchLoreInput
from verse_mcp.models.outputs import SearchLoreOutput
from verse_mcp.services.rag import run_rag_pipeline

async def sc_search_lore(query: str, top_k: int = 5) -> SearchLoreOutput:
    """Lore/univers depuis Galactapedia + Comm-Links, retourne `related_topics`"""
    rag_result = await run_rag_pipeline(question=query, top_k=top_k)
    
    # Convert sources to LoreResult
    from verse_mcp.models.outputs import LoreResult
    results = []
    for source in rag_result.sources:
        results.append(
            LoreResult(
                title=source.label,
                content=rag_result.answer[:500],  # placeholder content
                url=source.url,
                related_topics=[]  # placeholder
            )
        )
    
    return SearchLoreOutput(results=results)