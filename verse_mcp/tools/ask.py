"""Tool: sc_ask - General question answering pipeline."""

from verse_mcp.services.rag import run_rag_pipeline
from verse_mcp.services.synthesizer import synthesize_answer


async def sc_ask(question: str, category: str | None = None, top_k: int = 5) -> str:
    """General question — returns relevant Star Citizen knowledge chunks.

    Si LLM_SYNTHESIZE=true, retourne une réponse synthétisée + les sources.
    Sinon, comportement historique (chunks bruts filtrés par score).
    """
    raw = await run_rag_pipeline(question=question, category=category, top_k=top_k)

    # Pas de synthèse si déjà un message "Aucun résultat"
    if raw.startswith("Aucun résultat"):
        return raw

    synth = await synthesize_answer(question, raw)
    if synth is None:
        return raw

    return (
        f"{synth}\n\n"
        f"---\n\n"
        f"Sources utilisées :\n{raw}"
    )
