"""Big batch ingestion — sc_chunks with MAX_PAGES=200.

Covers all 6 sources:
  - /vehicles (ships)
  - /galactapedia (lore)
  - /comm-links (lore)
  - /items?filter[type]=WeaponPersonal (weapons)
  - /items?filter[category]=fps-armor (armor)
  - /items?filter[category]=fps-backpack (equipment)

Usage:
    MAX_PAGES=200 python3 -m ingestion.run
"""

import asyncio, os, time

# Override MAX_PAGES before importing wiki_ingest
os.environ["MAX_PAGES"] = "200"

from ingestion import wiki_ingest

async def main():
    print("=" * 60)
    print("BIG BATCH INGESTION — sc_chunks")
    print(f"MAX_PAGES = {os.getenv('MAX_PAGES')}")
    print("=" * 60)
    result = await wiki_ingest.run_ingestion_cycle()
    print(f"\nDone: {result['chunks_created']} chunks from {result['items_fetched']} items")

if __name__ == "__main__":
    asyncio.run(main())
