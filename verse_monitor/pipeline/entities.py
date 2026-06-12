"""Entity extraction for Star Citizen event text.

Extracts ships, patch versions, features, events, organizations, and systems
from unstructured text using pattern matching and known entity lists.
"""

import re
from dataclasses import dataclass, field


@dataclass
class ExtractedEntities:
    """Structured entities extracted from Star Citizen event text."""

    ships: list[str] = field(default_factory=list)
    patch_versions: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)


# --- Known entity lists (comprehensive but maintained as Python constants) ---

SHIP_NAMES: list[str] = sorted(
    set(
        [
            # Aegis
            "Vanguard",
            "Vanguard Warden",
            "Vanguard Harbinger",
            "Vanguard Sentinel",
            "Vanguard Hoplite",
            "Gladius",
            "Gladius Valiant",
            "Eclipse",
            "Hurricane",
            "Retaliator",
            "Retaliator Bomber",
            "Redeemer",
            "Hammerhead",
            "Ballista",
            "Ballista Dunestalker",
            "Ballista Snowblind",
            # Anvil
            "Hornet",
            "Hornet F7C",
            "Hornet F7C-M",
            "Hornet Tracker",
            "Hornet Ghost",
            "Hornet Super Hornet",
            "Gladiator",
            "F8C Lightning",
            "F8A Lightning",
            "C8X Pisces",
            "C8 Pisces",
            "A2 Hercules",
            "C2 Hercules",
            "M2 Hercules",
            "Atlas",
            "Cyclone",
            "Cyclone TR",
            "Cyclone RC",
            "Cyclone RN",
            "Cyclone AA",
            # Crusader
            "Mercury",
            "Mercury Star Runner",
            "Herald",
            "600i",
            "600i Explorer",
            "600i Touring",
            "890 Jump",
            "85X",
            "A1 Spirit",
            "C1 Spirit",
            "E1 Spirit",
            "Genesis Starliner",
            # Drake
            "Cutlass",
            "Cutlass Black",
            "Cutlass Red",
            "Cutlass Steel",
            "Caterpillar",
            "Caterpillar Pirate Edition",
            "Dragonfly",
            "Dragonfly Black",
            "Dragonfly Yellowjacket",
            "Buccaneer",
            "Vulture",
            "Kraken",
            "Kraken Privateer",
            "Corsair",
            # MISC
            "Starfarer",
            "Starfarer Gemini",
            "Hull A",
            "Hull B",
            "Hull C",
            "Hull D",
            "Hull E",
            "Freelancer",
            "Freelancer MAX",
            "Freelancer DUR",
            "Freelancer MIS",
            "Starlancer",
            "Starlancer MAX",
            "Starlancer TAC",
            "Starlancer BFS",
            # Origin
            "100i",
            "125a",
            "135c",
            "300i",
            "315p",
            "325a",
            "350r",
            "400i",
            "M50",
            "X1",
            "X1 Velocity",
            "X1 Force",
            # RSI
            "Constellation",
            "Constellation Andromeda",
            "Constellation Aquila",
            "Constellation Taurus",
            "Constellation Phoenix",
            "Constellation Phoenix Emerald",
            "Orion",
            "Zeus",
            "Zeus Mk II CL",
            "Zeus Mk II MR",
            "Zeus Mk II SRV",
            # Argo
            "MOLE",
            "MOLE Carbon",
            "MOLE Talus",
            "SRV",
            "Rampart",
            "RAFT",
            "G12a",
            "G12b",
            "G12r",
            # Manufacturers (kept for ship detection but lower priority)
            # Note: these overlap with ORGANIZATION_NAMES
            # Capital ships
            "Idris",
            "Idris P",
            "Idris M",
            "Javelin",
            "Reclaimer",
            "Reclaimer A1",
            "Pioneer",
            "Polaris",
            # Small craft
            "Nox",
            "Nox Kue",
            "Syulen",
            "Lynx",
            "Lynx II",
            # Special
            "Nova Tonk",
            "Cutter",
            "Cutter Rambler",
            "Cutter Scout",
            "Cutter Blue",
            "Prowler",
            "Prowler Eclipse",
        ]
    ),
    key=len,
    reverse=True,
)

