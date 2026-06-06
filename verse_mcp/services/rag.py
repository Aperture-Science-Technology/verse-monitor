"""RAG pipeline service."""

from verse_mcp.services.embeddings import generate_embedding
from verse_mcp.services.cache import get_cached_embedding, set_cached_embedding
from verse_mcp.services.retriever import search_chunks
from verse_mcp.constants import CHAR_LIMIT


async def run_rag_pipeline(
    question: str,
    category: str | None = None,
    top_k: int = 5,
) -> str:
    """Run the RAG pipeline: cache -> embedding -> search -> return formatted chunks."""
    embedding = await get_cached_embedding(question)
    if embedding is None:
        embedding = await generate_embedding(question)
        await set_cached_embedding(question, embedding)

    chunks = await search_chunks(embedding, top_k=top_k, category=category)

    if not chunks:
        return "No relevant information found."

    parts = []
    for c in chunks:
        header = f"[Source: {c.source} | {c.url}]"
        if c.patch_version:
            header += f" [Patch: {c.patch_version}]"
        parts.append(f"{header}\n\n{c.content}")

    result = "\n\n---\n\n".join(parts)

    if len(result) > CHAR_LIMIT:
        result = result[:CHAR_LIMIT] + "\n\n[Context truncated — refine the query for more precise results.]"

    return result
