"""
wyrd — Procedural map generator.

Seed-deterministic terrain generation using a simple value noise
implementation (no external dependencies for Phase 1).
"""

import random
import math
from .world import World, TERRAIN, BIOMES, Region, Settlement
from .lore import generate_lore, Lore
from .narrative import generate_narrative, Narrative
from .chronicles import generate_chronicles, Chronicles

# ── Seeded 2D Value Noise ──────────────────────────────────────────

def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)

def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)

def _hash_coord(x: int, y: int, seed: int) -> float:
    """Deterministic hash of integer coordinates into [0, 1)."""
    h = seed & 0x7FFFFFFF
    h = (h ^ (x * 374761393 + y * 668265263)) * 0x27D4EB2D
    h = (h ^ (h >> 15)) * 0x27D4EB2D
    h = h ^ (h >> 15)
    return (h & 0x7FFFFFFF) / 0x7FFFFFFF


class Noise:
    """2D value noise — seed-deterministic, no deps, works everywhere."""

    def __init__(self, seed: int):
        self._seed = seed
        # Build permutation table for coherent hashing
        rng = random.Random(seed)
        self._perm = list(range(512))
        rng.shuffle(self._perm)
        # Double for wrap-free lookups
        self._perm = self._perm + self._perm

    def _hash(self, x: int, y: int) -> float:
        idx = self._perm[(x & 255) + self._perm[y & 255]]
        # Use the index to seed a deterministic float
        h = (idx * 374761393) ^ (x * 668265263 + y * 1274126177)
        h = (h ^ (h >> 13)) * 0x27D4EB2D
        h = (h ^ (h >> 15)) * 0x27D4EB2D
        h = h ^ (h >> 15)
        return (h & 0x7FFFFFFF) / 0x7FFFFFFF

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


def _generate_rivers(world: 'World', noise: Noise, rng: random.Random) -> list[tuple[int, int]]:
    """Generate rivers by flowing from high elevation to the coast."""
    rivers: list[tuple[int, int]] = []
    width, height = world.width, world.height
    elevation = world.elevation
    visited = set()

    # Find starting points: cells in hills or mountains
    candidates = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            e = elevation[y][x]
            if 0.55 < e < 0.9:  # hills to high mountains, not snowy peaks
                # Check if it's a local high point (at least 2 of 4 cardinal neighbors lower)
                lower_count = 0
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    if elevation[y + dy][x + dx] < e - 0.005:
                        lower_count += 1
                if lower_count >= 2:
                    candidates.append((e, x, y))

    # Sort by elevation (highest first), take top candidates
    candidates.sort(reverse=True)
    max_rivers = max(3, width * height // 300)
    started = 0

    # Skip candidates that are too close to existing river starts
    min_start_dist = 5
    used_starts: list[tuple[int, int]] = []

    for _, sx, sy in candidates:
        if started >= max_rivers:
            break

        # Skip if too close to another river start
        if any(abs(sx - ux) + abs(sy - uy) < min_start_dist for ux, uy in used_starts):
            continue

        # Trace the river downhill
        cx, cy = sx, sy
        path = [(cx, cy)]
        dead_end = False
        steps = 0

        while not dead_end and steps < max(width, height) * 2:
            steps += 1
            best_e = elevation[cy][cx]
            best_x, best_y = cx, cy

            # Check all 8 neighbors — prefer steepest descent
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or nx >= width or ny < 0 or ny >= height:
                        continue
                    ne = elevation[ny][nx]
                    if ne < best_e:
                        best_e = ne
                        best_x, best_y = nx, ny

            # If no downhill neighbor, we're done
            if best_x == cx and best_y == cy:
                dead_end = True
            else:
                cx, cy = best_x, best_y
                path.append((cx, cy))
                # Stop when we reach deep water (ocean)
                if elevation[cy][cx] < 0.30:
                    break
                # If we hit an existing river cell, merge and stop
                if (cx, cy) in visited and len(path) >= 3:
                    break

        # Check if river is long enough and doesn't overlap too much
        if len(path) >= 4:
            overlap = sum(1 for p in path if p in visited)
            if overlap < len(path) * 0.6:  # allow up to 60% overlap
                for p in path:
                    visited.add(p)
                    rivers.append(p)
                used_starts.append((sx, sy))
                started += 1

    return rivers


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

    # ── 2. Generate rivers (before moisture, so rivers can affect it) ──
    world.rivers = _generate_rivers(world, noise, rng)

    # ── 3. Generate moisture map ───────────────────────────────────
    world.moisture = []
    river_set = set(world.rivers)
    for y in range(height):
        row = []
        for x in range(width):
            nx, ny = x / width, y / height
            # Rivers increase local moisture
            river_bonus = 0.0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    rx, ry = x + dx, y + dy
                    if (rx, ry) in river_set:
                        dist = abs(dx) + abs(dy)
                        river_bonus += 0.12 * max(0, 1 - dist / 3)
            m = noise.octave(nx * 4 + 100, ny * 4 + 100, octaves=3, persistence=0.5)
            row.append(min(1.0, m + river_bonus))
        world.moisture.append(row)

    # ── 4. Classify terrain ────────────────────────────────────────
    world.terrain = []
    for y in range(height):
        row = []
        for x in range(width):
            # Rivers take priority
            if (x, y) in river_set:
                row.append("river")
                continue
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
    # Shuffle the name pool once per world so we can pop unique names
    name_pool = list(SETTLEMENT_NAMES)
    rng.shuffle(name_pool)  # deterministic because rng is seeded with world seed

    world.regions = []
    num_regions = rng.randint(3, 6)

    for r in range(num_regions):
        region_seed = seed + r * 1000
        reg_rng = random.Random(region_seed)

        # Pick a biome for this region
        biome = reg_rng.choice(list(BIOMES.keys()))

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
            river_set_local = river_set
            while ((world.terrain[sy][sx] in ("deep_water", "shallow", "river")
                    or (sx, sy) in river_set_local)
                   and tries < 10):
                sx = reg_rng.randint(2, width - 3)
                sy = reg_rng.randint(2, height - 3)
                tries += 1

            # Pop a unique name from the shuffled pool
            if not name_pool:
                name_pool = list(SETTLEMENT_NAMES)
                rng.shuffle(name_pool)
            name = name_pool.pop()

            pop = reg_rng.randint(50, 3000)
            kind = ("hamlet" if pop < 200 else "village" if pop < 800
                    else "town" if pop < 2000 else "city")
            region.settlements.append(
                Settlement(name=name, x=sx, y=sy, population=pop, kind=kind)
            )

        world.regions.append(region)

    # ── 5. Generate lore ──────────────────────────────────────────
    world.lore = generate_lore(world)

    # ── 6. Generate narrative ─────────────────────────────────────
    world.narrative = generate_narrative(world)

    # ── 7. Generate chronicles ────────────────────────────────────
    world.chronicles = generate_chronicles(world, world.narrative)

    return world