FEATURE_NAMES: list[str] = sorted(
    set(
        [
            "server meshing",
            "persistent entity streaming",
            "icache",
            "vulkan",
            "gen12",
            "gen 12",
            "gen-12",
            "renderer",
            "optimization",
            "performance",
            "shader",
            "dx12",
            "directx 12",
            "quantum travel",
            "quantum drive",
            "quantum jump",
            "jump point",
            "jump points",
            "server occlusion",
            "object container streaming",
            "gen12 renderer",
            "vulkan renderer",
            "item port 2.0",
            "itemport 2.0",
            "actor status",
            "actor status system",
            "physics system",
            "ragdoll",
            "zero g",
            "atmospheric flight",
            "atmo flight",
            "ground vehicle",
            "ground vehicles",
            "ship to ship",
            "ship-to-ship",
            "refinery",
            "refineries",
            "salvage",
            "mining",
            "trading",
            "cargo system",
            "inventory system",
            "fps combat",
            "tractor beam",
            "tractor beams",
            "exploration",
            "bounty system",
            "bounty hunting",
            "mission system",
            "mission manager",
            "nvidia dlss",
            "dlss",
            "fsr",
            "fidelityfx",
            "ray tracing",
            "raytracing",
            "global illumination",
            "ambient occlusion",
            "volumetric clouds",
            "volumetric fog",
            "weather system",
            "weather",
            "ocean system",
            "water system",
            "procedural generation",
            "procedural",
            "ai system",
            "npc system",
            "npcs",
            "comms system",
            "communication",
            "power system",
            "power management",
            "shield system",
            "shields",
            "weapon system",
            "weapons",
            "missile system",
            "missiles",
            "countermeasures",
            "flares",
            "chaff",
            "fuel system",
            "fuel",
            "damage system",
            "damage model",
            "component system",
            "components",
            "ship upgrade",
            "ship upgrades",
            "building system",
            "base building",
            "farming",
            "farming system",
            "medical system",
            "medical",
            "repair system",
            "repair",
            "refueling",
            "refuel",
            "cargo",
            "trading system",
            "mining system",
            "salvage system",
            "bounty",
            "missions",
            "exploration system",
        ]
    ),
    key=len,
    reverse=True,
)

EVENT_NAMES: list[str] = sorted(
    set(
        [
            "interstellar aerospace expo",
            "citizencon",
            "citizen con",
            "invictus launch week",
            "invictus",
            "alien week",
            "free fly",
            "freefly",
            "anniversary",
            "ship sale",
            "concept sale",
            "squadron 42",
            "squadron42",
            "star citizen birthday",
            "lunar new year",
            "lunar new year event",
            "free fly event",
            "free fly friday",
            "alpha release",
            "beta release",
            "live release",
            "game launch",
            "1.0 release",
            "version 1.0",
            "gold master",
            "release candidate",
            "ptu wave",
            "ptu invite",
            "evocati",
            "evocati test",
            "community spotlight",
            "this week in star citizen",
            "twisc",
            "comm link",
            "comm-link",
            "spectrum dispatch",
            "spectrum",
            "galactapedia",
            "lore drop",
            "video patch",
            "patch video",
            "ship matrix",
            "ship matrix update",
            "roadmap update",
            "sneak peek",
            "sneak peek week",
            "flyable",
            "flyable sale",
            "war bond",
            "war bond edition",
            "champion edition",
            "veteran edition",
            "starter pack",
            "starter package",
            "pledge store",
            "pledge",
            "subscriber flair",
            "subscriber",
            "fleet week",
            "jump fest",
            "ship fest",
        ]
    ),
    key=len,
    reverse=True,
)

