"""Star Citizen Wiki ingestion via MediaWiki API.

Uses starcitizen.tools/api.php to fetch pages by category,
extract structured data from wikitext, chunk, embed via OpenRouter,
and upsert into Qdrant.
"""

import asyncio
import hashlib
import json
import os
import re
import time
from uuid import NAMESPACE_URL, uuid5

import httpx
import redis.asyncio as redis
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

# ── Configuration ──────────────────────────────────────────────────────
WIKI_API = "https://starcitizen.tools/api.php"
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis-verse:6379")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
COLLECTION_NAME = "sc_chunks"
CHUNK_SIZE = 600  # chars per chunk
CHUNK_OVERLAP = 100
RATE_LIMIT_DELAY = 0.3  # seconds between API calls
REQUEST_TIMEOUT = 30.0

# Categories to ingest: (wiki_category, our_category)
CATEGORIES = [
    ("Category:Ships", "ships"),
    ("Category:Ground_vehicles", "vehicles"),
    ("Category:Weapons", "items"),
    ("Category:Armor_sets", "items"),
    ("Category:Personal_armor", "items"),
    ("Category:Personal_equipment", "items"),
    ("Category:Comm-Link", "lore"),
    ("Category:Galactapedia", "lore"),
]

# ── HTTP clients ───────────────────────────────────────────────────────
wiki_client: httpx.AsyncClient | None = None
embedding_client: httpx.AsyncClient | None = None
qdrant_client: QdrantClient | None = None
redis_client: redis.Redis | None = None

# Stats
stats = {
    "pages_fetched": 0,
    "pages_skipped": 0,
    "chunks_created": 0,
    "embeddings_generated": 0,
    "embeddings_cached": 0,
    "errors": 0,
    "start_time": 0,
}


# ── Wiki API ───────────────────────────────────────────────────────────
async def wiki_get(params: dict) -> dict:
    """Make a GET request to the MediaWiki API."""
    params["format"] = "json"
    r = await wiki_client.get(WIKI_API, params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


async def fetch_category_members(category: str, limit: int = 500) -> list[str]:
    """Fetch all page titles in a category."""
    titles = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": min(limit, 500),
        "cmtype": "page",
    }
    while True:
        data = await wiki_get(params)
        if "query" in data and "categorymembers" in data["query"]:
            for m in data["query"]["categorymembers"]:
                titles.append(m["title"])
        if "continue" in data and "cmcontinue" in data["continue"]:
            params["cmcontinue"] = data["continue"]["cmcontinue"]
            await asyncio.sleep(RATE_LIMIT_DELAY)
        else:
            break
    return titles


async def fetch_page_wikitext(title: str) -> str | None:
    """Fetch the raw wikitext of a page."""
    data = await wiki_get({
        "action": "parse",
        "page": title,
        "prop": "wikitext",
    })
    if "parse" in data and "wikitext" in data["parse"]:
        return data["parse"]["wikitext"]["*"]
    return None


# ── Wikitext parsing ───────────────────────────────────────────────────
def extract_template_params(wikitext: str, template_name: str) -> dict[str, str]:
    """Extract parameters from a wiki template like {{Vehicle|key=val|...}}."""
    # Find the template
    pattern = r"\{\{" + re.escape(template_name) + r"\s*\|"
    match = re.search(pattern, wikitext, re.IGNORECASE)
    if not match:
        return {}

    # Extract the full template content (handle nested templates)
    start = match.start()
    depth = 0
    end = start
    for i in range(start, len(wikitext)):
        if wikitext[i:i+2] == "{{":
            depth += 1
        elif wikitext[i:i+2] == "}}":
            depth -= 1
            if depth == 0:
                end = i + 2
                break

    template_content = wikitext[start:end]
    # Parse key=value pairs
    params = {}
    # Remove {{TemplateName| and }}
    inner = template_content[2 + len(template_name) + 1:-2]
    # Split by | but respect nested templates
    parts = []
    current = ""
    depth = 0
    for char in inner:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        if char == "|" and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    if current:
        parts.append(current)

    for part in parts:
        if "=" in part:
            key, _, value = part.partition("=")
            key = key.strip()
            value = value.strip()
            if key and value:
                params[key] = value

    return params


