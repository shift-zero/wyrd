"""
wyrd — Procedural map generator.

Seed-deterministic terrain generation using a simple value noise
implementation (no external dependencies for Phase 1).
"""

import random
import math
from .world import World, TERRAIN, Region, Settlement

# ── Simple Value Noise ─────────────────────────────────────────────

def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)

def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)

class Noise:
    """Simple 2D value noise — seed-deterministic, no deps."""

    def __init__(self, seed: int):
        rng = random.Random(seed)
        self._grid = {}
        for i in range(1024):
            self._grid[(rng.randint(0, 4095), rng.randint(0, 4095))] = rng.random()

    def _hash(self, x: int, y: int) -> float:
        key = (x & 4095, y & 4095)
        return self._grid.get(key, 0.5)

    def sample(self, x: float, y: float) -> float:
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        x1, y1 = x0 + 1, y0 + 1
        fx, fy = _fade(x - x0), _fade(y - y0)

        n00 = self._hash(x0, y0)
        n10 = self._hash(x1, y0)
        n01 = self._hash(x0, y1)
        n11 = self._hash(x1, y1)

        nx0 = _lerp(n00, n10, fx)
        nx1 = _lerp(n01, n11, fx)
        return _lerp(nx0, nx1, fy)

    def octave(self, x: float, y: float, octaves: int = 3, persistence: float = 0.5) -> float:
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_val = 0.0
        for _ in range(octaves):
            value += amplitude * self.sample(x * frequency, y * frequency)
            max_val += amplitude
            amplitude *= persistence
            frequency *= 2.0
        return value / max_val


# ── Name Generation ────────────────────────────────────────────────

PREFIXES = ["Ash", "Black", "Briar", "Broken", "Cold", "Crystal", "Dark",
            "Deep", "Dragon", "Dusk", "Eagle", "Elder", "Ember", "Fair",
            "Fallen", "Fern", "Fire", "Frost", "Golden", "Gray", "Green",
            "Hollow", "Iron", "Kind", "Lake", "Lunar", "Mist", "Moon",
            "Moss", "Mountain", "Murk", "Oak", "Pale", "Raven", "Red",
            "Rift", "River", "Rust", "Sage", "Shadow", "Silver", "Sky",
            "Stone", "Storm", "Sun", "Thorn", "Thunder", "Vale", "White",
            "Wild", "Wind", "Winter", "Wolf", "Wood", "Wyrm"]

SUFFIXES = ["brook", "cliff", "combe", "dale", "dell", "downs", "edge",
            "fall", "fell", "ford", "gate", "glen", "grove", "haven",
            "holt", "keep", "knoll", "land", "march", "marsh", "moor",
            "pass", "reach", "ridge", "rift", "run", "shade", "shield",
            "shire", "spire", "stead", "stone", "vale", "wall", "watch",
            "wood", "wold"]

SETTLEMENT_NAMES = [
    "Aldwych", "Bracken", "Briarwood", "Coldwater", "Crowsrest",
    "Dunmoor", "Eagleford", "Embervale", "Fairhaven", "Fernwood",
    "Frosthold", "Goldcrest", "Grayrock", "Greendale", "Hollowbrook",
    "Ironforge", "Lakeview", "Millbrook", "Misthollow", "Moonvale",
    "Oakenshire", "Pinehold", "Redstone", "Riverbend", "Shadowmere",
    "Silverdale", "Southgate", "Starbrook", "Stonewall", "Thornwick",
    "Westmarch", "Whitestone", "Wilderwood", "Windmere", "Wolfden",
    "Wyrmrest", "Yorkshire", "Zephyr"
]


def generate_world(seed: int, width: int = 80, height: int = 40) -> World:
    """Generate a complete world from a seed."""
    world = World(seed=seed, width=width, height=height)
    noise = Noise(seed)
    rng = random.Random(seed)

    # ── 1. Generate elevation map ──────────────────────────────────
    world.elevation = []
    for y in range(height):
        row = []
        for x in range(width):
            nx, ny = x / width, y / height
            e = noise.octave(nx * 6, ny * 6, octaves=4, persistence=0.6)
            row.append(e)
        world.elevation.append(row)

    # ── 2. Generate moisture map ───────────────────────────────────
    world.moisture = []
    for y in range(height):
        row = []
        for x in range(width):
            nx, ny = x / width, y / height
            m = noise.octave(nx * 4 + 100, ny * 4 + 100, octaves=3, persistence=0.5)
            row.append(m)
        world.moisture.append(row)

    # ── 3. Classify terrain ────────────────────────────────────────
    world.terrain = []
    for y in range(height):
        row = []
        for x in range(width):
            e = world.elevation[y][x]
            m = world.moisture[y][x]

            if e < 0.3:
                t = "deep_water"
            elif e < 0.38:
                t = "shallow"
            elif e < 0.42:
                t = "sand"
            elif e < 0.55:
                t = "grass"
            elif e < 0.68:
                t = "forest" if m > 0.4 else "grass"
            elif e < 0.82:
                t = "hills" if m < 0.6 else "forest"
            elif e < 0.93:
                t = "mountains"
            else:
                t = "snow"
            row.append(t)
        world.terrain.append(row)

    # ── 4. Place settlements ───────────────────────────────────────
    world.regions = []
    num_regions = rng.randint(3, 6)

    for r in range(num_regions):
        region_seed = seed + r * 1000
        reg_rng = random.Random(region_seed)

        # Pick a biome for this region
        biome = reg_rng.choice(list(TERRAIN.keys()))

        # Name the region
        prefix = reg_rng.choice(PREFIXES)
        suffix = reg_rng.choice(SUFFIXES)
        region_name = f"{prefix}{suffix}"

        region = Region(name=region_name, biome=biome)

        # Place 1-4 settlements in this region
        num_settlements = reg_rng.randint(1, 4)
        for _ in range(num_settlements):
            sx = reg_rng.randint(2, width - 3)
            sy = reg_rng.randint(2, height - 3)
            # Ensure settlement is on land
            tries = 0
            while (world.terrain[sy][sx] in ("deep_water", "shallow")
                   and tries < 10):
                sx = reg_rng.randint(2, width - 3)
                sy = reg_rng.randint(2, height - 3)
                tries += 1

            name = reg_rng.choice(SETTLEMENT_NAMES)
            pop = reg_rng.randint(50, 3000)
            kind = ("hamlet" if pop < 200 else "village" if pop < 800
                    else "town" if pop < 2000 else "city")
            region.settlements.append(
                Settlement(name=name, x=sx, y=sy, population=pop, kind=kind)
            )

        world.regions.append(region)

    return world
