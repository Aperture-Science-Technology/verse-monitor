"""Star Citizen Wiki ingestion script.

Fetches pages from the Star Citizen Wiki (MediaWiki API), extracts content
from templates, chunks it, generates embeddings via OpenRouter, and stores
everything in Qdrant + Redis cache.

Usage:
    python3 -m ingestion.wiki_ingest          # full ingestion
    python3 -m ingestion.test_quick           # quick test (3 ships)
    python3 -m ingestion.test_ingest          # single ship test
"""

import asyncio
import json
import os
import re
import time
from uuid import NAMESPACE_URL, uuid5

import httpx
import redis.asyncio as redis_lib

from verse_mcp.constants import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    VECTOR_COLLECTION_NAME,
    REDIS_TTL_SECONDS,
    QDRANT_TIMEOUT,
)

# ---------------------------------------------------------------------------
# Configuration (read from env vars at runtime, not import time)
def _env(key: str, default: str) -> str:
    """Read env var at call time, not module load time."""
    return os.getenv(key, default)

WIKI_API_BASE = "https://starcitizen.tools/api.php"
EMBEDDING_BASE_URL = "https://openrouter.ai/api/v1"

# Categories to ingest (Wiki category name -> our category tag)
CATEGORIES = [
    ("Category:Ships", "ships"),
    ("Category:Personal_armor", "armor"),
    ("Category:Ground_vehicles", "vehicles"),
    ("Category:Personal_equipment", "equipment"),
    ("Category:Comm-Link", "lore"),
    ("Category:Armor_sets", "armor"),
]

# Chunking
CHUNK_SIZE = 600       # chars per chunk
CHUNK_OVERLAP = 100    # overlap between chunks

# Rate limiting (seconds between API calls)
RATE_LIMIT_DELAY = 0.3

# Pagination
WIKI_PAGE_LIMIT = 50   # max per API call (MediaWiki allows up to 500)

# ---------------------------------------------------------------------------
# Global clients (initialized in main / test)
# ---------------------------------------------------------------------------

wiki_client: httpx.AsyncClient | None = None
embedding_client: httpx.AsyncClient | None = None
redis_client: redis_lib.Redis | None = None
qdrant_client = None  # initialized via init_qdrant

stats = {
    "pages_fetched": 0,
    "chunks_created": 0,
    "embeddings_generated": 0,
    "embeddings_cached": 0,
    "errors": 0,
    "start_time": 0,
}


# ---------------------------------------------------------------------------
# Wiki API helpers
# ---------------------------------------------------------------------------

async def wiki_get(params: dict) -> dict:
    """Make a GET request to the MediaWiki API."""
    assert wiki_client is not None
    params["format"] = "json"
    params["formatversion"] = 2
    resp = await wiki_client.get(WIKI_API_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Wiki API error: {data['error']}")
    return data


async def fetch_category_members(category: str, limit: int = 0) -> list[str]:
    """Fetch all page titles in a Wiki category (handles pagination)."""
    titles = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": min(limit, WIKI_PAGE_LIMIT) if limit else WIKI_PAGE_LIMIT,
        "cmtype": "page",
    }

    while True:
        data = await wiki_get(params)
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            titles.append(m["title"])

        # Handle pagination
        if "continue" in data and "cmcontinue" in data["continue"]:
            if limit and len(titles) >= limit:
                titles = titles[:limit]
                break
            params["cmcontinue"] = data["continue"]["cmcontinue"]
            await asyncio.sleep(RATE_LIMIT_DELAY)
        else:
            break

    return titles