def wikitext_to_text(wikitext: str) -> str:
    """Convert wikitext to clean plain text."""
    text = wikitext
    # Remove templates we've already parsed
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    # Remove [[ links but keep display text
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Remove external links
    text = re.sub(r"\[https?://[^\s\]]+\s*([^\]]*)\]", r"\1", text)
    # Remove bold/italic markers
    text = re.sub(r"''+", "", text)
    # Remove headings markers
    text = re.sub(r"=+\s*([^=]+)\s*=+", r"\1", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove refs
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_template_type(wikitext: str) -> str:
    """Detect the primary template type of a page."""
    for template in ["Vehicle", "Ship", "Weapon", "Armor", "Item", "Component", "Comm-Link", "Galactapedia"]:
        if re.search(r"\{\{" + template + r"\s*\|", wikitext, re.IGNORECASE):
            return template
    return "Generic"


# ── Chunking ───────────────────────────────────────────────────────────
def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end within last 100 chars
            search_start = max(start + size - 100, start)
            sentence_end = text.rfind(". ", search_start, end)
            if sentence_end > search_start:
                end = sentence_end + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


# ── Embedding ──────────────────────────────────────────────────────────
async def get_embedding(text: str) -> list[float]:
    """Get embedding from cache or generate via API."""
    # Check cache first
    cache_key = f"emb:{hashlib.md5(text.encode()).hexdigest()}"
    if redis_client:
        cached = await redis_client.get(cache_key)
        if cached:
            stats["embeddings_cached"] += 1
            return json.loads(cached)

    # Generate via API
    response = await embedding_client.post(
        f"{EMBEDDING_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={
            "input": text,
            "model": EMBEDDING_MODEL,
            "dimensions": EMBEDDING_DIMENSIONS,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data["data"][0]["embedding"]
    stats["embeddings_generated"] += 1

    # Cache the result
    if redis_client:
        await redis_client.set(cache_key, json.dumps(embedding), ex=60 * 60 * 24 * 30)

    return embedding


# ── Qdrant ─────────────────────────────────────────────────────────────
def init_qdrant():
    """Initialize Qdrant client and ensure collection exists."""
    global qdrant_client
    qdrant_client = QdrantClient(url=QDRANT_URL, timeout=10)
    collections = qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]
    if COLLECTION_NAME not in collection_names:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=qdrant_models.Distance.COSINE,
            ),
        )
        print(f"  Created collection '{COLLECTION_NAME}'")


async def upsert_chunks(chunks: list[dict]):
    """Upsert chunks into Qdrant."""
    points = []
    for chunk in chunks:
        point_id = str(uuid5(NAMESPACE_URL, chunk["uid"]))
        points.append(
            qdrant_models.PointStruct(
                id=point_id,
                vector=chunk["embedding"],
                payload={
                    "content": chunk["content"],
                    "source": chunk["source"],
                    "url": chunk["url"],
                    "category": chunk["category"],
                    "item_name": chunk.get("item_name", ""),
                    "item_id": chunk.get("item_id", ""),
                    "template_type": chunk.get("template_type", ""),
                    "patch_version": chunk.get("patch_version", ""),
                },
            )
        )
    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)


