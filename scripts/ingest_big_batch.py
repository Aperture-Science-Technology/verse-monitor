"""Big batch ingestion — sc_chunks with MAX_PAGES=200.

Usage:
    MAX_PAGES=200 REDIS_URL=redis://:pass@redis:6379 QDRANT_URL=http://qdrant:6333 \
    OPENROUTER_API_KEY=sk-... python3 ingest_big_batch.py
"""

import asyncio, os, sys, time

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Override MAX_PAGES before importing
os.environ["MAX_PAGES"] = os.getenv("MAX_PAGES", "200")

from ingestion import wiki_ingest

async def main():
    print("=" * 60)
    print("BIG BATCH INGESTION — sc_chunks")
    print(f"MAX_PAGES = {os.getenv('MAX_PAGES')}")
    print(f"REDIS_URL = {os.getenv('REDIS_URL', 'not set')}")
    print(f"QDRANT_URL = {os.getenv('QDRANT_URL', 'not set')}")
    print(f"API_BASE = {os.getenv('API_BASE', wiki_ingest.API_BASE)}")
    print(f"OPENROUTER_API_KEY present: {bool(os.getenv('OPENROUTER_API_KEY'))}")
    print("=" * 60)
    result = await wiki_ingest.run_ingestion_cycle()
    print(f"\nDone: {result}")
    return result

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result.get("errors", 0) == 0 else 1)
