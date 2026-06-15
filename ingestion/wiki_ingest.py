"""Star Citizen Wiki API v2 ingestion script.

Uses api.star-citizen.wiki as the primary data source.
All endpoints return JSON with pagination (data/links/meta structure).

Endpoints used:
    /api/vehicles       → Ship/vehicle stats (sc_get_ship_stats)
    /api/galactapedia   → Lore articles (sc_search_lore)
    /api/comm-links     → Official communications (sc_search_lore)
    /api/items          → Items: armor, weapons, equipment (sc_ask)

Content from galactapedia and comm-links is in translations.en_EN.
Vehicles have structured fields (manufacturer, career, role, stats, etc.).

Usage:
    python3 -m ingestion.run              # full ingestion
    python3 -m ingestion.test_v2          # quick test (3 vehicles)
"""

import asyncio
import hashlib
import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone
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
from ingestion.chunking import semantic_chunk_text

# ---------------------------------------------------------------------------
# Configuration (read from env vars at runtime)
# ---------------------------------------------------------------------------

def _env(key: str, default: str) -> str:
    return os.getenv(key, default)

API_BASE = _env("WIKI_API_BASE", "https://api.star-citizen.wiki/api")
EMBEDDING_BASE_URL = _env("EMBEDDING_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY", "")
REDIS_URL = _env("REDIS_URL", "redis://localhost:6379")
QDRANT_URL = _env("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = _env("QDRANT_API_KEY", "")

# Pagination
API_PAGE_LIMIT = 200  # max per page (API allows up to 200)
API_TIMEOUT = 300.0   # seconds (galactapedia can be very slow)
MAX_PAGES = 50         # max pages per source (to avoid extremely long runs)

# Rate limiting
RATE_LIMIT_DELAY = 0.2  # seconds between API calls

# Chunking
CHUNK_SIZE = 600
CHUNK_OVERLAP = 2

# Ingestion sources: (endpoint, category, content_extractor_name)
# Each source defines how to extract searchable text from its items
SOURCES = [
    {
        "endpoint": "/vehicles",
        "category": "ships",
        "description": "Ship and vehicle specifications",
        "content_extractor": "vehicle",
    },
    {
        "endpoint": "/galactapedia",
        "category": "lore",
        "description": "Galactapedia lore articles",
        "content_extractor": "galactapedia",
    },
    {
        "endpoint": "/comm-links",
        "category": "lore",
        "description": "Official Comm-Links",
        "content_extractor": "comm_link",
    },
    {
        "endpoint": "/items?filter[type]=WeaponPersonal",
        "category": "weapons",
        "description": "Personal weapons",
        "content_extractor": "item",
    },
    {
        "endpoint": "/items?filter[category]=fps-armor",
        "category": "armor",
        "description": "FPS armor",
        "content_extractor": "item",
    },
    {
        "endpoint": "/items?filter[category]=fps-backpack",
        "category": "equipment",
        "description": "FPS backpacks and equipment",
        "content_extractor": "item",
    },
]

# ---------------------------------------------------------------------------
# Global clients
# ---------------------------------------------------------------------------

api_client: httpx.AsyncClient | None = None
embedding_client: httpx.AsyncClient | None = None
redis_client: redis_lib.Redis | None = None
qdrant_client = None

stats = {
    "items_fetched": 0,
    "chunks_created": 0,
    "embeddings_generated": 0,
    "embeddings_cached": 0,
    "errors": 0,
    "start_time": 0,
}


# ---------------------------------------------------------------------------
# API v2 helpers
# ---------------------------------------------------------------------------

async def api_get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to the Star Citizen Wiki API v2."""
    assert api_client is not None
    url = f"{API_BASE}{path}"
    headers = {"Accept": "application/json"}
    resp = await api_client.get(url, params=params or {}, headers=headers, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


async def fetch_all_pages(endpoint: str, max_pages: int = MAX_PAGES) -> list[dict]:
    """Fetch items from a paginated API endpoint, up to max_pages."""
    all_items = []
    page = 1

    while page <= max_pages:
        data = await api_get(endpoint, params={"limit": API_PAGE_LIMIT, "page": page})
        items = data.get("data", [])
        if not items:
            break
        all_items.extend(items)

        # Check if there's a next page
        links = data.get("links", {})
        if not links.get("next"):
            break
        page += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_items


async def fetch_item_detail(api_url: str) -> dict:
    """Fetch a single item by its full API URL."""
    assert api_client is not None
    headers = {"Accept": "application/json"}
    resp = await api_client.get(api_url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", data)


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

def _tr(val):
    """Extract English text from a multilingual field (dict or plain string)."""
    if isinstance(val, dict):
        return val.get("en_EN") or val.get("de_DE") or val.get("fr_FR") or val.get("zh_CN") or ""
    return str(val) if val else ""


def extract_vehicle_text(item: dict) -> str:
    """Extract searchable English text from a vehicle item."""
    parts = []

    name = _tr(item.get("name", ""))
    if name:
        parts.append(f"# {name}")

    game_name = _tr(item.get("game_name", ""))
    if game_name and game_name != name:
        parts.append(f"Game Name: {game_name}")

    manufacturer = item.get("manufacturer", {})
    if isinstance(manufacturer, dict):
        mfg_name = manufacturer.get("name", manufacturer.get("code", ""))
        if mfg_name:
            parts.append(f"Manufacturer: {mfg_name}")

    for field in ["career", "role", "type", "production_status", "size_class"]:
        val = _tr(item.get(field, ""))
        if val and val.strip():
            parts.append(f"{field.replace('_', ' ').title()}: {val}")

    # Description — prefer en_EN
    desc = _tr(item.get("game_description", item.get("description", "")))
    if desc and desc.strip():
        parts.append(f"\n{desc}")

    # Key stats
    stats_lines = []
    for stat_key in ["cargo_capacity", "crew", "mass", "speed", "shield_hp"]:
        val = item.get(stat_key)
        if val is not None:
            if isinstance(val, dict):
                val_str = ", ".join(f"{k}: {v}" for k, v in val.items())
                stats_lines.append(f"  {stat_key}: {val_str}")
            else:
                stats_lines.append(f"  {stat_key}: {val}")

    if stats_lines:
        parts.append("\nStats:\n" + "\n".join(stats_lines))

    # Loaner ships
    loaner = item.get("loaner", [])
    if loaner:
        loaner_names = []
        for l in loaner:
            if isinstance(l, dict):
                loaner_names.append(l.get("name", l.get("slug", "")))
            elif isinstance(l, str):
                loaner_names.append(l)
        if loaner_names:
            parts.append(f"\nLoaner: {', '.join(loaner_names)}")

    # MSRP
    msrp = item.get("msrp")
    if msrp:
        parts.append(f"MSRP: ${msrp}")

    # Patch version
    version = item.get("version", "")
    if version:
        parts.append(f"Version: {version}")

    return "\n".join(parts)


def extract_galactapedia_text(item: dict) -> str:
    """Extract searchable text from a Galactapedia article."""
    parts = []

    title = item.get("title", "")
    if title:
        parts.append(f"# {title}")

    # Content is in translations
    translations = item.get("translations", {})
    content = translations.get("en_EN", "")
    if not content:
        # Fallback to any available translation
        for lang in ["en_EN", "de_DE", "fr_FR", "zh_CN"]:
            content = translations.get(lang, "")
            if content:
                break

    if content and content != "Pending review by the Ark research team...":
        parts.append(content)

    # Categories
    categories = item.get("categories", [])
    if categories:
        cat_names = [c.get("name", "") for c in categories if isinstance(c, dict)]
        if cat_names:
            parts.append(f"Categories: {', '.join(cat_names)}")

    return "\n\n".join(parts)


def extract_comm_link_text(item: dict) -> str:
    """Extract searchable text from a Comm-Link."""
    parts = []

    title = item.get("title", "")
    if title:
        parts.append(f"# {title}")

    # Content is in translations
    translations = item.get("translations", {})
    content = translations.get("en_EN", "")
    if not content:
        for lang in ["en_EN", "de_DE", "fr_FR", "zh_CN"]:
            content = translations.get(lang, "")
            if content:
                break

    if content:
        parts.append(content)

    # Metadata
    for field in ["channel", "category", "series"]:
        val = item.get(field, "")
        if val and str(val).strip():
            parts.append(f"{field.title()}: {val}")

    return "\n\n".join(parts)


def extract_item_text(item: dict) -> str:
    """Extract searchable text from an item (weapon, armor, equipment)."""
    parts = []

    name = item.get("name", item.get("title", ""))
    if name:
        parts.append(f"# {name}")

    for field in ["type", "category", "size", "grade"]:
        val = item.get(field, "")
        if val and str(val).strip():
            parts.append(f"{field.title()}: {val}")

    description = _tr(item.get("description", item.get("game_description", "")))
    if description and description.strip():
        parts.append(f"\n{description}")

    # Version / patch
    version = item.get("version", "")
    if version:
        parts.append(f"Version: {version}")

    return "\n".join(parts)


def get_content_extractor(endpoint: str):
    """Return the appropriate content extractor for an endpoint."""
    if "vehicles" in endpoint:
        return extract_vehicle_text
    elif "galactapedia" in endpoint:
        return extract_galactapedia_text
    elif "comm-links" in endpoint:
        return extract_comm_link_text
    else:
        return extract_item_text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Legacy wrapper — delegates to semantic_chunk_text.  Kept for backward compatibility."""
    return semantic_chunk_text(text, target_size=size, overlap_sentences=overlap)


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
        f"{EMBEDDING_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
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

    warnings.filterwarnings("ignore", message="Api key is used with an insecure connection")

    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        timeout=QDRANT_TIMEOUT,
    )

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