async def fetch_page_content(title: str) -> str:
    """Fetch the raw wikitext content of a single page."""
    data = await wiki_get({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return ""
    page = pages[0]
    if "missing" in page:
        return ""
    revisions = page.get("revisions", [])
    if not revisions:
        return ""
    return revisions[0].get("slots", {}).get("main", {}).get("content", "")


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

def extract_template_params(wikitext: str) -> dict[str, str]:
    """Extract key-value pairs from the first template in wikitext."""
    params: dict[str, str] = {}
    # Find the first {{TemplateName ... }} block
    match = re.search(r"\{\{(\w+[^{]*?)\}\}", wikitext, re.DOTALL)
    if not match:
        return params

    block = match.group(1)
    # Parse |key = value pairs
    for m in re.finditer(r"\|\s*(\w+)\s*=\s*([^\n|}]+)", block):
        key = m.group(1).strip()
        value = m.group(2).strip()
        if value and value != "":  # skip empty
            params[key] = value
    return params


def wikitext_to_plain_text(wikitext: str) -> str:
    """Convert wikitext to plain text (strip templates, links, etc.)."""
    text = wikitext
    # Remove [[File:...]] and [[Image:...]]
    text = re.sub(r"\[\[(?:File|Image):[^\]]+\]\]", "", text)
    # Replace [[Target|Label]] with Label
    text = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", text)
    # Replace [[Target]] with Target
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Remove {{Ref|...}} and similar templates
    text = re.sub(r"\{\{[^{}]+\}\}", "", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove '''bold''' and ''italic''
    text = re.sub(r"'''+([^']+)'''+", r"\1", text)
    text = re.sub(r"''([^']+)''", r"\1", text)
    # Remove headings markers
    text = re.sub(r"=+\s*(.+?)\s*=+", r"\1", text)
    # Remove bullet points / numbered lists markers
    text = re.sub(r"^[\*#]+", "", text, flags=re.MULTILINE)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

async def generate_embedding(text: str) -> list[float]:
    """Generate embedding via OpenRouter, with Redis cache."""
    global redis_client

    # Check cache
    if redis_client:
        cached = await redis_client.get(f"emb:{text[:200]}")
        if cached:
            stats["embeddings_cached"] += 1
            return json.loads(cached)

    assert embedding_client is not None
    resp = await embedding_client.post(
        f"{_env('EMBEDDING_BASE_URL', 'https://openrouter.ai/api/v1')}/embeddings",
        headers={"Authorization": f"Bearer {_env('OPENROUTER_API_KEY', '')}"},
        json={
            "input": text,
            "model": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_DIMENSIONS,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data["data"][0]["embedding"]
    stats["embeddings_generated"] += 1

    # Cache it
    if redis_client:
        await redis_client.set(
            f"emb:{text[:200]}",
            json.dumps(embedding),
            ex=REDIS_TTL_SECONDS,
        )

    return embedding


# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------

def init_qdrant():
    """Initialize Qdrant client and ensure collection exists."""
    global qdrant_client
    import warnings
    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    qdrant_url = _env("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = _env("QDRANT_API_KEY", "")

    warnings.filterwarnings("ignore", message="Api key is used with an insecure connection")

    qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key or None,
        timeout=QDRANT_TIMEOUT,
    )

    # Ensure collection exists
    collections = qdrant_client.get_collections().collections
    if VECTOR_COLLECTION_NAME not in [c.name for c in collections]:
        qdrant_client.create_collection(
            collection_name=VECTOR_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )
        print(f"Created collection '{VECTOR_COLLECTION_NAME}'")
    else:
        print(f"Collection '{VECTOR_COLLECTION_NAME}' already exists")


async def upsert_chunks(chunks: list[str], source: str, url: str, category: str):
    """Embed and upsert chunks into Qdrant."""
    from qdrant_client.http import models

    points = []
    for chunk_text in chunks:
        embedding = await generate_embedding(chunk_text)
        uid = uuid5(NAMESPACE_URL, f"{source}:{chunk_text[:100]}")
        points.append(
            models.PointStruct(
                id=str(uid),
                vector=embedding,
                payload={
                    "content": chunk_text,
                    "source": source,
                    "url": url,
                    "category": category,
                },
            )
        )

    if points:
        qdrant_client.upsert(
            collection_name=VECTOR_COLLECTION_NAME,
            points=points,
            wait=True,
        )
        stats["chunks_created"] += len(points)


# ---------------------------------------------------------------------------
# Page processing pipeline
# ---------------------------------------------------------------------------

async def process_page(title: str, category: str) -> int:
    """Fetch a wiki page, extract content, chunk, embed, and store. Returns chunk count."""
    try:
        wikitext = await fetch_page_content(title)
        if not wikitext:
            print(f"  [SKIP] {title}: no content")
            return 0

        stats["pages_fetched"] += 1

        # Extract template params for metadata
        params = extract_template_params(wikitext)

        # Convert to plain text
        plain = wikitext_to_plain_text(wikitext)
        if not plain or len(plain) < 50:
            print(f"  [SKIP] {title}: content too short ({len(plain)} chars)")
            return 0

        # Build enriched text with template params
        header_parts = [f"# {title}"]
        if params.get("manufacturer"):
            header_parts.append(f"Manufacturer: {params['manufacturer']}")
        if params.get("career"):
            header_parts.append(f"Career: {params['career']}")
        if params.get("role"):
            header_parts.append(f"Role: {params['role']}")
        if params.get("size"):
            header_parts.append(f"Size: {params['size']}")

        enriched = "\n".join(header_parts) + "\n\n" + plain

        # Chunk
        chunks = chunk_text(enriched)
        if not chunks:
            return 0

        # Build URL
        page_url = f"https://starcitizen.tools/{title.replace(' ', '_')}"

        # Embed and store
        await upsert_chunks(chunks, source=f"wiki:{title}", url=page_url, category=category)

        await asyncio.sleep(RATE_LIMIT_DELAY)
        return len(chunks)

    except Exception as e:
        stats["errors"] += 1
        print(f"  [ERROR] {title}: {e}")
        return 0


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------

async def run_wiki_ingestion():
    """Run full ingestion for all configured categories."""
    global wiki_client, embedding_client, redis_client

    stats["start_time"] = time.time()

    # Init clients
    wiki_client = httpx.AsyncClient(follow_redirects=True)
    embedding_client = httpx.AsyncClient()

    try:
        r = redis_lib.from_url(_env("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
        await r.ping()
        redis_client = r
        print("Redis: OK")
    except Exception as e:
        redis_client = None
        print(f"Redis: {e} (continuing without cache)")

    init_qdrant()
    print(f"Qdrant: OK ({_env('QDRANT_URL', 'http://localhost:6333')})")
    print(f"Embeddings: {EMBEDDING_MODEL} via {_env('EMBEDDING_BASE_URL', 'https://openrouter.ai/api/v1')}")
    print(f"API key present: {bool(_env('OPENROUTER_API_KEY', ''))}")
    print(f"Categories: {len(CATEGORIES)}")
    print()

    total_chunks = 0

    for cat_name, cat_tag in CATEGORIES:
        print(f"{'='*60}")
        print(f"Category: {cat_name} -> {cat_tag}")
        print(f"{'='*60}")

        titles = await fetch_category_members(cat_name)
        print(f"  Found {len(titles)} pages")

        for i, title in enumerate(titles):
            n = await process_page(title, cat_tag)
            total_chunks += n
            elapsed = time.time() - stats["start_time"]
            print(
                f"  [{i+1}/{len(titles)}] {title}: {n} chunks | "
                f"Total: {stats['chunks_created']} chunks, "
                f"{stats['embeddings_generated']} emb, "
                f"{stats['embeddings_cached']} cached | "
                f"{elapsed:.1f}s"
            )

    # Summary
    elapsed = time.time() - stats["start_time"]
    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"Pages fetched:    {stats['pages_fetched']}")
    print(f"Chunks created:   {stats['chunks_created']}")
    print(f"Embeddings API:   {stats['embeddings_generated']}")
    print(f"Embeddings cache: {stats['embeddings_cached']}")
    print(f"Errors:           {stats['errors']}")
    print(f"Time:             {elapsed:.1f}s")
    cost = stats['embeddings_generated'] * 0.00002
    print(f"Cost estimate:    ~${cost:.4f}")

    # Verify
    count = qdrant_client.count(collection_name=VECTOR_COLLECTION_NAME)
    print(f"Qdrant points:    {count.count}")

    # Cleanup
    await wiki_client.aclose()
    await embedding_client.aclose()
    if redis_client:
        await redis_client.close()
    qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(run_wiki_ingestion())
