"""Quick test: ingest a few items from Star Citizen Wiki API v2."""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ingestion.wiki_ingest as wi


async def main():
    wi.stats["start_time"] = time.time()

    import httpx
    import redis.asyncio as redis_lib

    wi.api_client = httpx.AsyncClient(follow_redirects=True)
    wi.embedding_client = httpx.AsyncClient()

    try:
        r = redis_lib.from_url(wi.REDIS_URL, decode_responses=True)
        await r.ping()
        wi.redis_client = r
        print("Redis: OK")
    except Exception as e:
        wi.redis_client = None
        print(f"Redis: {e}")

    wi.init_qdrant()
    print(f"Qdrant: OK")
    print(f"API: {wi.API_BASE}")
    print(f"Embeddings: {wi.EMBEDDING_MODEL} via {wi.EMBEDDING_BASE_URL}")
    print(f"API key present: {bool(wi.OPENROUTER_API_KEY)}")

    # Test with 3 vehicles + 3 items
    wi.API_PAGE_LIMIT = 3

    print("\n--- Vehicles ---")
    vehicles = await wi.fetch_all_pages("/vehicles")
    for i, v in enumerate(vehicles):
        n = await wi.process_item(v, "ships", "/vehicles")
        print(f"  [{i+1}/{len(vehicles)}] {v.get('name', '?')}: {n} chunks")

    print("\n--- Comm-Links ---")
    comm_links = await wi.fetch_all_pages("/comm-links")
    for i, c in enumerate(comm_links):
        n = await wi.process_item(c, "lore", "/comm-links")
        title = c.get("title", "?")
        print(f"  [{i+1}/{len(comm_links)}] {title}: {n} chunks")

    # Summary
    elapsed = time.time() - wi.stats["start_time"]
    print(f"\n{'='*50}")
    print(f"QUICK TEST COMPLETE")
    print(f"Items:  {wi.stats['items_fetched']}")
    print(f"Chunks: {wi.stats['chunks_created']}")
    print(f"Emb API: {wi.stats['embeddings_generated']}")
    print(f"Emb cache: {wi.stats['embeddings_cached']}")
    print(f"Errors: {wi.stats['errors']}")
    print(f"Time:   {elapsed:.1f}s")

    count = wi.qdrant_client.count(collection_name=wi.VECTOR_COLLECTION_NAME)
    print(f"Qdrant: {count.count} points")

    await wi.api_client.aclose()
    await wi.embedding_client.aclose()
    if wi.redis_client:
        await wi.redis_client.aclose()
    if wi.qdrant_client:
        wi.qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(main())
