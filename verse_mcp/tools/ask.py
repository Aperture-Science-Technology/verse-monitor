"""Tool: sc_ask - General question answering pipeline."""

import re

from verse_mcp.services.rag import run_rag_pipeline
from verse_mcp.models.outputs import RagResult, RagSource


def _parse_sources(text: str) -> list[RagSource]:
    return [
        RagSource(label=m.group(1).strip(), url=m.group(2).strip())
        for m in re.finditer(r"\[Source: ([^|]+) \| ([^\]]+)\]", text)
    ]


def _parse_patch_version(text: str) -> str | None:
    m = re.search(r"\[Patch: ([^\]]+)\]", text)
    return m.group(1).strip() if m else None


async def sc_ask(
    question: str,
    category: str | None = None,
    system_prompt: str = "",
    top_k: int = 5,
) -> RagResult:
    """General question — returns relevant Star Citizen knowledge chunks with sources."""
    text = await run_rag_pipeline(question=question, category=category, top_k=top_k)
    return RagResult(
        answer=text,
        sources=_parse_sources(text),
        patch_version=_parse_patch_version(text),
    )
