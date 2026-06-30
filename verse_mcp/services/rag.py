"""RAG pipeline service."""

import logging

from verse_mcp.services.embeddings import generate_embedding
from verse_mcp.services.cache import get_cached_embedding, set_cached_embedding
from verse_mcp.services.retriever import search_chunks, DEFAULT_SCORE_THRESHOLD
from verse_mcp.constants import CHAR_LIMIT
from verse_monitor.errors import error_to_json

logger = logging.getLogger(__name__)


# Seuils par outil — sc_ship veut du rappel, sc_lore veut de la précision
SCORE_THRESHOLDS = {
    "ships": 0.35,
    "lore": 0.50,
    "guide": 0.40,
    "community": 0.35,
    "ask": 0.40,
    "_default": DEFAULT_SCORE_THRESHOLD,
}


def _threshold_for(category: str | None) -> float:
    if category is None:
        return SCORE_THRESHOLDS["_default"]
    return SCORE_THRESHOLDS.get(category, SCORE_THRESHOLDS["_default"])


async def run_rag_pipeline(
    question: str,
    category: str | None = None,
    top_k: int = 5,
    score_threshold: float | None = None,
) -> str:
    """Run the RAG pipeline: cache -> embedding -> search -> return formatted chunks.

    Si aucun résultat ne dépasse le seuil, renvoie un message explicite
    avec le score max observé (bug #4 fix).
    """
    try:
        embedding = await get_cached_embedding(question)
        if embedding is None:
            embedding = await generate_embedding(question)
            await set_cached_embedding(question, embedding)

        threshold = score_threshold if score_threshold is not None else _threshold_for(category)
        chunks, max_seen = await search_chunks(
            embedding, top_k=top_k, category=category, score_threshold=threshold
        )

        if not chunks:
            if max_seen == 0.0:
                return "Aucun résultat trouvé pour cette requête (corpus vide ou filtre trop restrictif)."
            return (
                f"Aucun résultat fiable trouvé pour cette requête "
                f"(score max observé : {max_seen:.2f} < seuil {threshold}). "
                f"Réformulez votre question ou essayez des termes plus précis."
            )

        parts = []
        for c in chunks:
            header = f"[Source: {c.source} | {c.url} | score: {c.score:.2f}]"
            if c.patch_version:
                header += f" [Patch: {c.patch_version}]"
            parts.append(f"{header}\n\n{c.content}")

        result = "\n\n---\n\n".join(parts)

        if len(result) > CHAR_LIMIT:
            result = result[:CHAR_LIMIT] + "\n\n[Context truncated — refine the query for more precise results.]"

        return result
    except Exception as exc:
        logger.error("Erreur RAG pipeline: %s", exc)
        return error_to_json(exc)
