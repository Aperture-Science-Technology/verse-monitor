"""Tool: sc_search_community — Search community discussions from Reddit r/starcitizen."""

from verse_mcp.services.rag import run_rag_pipeline


async def sc_search_community(query: str, top_k: int = 5) -> str:
    """Search community discussions from r/starcitizen.

    Returns relevant Reddit posts and comments matching the query,
    formatted with source attribution.
    """
    return await run_rag_pipeline(question=query, category="community", top_k=top_k)
