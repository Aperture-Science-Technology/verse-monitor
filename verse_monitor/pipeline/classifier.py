"""Classifier déterministe (zéro LLM) pour les événements RSI.

Tables de règles :
- Priorité de base par EventType
- Keywords qui font monter d'un cran
- Catégories par keywords
"""

from verse_monitor.models import EventType, Priority

# Priorité de base par EventType
BASE_PRIORITY: dict[EventType, Priority] = {
    EventType.PATCH_NOTES_LIVE: Priority.CRITICAL,
    EventType.ROADMAP_CARD_REMOVED: Priority.HIGH,
    EventType.ROADMAP_CARD_DELAYED: Priority.HIGH,
    EventType.ROADMAP_CARD_RELEASED: Priority.HIGH,
    EventType.ROADMAP_CARD_ADDED: Priority.MEDIUM,
    EventType.DEVTRACKER_POST: Priority.MEDIUM,
    EventType.COMM_LINK_PUBLISHED: Priority.MEDIUM,
    EventType.MONTHLY_REPORT: Priority.MEDIUM,
    EventType.TWISC_PUBLISHED: Priority.LOW,
    EventType.ROADMAP_CARD_UPDATED: Priority.LOW,
}

# Keywords qui font monter d'un cran (LOW → MEDIUM → HIGH → CRITICAL)
ESCALATION_KEYWORDS = [
    "delay", "delayed", "pushed", "cancelled", "wipe", "full wipe",
    "citizencon", "1.0", "new ship", "concept sale", "flyable",
    "server meshing", "hotfix", "emergency patch",
]

# Catégories par keywords
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ship": [
        "ship", "vessel", "fighter", "anvil", "aegis", "origin", "crusader",
        "drake", "misc", "constellation", "carrack", "cutter", "freelancer",
        "starfarer", "hull", "mercury", "taurus", "andromeda", "aquila",
        "hercules", "valkyrie", "vanguard", "reclaimer", "retaliator",
        "eclipse", "hurricane", "gladius", "arrow", "stalker",
    ],
    "gameplay": [
        "mission", "combat", "mining", "trading", "cargo", "bounty",
        "salvage", "fps", "inventory", "refinery", "tractor beam",
        "quantum", "jump", "exploration",
    ],
    "tech": [
        "server meshing", "persistent entity streaming", "icache",
        "vulkan", "gen12", "renderer", "optimization", "performance",
        "shader", "dx12",
    ],
    "event": [
        "event", "free fly", "iae", "annivers", "citizencon", "invictus",
        "alien week", "interstellar aerospace expo", "ship sale", "concept sale",
    ],
    "lore": [
        "lore", "galactapedia", "uee", "vanduul", "xi'an", "banu",
        "tevarin", "arthur", "messer", "old war", "crusader industries",
    ],
}

_PRIORITY_ORDER = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]


def classify_priority(event_type: EventType, text: str) -> Priority:
    """Classifie la priorité d'un événement selon son type et son texte."""
    base = BASE_PRIORITY.get(event_type, Priority.LOW)
    text_lower = text.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in text_lower:
            idx = _PRIORITY_ORDER.index(base)
            if idx < len(_PRIORITY_ORDER) - 1:
                return _PRIORITY_ORDER[idx + 1]
    return base


def classify_category(text: str) -> str | None:
    """Classifie la catégorie d'un événement selon son texte."""
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def extract_keywords(text: str) -> list[str]:
    """Extrait les keywords d'escalation présents dans le texte."""
    text_lower = text.lower()
    return [kw for kw in ESCALATION_KEYWORDS if kw in text_lower]
