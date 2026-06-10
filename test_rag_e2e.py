"""End-to-end RAG test for Verse MCP.

Tests the full pipeline: embedding → Qdrant search → result quality.
Runs directly against the services (bypasses MCP/HTTP layer).

NOTE: The RAG pipeline is retrieval-only. The MCP client's LLM model
is responsible for synthesizing the final answer from returned chunks.
We test retrieval quality, not answer generation.
"""

import asyncio
import os
import sys
import json

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from verse_mcp.services.embeddings import generate_embedding
from verse_mcp.services.retriever import init_qdrant, close_qdrant, search_chunks
from verse_mcp.services.cache import init_redis, close_redis, get_cached_embedding, set_cached_embedding
from verse_mcp.services.rag import run_rag_pipeline


async def test_embedding():
    """Test 1: Embedding generation."""
    print("=" * 60)
    print("TEST 1: Embedding Generation")
    print("=" * 60)

    text = "Star Carrack exploration ship"
    embedding = await generate_embedding(text)

    assert len(embedding) == 1536, f"Expected 1536 dims, got {len(embedding)}"
    assert all(isinstance(x, float) for x in embedding), "Not all values are float"
    assert any(x != 0.0 for x in embedding), "Embedding is all zeros"

    print(f"  OK Embedding: {len(embedding)} dimensions")
    print(f"  OK Sample: {embedding[:5]}")
    print()
    return embedding


async def test_qdrant_search(embedding):
    """Test 2: Qdrant vector search returns results."""
    print("=" * 60)
    print("TEST 2: Qdrant Vector Search")
    print("=" * 60)

    chunks = await search_chunks(embedding, top_k=5)

    if not chunks:
        print("  FAIL No chunks returned from Qdrant!")
        print("  This means the knowledge base is empty or unreachable.")
        return []

    print(f"  OK Returned {len(chunks)} chunks")
    for i, chunk in enumerate(chunks):
        content_preview = chunk.content[:120].replace('\n', ' ')
        print(f"  [{i+1}] Source: {chunk.source}")
        print(f"       URL: {chunk.url}")
        print(f"       Content: {content_preview}...")
        print()

    return chunks


async def test_full_pipeline():
    """Test 3: Full RAG pipeline with real questions."""
    print("=" * 60)
    print("TEST 3: Full RAG Pipeline (Retrieval Only)")
    print("=" * 60)
    print("  Note: Verse MCP returns raw chunks. The MCP client's LLM")
    print("  model synthesizes the final answer from these chunks.\n")

    questions = [
        "What is the best mining ship in Star Citizen?",
        "How does quantum travel work?",
        "Tell me about the Aurora MR",
        "What are the weapons available for the Gladius?",
        "Explain the cargo system in Star Citizen",
    ]

    results = {}
    for q in questions:
        print(f"  Question: {q}")
        result = await run_rag_pipeline(q, top_k=5)

        has_content = len(result) > 50 and "No relevant" not in result
        results[q] = {
            "has_content": has_content,
            "length": len(result),
            "preview": result[:200].replace('\n', ' '),
        }

        status = "OK" if has_content else "FAIL"
        print(f"  [{status}] Response length: {len(result)} chars")
        print(f"       Preview: {result[:150]}...")
        print()

    return results


async def test_redis_cache():
    """Test 4: Redis embedding cache."""
    print("=" * 60)
    print("TEST 4: Redis Embedding Cache")
    print("=" * 60)

    test_key = "__test_rag_e2e__"

    emb1 = await generate_embedding(test_key)
    await set_cached_embedding(test_key, emb1)

    cached = await get_cached_embedding(test_key)
    assert cached is not None, "Cache returned None!"
    assert cached == emb1, "Cached embedding doesn't match!"

    print(f"  OK Cache write: OK")
    print(f"  OK Cache read: OK (match={cached == emb1})")
    print()


async def test_data_quality():
    """Test 5: Check Qdrant data quality and coverage."""
    print("=" * 60)
    print("TEST 5: Knowledge Base Coverage")
    print("=" * 60)

    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    client = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

    coll = client.get_collection("sc_chunks")
    total = coll.points_count
    print(f"  Total chunks in Qdrant: {total}")

    categories = ["ships", "vehicles", "armor", "weapons", "equipment", "comm-links", "galactapedia"]
    for cat in categories:
        result, _ = client.scroll(
            "sc_chunks",
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="category", match=models.MatchValue(value=cat))]
            ),
            limit=5000,
            with_payload=False,
            with_vectors=False,
        )
        count = len(result)
        pct = (count / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        print(f"  {cat:15s} {count:5d} ({pct:5.1f}%) [{bar}]")

    client.close()
    print()


async def main():
    print()
    print("=" * 60)
    print("  VERSE MCP — End-to-End RAG Test Suite")
    print("=" * 60)
    print()

    required = ["OPENROUTER_API_KEY", "QDRANT_URL", "REDIS_URL"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"FAIL Missing env vars: {missing}")
        sys.exit(1)

    print(f"  OPENROUTER_API_KEY: set")
    print(f"  QDRANT_URL: {os.getenv('QDRANT_URL')}")
    print(f"  REDIS_URL: {os.getenv('REDIS_URL')}")
    print(f"  EMBEDDING_BASE_URL: {os.getenv('EMBEDDING_BASE_URL', 'default')}")
    print()

    try:
        await init_redis()
        await init_qdrant()

        embedding = await test_embedding()
        chunks = await test_qdrant_search(embedding)
        pipeline_results = await test_full_pipeline()
        await test_redis_cache()
        await test_data_quality()

        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)

        total_q = len(pipeline_results)
        passed_q = sum(1 for r in pipeline_results.values() if r["has_content"])

        print(f"  Embedding:       OK (1536 dims)")
        print(f"  Qdrant search:   {'OK' if chunks else 'FAIL (no results)'}")
        print(f"  Redis cache:     OK")
        print(f"  RAG retrieval:   {passed_q}/{total_q} questions returned content")
        print()

        if passed_q < total_q:
            print("  WARN Questions with no results:")
            for q, r in pipeline_results.items():
                if not r["has_content"]:
                    print(f"    - {q}")
            print()

        if passed_q == total_q:
            print("  ALL TESTS PASSED — Retrieval pipeline is functional!")
        elif passed_q >= total_q // 2:
            print("  PARTIAL SUCCESS — Some queries returned no results.")
        else:
            print("  MAJOR ISSUES — Most queries returned no results.")

    finally:
        await close_redis()
        await close_qdrant()


if __name__ == "__main__":
    asyncio.run(main())
