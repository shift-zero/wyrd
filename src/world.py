# wyrd — Core types for procedural world generation

import random
from dataclasses import dataclass, field
from typing import Optional

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

    @property
    def tiles(self) -> int:
        return self.width * self.height
