"""RAG pipeline service."""

import asyncio
from verse_mcp.services.embeddings import generate_embedding
from verse_mcp.services.cache import get_cached_embedding, set_cached_embedding
from verse_mcp.services.retriever import search_chunks
from verse_mcp.services.llm import call_claude
from verse_mcp.models.outputs import RagResult
from verse_mcp.constants import CHAR_LIMIT

async def run_rag_pipeline(
    question: str,
    category: str | None = None,
    system_prompt: str = "",
    top_k: int = 5,
) -> RagResult:
    """Run the full RAG pipeline: cache -> embedding -> search -> LLM."""
    # 1. Redis cache
    embedding = await get_cached_embedding(question)
    if embedding is None:
        embedding = await generate_embedding(question)
        await set_cached_embedding(question, embedding)

    # 2. Qdrant search
    chunks = await search_chunks(embedding, top_k=top_k, category=category)

    # 3. Assemble RAG context
    context = "\n\n---\n\n".join(
        f"[Source: {c.source} | URL: {c.url}]\n{c.content}"
        for c in chunks
    )

    # 4. Claude call
    prompt = f"{system_prompt}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}"
    answer = await call_claude(prompt)

    if len(answer) > CHAR_LIMIT:
        answer = answer[:CHAR_LIMIT] + "\n\n[Answer truncated — refine the question.]"

    return RagResult(
        answer=answer,
        sources=[{"label": c.source, "url": c.url} for c in chunks],
        patch_version=next((c.patch_version for c in chunks if c.patch_version), None),
    )