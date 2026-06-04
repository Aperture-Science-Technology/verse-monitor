"""LLM service (Anthropic)."""

import os
import anthropic
from anthropic import AsyncAnthropic

_anthropic_client: AsyncAnthropic | None = None


def init_anthropic() -> None:
    global _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    _anthropic_client = AsyncAnthropic(api_key=api_key)


async def call_claude(prompt: str) -> str:
    """Call Claude API and return the completion."""
    global _anthropic_client
    if not _anthropic_client:
        raise RuntimeError("Anthropic not initialized")
    
    # Using the Claude model specified in the prompt: claude-sonnet-4-6
    # Note: The exact model string might be "claude-sonnet-4-6" or similar.
    # We'll use the model from the environment or default.
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    
    response = await _anthropic_client.messages.create(
        model=model,
        max_tokens=8000,
        temperature=0.7,
        system="You are a helpful Star Citizen expert.",
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    # Assuming the response is a list of content blocks, we take the first text block.
    if response.content:
        return response.content[0].text
    return ""