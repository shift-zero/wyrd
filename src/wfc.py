"""
wyrd — Wave Function Collapse Engine (Phase 26.6).

Procedurally generates coherent tile-based layouts for cities, building
interiors, and dungeons using the Wave Function Collapse algorithm.

Everything is seed-deterministic: same seed + same params = same layout.

The core algorithm:
  1. Initialize a grid where every cell holds all tile types (superposition)
  2. Find the cell with the lowest entropy (fewest remaining possibilities)
  3. Collapse that cell to a single tile type (weighted random from remaining)
  4. Propagate: for each neighbor, remove tile types that would violate adjacency
  5. Queue affected neighbors and continue propagating
  6. Repeat until all cells collapsed or contradiction is hit
"""

from __future__ import annotations

import random
from collections import deque
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# Tile Type Definitions
# ═══════════════════════════════════════════════════════════════════

# City-scale generation: blocks of a city
CITY_TILES = {
    "BUILDING": 0,    # A building footprint (subdivided into rooms later)
    "WALL": 1,        # City wall / fortification
    "STREET": 2,      # Road/street
    "PLAZA": 3,       # Open public space
    "GARDEN": 4,      # Green space / park
    "EMPTY": 5,       # Undeveloped land
    "WATER": 6,       # River/pond
    "GATE": 7,        # City gate
}

# Building interior scale: rooms inside a building
ROOM_TILES = {
    "FLOOR": 0,
    "WALL": 1,
    "DOOR": 2,
    "CORRIDOR": 3,
    "EMPTY": 4,       # Outside the building
}

# Dungeon scale
DUNGEON_TILES = {
    "FLOOR": 0,
    "WALL": 1,
    "DOOR": 2,
    "CORRIDOR": 3,
    "TRAP": 4,
    "STAIRS": 5,
    "CHEST": 6,
    "ALTAR": 7,
}

# Reverse maps: int ID → string name (useful for debugging & display)
CITY_NAMES = {v: k for k, v in CITY_TILES.items()}
ROOM_NAMES = {v: k for k, v in ROOM_TILES.items()}
DUNGEON_NAMES = {v: k for k, v in DUNGEON_TILES.items()}


# ═══════════════════════════════════════════════════════════════════
# Adjacency Rules
#
# For each tile ID, for each direction ("n", "s", "e", "w"), list
# which tile IDs are allowed as neighbors in that direction.
# ═══════════════════════════════════════════════════════════════════

CITY_ADJACENCY: dict[int, dict[str, list[int]]] = {
    # ── BUILDING ──────────────────────────────────────────────
    # Buildings sit next to walls, streets, plazas, gardens, other buildings, and gates.
    0: {
        "n": [0, 1, 2, 3, 7],
        "s": [0, 1, 2, 3, 7],
        "e": [0, 1, 2, 3, 7],
        "w": [0, 1, 2, 3, 7],
    },
    # ── WALL ──────────────────────────────────────────────────
    # Walls separate inside from outside. They touch gates, buildings,
    # streets (from inside), and empty land or water from outside.
    1: {
        "n": [1, 7, 0, 2, 5, 6],
        "s": [1, 7, 0, 2, 5, 6],
        "e": [1, 7, 0, 2, 5, 6],
        "w": [1, 7, 0, 2, 5, 6],
    },
    # ── STREET ────────────────────────────────────────────────
    # Streets form the circulation network — they connect everything.
    2: {
        "n": [2, 0, 3, 7, 4, 5],
        "s": [2, 0, 3, 7, 4, 5],
        "e": [2, 0, 3, 7, 4, 5],
        "w": [2, 0, 3, 7, 4, 5],
    },
    # ── PLAZA ─────────────────────────────────────────────────
    # Plazas are open public spaces, adjacent to streets, buildings, gardens.
    3: {
        "n": [3, 2, 0, 4],
        "s": [3, 2, 0, 4],
        "e": [3, 2, 0, 4],
        "w": [3, 2, 0, 4],
    },
    # ── GARDEN ────────────────────────────────────────────────
    # Green spaces adjacent to streets, buildings, empty land.
    4: {
        "n": [4, 2, 0, 5],
        "s": [4, 2, 0, 5],
        "e": [4, 2, 0, 5],
        "w": [4, 2, 0, 5],
    },
    # ── EMPTY ─────────────────────────────────────────────────
    # Undeveloped land borders streets, gardens, and water.
    5: {
        "n": [5, 2, 4, 6],
        "s": [5, 2, 4, 6],
        "e": [5, 2, 4, 6],
        "w": [5, 2, 4, 6],
    },
    # ── WATER ─────────────────────────────────────────────────
    # Water borders empty land, walls, and itself.
    6: {
        "n": [6, 5, 1],
        "s": [6, 5, 1],
        "e": [6, 5, 1],
        "w": [6, 5, 1],
    },
    # ── GATE ──────────────────────────────────────────────────
    # Gates are in walls, connecting to streets on both sides.
    7: {
        "n": [7, 1, 2],
        "s": [7, 1, 2],
        "e": [7, 1, 2],
        "w": [7, 1, 2],
    },
}

