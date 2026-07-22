# wyrd — Core types for procedural world generation

import random
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .lore import Lore
    from .narrative import Narrative
    from .chronicles import Chronicles
    from .magic import MagicSystem
    from .religion import PantheonSystem

# ── Adventure Zone Types ─────────────────────────────────────────────

ADVENTURE_ZONE_TYPES = {
    "dungeon": {
        "char": "D",
        "color": 160,
        "desc": "Dungeon — underground complex",
        "preferred_terrain": ["hills", "mountains"],
    },
    "cave": {
        "char": "C",
        "color": 250,
        "desc": "Cave — natural cavern system",
        "preferred_terrain": ["hills", "mountains"],
    },
    "ruin": {
        "char": "R",
        "color": 124,
        "desc": "Ruins — abandoned structures",
        "preferred_terrain": ["grass", "forest", "hills"],
    },
    "tower": {
        "char": "T",
        "color": 179,
        "desc": "Tower — isolated arcane or watch tower",
        "preferred_terrain": ["hills", "grass"],
    },
    "grove": {
        "char": "G",
        "color": 34,
        "desc": "Grove — sacred natural area",
        "preferred_terrain": ["forest"],
    },
    "lair": {
        "char": "L",
        "color": 196,
        "desc": "Lair — monster den or creature nesting ground",
        "preferred_terrain": ["hills", "mountains", "forest"],
    },
    "shrine": {
        "char": "S",
        "color": 99,
        "desc": "Shrine — small religious or mystical site",
        "preferred_terrain": ["grass", "hills", "forest"],
    },
    "mine": {
        "char": "M",
        "color": 172,
        "desc": "Mine — old excavation or mineral works",
        "preferred_terrain": ["hills", "mountains"],
    },
}

ADVENTURE_DIFFICULTIES = ["trivial", "easy", "moderate", "hard", "deadly"]

# ── Terrain Types ──────────────────────────────────────────────────

TERRAIN = {
    "deep_water":  {"char": "~", "color": 27,  "height": -2,  "desc": "Deep ocean"},
    "shallow":     {"char": "~", "color": 33,  "height": -1,  "desc": "Shallow water"},
    "sand":        {"char": ".", "color": 223, "height": 0,   "desc": "Beach / sand"},
    "grass":       {"char": ",", "color": 28,  "height": 1,   "desc": "Grassland"},
    "forest":      {"char": "*", "color": 22,  "height": 2,   "desc": "Forest"},
    "hills":       {"char": "^", "color": 94,  "height": 3,   "desc": "Hills"},
    "mountains":   {"char": "▲", "color": 130, "height": 4,   "desc": "Mountains"},
    "snow":        {"char": "◌", "color": 255, "height": 5,   "desc": "Snowy peaks"},
    "river":       {"char": "≈", "color": 45,  "height": 0,   "desc": "River"},
}

# ── Biomes ─────────────────────────────────────────────────────────

BIOMES = {
    "temperate":  {"color": 28,  "desc": "Temperate forests and fields"},
    "arid":       {"color": 172, "desc": "Dry grasslands and desert scrub"},
    "tundra":     {"color": 250, "desc": "Cold, sparse landscape"},
    "tropical":   {"color": 35,  "desc": "Lush, dense vegetation"},
}

# ── World Structure ────────────────────────────────────────────────

@dataclass
class AdventureZone:
    """A point of interest — dungeon, lair, grove, etc. for player exploration."""
    name: str
    zone_type: str  # one of ADVENTURE_ZONE_TYPES keys
    x: int
    y: int
    region: str
    difficulty: str = "moderate"
    inhabitants: str = ""
    description: str = ""
    treasure_tier: int = 1  # 1-5
    is_cleared: bool = False
    quest_hook: str = ""

    @property
    def char(self) -> str:
        return ADVENTURE_ZONE_TYPES.get(self.zone_type, {}).get("char", "?")

    @property
    def color(self) -> int:
        return ADVENTURE_ZONE_TYPES.get(self.zone_type, {}).get("color", 250)

@dataclass
class Settlement:
    name: str
    x: int
    y: int
    population: int
    kind: str  # hamlet, village, town, city

    @property
    def char(self) -> str:
        return {1: "·", 2: "∘", 3: "●", 4: "◉"}.get(min(self.population // 500 + 1, 4), "◉")

@dataclass
class Region:
    """A named geographic region within a world."""
    name: str
    biome: str
    settlements: list[Settlement] = field(default_factory=list)

@dataclass
class World:
    """A complete generated world."""
    seed: int
    width: int
    height: int
    elevation: list[list[float]] = field(default_factory=list)
    moisture: list[list[float]] = field(default_factory=list)
    terrain: list[list[str]] = field(default_factory=list)
    rivers: list[tuple[int, int]] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    adventure_zones: list[AdventureZone] = field(default_factory=list)
    lore: Optional['Lore'] = None
    narrative: Optional['Narrative'] = None
    chronicles: Optional['Chronicles'] = None
    magic: Optional['MagicSystem'] = None
    pantheon: Optional['PantheonSystem'] = None

    @property
    def tiles(self) -> int:
        return self.width * self.height
