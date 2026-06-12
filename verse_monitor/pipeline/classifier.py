"""Classifier dterministe (zero LLM) pour les vnements RSI.

Tables de rgles :
- Priorit de base par EventType
- Keywords qui font monter d'un cran
- Catgories par keywords
- Extraction d'entits pour enrichissement
"""

from verse_monitor.models import EventType, Priority
from verse_monitor.pipeline.entities import extract_entities

# Priorit de base par EventType
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

# Keywords qui font monter d'un cran (LOW  MEDIUM  HIGH  CRITICAL)
ESCALATION_KEYWORDS = [
    "delay", "delayed", "pushed", "cancelled", "wipe", "full wipe",
    "citizencon", "1.0", "new ship", "concept sale", "flyable",
    "server meshing", "hotfix", "emergency patch",
]

# Catgories par keywords (fallback)
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


def _escalate_priority(current: Priority, levels: int = 1) -> Priority:
    """Escalate priority by given number of levels, capped at CRITICAL."""
    idx = _PRIORITY_ORDER.index(current)
    new_idx = min(idx + levels, len(_PRIORITY_ORDER) - 1)
    return _PRIORITY_ORDER[new_idx]


def classify_priority(event_type: EventType, text: str) -> Priority:
    """Classify event priority using keyword rules and entity extraction.

    Rules (applied in order, later rules can only raise priority):
    1. Base priority from EventType
    2. Keyword escalation (legacy ESCALATION_KEYWORDS)
    3. Entity-based escalation:
       - "server meshing" or "persistent entity streaming" -> minimum HIGH
       - Patch version present -> minimum MEDIUM
       - Ship name + "concept sale" or "flyable" -> minimum HIGH
       - "1.0" in text -> CRITICAL
    """
    base = BASE_PRIORITY.get(event_type, Priority.LOW)
    text_lower = text.lower()

    # Step 1: Legacy keyword escalation (single level)
    priority = base
    for kw in ESCALATION_KEYWORDS:
        if kw in text_lower:
            priority = _escalate_priority(priority, 1)

    # Step 2: Entity-based escalation
    entities = extract_entities(text)

    # "1.0" -> CRITICAL
    if "1.0" in text_lower:
        return Priority.CRITICAL

    # "server meshing" or "persistent entity streaming" -> minimum HIGH
    critical_features = {"server meshing", "persistent entity streaming"}
    if any(f in entities.features for f in critical_features):
        if _PRIORITY_ORDER.index(priority) < _PRIORITY_ORDER.index(Priority.HIGH):
            priority = Priority.HIGH

    # Patch version present -> minimum MEDIUM
    if entities.patch_versions:
        if _PRIORITY_ORDER.index(priority) < _PRIORITY_ORDER.index(Priority.MEDIUM):
            priority = Priority.MEDIUM

    # Ship name + "concept sale" or "flyable" -> minimum HIGH
    if entities.ships and ("concept sale" in text_lower or "flyable" in text_lower):
        if _PRIORITY_ORDER.index(priority) < _PRIORITY_ORDER.index(Priority.HIGH):
            priority = Priority.HIGH

    return priority


def classify_category(text: str) -> str | None:
    """Classify event category using entity extraction and keyword fallback.

    Entity-based rules (higher priority):
    - Ships detected -> "ship"
    - Features detected -> "tech"
    - Events detected -> "event"
    - Organizations/systems detected -> "lore"

    Keyword fallback preserves legacy behavior.
    """
    entities = extract_entities(text)

    # Entity-based classification (priority order matters)
    if entities.ships:
        return "ship"
    if entities.features:
        return "tech"
    if entities.events:
        return "event"
    if entities.organizations or entities.systems:
        return "lore"

    # Keyword fallback
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def extract_keywords(text: str) -> list[str]:
    """Extract escalation keywords and entity-derived keywords from text.

    Returns legacy ESCALATION_KEYWORDS found in text, plus:
    - Detected ship names
    - Detected feature names
    - Detected event names
    - Detected organization names
    - Detected system names
    - Detected patch versions
    """
    text_lower = text.lower()
    keywords = [kw for kw in ESCALATION_KEYWORDS if kw in text_lower]

    entities = extract_entities(text)
    keywords.extend(entities.ships)
    keywords.extend(entities.features)
    keywords.extend(entities.events)
    keywords.extend(entities.organizations)
    keywords.extend(entities.systems)
    keywords.extend(entities.patch_versions)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for kw in keywords:
        lower = kw.lower()
        if lower not in seen:
            seen.add(lower)
            deduped.append(kw)

    return deduped
