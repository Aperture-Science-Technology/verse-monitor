"""Tool: sc_get_ship_stats — exact-name-first re-ranking (bug #6 fix).

"Avenger Titan" ne doit pas renvoyer "Avenger Titan Renegade" en premier.
Stratégie : retrieval sémantique broad (top_k=15) puis re-rank par boost
de +0.2 sur les chunks dont le contenu contient le nom exact du vaisseau
(comme mot-plein, pas comme sous-chaîne d'un nom plus long).
"""

import re

from verse_mcp.services.retriever import search_chunks, DEFAULT_SCORE_THRESHOLD
from verse_mcp.services.embeddings import generate_embedding
from verse_mcp.services.cache import get_cached_embedding, set_cached_embedding
from verse_mcp.constants import CHAR_LIMIT

# Boost score pour les chunks où le nom EXACT du vaisseau est présent
_EXACT_NAME_BOOST = 0.2


def _normalize(name: str) -> str:
    return name.strip().lower()


def _exact_contains(content: str, ship_norm: str) -> bool:
    """True si `ship_norm` apparaît comme mot-plein exact dans le contenu."""
    escaped = r"\s+".join(re.escape(part) for part in ship_norm.split())
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return re.search(pattern, content, re.IGNORECASE) is not None


def _format_chunks(chunks) -> str:
    """Formater une liste de chunks en texte lisible."""
    if not chunks:
        return "Aucun résultat fiable trouvé pour ce vaisseau."
    parts = []
    for c in chunks:
        header = f"[Source: {c.source} | {c.url} | score: {c.score:.2f}]"
        if c.patch_version:
            header += f" [Patch: {c.patch_version}]"
        parts.append(f"{header}\n\n{c.content}")
    result = "\n\n---\n\n".join(parts)
    if len(result) > CHAR_LIMIT:
        result = result[:CHAR_LIMIT] + "\n\n[Context truncated — refine the query.]"
    return result


async def sc_get_ship_stats(ship_name: str) -> str:
    """Full ship stats — exact-name-first retrieval with re-ranking (bug #6)."""
    # 1. Embedding
    embedding = await get_cached_embedding(ship_name)
    if embedding is None:
        embedding = await generate_embedding(ship_name)
        await set_cached_embedding(ship_name, embedding)

    # 2. Retrieval broad (top_k=15, seuil ships=0.35)
    chunks, max_seen = await search_chunks(
        embedding,
        top_k=15,
        category="ships",
        score_threshold=0.35,
    )

    if not chunks:
        if max_seen == 0.0:
            return "Aucun résultat trouvé pour ce vaisseau (catégorie ships vide)."
        return (
            f"Aucun résultat fiable pour '{ship_name}' "
            f"(score max {max_seen:.2f} < seuil 0.35)."
        )

    # 3. Re-ranking : boost +0.2 sur les chunks contenant le nom exact
    ship_norm = _normalize(ship_name)
    boosted = []
    for c in chunks:
        effective_score = c.score
        if _exact_contains(c.content, ship_norm):
            effective_score += _EXACT_NAME_BOOST
        boosted.append((effective_score, c))

    boosted.sort(key=lambda x: x[0], reverse=True)

    # 4. Retourner les top_k=5 après re-ranking
    top_chunks = [c for _, c in boosted[:5]]

    # 5. Mettre à jour les scores affichés avec le boost appliqué
    for c, (effective, _) in zip(top_chunks, boosted[:5]):
        c.score = effective

    return _format_chunks(top_chunks)