# ── Main ingestion ─────────────────────────────────────────────────────
async def process_page(title: str, category: str) -> int:
    """Process a single wiki page: fetch, parse, chunk, embed, store."""
    try:
        wikitext = await fetch_page_wikitext(title)
        if not wikitext:
            stats["pages_skipped"] += 1
            return 0

        stats["pages_fetched"] += 1

        # Detect template and extract structured data
        template_type = detect_template_type(wikitext)
        template_params = extract_template_params(wikitext, template_type)

        # Build rich text representation
        name = template_params.get("name", title)
        description = template_params.get("description", "")

        # Create a structured text for embedding
        text_parts = [f"# {name}"]
        if template_type != "Generic":
            text_parts.append(f"Type: {template_type}")
        if category:
            text_parts.append(f"Category: {category}")

        # Add key template params
        priority_fields = [
            "manufacturer", "career", "role", "size", "crew",
            "length", "width", "height", "mass", "cargo",
            "productionstate", "mincrew", "maxcrew",
        ]
        for field in priority_fields:
            if field in template_params:
                text_parts.append(f"{field}: {template_params[field]}")

        # Add description
        if description:
            text_parts.append(f"\n{description}")

        # Add cleaned wikitext body
        body_text = wikitext_to_text(wikitext)
        if body_text:
            text_parts.append(f"\n{body_text}")

        full_text = "\n".join(text_parts)

        # Chunk the text
        chunks_text = chunk_text(full_text)
        if not chunks_text:
            stats["pages_skipped"] += 1
            return 0

        # Generate embeddings and prepare chunks
        chunks = []
        for i, chunk_text_content in enumerate(chunks_text):
            embedding = await get_embedding(chunk_text_content)
            chunk_uid = f"wiki:{title}:{i}:{hashlib.md5(chunk_text_content.encode()).hexdigest()[:8]}"
            chunks.append({
                "uid": chunk_uid,
                "content": chunk_text_content,
                "source": f"wiki:{category}",
                "url": f"https://starcitizen.tools/{title.replace(' ', '_')}",
                "category": category,
                "item_name": name,
                "item_id": template_params.get("uuid", ""),
                "template_type": template_type,
                "patch_version": template_params.get("productionstate", ""),
                "embedding": embedding,
            })
            await asyncio.sleep(RATE_LIMIT_DELAY)

        # Upsert to Qdrant
        await upsert_chunks(chunks)
        stats["chunks_created"] += len(chunks)
        return len(chunks)

    except Exception as e:
        stats["errors"] += 1
        print(f"  ERROR processing {title}: {e}")
        return 0


async def ingest_category(wiki_category: str, our_category: str):
    """Ingest all pages from a wiki category."""
    print(f"\n{'='*60}")
    print(f"Category: {wiki_category} -> {our_category}")
    print(f"{'='*60}")

    titles = await fetch_category_members(wiki_category)
    print(f"Found {len(titles)} pages")

    for i, title in enumerate(titles):
        chunks = await process_page(title, our_category)
        elapsed = time.time() - stats["start_time"]
        rate = stats["embeddings_generated"] / max(elapsed, 1)
        print(
            f"  [{i+1}/{len(titles)}] {title}: {chunks} chunks | "
            f"Total: {stats['chunks_created']} chunks, "
            f"{stats['embeddings_generated']} embeddings, "
            f"{stats['embeddings_cached']} cached | "
            f"{rate:.1f} emb/s"
        )
        await asyncio.sleep(RATE_LIMIT_DELAY)


async def main():
    global wiki_client, embedding_client, redis_client, stats

    stats["start_time"] = time.time()

    print("=" * 60)
    print("VERSE Wiki Ingestion — Star Citizen Wiki (starcitizen.tools)")
    print("=" * 60)

    # Initialize clients
    wiki_client = httpx.AsyncClient(follow_redirects=True)
    embedding_client = httpx.AsyncClient()
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print("Redis: connected")
    except Exception as e:
        print(f"Redis: unavailable ({e}), running without cache")
        redis_client = None

    init_qdrant()
    print(f"Qdrant: connected to {QDRANT_URL}")
    print(f"Embeddings: {EMBEDDING_MODEL} via {EMBEDDING_BASE_URL}")

    # Ingest each category
    for wiki_cat, our_cat in CATEGORIES:
        await ingest_category(wiki_cat, our_cat)

    # Print summary
    elapsed = time.time() - stats["start_time"]
    print(f"\n{'='*60}")
    print("INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"Pages fetched:    {stats['pages_fetched']}")
    print(f"Pages skipped:    {stats['pages_skipped']}")
    print(f"Chunks created:   {stats['chunks_created']}")
    print(f"Embeddings (API): {stats['embeddings_generated']}")
    print(f"Embeddings (cache): {stats['embeddings_cached']}")
    print(f"Errors:           {stats['errors']}")
    print(f"Time:             {elapsed:.1f}s")
    print(f"Cost estimate:    ~${stats['embeddings_generated'] * 0.00002:.4f}")
    print(f"  (at ~$0.02/1M tokens, ~100 tokens/chunk)")

    # Cleanup
    await wiki_client.aclose()
    await embedding_client.aclose()
    if redis_client:
        await redis_client.close()
    if qdrant_client:
        qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(main())
