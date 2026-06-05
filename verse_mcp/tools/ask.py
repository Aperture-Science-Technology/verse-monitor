"""Tool: sc_ask - General question answering pipeline."""

from verse_mcp.models.inputs import AskInput
from verse_mcp.models.outputs import RagResult
from verse_mcp.services.rag import run_rag_pipeline

async def sc_ask(
    question: str,
    category: str | None = None,
    system_prompt: str = "",
    top_k: int = 5,
) -> RagResult:
    """General question — full RAG pipeline, auto-detect answer type."""
    return await run_rag_pipeline(
        question=question,
        category=category,
        system_prompt=system_prompt,
        top_k=top_k,
    )