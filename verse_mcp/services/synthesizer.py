"""Synthèse LLM optionnelle pour sc_ask.

Activée via LLM_SYNTHESIZE=true dans .env.
Désactivée par défaut pour ne pas impacter la prod actuelle (bug #3).

Le modèle utilisé est un flash model OpenRouter (google/gemini-2.0-flash-001)
avec ≤ 200 tokens output. Coût cible < $0.01/req.
"""

import logging

import httpx

from verse_monitor.config import settings

logger = logging.getLogger(__name__)

LLM_SYNTHESIZE_ENABLED = settings.LLM_SYNTHESIZE.lower() in ("1", "true", "yes", "on")
LLM_MODEL = settings.LLM_SYNTHESIZE_MODEL
LLM_MAX_TOKENS = settings.LLM_SYNTHESIZE_MAX_TOKENS
LLM_BASE_URL = settings.LLM_BASE_URL
LLM_SYSTEM_PROMPT = (
    "Tu es un assistant expert sur Star Citizen. "
    "Synthétise une réponse concise et factuelle à la question de l'utilisateur "
    "en te basant UNIQUEMENT sur les sources fournies ci-dessous. "
    "Si les sources sont insuffisantes pour répondre clairement, indique-le. "
    "Réponds en français si la question est en français, sinon en anglais."
)


async def _call_llm(messages: list[dict[str, str]]) -> str:
    """Appel chat completions via OpenRouter."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": LLM_MAX_TOKENS,
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def synthesize_answer(question: str, chunks_text: str) -> str | None:
    """Synthétise une réponse LLM basée sur les chunks."""
    if not LLM_SYNTHESIZE_ENABLED:
        return None

    if not settings.OPENROUTER_API_KEY:
        return None

    try:
        messages = [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question : {question}\n\n"
                    f"--- Sources ---\n{chunks_text}\n\n"
                    "-- Fin des sources --"
                ),
            },
        ]
        return await _call_llm(messages)
    except Exception as exc:
        logger.warning("LLM synthèse échec (retour raw) : %s", exc)
        return None
