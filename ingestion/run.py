"""Main ingestion orchestrator."""

import asyncio
from .wiki_api import run_wiki_ingestion
# TODO: Import other ingestion modules when implemented
# from .scunpacked import run_scunpacked_ingestion
# from .web_scraper import run_web_scraping
# from .chunker import run_chunking

async def main():
    """Run all ingestion processes."""
    print("Starting VERSE data ingestion...")
    await run_wiki_ingestion()
    # TODO: Run other ingestion processes
    print("Ingestion completed.")

if __name__ == "__main__":
    asyncio.run(main())