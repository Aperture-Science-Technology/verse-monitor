"""Embeddings service."""

import os
import httpx
from verse_mcp.constants import EMBEDDING_MODEL, EMBEDDING_DIMENSIONS


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using OpenRouter (or OpenAI fallback)."""
    # Prefer OpenRouter key, fall back to OPENAI_API_KEY
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Neither OPENROUTER_API_KEY nor OPENAI_API_KEY is set"
        )

    base_url = os.getenv(
        "EMBEDDING_BASE_URL", "https://openrouter.ai/api/v1"
    )

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