async def upsert_chunks(chunks: list[str], source: str, url: str, category: str, patch_version: str | None = None, source_modified_at: str | None = None):
    """Embed and upsert chunks into Qdrant."""
    from qdrant_client.http import models

    indexed_at = datetime.now(timezone.utc).isoformat()
    points = []
    for chunk_text in chunks:
        content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()

        # Skip chunks whose content already exists in Qdrant
        existing, _ = await asyncio.to_thread(
            qdrant_client.scroll,
            collection_name=VECTOR_COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="content_hash", match=models.MatchValue(value=content_hash))]
            ),
            limit=1,
            with_payload=False,
        )
        if existing:
            continue

        embedding = await generate_embedding(chunk_text)
        uid = uuid5(NAMESPACE_URL, f"{category}:{source}:{chunk_text[:100]}")
        payload = {
            "content": chunk_text,
            "source": source,
            "url": url,
            "category": category,
            "indexed_at": indexed_at,
            "source_modified_at": source_modified_at,
            "content_hash": content_hash,
        }
        if patch_version:
            payload["patch_version"] = patch_version
        points.append(
            models.PointStruct(
                id=str(uid),
                vector=embedding,
                payload=payload,
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
# Ingestion pipeline
# ---------------------------------------------------------------------------

async def process_item(item: dict, category: str, endpoint: str) -> int:
    """Process a single API item: extract text, chunk, embed, store."""
    try:
        extractor = get_content_extractor(endpoint)
        text = extractor(item)

        if not text or len(text.strip()) < 30:
            return 0

        stats["items_fetched"] += 1

        # Chunk
        chunks = chunk_text(text)
        if not chunks:
            return 0

        # Build source URL
        name = _tr(item.get("name", item.get("title", "")))
        slug = item.get("slug", name.replace(" ", "_"))
        source_url = item.get("web_url", f"https://api.star-citizen.wiki/{endpoint.split('?')[0].strip('/')}/{slug}")

        # Extract patch version from item metadata
        patch_version = item.get("patch_version", item.get("version", None))
        if not patch_version:
            # Try to extract from production_status or other fields
            patch_version = item.get("production_status", None)

        # Embed and store
        source = f"api:{endpoint.split('?')[0].strip('/')}:{name}"
        source_modified_at = item.get("updated_at", None)
        await upsert_chunks(chunks, source=source, url=source_url, category=category, patch_version=patch_version, source_modified_at=source_modified_at)

        return len(chunks)

    except Exception as e:
        stats["errors"] += 1
        name = _tr(item.get("name", item.get("title", "unknown")))
        print(f"  [ERROR] {name}: {e}")
        return 0


async def ingest_source(source_config: dict) -> int:
    """Ingest all items from a single source endpoint."""
    endpoint = source_config["endpoint"]
    category = source_config["category"]
    description = source_config["description"]

    print(f"\n{'='*60}")
    print(f"Source: {endpoint}")
    print(f"Category: {category} — {description}")
    print(f"{'='*60}")

    items = await fetch_all_pages(endpoint)
    print(f"  Fetched {len(items)} items")

    total_chunks = 0
    for i, item in enumerate(items):
        n = await process_item(item, category, endpoint)
        total_chunks += n
        elapsed = time.time() - stats["start_time"]
        name = item.get("name", item.get("title", f"item_{i}"))
        print(
            f"  [{i+1}/{len(items)}] {name}: {n} chunks | "
            f"Total: {stats['chunks_created']} chunks, "
            f"{stats['embeddings_generated']} emb, "
            f"{stats['embeddings_cached']} cached | "
            f"{elapsed:.1f}s"
        )

    return total_chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_ingestion_cycle(categories: list[str] | None = None) -> dict:
    """Run an ingestion cycle, optionally filtered to specific source categories.

    Returns stats dict with keys: items_fetched, chunks_created,
    embeddings_generated, errors, elapsed_seconds.
    """
    global api_client, embedding_client, redis_client

    # Reset global stats for this cycle
    stats.update({
        "items_fetched": 0,
        "chunks_created": 0,
        "embeddings_generated": 0,
        "embeddings_cached": 0,
        "errors": 0,
        "start_time": time.time(),
    })

    sources = SOURCES if categories is None else [s for s in SOURCES if s["category"] in categories]

    api_client = httpx.AsyncClient(follow_redirects=True)
    embedding_client = httpx.AsyncClient()

    try:
        r = redis_lib.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        redis_client = r
        print("Redis: OK")
    except Exception as e:
        redis_client = None
        print(f"Redis: {e} (continuing without cache)")

    init_qdrant()
    print(f"Qdrant: OK ({QDRANT_URL})")
    print(f"API: {API_BASE}")
    print(f"Embeddings: {EMBEDDING_MODEL} via {EMBEDDING_BASE_URL}")
    print(f"API key present: {bool(OPENROUTER_API_KEY)}")
    print(f"Sources: {len(sources)} (filtered by categories={categories})")

    for source in sources:
        await ingest_source(source)

    elapsed = time.time() - stats["start_time"]
    print(f"\n{'='*60}")
    print(f"INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"Items fetched:    {stats['items_fetched']}")
    print(f"Chunks created:   {stats['chunks_created']}")
    print(f"Embeddings API:   {stats['embeddings_generated']}")
    print(f"Embeddings cache: {stats['embeddings_cached']}")
    print(f"Errors:           {stats['errors']}")
    print(f"Time:             {elapsed:.1f}s")
    cost = stats['embeddings_generated'] * 0.00002
    print(f"Cost estimate:    ~${cost:.4f}")

    count = qdrant_client.count(collection_name=VECTOR_COLLECTION_NAME)
    print(f"Qdrant points:    {count.count}")

    await api_client.aclose()
    await embedding_client.aclose()
    if redis_client:
        await redis_client.aclose()
    qdrant_client.close()

    return {
        "items_fetched": stats["items_fetched"],
        "chunks_created": stats["chunks_created"],
        "embeddings_generated": stats["embeddings_generated"],
        "errors": stats["errors"],
        "elapsed_seconds": elapsed,
    }


async def run_ingestion():
    """Run full ingestion from all API v2 sources (backward-compatible entry point)."""
    await run_ingestion_cycle(categories=None)


if __name__ == "__main__":
    asyncio.run(run_ingestion())