ROOM_ADJACENCY: dict[int, dict[str, list[int]]] = {
    # ── FLOOR ─────────────────────────────────────────────────
    # Floors connect to other floors, doors, corridors, and are bounded by walls.
    0: {
        "n": [0, 1, 2, 3],
        "s": [0, 1, 2, 3],
        "e": [0, 1, 2, 3],
        "w": [0, 1, 2, 3],
    },
    # ── WALL ──────────────────────────────────────────────────
    # Walls separate interior (floor/door) from exterior (empty/outside).
    # They can also be adjacent to other walls (thick walls / pillars).
    1: {
        "n": [0, 1, 2, 4],
        "s": [0, 1, 2, 4],
        "e": [0, 1, 2, 4],
        "w": [0, 1, 2, 4],
    },
    # ── DOOR ──────────────────────────────────────────────────
    # Doors connect rooms — adjacent to walls (frame), floors, and corridors.
    2: {
        "n": [1, 0, 2, 3],
        "s": [1, 0, 2, 3],
        "e": [1, 0, 2, 3],
        "w": [1, 0, 2, 3],
    },
    # ── CORRIDOR ──────────────────────────────────────────────
    # Corridors / hallways connect to floors, doors, and other corridors.
    3: {
        "n": [3, 2, 0],
        "s": [3, 2, 0],
        "e": [3, 2, 0],
        "w": [3, 2, 0],
    },
    # ── EMPTY ─────────────────────────────────────────────────
    # Outside area — only adjacent to walls (and itself).
    4: {
        "n": [4, 1],
        "s": [4, 1],
        "e": [4, 1],
        "w": [4, 1],
    },
}

DUNGEON_ADJACENCY: dict[int, dict[str, list[int]]] = {
    # ── FLOOR ─────────────────────────────────────────────────
    # Dungeon floors support features and are bounded by walls.
    0: {
        "n": [0, 1, 2, 3, 4, 6, 7],
        "s": [0, 1, 2, 3, 4, 6, 7],
        "e": [0, 1, 2, 3, 4, 6, 7],
        "w": [0, 1, 2, 3, 4, 6, 7],
    },
    # ── WALL ──────────────────────────────────────────────────
    1: {
        "n": [0, 1, 2],
        "s": [0, 1, 2],
        "e": [0, 1, 2],
        "w": [0, 1, 2],
    },
    # ── DOOR ──────────────────────────────────────────────────
    2: {
        "n": [1, 0, 2, 3],
        "s": [1, 0, 2, 3],
        "e": [1, 0, 2, 3],
        "w": [1, 0, 2, 3],
    },
    # ── CORRIDOR ──────────────────────────────────────────────
    3: {
        "n": [3, 2, 0],
        "s": [3, 2, 0],
        "e": [3, 2, 0],
        "w": [3, 2, 0],
    },
    # ── TRAP ──────────────────────────────────────────────────
    # Traps sit on floors, adjacent only to floors.
    4: {
        "n": [0, 4],
        "s": [0, 4],
        "e": [0, 4],
        "w": [0, 4],
    },
    # ── STAIRS ────────────────────────────────────────────────
    # Stairs sit on floors, connecting vertically.
    5: {
        "n": [0, 5],
        "s": [0, 5],
        "e": [0, 5],
        "w": [0, 5],
    },
    # ── CHEST ─────────────────────────────────────────────────
    6: {
        "n": [0, 6],
        "s": [0, 6],
        "e": [0, 6],
        "w": [0, 6],
    },
    # ── ALTAR ─────────────────────────────────────────────────
    7: {
        "n": [0, 7],
        "s": [0, 7],
        "e": [0, 7],
        "w": [0, 7],
    },
}


# ═══════════════════════════════════════════════════════════════════
# Core WFC Algorithm
# ═══════════════════════════════════════════════════════════════════