ORGANIZATION_NAMES: list[str] = sorted(
    set(
        [
            "cloud imperium games",
            "cig",
            "robert space industries",
            "rsi",
            "united empire of earth",
            "uee",
            "vanduul clans",
            "vanduul",
            "xi an empire",
            "xi-an empire",
            "banu protectorate",
            "banu",
            "tevarin",
            "messer regime",
            "messer",
            "old war",
            "aegis dynamics",
            "aegis",
            "anvil aerospace",
            "anvil",
            "crusader industries",
            "crusader",
            "drake interplanetary",
            "drake",
            "musashi industrial",
            "misc",
            "origin jumpworks",
            "origin",
            "argo astronautics",
            "argo",
            "hurston dynamics",
            "hurston",
            "microtech",
            "arccorp",
            "arc corp",
            "kastak arms",
            "kastak",
            "klescher",
            "the advocacy",
            "advocacy",
            "pirates",
            "xian",
        ]
    ),
    key=len,
    reverse=True,
)

SYSTEM_NAMES: list[str] = sorted(
    set(
        [
            "stanton system",
            "stanton",
            "pyro system",
            "pyro",
            "terra system",
            "terra",
            "microtech system",
            "microtech",
            "crusader system",
            "crusader",
            "hurston system",
            "hurston",
            "arccorp system",
            "arccorp",
            "nemo system",
            "nemo",
            "ellis system",
            "ellis",
            "kiel system",
            "kiel",
            "goss system",
            "goss",
            "calixc system",
            "calixc",
            "cathcart system",
            "cathcart",
            "croshaw system",
            "croshaw",
            "fora system",
            "fora",
            "hadrian system",
            "hadrian",
            "magda system",
            "magda",
            "mariana system",
            "mariana",
            "nyx system",
            "nyx",
            "odyssey system",
            "odyssey",
            "olympus system",
            "olympus",
            "rhetor system",
            "rhetor",
            "solaris system",
            "solaris",
            "terminus system",
            "terminus",
            "tyrol system",
            "tyrol",
            "virgil system",
            "virgil",
            "yela system",
            "yela",
            "daymar",
            "cellin",
            "aberday",
            "marca",
        ]
    ),
    key=len,
    reverse=True,
)

# --- Regex patterns ---

STRICT_PATCH_RE = re.compile(
    r"(?:alpha|patch|version|v)\s+(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

VERSION_NUMBER_RE = re.compile(
    r"\b(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\b",
)


def _match_entities(text: str, entity_list: list[str]) -> list[str]:
    """Match entities from a known list against text (case-insensitive, longest-first)."""
    text_lower = text.lower()
    found = []
    for entity in entity_list:
        if entity.lower() in text_lower:
            found.append(entity)
    return found


def _extract_patch_versions(text: str) -> list[str]:
    """Extract patch version strings from text."""
    versions = []
    # First try strict patterns (Alpha X.Y, Patch X.Y, etc.)
    for match in STRICT_PATCH_RE.finditer(text):
        ver = match.group(1)
        if ver not in versions:
            versions.append(ver)
    # If no strict matches, try loose version numbers
    if not versions:
        for match in VERSION_NUMBER_RE.finditer(text):
            ver = match.group(1)
            parts = ver.split(".")
            if len(parts) >= 2 and all(p.isdigit() for p in parts):
                if ver not in versions:
                    versions.append(ver)
    return versions


def extract_entities(text: str) -> ExtractedEntities:
    """Extract named entities from Star Citizen event text.

    Args:
        text: The event text to extract entities from.

    Returns:
        ExtractedEntities with all detected entities.
    """
    if not text:
        return ExtractedEntities()

    ships = _match_entities(text, SHIP_NAMES)
    patch_versions = _extract_patch_versions(text)
    features = _match_entities(text, FEATURE_NAMES)
    events = _match_entities(text, EVENT_NAMES)
    organizations = _match_entities(text, ORGANIZATION_NAMES)
    systems = _match_entities(text, SYSTEM_NAMES)

    return ExtractedEntities(
        ships=ships,
        patch_versions=patch_versions,
        features=features,
        events=events,
        organizations=organizations,
        systems=systems,
    )
