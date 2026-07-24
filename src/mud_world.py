"""wyrd — Chunk-based infinite world expansion.

The world is divided into chunks. As the player walks, new chunks are
generated on demand using the world seed. Each chunk produces terrain
(via noise), and if the chunk contains a settlement, WFC generates its
city layout and building interiors.

Same seed + same chunk coordinates = same result, always.
"""

from __future__ import annotations

import math
import random
from typing import Optional

from .world import World, Region, Settlement
from .generate import generate_world
from .lore import generate_lore
from .narrative import generate_narrative
from .religion import generate_pantheon
from .magic import generate_magic_system
from .faction import generate_factions
from .chronicles import generate_chronicles
from .bestiary import generate_bestiary

from .room import Zone, Room
from .wfc import (
    generate_city_layout,
    generate_building_interior,
    CITY_TILES, ROOM_TILES, DUNGEON_TILES,
)


# ── Constants ──────────────────────────────────────────────────────────

CHUNK_SIZE = 32  # tiles per chunk
WORLD_SIZE = 64  # initial world is 64x64 tiles (2x2 chunks)


# ── Chunk coordinates ──────────────────────────────────────────────────

def chunk_key(cx: int, cy: int) -> str:
    """Canonical key for a chunk at (cx, cy)."""
    return f"{cx},{cy}"


def tile_to_chunk(tx: int, ty: int) -> tuple[int, int]:
    """Convert tile coordinates to chunk coordinates."""
    return tx // CHUNK_SIZE, ty // CHUNK_SIZE


# ── Settlement metadata cache ──────────────────────────────────────────

class ChunkSettlement:
    """A settlement discovered in a chunk."""
    name: str
    chunk_x: int
    chunk_y: int
    population: int
    economy: str
    zones: dict[str, Zone]  # zone_name -> Zone

    def __init__(self, name: str, cx: int, cy: int, pop: int = 500, economy: str = "general"):
        self.name = name
        self.chunk_x = cx
        self.chunk_y = cy
        self.population = pop
        self.economy = economy
        self.zones = {}


# ── World Expansion Manager ────────────────────────────────────────────

