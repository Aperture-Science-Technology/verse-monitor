"""Quick test: ingest 3 ships from Star Citizen Wiki."""

import asyncio
import sys
import time

sys.path.insert(0, "/app")

import ingestion.wiki_ingest as wi

# Override config for test
wi.CATEGORIES = [
    ("Category:Ships", "ships"),
]
wi.CHUNK_SIZE = 500
wi.CHUNK_OVERLAP = 100
wi.RATE_LIMIT_DELAY = 0.5


async def main():
    wi.stats["start_time"] = time.time()

    import httpx
    import redis.asyncio as redis_lib

    wi.wiki_client = httpx.AsyncClient(follow_redirects=True)
    wi.embedding_client = httpx.AsyncClient()

    try:
        r = redis_lib.from_url(wi._env("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
        await r.ping()
        wi.redis_client = r
        print("Redis: OK")
    except Exception as e:
        wi.redis_client = None
        print(f"Redis: {e}")

    wi.init_qdrant()
    print(f"Qdrant: OK")
    print(f"Embeddings: {wi.EMBEDDING_MODEL} via {wi.EMBEDDING_BASE_URL}")
    print(f"API key present: {bool(wi._env('OPENROUTER_API_KEY', ''))}")

    # Fetch only 3 ships
    titles = await wi.fetch_category_members("Category:Ships", limit=3)
    print(f"\nShips: {titles}")

    for i, title in enumerate(titles):
        chunks = await wi.process_page(title, "ships")
        elapsed = time.time() - wi.stats["start_time"]
        print(
            f"[{i+1}/{len(titles)}] {title}: {chunks} chunks | "
            f"Total: {wi.stats['chunks_created']} chunks, "
            f"{wi.stats['embeddings_generated']} emb, "
            f"{wi.stats['embeddings_cached']} cached | "
            f"{elapsed:.1f}s"
        )

    # Summary
    elapsed = time.time() - wi.stats["start_time"]
    print(f"\n{'='*50}")
    print(f"TEST COMPLETE")
    print(f"Pages fetched:  {wi.stats['pages_fetched']}")
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

    await wi.wiki_client.aclose()
    await wi.embedding_client.aclose()
    if wi.redis_client:
        await wi.redis_client.aclose()
    if wi.qdrant_client:
        wi.qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(main())
