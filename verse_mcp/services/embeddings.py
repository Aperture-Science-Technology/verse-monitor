"""Embeddings service."""

import httpx
from verse_mcp.constants import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from verse_monitor.config import settings


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using OpenRouter."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    base_url = settings.EMBEDDING_BASE_URL

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": text,
                "model": EMBEDDING_MODEL,
                "dimensions": EMBEDDING_DIMENSIONS,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]