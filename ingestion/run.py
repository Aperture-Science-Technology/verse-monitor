"""Main ingestion orchestrator — uses wiki_ingest (v2 API)."""

import asyncio
import sys
import os

# Ensure /app is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.wiki_ingest import run_ingestion

async def main():
    print("Starting VERSE data ingestion (API v2 — enriched)...")
    await run_ingestion()
    print("Ingestion completed.")

if __name__ == "__main__":
    asyncio.run(main())
