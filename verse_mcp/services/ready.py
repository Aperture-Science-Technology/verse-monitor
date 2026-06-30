"""Readiness flag global pour Verse MCP.

Le lifespan ne yield que quand Redis ET Qdrant sont ping-success.
Les wrappers tools dans server.py utilisent is_ready() pour renvoyer
une erreur explicite si appelé avant readiness (bug #2).
"""

import asyncio

_ready_event = asyncio.Event()


async def wait_ready(timeout: float = 5.0) -> bool:
    """Attendre que le serveur soit prêt (timeout en secondes)."""
    try:
        await asyncio.wait_for(_ready_event.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False


def set_ready() -> None:
    _ready_event.set()


def set_unready() -> None:
    _ready_event.clear()


def is_ready() -> bool:
    return _ready_event.is_set()
