"""Star Citizen Wiki API ingestion."""

import httpx
import asyncio
from verse_mcp.services.embeddings import generate_embedding
from verse_mcp.services.cache import set_cached_embedding
from verse_mcp.services.retriever import init_qdrant
from verse_mcp.constants import VECTOR_COLLECTION_NAME
import json
from uuid import NAMESPACE_URL, uuid5

WIKI_API_BASE = "https://api.star-citizen.wiki/api/v2"

async def fetch_wiki_endpoint(endpoint: str) -> dict:
    """Fetch data from the Star Citizen Wiki API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{WIKI_API_BASE}/{endpoint}")
        response.raise_for_status()
        return response.json()

async def process_and_store(data: list, category: str, source: str):
    """Process a list of items and store embeddings in Qdrant."""
    # Initialize Qdrant client (assuming it's already initialized via lifespan)
    # In a real ingestion script, we would initialize the client here or pass it.
    # For simplicity, we assume the client is available via a global or we re-initialize.
    # We'll just show the logic; actual implementation would need to connect to Qdrant.
    for item in data:
        # Convert item to text for embedding
        text = json.dumps(item)
        embedding = await generate_embedding(text)
        # Generate deterministic UUID
        uid = uuid5(NAMESPACE_URL, f"{source}:{item.get('id', '')}:{text}")
        # Prepare payload
        payload = {
            "content": text,
            "source": source,
            "url": f"{WIKI_API_BASE}/{endpoint}",
            "category": category,
            # Add any other metadata from item
        }
        # Upsert to Qdrant (pseudo-code)
        # qdrant_client.upsert(collection_name=VECTOR_COLLECTION_NAME, points=[...])
        print(f"Would upsert item {item.get('id')} with category {category}")

async def run_wiki_ingestion():
    """Run ingestion for all Wiki API endpoints."""
    endpoints = [
        ("ships", "ships"),
        ("vehicles", "vehicles"),
        ("items", "items"),
        ("comm-links", "lore"),
        ("galactapedia", "lore"),
    ]
    for endpoint, category in endpoints:
        print(f"Fetching {endpoint}...")
        data = await fetch_wiki_endpoint(endpoint)
        # Assuming the API returns a list under a key or the root is a list
        if isinstance(data, dict) and 'data' in data:
            items = data['data']
        elif isinstance(data, list):
            items = data
        else:
            items = [data]
        await process_and_store(items, category, f"wiki:{endpoint}")

if __name__ == "__main__":
    asyncio.run(run_wiki_ingestion())