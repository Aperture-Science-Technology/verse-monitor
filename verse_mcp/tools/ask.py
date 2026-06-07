"""Tool: sc_ask - General question answering pipeline."""

from verse_mcp.services.rag import run_rag_pipeline


async def sc_ask(question: str, category: str | None = None, top_k: int = 5) -> str:
    """General question — returns relevant Star Citizen knowledge chunks."""
    return await run_rag_pipeline(question=question, category=category, top_k=top_k)
