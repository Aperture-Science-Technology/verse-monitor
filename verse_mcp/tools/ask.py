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
    """Question générale — pipeline RAG complet, détection auto du type de réponse."""
    return await run_rag_pipeline(
        question=question,
        category=category,
        system_prompt=system_prompt,
        top_k=top_k,
    )