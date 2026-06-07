"""Quick test: fetch one ship, embed it, store in Qdrant."""

import asyncio
import time

import httpx
import redis.asyncio as redis_lib

from ingestion.wiki_ingest import (
    init_qdrant,
    fetch_category_members,
    process_page,
    wiki_client,
    embedding_client,
    redis_client,
    stats,
    _env,
)


async def test():
    stats["start_time"] = time.time()

    # Init clients
    import ingestion.wiki_ingest as wi
    wi.wiki_client = httpx.AsyncClient(follow_redirects=True)
    wi.embedding_client = httpx.AsyncClient()
    wi.redis_client = None
    try:
        r = redis_lib.from_url(_env("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
        await r.ping()
        wi.redis_client = r
        print("Redis: OK")
    except Exception as e:
        print(f"Redis: {e}")

    init_qdrant()

    # Fetch 3 ships
    titles = await fetch_category_members("Category:Ships", limit=3)
    print(f"Ships found: {titles}")

    if titles:
        chunks = await process_page(titles[0], "ships")
        print(f"Result: {chunks} chunks from '{titles[0]}'")
        print(f"Stats: {stats}")

    # Cleanup
    await wi.wiki_client.aclose()
    await wi.embedding_client.aclose()
    if wi.redis_client:
        await wi.redis_client.close()


if __name__ == "__main__":
    asyncio.run(test())
