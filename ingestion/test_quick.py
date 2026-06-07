"""Quick test: ingest 3 vehicles from Star Citizen Wiki API v2."""

import asyncio
import sys
import time

sys.path.insert(0, "/app")

import ingestion.wiki_ingest as wi


async def main():
    wi.stats["start_time"] = time.time()

    import httpx
    import redis.asyncio as redis_lib

    wi.api_client = httpx.AsyncClient(headers={"Accept": "application/json"})
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

    # Fetch only 3 vehicles for test
    old_limit = wi.API_PAGE_LIMIT
    wi.API_PAGE_LIMIT = 3
    vehicles = await wi.fetch_all_pages("/vehicles")
    wi.API_PAGE_LIMIT = old_limit
    print(f"\nVehicles found: {len(vehicles)}")

    for i, vehicle in enumerate(vehicles):
        name = vehicle.get("name", "Unknown")
        n = await wi.process_item(vehicle, "ships", "/vehicles")
        elapsed = time.time() - wi.stats["start_time"]
        print(
            f"[{i+1}/{len(vehicles)}] {name}: {n} chunks | "
            f"Total: {wi.stats['chunks_created']} chunks, "
            f"{wi.stats['embeddings_generated']} emb, "
            f"{wi.stats['embeddings_cached']} cached | "
            f"{elapsed:.1f}s"
        )

    # Summary
    elapsed = time.time() - wi.stats["start_time"]
    print(f"\n{'='*50}")
    print(f"TEST COMPLETE")
    print(f"Items fetched:  {wi.stats['items_fetched']}")
    print(f"Chunks created: {wi.stats['chunks_created']}")
    print(f"Embeddings API: {wi.stats['embeddings_generated']}")
    print(f"Embeddings cache: {wi.stats['embeddings_cached']}")
    print(f"Errors:         {wi.stats['errors']}")
    print(f"Time:           {elapsed:.1f}s")
    cost = wi.stats['embeddings_generated'] * 0.00002
    print(f"Cost estimate:  ~${cost:.4f}")

    # Verify in Qdrant
    count = wi.qdrant_client.count(collection_name=wi.VECTOR_COLLECTION_NAME)
    print(f"Qdrant points:  {count.count}")

    await wi.api_client.aclose()
    await wi.embedding_client.aclose()
    if wi.redis_client:
        await wi.redis_client.aclose()
    if wi.qdrant_client:
        wi.qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(main())