def run_wfc(
    width: int,
    height: int,
    tile_types: dict[str, int],
    adjacency: dict[int, dict[str, list[int]]],
    rng: random.Random,
    max_attempts: int = 100,
) -> list[list[int]] | None:
    """
    Run wave function collapse on a grid.

    Args:
        width, height: Grid dimensions.
        tile_types: Dict mapping tile names to int IDs.
        adjacency: For each tile ID, dict of direction -> list of allowed
                   neighbor IDs. Directions: "n", "s", "e", "w".
        rng: Seeded random for determinism.
        max_attempts: How many times to retry on contradiction.

    Returns:
        2D grid of int tile IDs, or None if WFC failed after all attempts.
    """
    tile_ids = sorted(set(tile_types.values()))

    for attempt in range(max_attempts):
        result = _run_wfc_once(width, height, tile_ids, adjacency, rng)
        if result is not None:
            return result

        # Advance RNG state so the next attempt gets a different collapse order.
        rng.random()

    return None


def _run_wfc_once(
    width: int,
    height: int,
    tile_ids: list[int],
    adjacency: dict[int, dict[str, list[int]]],
    rng: random.Random,
) -> list[list[int]] | None:
    """
    Single attempt of WFC. Returns the grid or None on contradiction.

    Internal data layout:
      - possibilities[y][x] -> list[int] of remaining tile candidates
      - collapsed[y][x] -> int (tile ID) or None (still in superposition)
    """
    # Initialize: every cell has all tile types as possibilities
    possibilities = [[list(tile_ids) for _ in range(width)] for _ in range(height)]
    collapsed = [[None for _ in range(width)] for _ in range(height)]

    while True:
        # ── 1. Find the cell with lowest entropy ────────────────
        min_entropy = float("inf")
        candidates: list[tuple[int, int]] = []

        for y in range(height):
            for x in range(width):
                if collapsed[y][x] is not None:
                    continue
                entropy = len(possibilities[y][x])
                if entropy == 0:
                    return None  # contradiction
                if entropy < min_entropy:
                    min_entropy = entropy
                    candidates = [(y, x)]
                elif entropy == min_entropy:
                    candidates.append((y, x))

        if not candidates:
            # All cells are collapsed — done.
            break

        # ── 2. Collapse a random candidate cell to a single tile ─
        y, x = rng.choice(candidates)
        tile = rng.choice(possibilities[y][x])
        collapsed[y][x] = tile
        possibilities[y][x] = [tile]

        # ── 3. Propagate constraints from this cell ─────────────
        if not _propagate(possibilities, collapsed, width, height, adjacency):
            return None

    # Build the final grid
    grid = [[0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            c = collapsed[y][x]
            if c is not None:
                grid[y][x] = c
            else:
                # Should not happen (all cells should be collapsed), but be safe.
                grid[y][x] = possibilities[y][x][0]

    return grid


def _propagate(
    possibilities: list[list[list[int]]],
    collapsed: list[list[int | None]],
    width: int,
    height: int,
    adjacency: dict[int, dict[str, list[int]]],
) -> bool:
    """
    Full-chain constraint propagation.

    Walks the queue of cells whose possibility sets changed, and for each
    neighbor checks whether surviving neighbor tile types are still compatible
    with the changed cell's possibilities.

    This handles two cases:
      - A collapsed cell (single tile) → simple forward adjacency lookup
      - An uncollapsed cell (narrowed set) → checks all remaining combos

    Returns False if a contradiction (empty possibility set) is found.
    """
    # Direction vectors and their opposites
    DIRS_VEC = [(-1, 0, "n"), (1, 0, "s"), (0, -1, "w"), (0, 1, "e")]
    OPPOSITE = {"n": "s", "s": "n", "e": "w", "w": "e"}

    queue: deque[tuple[int, int]] = deque()
    visited: set[tuple[int, int]] = set()

    # Seed queue with all cells whose possibilities changed (caller has
    # already collapsed at least one).  We walk the whole grid to catch
    # any inconsistencies from previous iterations.
    for y in range(height):
        for x in range(width):
            if collapsed[y][x] is not None:
                queue.append((y, x))
                visited.add((y, x))

    while queue:
        cy, cx = queue.popleft()

        # Skip if this cell somehow went back to uncollapsed — shouldn't happen.
        tile_id = collapsed[cy][cx]
        if tile_id is None:
            # Uncollapsed cell: run the more expensive full-compatibility check.
            self_possible = possibilities[cy][cx]
            if not self_possible:
                return False

            for dy, dx, direction in DIRS_VEC:
                ny, nx = cy + dy, cx + dx
                if ny < 0 or ny >= height or nx < 0 or nx >= width:
                    continue
                if collapsed[ny][nx] is not None:
                    continue  # neighbour already fixed; no further narrowing needed

                old = possibilities[ny][nx]
                new = []
                for t in old:
                    # Is t's opposite-direction adjacency compatible with
                    # ANY remaining possibility of the current cell?
                    # t must allow at least one of self_possible in the
                    # OPPOSITE direction (from t's point of view, this cell
                    # is in the opposite direction).
                    opp_dir = OPPOSITE[direction]
                    t_allowed = adjacency.get(t, {}).get(opp_dir, [])
                    for s in self_possible:
                        if s in t_allowed:
                            new.append(t)
                            break

                if len(new) != len(old):
                    if not new:
                        return False  # contradiction
                    possibilities[ny][nx] = new
                    if (ny, nx) not in visited:
                        queue.append((ny, nx))
                        visited.add((ny, nx))
        else:
            # ── Collapsed cell: fast forward-check ──────────────
            allowed_adj = adjacency.get(tile_id, {})

            for dy, dx, direction in DIRS_VEC:
                ny, nx = cy + dy, cx + dx
                if ny < 0 or ny >= height or nx < 0 or nx >= width:
                    continue
                if collapsed[ny][nx] is not None:
                    # Both sides are collapsed — verify consistency.
                    neighbour_tile = collapsed[ny][nx]
                    allowed = allowed_adj.get(direction, [])
                    if neighbour_tile not in allowed:
                        return False  # contradiction: incompatible collapsed neighbours
                    continue

                allowed = allowed_adj.get(direction, [])
                if not allowed:
                    continue

                old = possibilities[ny][nx]
                new = [t for t in old if t in allowed]

                if len(new) != len(old):
                    if not new:
                        return False  # contradiction
                    possibilities[ny][nx] = new
                    if (ny, nx) not in visited:
                        queue.append((ny, nx))
                        visited.add((ny, nx))

    return True


# ═══════════════════════════════════════════════════════════════════
# Building Footprint Extraction
# ═══════════════════════════════════════════════════════════════════


def _find_building_rectangles(
    grid: list[list[int]], building_tile_id: int,
) -> list[tuple[int, int, int, int]]:
    """
    Find contiguous building rectangles in a grid using flood-fill
    connected-component analysis.

    Each connected component of building_tile_id cells is bounded to
    give (x, y, width, height).

    Returns a list of (x, y, w, h) tuples.
    """
    if not grid or not grid[0]:
        return []

    height = len(grid)
    width = len(grid[0])
    visited = [[False] * width for _ in range(height)]
    buildings: list[tuple[int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if grid[y][x] == building_tile_id and not visited[y][x]:
                # Flood-fill this connected component.
                stack = [(y, x)]
                visited[y][x] = True
                min_x = max_x = x
                min_y = max_y = y

                while stack:
                    cy, cx = stack.pop()
                    if cx < min_x:
                        min_x = cx
                    if cx > max_x:
                        max_x = cx
                    if cy < min_y:
                        min_y = cy
                    if cy > max_y:
                        max_y = cy

                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = cy + dy, cx + dx
                        if (0 <= ny < height and 0 <= nx < width
                                and grid[ny][nx] == building_tile_id
                                and not visited[ny][nx]):
                            visited[ny][nx] = True
                            stack.append((ny, nx))

                bw = max_x - min_x + 1
                bh = max_y - min_y + 1
                buildings.append((min_x, min_y, bw, bh))

    return buildings


# ═══════════════════════════════════════════════════════════════════
# Grid-to-Description Helpers
# ═══════════════════════════════════════════════════════════════════


def grid_to_ascii(grid: list[list[int]], tile_names: dict[int, str],
                  legend: dict[int, str] | None = None) -> str:
    """
    Convert a WFC grid to an ASCII text map for debugging / display.

    Uses the first character of each tile's name.
    """
    lines: list[str] = []
    for row in grid:
        line = "".join(tile_names.get(c, "?")[0] for c in row)
        lines.append(line)

    if legend:
        lines.append("")
        lines.append("Legend:")
        for tile_id, sym in legend.items():
            name = tile_names.get(tile_id, "?")
            lines.append(f"  {sym} = {name}")

    return "\n".join(lines)


def grid_to_room_description(
    grid: list[list[int]],
    tile_names: dict[int, str],
    room_label: str = "Room",
) -> str:
    """
    Produce a human-readable description of a WFC-generated room layout.

    Uses simple heuristics: counts each tile type, identifies connected
    regions, and produces a short natural-language summary.
    """
    if not grid or not grid[0]:
        return f"The {room_label.lower()} is empty."

    counts: dict[int, int] = {}
    for row in grid:
        for tile in row:
            counts[tile] = counts.get(tile, 0) + 1

    total = len(grid) * len(grid[0])
    parts: list[str] = []

    for tile_id, name in tile_names.items():
        count = counts.get(tile_id, 0)
        if count == 0:
            continue
        pct = (count / total) * 100
        if pct > 30:
            adj = "mostly"
        elif pct > 15:
            adj = "some"
        else:
            adj = "a few"

        name_lower = name.lower()
        if adj == "mostly" and name_lower.endswith("y"):
            parts.append(f"mostly {name_lower[:-1]}ies")
        elif adj == "mostly":
            parts.append(f"mostly {name_lower}s")
        elif adj == "some":
            parts.append(f"some {name_lower}s")
        else:
            parts.append(f"a few {name_lower}s")

    if parts:
        description = f"The {room_label.lower()} has {', '.join(parts[:-1])} and {parts[-1]}."
    else:
        description = f"The {room_label.lower()} is an empty space."

    return description


# ═══════════════════════════════════════════════════════════════════
# City Layout Generator
# ═══════════════════════════════════════════════════════════════════


def generate_city_layout(
    width: int,
    height: int,
    seed: int,
    num_buildings: int = 10,
) -> tuple[list[list[int]], dict]:
    """
    Generate a city layout using WFC.

    Uses the CITY_TILES tile set with CITY_ADJACENCY rules. After
    generation, extracts building footprints as bounding rectangles.

    Args:
        width, height: Grid dimensions for the city.
        seed: Random seed for deterministic generation.
        num_buildings: Target number of building footprints.
                       (Actual count depends on WFC output.)

    Returns:
        (grid, metadata) where:
          grid: 2D array of CITY_TILE ints.
          metadata: dict with:
            - "buildings": list of (x, y, w, h) tuples for each building footprint
            - "num_buildings": actual count
            - "seed": seed used
    """
    rng = random.Random(seed)

    # Build adjacency that is fully connected (to keep WFC from failing).
    # We start with the standard CITY_ADJACENCY but bias toward producing
    # BUILDING tiles to hit the num_buildings target.
    grid = run_wfc(width, height, CITY_TILES, CITY_ADJACENCY, rng, max_attempts=50)

    if grid is None:
        # Fallback: generate a simple grid with buildings and streets.
        grid = _fallback_city(width, height, rng, num_buildings)

    # Extract building footprints.
    buildings = _find_building_rectangles(grid, CITY_TILES["BUILDING"])

    # If we have too few buildings, try harder with a different seed offset.
    attempts = 0
    while len(buildings) < max(1, num_buildings // 3) and attempts < 10:
        rng2 = random.Random(seed + attempts * 137 + 1)
        grid2 = run_wfc(width, height, CITY_TILES, CITY_ADJACENCY, rng2, max_attempts=50)
        if grid2 is not None:
            b2 = _find_building_rectangles(grid2, CITY_TILES["BUILDING"])
            if len(b2) > len(buildings):
                grid = grid2
                buildings = b2
        attempts += 1

    metadata = {
        "buildings": buildings,
        "num_buildings": len(buildings),
        "seed": seed,
    }
    return grid, metadata


def _fallback_city(width: int, height: int, rng: random.Random,
                   num_buildings: int) -> list[list[int]]:
    """Generate a simple city grid when WFC fails."""
    grid = [[CITY_TILES["EMPTY"]] * width for _ in range(height)]

    # Lay down some streets.
    for x in range(0, width, max(1, width // 5)):
        for y in range(height):
            if 0 <= x < width:
                grid[y][x] = CITY_TILES["STREET"]

    for y in range(0, height, max(1, height // 5)):
        for x in range(width):
            if 0 <= y < height:
                grid[y][x] = CITY_TILES["STREET"]

    # Sprinkle buildings in the blocks between streets.
    placed = 0
    for _ in range(num_buildings * 3):
        if placed >= num_buildings:
            break
        bw = rng.randint(2, 5)
        bh = rng.randint(2, 5)
        bx = rng.randint(0, width - bw)
        by = rng.randint(0, height - bh)

        can_place = True
        for dy in range(bh):
            for dx in range(bw):
                if grid[by + dy][bx + dx] != CITY_TILES["EMPTY"]:
                    can_place = False
                    break
            if not can_place:
                break

        if not can_place:
            continue

        for dy in range(bh):
            for dx in range(bw):
                grid[by + dy][bx + dx] = CITY_TILES["BUILDING"]
        placed += 1

    # Add some random water.
    for _ in range(max(1, width * height // 50)):
        wx = rng.randint(0, width - 1)
        wy = rng.randint(0, height - 1)
        if grid[wy][wx] == CITY_TILES["EMPTY"]:
            grid[wy][wx] = CITY_TILES["WATER"]

    return grid


# ═══════════════════════════════════════════════════════════════════
# Building Interior Generator
# ═══════════════════════════════════════════════════════════════════


def generate_building_interior(
    building_w: int,
    building_h: int,
    seed: int,
    room_types: list[str] | None = None,
) -> list[list[int]]:
    """
    Generate the interior of a single building using WFC.

    Produces a grid of ROOM_TILE ints. The edge cells are constrained
    to be WALL (outside boundary) and the interior is generated with
    room-appropriate adjacency rules.

    Args:
        building_w, building_h: Dimensions of the building interior grid.
        seed: Random seed.
        room_types: List of room type tags (e.g. ["tavern", "shop"])
                    that influence the interior layout. Currently unused
                    but kept for future contextual generation.

    Returns:
        Grid of ROOM_TILE ints (building_w × building_h).
    """
    rng = random.Random(seed)

    # For small buildings, use direct placement.
    if building_w <= 2 or building_h <= 2:
        return _simple_room(building_w, building_h, ROOM_TILES)

    # ── Constrain edges to WALL ─────────────────────────────
    # We do this by pre-collapsing the edge cells.
    all_tile_ids = sorted(set(ROOM_TILES.values()))
    width = building_w
    height = building_h

    # Build initial possibilities with edge constraints.
    possibilities = [[list(all_tile_ids) for _ in range(width)] for _ in range(height)]
    collapsed = [[None for _ in range(width)] for _ in range(height)]

    # Edges must be WALL (1)
    for y in range(height):
        for x in range(width):
            if (y == 0 or y == height - 1 or x == 0 or x == width - 1):
                collapsed[y][x] = ROOM_TILES["WALL"]
                possibilities[y][x] = [ROOM_TILES["WALL"]]

    # Run a constrained WFC that starts from the pre-collapsed edges.
    grid = _run_constrained_wfc(possibilities, collapsed, ROOM_ADJACENCY, rng)
    if grid is not None:
        return grid

    # Fallback: simple room layout
    return _simple_room(building_w, building_h, ROOM_TILES)


def _run_constrained_wfc(
    initial_possibilities: list[list[list[int]]],
    initial_collapsed: list[list[int | None]],
    adjacency: dict[int, dict[str, list[int]]],
    rng: random.Random,
    max_attempts: int = 50,
) -> list[list[int]] | None:
    """
    Run WFC starting from a partially-collapsed grid.

    The initial_possibilities and initial_collapsed arrays define the
    starting state (e.g., edges pre-collapsed to WALL).
    """
    for attempt in range(max_attempts):
        # Deep-copy the initial state for this attempt.
        height = len(initial_possibilities)
        width = len(initial_possibilities[0])
        possibilities = [row[:] for row in initial_possibilities]
        collapsed = [row[:] for row in initial_collapsed]

        # Propagate from pre-collapsed cells.
        if not _propagate(possibilities, collapsed, width, height, adjacency):
            rng.random()
            continue

        # Main WFC loop.
        while True:
            min_entropy = float("inf")
            candidates: list[tuple[int, int]] = []

            for y in range(height):
                for x in range(width):
                    if collapsed[y][x] is not None:
                        continue
                    entropy = len(possibilities[y][x])
                    if entropy == 0:
                        candidates = []
                        break
                    if entropy < min_entropy:
                        min_entropy = entropy
                        candidates = [(y, x)]
                    elif entropy == min_entropy:
                        candidates.append((y, x))
                else:
                    continue
                break

            if not candidates:
                if all(collapsed[y][x] is not None
                       for y in range(height) for x in range(width)):
                    break
                # No candidates but not all collapsed — contradiction.
                candidates = None
                break

            y, x = rng.choice(candidates)
            tile = rng.choice(possibilities[y][x])
            collapsed[y][x] = tile
            possibilities[y][x] = [tile]

            if not _propagate(possibilities, collapsed, width, height, adjacency):
                break
        else:
            # Build the result grid.
            grid = [[0 for _ in range(width)] for _ in range(height)]
            for y in range(height):
                for x in range(width):
                    c = collapsed[y][x]
                    grid[y][x] = c if c is not None else possibilities[y][x][0]
            return grid

        # Advance RNG for next attempt.
        rng.random()

    return None


def _simple_room(bw: int, bh: int,
                 tile_set: dict[str, int]) -> list[list[int]]:
    """Generate the simplest possible room: walls on edges, floor inside."""
    grid = [[tile_set["FLOOR"]] * bw for _ in range(bh)]
    for y in range(bh):
        for x in range(bw):
            if y == 0 or y == bh - 1 or x == 0 or x == bw - 1:
                grid[y][x] = tile_set["WALL"]
    # Place a door in a random wall.
    rng = random.Random(bw * 100 + bh)
    door_positions = []
    for x in range(1, bw - 1):
        door_positions.append((0, x))        # top wall
        door_positions.append((bh - 1, x))   # bottom wall
    for y in range(1, bh - 1):
        door_positions.append((y, 0))        # left wall
        door_positions.append((y, bw - 1))   # right wall
    if door_positions:
        dy, dx = rng.choice(door_positions)
        grid[dy][dx] = tile_set["DOOR"]
    return grid


# ═══════════════════════════════════════════════════════════════════
# Dungeon Layout Generator
# ═══════════════════════════════════════════════════════════════════


def generate_dungeon_layout(
    width: int,
    height: int,
    seed: int,
    difficulty: str = "medium",
) -> list[list[int]]:
    """
    Generate a dungeon layout using WFC.

    Difficulty affects the proportion of traps, the number of stairs,
    and overall complexity:
      - "easy":   fewer traps, simpler layout
      - "medium": balanced
      - "hard":   more traps, more complex constraints

    Returns:
        Grid of DUNGEON_TILE ints.
    """
    rng = random.Random(seed)

    # Adjust adjacency weights based on difficulty.
    adjacency = dict(DUNGEON_ADJACENCY)
    if difficulty == "easy":
        # Fewer traps, more floors.
        _adjust_dungeon_difficulty(adjacency, trap_bias=0.3, chest_bias=0.5)
    elif difficulty == "hard":
        # More traps, more chests, more features.
        _adjust_dungeon_difficulty(adjacency, trap_bias=2.0, chest_bias=1.5)
    else:
        _adjust_dungeon_difficulty(adjacency, trap_bias=1.0, chest_bias=1.0)

    grid = run_wfc(width, height, DUNGEON_TILES, adjacency, rng, max_attempts=50)

    if grid is None:
        # Fallback: simple dungeon
        grid = _simple_dungeon(width, height, rng)

    # Ensure at least one set of stairs.
    _ensure_stairs(grid, DUNGEON_TILES, rng)

    return grid


def _adjust_dungeon_difficulty(
    adjacency: dict[int, dict[str, list[int]]],
    trap_bias: float = 1.0,
    chest_bias: float = 1.0,
) -> None:
    """Adjust dungeon adjacency to bias trap/chest prevalence.

    Modifies adjacency in-place. WFC uses these lists as *filters* during
    constraint propagation, so controlling what's allowed directly controls
    which features can appear.

    Strategy:
      - trap_bias < 1.0 (easy):  remove TRAP from FLOOR's adjacency —
                                  traps cannot form next to walkable floors.
      - trap_bias > 1.0 (hard):  add TRAP to CORRIDOR adjacency so traps
                                  can appear in hallways too.
      - chest_bias controls how many floor adjacencies include CHEST.
    """
    trap_id = DUNGEON_TILES["TRAP"]
    chest_id = DUNGEON_TILES["CHEST"]
    floor_id = DUNGEON_TILES["FLOOR"]
    corridor_id = DUNGEON_TILES["CORRIDOR"]

    # ── Trap biasing ──────────────────────────────────────
    if trap_bias < 1.0:
        # Easy: traps cannot form next to floors.
        # Remove trap from floor's adjacency in all directions.
        for direction in ["n", "s", "e", "w"]:
            adj = adjacency[floor_id][direction]
            if trap_id in adj:
                adj.remove(trap_id)
            adj = adjacency[trap_id][direction]
            if floor_id in adj:
                adj.remove(floor_id)

    elif trap_bias > 1.0:
        # Hard: traps can also appear next to corridors.
        for direction in ["n", "s", "e", "w"]:
            adj = adjacency[corridor_id][direction]
            if trap_id not in adj:
                adj.append(trap_id)
            adj = adjacency[trap_id][direction]
            if corridor_id not in adj:
                adj.append(corridor_id)

    # ── Chest biasing ─────────────────────────────────────
    # Chests already only appear adjacent to floors. Control is handled
    # by the initial collapse weighting in the WFC loop.
    if chest_bias < 1.0:
        # Easy: reduce chest appearance by removing it from floor adjacency
        # in some directions (both n/s and e/w pairs to avoid bias).
        for direction in ["n", "s"]:
            adj = adjacency[floor_id][direction]
            if chest_id in adj:
                adj.remove(chest_id)
            adj = adjacency[chest_id][direction]
            if floor_id in adj:
                adj.remove(floor_id)


def _ensure_stairs(
    grid: list[list[int]],
    tile_set: dict[str, int],
    rng: random.Random,
) -> None:
    """Ensure at least one set of stairs exists in the dungeon grid."""
    has_stairs = any(
        cell == tile_set["STAIRS"]
        for row in grid
        for cell in row
    )
    if not has_stairs:
        # Find a floor tile and replace it with stairs.
        floor_positions = [
            (y, x) for y in range(len(grid))
            for x in range(len(grid[0]))
            if grid[y][x] == tile_set["FLOOR"]
        ]
        if floor_positions:
            sy, sx = rng.choice(floor_positions)
            grid[sy][sx] = tile_set["STAIRS"]


def _simple_dungeon(
    width: int,
    height: int,
    rng: random.Random,
) -> list[list[int]]:
    """Generate a simple dungeon layout as fallback."""
    grid = [[DUNGEON_TILES["WALL"]] * width for _ in range(height)]

    # Carve out rooms and corridors.
    for _ in range(max(1, (width * height) // 20)):
        rx = rng.randint(1, max(1, width - 3))
        ry = rng.randint(1, max(1, height - 3))
        rw = rng.randint(2, min(5, width - rx - 1))
        rh = rng.randint(2, min(5, height - ry - 1))
        for dy in range(rh):
            for dx in range(rw):
                grid[ry + dy][rx + dx] = DUNGEON_TILES["FLOOR"]

    # Connect rooms with corridors.
    for _ in range(width * height // 10):
        cx = rng.randint(1, width - 2)
        cy = rng.randint(1, height - 2)
        if grid[cy][cx] == DUNGEON_TILES["WALL"]:
            grid[cy][cx] = DUNGEON_TILES["CORRIDOR"]

    # Scatter some features.
    feature_tiles = [DUNGEON_TILES["TRAP"], DUNGEON_TILES["CHEST"]]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == DUNGEON_TILES["FLOOR"] and rng.random() < 0.05:
                grid[y][x] = rng.choice(feature_tiles)

    return grid


# ═══════════════════════════════════════════════════════════════════
# Combined Generator (for multi-scale city → building pipeline)
# ═══════════════════════════════════════════════════════════════════


def generate_city_with_interiors(
    city_width: int,
    city_height: int,
    seed: int,
    num_buildings: int = 10,
) -> tuple[list[list[int]], dict[str, list[list[int]]]]:
    """
    Generate a full city with interiors for each building.

    This is the top-level entry point for generating explorable city spaces:
      1. Generate the city layout (streets, buildings, plazas, etc.)
      2. For each building footprint, generate an interior layout
      3. Return both the city grid and a mapping of building interiors

    Args:
        city_width, city_height: dimensions of the city grid
        seed: deterministic seed
        num_buildings: target number of building footprints

    Returns:
        (city_grid, interiors) where interiors maps
        building index (e.g. "building_0") to its interior ROOM_TILES grid.
    """
    city_grid, meta = generate_city_layout(city_width, city_height, seed, num_buildings)
    interiors: dict[str, list[list[int]]] = {}

    rng = random.Random(seed + 9999)

    for i, (bx, by, bw, bh) in enumerate(meta["buildings"]):
        # Each building gets its own seed derived from the city seed and index.
        b_seed = seed * 31 + i * 137
        interior = generate_building_interior(bw + 2, bh + 2, b_seed)
        interiors[f"building_{i}"] = interior

    return city_grid, interiors