class MudWorld:
    """Manages infinite chunk-based world expansion.

    The player starts in the seed-generated world. As they walk to the
    edge, new chunks are generated.

    Each chunk has:
    - Terrain (noise-based, extending the existing generators)
    - Optional settlement (WFC city layout if conditions are right)
    - Optional dungeon/ruin (WFC dungeon layout if appropriate)
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.base_world: World | None = None  # The initial generated world
        self.chunks: dict[str, dict] = {}     # chunk_key -> chunk data
        self.settlements: dict[str, ChunkSettlement] = {}
        self.loaded_zones: dict[str, Zone] = {}  # All zones across all chunks

    def init_from_seed(self) -> World:
        """Generate the base world from the seed."""
        w = generate_world(self.seed)
        w.lore = generate_lore(w)
        w.narrative = generate_narrative(w)
        w.pantheon = generate_pantheon(w)
        w.magic = generate_magic_system(w)
        w.factions = generate_factions(w)
        w.chronicles = generate_chronicles(w)
        w.bestiary = generate_bestiary(w)
        self.base_world = w

        # Register base world settlements WITH their zones
        for region in w.regions:
            for s in region.settlements:
                cx, cy = tile_to_chunk(s.x, s.y)
                # Generate zones for this settlement using WFC city layout
                settlement_data = self._generate_chunk_settlement(cx, cy)
                if settlement_data:
                    zones = self._city_to_zones(settlement_data, cx, cy)
                    self.loaded_zones.update(zones)
                    cs = ChunkSettlement(
                        name=s.name, cx=cx, cy=cy,
                        pop=settlement_data["population"],
                        economy=settlement_data["economy"],
                    )
                    cs.zones = zones
                    self.settlements[s.name] = cs
                else:
                    cs = ChunkSettlement(
                        name=s.name, cx=cx, cy=cy,
                        pop=s.population if hasattr(s, 'population') and s.population else 300 + (s.x * 7 + s.y * 13) % 2000,
                        economy=self._infer_economy(w, s.x, s.y),
                    )
                    self.settlements[s.name] = cs

        return w

    def _infer_economy(self, world: World, tx: int, ty: int) -> str:
        """Infer economy type from terrain."""
        if 0 <= ty < world.height and 0 <= tx < world.width:
            terrain = world.terrain[ty][tx]
            if terrain in ("deep_water", "shallow"):
                return "fishing"
            if terrain in ("forest", "hills"):
                return "logging"
            if terrain in ("mountains",):
                return "mining"
            if terrain in ("grass",):
                return "farming"
        return "general"

    def get_chunk(self, cx: int, cy: int) -> dict | None:
        """Get or generate a chunk at (cx, cy)."""
        key = chunk_key(cx, cy)
        if key in self.chunks:
            return self.chunks[key]

        # Generate the chunk
        chunk = self._generate_chunk(cx, cy)
        self.chunks[key] = chunk
        return chunk

    def _generate_chunk(self, cx: int, cy: int) -> dict:
        """Generate terrain + optional settlement for a chunk."""
        # Determine if this chunk should have a settlement
        can_have_settlement = self._should_have_settlement(cx, cy)

        chunk = {
            "cx": cx,
            "cy": cy,
            "terrain": None,  # filled below
            "settlement": None,
            "dungeon": None,
        }

        if can_have_settlement:
            settlement = self._generate_chunk_settlement(cx, cy)
            if settlement:
                chunk["settlement"] = settlement
                name = settlement["name"]
                # Extract zones from the city
                zones = self._city_to_zones(settlement, cx, cy)
                cs = ChunkSettlement(name=name, cx=cx, cy=cy, pop=settlement["population"], economy=settlement["economy"])
                cs.zones = zones
                self.settlements[name] = cs
                self.loaded_zones.update(zones)

        # Maybe a dungeon
        if not chunk["settlement"] and self._should_have_dungeon(cx, cy):
            dungeon = self._generate_chunk_dungeon(cx, cy)
            if dungeon:
                chunk["dungeon"] = dungeon
                zones = self._dungeon_to_zones(dungeon, cx, cy)
                self.loaded_zones.update(zones)

        return chunk

    def _should_have_settlement(self, cx: int, cy: int) -> bool:
        """Deterministic check — should this chunk have a settlement?"""
        rng = random.Random(self.seed + cx * 7919 + cy * 104729)
        # ~25% chance for any given chunk, but clusters near origin
        dist = math.sqrt(cx * cx + cy * cy)
        probability = max(0.05, 0.3 - dist * 0.005)
        return rng.random() < probability

    def _should_have_dungeon(self, cx: int, cy: int) -> bool:
        """Deterministic check — should this chunk have a dungeon?"""
        rng = random.Random(self.seed + cx * 6271 + cy * 107367)
        dist = math.sqrt(cx * cx + cy * cy)
        # Dungeons more common at distance
        probability = min(0.4, 0.05 + dist * 0.01)
        return rng.random() < probability

    def _generate_chunk_settlement(self, cx: int, cy: int) -> dict | None:
        """Generate a settlement in a chunk using WFC."""
        rng = random.Random(self.seed + cx * 100003 + cy * 200003)

        # Settlement name from seed
        prefixes = ["North", "South", "East", "West", "New", "Old", "Port", "Fort",
                     "Iron", "Gold", "Silver", "Copper", "Ash", "Oak", "Pine", "Stone",
                     "Red", "White", "Black", "Green", "High", "Deep", "Far", "Fair"]
        suffixes = ["town", "field", "shire", "bridge", "ford", "brook", "haven",
                     "worth", "wick", "stead", "burg", "fell", "gate", "holm",
                     "moor", "dale", "firth", "beck", "thorpe"]
        name = f"{rng.choice(prefixes)}{rng.choice(suffixes)}"

        # Population scales with distance from origin
        dist = math.sqrt(cx * cx + cy * cy)
        population = int(max(50, rng.gauss(300 + dist * 20, 100)))

        economy = rng.choice(["farming", "mining", "fishing", "logging", "trade", "general"])

        # Generate city layout with WFC
        city_w, city_h = 30, 30
        city_grid, city_meta = generate_city_layout(city_w, city_h, self.seed + cx * 7 + cy * 13)

        if city_grid is None:
            return None

        return {
            "name": name,
            "population": population,
            "economy": economy,
            "grid": city_grid,
            "buildings": city_meta.get("buildings", []),
            "chunk_x": cx,
            "chunk_y": cy,
        }

    def _city_to_zones(self, settlement: dict, cx: int, cy: int) -> dict[str, Zone]:
        """Convert a WFC city layout into MUD zones and rooms."""
        zones = {}
        zone = Zone(
            name=settlement["name"],
            zone_type="settlement",
            entry_room="town_square",
            rooms={},
        )

        rng = random.Random(self.seed + cx * 3001 + cy * 5003)
        name = settlement["name"]
        economy = settlement["economy"]
        pop = settlement["population"]

        # Town square (always)
        zone.rooms["town_square"] = Room(
            room_id="town_square",
            name=f"{name} Town Square",
            description=(f"The heart of {name}, a bustling square where traders hawk their wares "
                         f"and townsfolk gather. The cobblestones are worn smooth by countless feet. "
                         f"{name} has a {economy}-based economy and a population of about {pop:,}."),
            exits={"n": "market_row", "s": "tavern", "e": "leader_hall", "w": "wilderness"},
            contents=[],
            npcs=[
                {"name": "Town Crier", "title": "gossip", "dialog": f"Hear ye! News from {name}!"},
            ],
            tags=["outdoors", "town_square"],
        )

        # Market row
        zone.rooms["market_row"] = Room(
            room_id="market_row",
            name=f"{name} Market Row",
            description=f"A lively street lined with stalls and shops. Merchants call out their wares. "
                        f"The air smells of fresh bread, spices, and smoke.",
            exits={"s": "town_square"},
            contents=[],
            npcs=[
                {"name": "Merchant", "title": "trader", "dialog": "Fine wares! Best prices in town!"},
            ],
            tags=["outdoors", "market", "shop"],
        )

        # Tavern
        tavern_name = rng.choice(["The Sleeping Fox", "The Rusty Anchor", "The Golden Tankard",
                                    "The Wanderer's Rest", "The Velvet Rose", "The Tipsy Dragon"])
        zone.rooms["tavern"] = Room(
            room_id="tavern",
            name=tavern_name,
            description=f"A warm, smoky tavern filled with the murmur of conversation and the clink of mugs. "
                        f"The hearth crackles, casting dancing shadows across timbered walls.",
            exits={"n": "town_square"},
            contents=[],
            npcs=[
                {"name": "Barkeep", "title": "innkeeper", "dialog": "What'll it be, traveler?"},
            ],
            tags=["indoors", "tavern"],
        )

        # Leader hall
        zone.rooms["leader_hall"] = Room(
            room_id="leader_hall",
            name=f"{name} Council Hall",
            description=f"A sturdy stone building that serves as the seat of local governance. "
                        f"Decrees and maps cover the walls. The air smells of old parchment.",
            exits={"w": "town_square"},
            contents=[],
            npcs=[
                {"name": "Elder", "title": "settlement leader", "dialog": f"Welcome to {name}. We're a peaceful folk."},
            ],
            tags=["indoors", "civic"],
        )

        # Add buildings from WFC city layout
        buildings = settlement.get("buildings", [])
        for i, (bx, by, bw, bh) in enumerate(buildings):
            if i >= 6:  # Limit to 6 extra buildings
                break
            bid = f"building_{i}"
            room_name = rng.choice(["Armory", "Smithy", "Granary", "Temple", "Library", "Guild Hall",
                                     "Warehouse", "Barracks", "Apothecary", "Stable"])
            zone.rooms[bid] = Room(
                room_id=bid,
                name=room_name,
                description=f"A {room_name.lower()} in {name}. The building looks well-used and functional.",
                exits={"s": "town_square"},
                contents=[],
                npcs=[],
                tags=["indoors", room_name.lower()],
            )

        zone.entry_room = "town_square"
        zones[settlement["name"]] = zone
        return zones

    def _generate_chunk_dungeon(self, cx: int, cy: int) -> dict | None:
        """Generate a dungeon in a chunk using WFC."""
        from .wfc import generate_dungeon_layout
        rng = random.Random(self.seed + cx * 40001 + cy * 60007)

        difficulty = rng.choices(["easy", "medium", "hard"], weights=[3, 2, 1])[0]
        dungeon_grid = generate_dungeon_layout(20, 20, self.seed + cx * 11 + cy * 17, difficulty)

        if dungeon_grid is None:
            return None

        dungeon_name = rng.choice(["The Forgotten Catacombs", "The Sunken Vault", "The Crystal Caves",
                                     "The Dark Warrens", "The Spider's Nest", "The Ancient Barrow",
                                     "The Obsidian Pit", "The Hollow Hill"])

        return {
            "name": dungeon_name,
            "difficulty": difficulty,
            "grid": dungeon_grid,
            "chunk_x": cx,
            "chunk_y": cy,
        }

    def _dungeon_to_zones(self, dungeon: dict, cx: int, cy: int) -> dict[str, Zone]:
        """Convert a WFC dungeon layout into MUD zones and rooms."""
        zone = Zone(
            name=dungeon["name"],
            zone_type="dungeon",
            entry_room="dungeon_entrance",
            rooms={},
        )

        zone.rooms["dungeon_entrance"] = Room(
            room_id="dungeon_entrance",
            name=f"Entrance to {dungeon['name']}",
            description=f"A dark opening in the earth, leading into {dungeon['name']}. "
                        f"The air is cold and damp. This dungeon is rated [{dungeon['difficulty']}].",
            exits={"in": "dungeon_hall_1", "out": "wilderness"},
            contents=[],
            npcs=[],
            tags=["dungeon"],
        )

        # Generate some dungeon rooms
        dng = dungeon["grid"]
        # Find chambers in the grid (contiguous FLOOR areas)
        chambers = []
        visited = set()
        for y in range(len(dng)):
            for x in range(len(dng[0])):
                if dng[y][x] == ROOM_TILES["FLOOR"] and (x, y) not in visited:
                    # BFS to find chamber size
                    stack = [(x, y)]
                    chamber = []
                    while stack:
                        cx2, cy2 = stack.pop()
                        if (cx2, cy2) in visited:
                            continue
                        visited.add((cx2, cy2))
                        if 0 <= cy2 < len(dng) and 0 <= cx2 < len(dng[0]) and dng[cy2][cx2] == ROOM_TILES["FLOOR"]:
                            chamber.append((cx2, cy2))
                            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                                stack.append((cx2 + dx, cy2 + dy))
                    if len(chamber) >= 4:
                        chambers.append(chamber)

        for i, chamber in enumerate(chambers[:5]):  # Max 5 chambers
            rid = f"dungeon_room_{i}"
            zone.rooms[rid] = Room(
                room_id=rid,
                name=f"Chamber of {dungeon['name']}",
                description=f"A dark, damp chamber. The walls are rough-hewn stone, "
                            f"and the air carries the scent of earth and decay.",
                exits={"back": "dungeon_hall_1"},
                contents=[],
                npcs=[],
                tags=["dungeon", "indoors"],
            )

        zone.rooms["dungeon_hall_1"] = Room(
            room_id="dungeon_hall_1",
            name="Dark Corridor",
            description="A narrow corridor stretches into darkness. Water drips somewhere in the distance.",
            exits={"n": "dungeon_entrance", "s": "dungeon_room_0"},
            contents=[],
            npcs=[],
            tags=["dungeon", "corridor"],
        )

        return {dungeon["name"]: zone}

    def get_zone_for_location(self, chunk_cx: int, chunk_cy: int, settlement_name: str | None = None) -> Zone | None:
        """Get the zone at a specific chunk coordinate."""
        if settlement_name and settlement_name in self.settlements:
            cs = self.settlements[settlement_name]
            if settlement_name in cs.zones:
                return cs.zones[settlement_name]

        # Check loaded zones
        key = chunk_key(chunk_cx, chunk_cy)
        for name, zone in self.loaded_zones.items():
            if name in self.settlements:
                cs = self.settlements[name]
                if cs.chunk_x == chunk_cx and cs.chunk_y == chunk_cy:
                    return zone

        return None

    def get_settlement_names(self) -> list[str]:
        """Get all known settlement names (base world + discovered)."""
        names = []
        if self.base_world:
            for region in self.base_world.regions:
                for s in region.settlements:
                    names.append(s.name)
        names.extend([n for n in self.settlements.keys() if n not in names])
        return names
