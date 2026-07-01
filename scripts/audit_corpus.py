"""Audit de la répartition du corpus Qdrant par catégorie/source.

Usage :
    python3 -m scripts.audit_corps --threshold-lore 15

Sortie : tableau répartition + exit code 1 si catégorie lore < seuil.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from verse_mcp.constants import VECTOR_COLLECTION_NAME, QDRANT_TIMEOUT
from verse_monitor.config import settings


async def audit(threshold_lore: float = 15.0) -> dict:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        timeout=int(QDRANT_TIMEOUT),
    )

    count_resp = await asyncio.to_thread(
        client.count, collection_name=VECTOR_COLLECTION_NAME, exact=True
    )
    total = count_resp.count

    by_category: dict[str, int] = {}
    by_source: dict[str, int] = {}
    offset = None
    while True:
        records, next_offset = await asyncio.to_thread(
            client.scroll,
            collection_name=VECTOR_COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=["category", "source"],
            with_vectors=False,
        )
        for r in records:
            p = r.payload or {}
            cat = p.get("category") or "unknown"
            src = p.get("source") or "unknown"
            by_category[cat] = by_category.get(cat, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1
        if next_offset is None:
            break
        offset = next_offset

    lore_count = by_category.get("lore", 0)
    lore_pct = (lore_count / total * 100) if total else 0

    result = {
        "total": total,
        "by_category": {
            k: {"count": v, "pct": round(v / total * 100, 2) if total else 0}
            for k, v in sorted(by_category.items(), key=lambda x: -x[1])
        },
        "by_source": {
            k: {"count": v, "pct": round(v / total * 100, 2) if total else 0}
            for k, v in sorted(by_source.items(), key=lambda x: -x[1])[:15]
        },
        "lore_pct": round(lore_pct, 2),
        "lore_below_threshold": lore_pct < threshold_lore,
        "threshold": threshold_lore,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Audit de répartition corpus Qdrant")
    parser.add_argument("--threshold-lore", type=float, default=15.0,
                        help="Seuil minimum % de chunks lore (défaut: 15.0)")
    parser.add_argument("--json", action="store_true", help="Sortie JSON pur")
    args = parser.parse_args()

    result = asyncio.run(audit(args.threshold_lore))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"VERSE Corpus Audit — {result['total']} chunks total")
        print(f"{'='*50}")
        print(f"\nRépartition par catégorie (top 10) :")
        for k, v in list(result["by_category"].items())[:10]:
            print(f"  {k:<15} {v['count']:>6}  ({v['pct']:>5}%)")
        print(f"\nRépartition par source (top 10) :")
        for k, v in list(result["by_source"].items())[:10]:
            print(f"  {k:<30} {v['count']:>6}  ({v['pct']:>5}%)")
        print(f"\nLore : {result['lore_pct']}% (seuil: {result['threshold']}%) ", end="")
        if result["lore_below_threshold"]:
            print("� SOUS LE SEUIL — ré-ingestion Galactapedia recommandée")
            print("\nPour ré-ingérer : python3 -m ingestion.run --categories lore")
        else:
            print("✅ OK")

    sys.exit(1 if result["lore_below_threshold"] else 0)


if __name__ == "__main__":
    main()
