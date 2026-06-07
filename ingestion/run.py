"""Main ingestion orchestrator."""

import asyncio
from .wiki_ingest import run_ingestion


async def main():
    """Run all ingestion processes."""
    print("Starting VERSE data ingestion (API v2)...")
    await run_ingestion()
    print("Ingestion completed.")


if __name__ == "__main__":
    asyncio.run(main())
