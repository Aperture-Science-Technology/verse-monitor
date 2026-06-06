"""Tool: sc_get_guide and sc_search_lore."""

import re

from verse_mcp.services.rag import run_rag_pipeline
from verse_mcp.models.outputs import GuideOutput, SearchLoreOutput, LoreResult


def _parse_lore_results(text: str) -> list[LoreResult]:
    results = []
    for chunk in text.split("\n\n---\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("\n\n", 1)
        header = parts[0].strip()
        content = parts[1].strip() if len(parts) > 1 else header
        m = re.match(r"\[Source: ([^|]+) \| ([^\]]+)\]", header)
        title = m.group(1).strip() if m else "Unknown"
        url = m.group(2).strip() if m else ""
        results.append(LoreResult(title=title, content=content, url=url, related_topics=[]))
    return results


async def sc_get_guide(guide_title: str, player_level: str = "beginner") -> GuideOutput:
    """Step-by-step guide, `player_level` parameter (beginner/intermediate/advanced)"""
    question = f"Provide a step-by-step guide for {guide_title} suitable for {player_level} players."
    text = await run_rag_pipeline(question=question, top_k=10)
    steps = [c.strip() for c in text.split("\n\n---\n\n") if c.strip()]
    return GuideOutput(title=guide_title, steps=steps, player_level=player_level, tips=None)


async def sc_search_lore(query: str, top_k: int = 5) -> SearchLoreOutput:
    """Lore/universe from Galactapedia + Comm-Links, returns `related_topics`"""
    text = await run_rag_pipeline(question=query, top_k=top_k)
    return SearchLoreOutput(results=_parse_lore_results(text))
