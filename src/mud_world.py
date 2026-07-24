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
                # Generate zones for this settlement using WFC, seeded by settlement position
                settlement_data = self._generate_city_for_base_settlement(s.name, s.x, s.y)
                if settlement_data:
                    zones = self._city_to_zones(settlement_data, cx, cy, name_override=s.name)
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

        # Add wilderness zone
        from .room import Room
        wilderness_zone = Zone(
            name="Wilderness",
            zone_type="wilderness",
            entry_room="wilderness_center",
            rooms={
                "wilderness_center": Room(
                    room_id="wilderness_center",
                    name="The Wild Lands",
                    description="You stand in the untamed wilderness. The land stretches out in all directions, dotted with trees, hills, and the occasional animal track. The air is fresh and cool.",
                    exits={"north": "wilderness", "south": "wilderness", "east": "wilderness", "west": "wilderness"},
                    contents=[{"name": "wildflowers", "type": "plant"}, {"name": "rabbit", "type": "animal"}],
                    npcs=[],
                    tags=["outdoors", "wilderness"],
                ),
                "wilderness": Room(
                    room_id="wilderness",
                    name="The Wild Lands",
                    description="The wilderness stretches on. You see rolling hills, dense forests, and the occasional bird soaring overhead. The path back to civilization is not far.",
                    exits={},
                    contents=[{"name": "tall grass", "type": "plant"}, {"name": "deer", "type": "animal"}],
                    npcs=[],
                    tags=["outdoors", "wilderness"],
                ),
            },
        )
        self.loaded_zones["Wilderness"] = wilderness_zone

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

    def _generate_city_for_base_settlement(self, name: str, tx: int, ty: int) -> dict | None:
        """Generate a city layout for a base world settlement using its position as seed."""
        rng = random.Random(self.seed + tx * 90001 + ty * 70001 + hash(name) % (2**31))
        pop = int(max(50, rng.gauss(300, 100)))
        economy = rng.choice(["farming", "mining", "fishing", "logging", "trade", "general"])
        city_w, city_h = 30, 30
        city_grid, city_meta = generate_city_layout(city_w, city_h, self.seed + tx * 7 + ty * 13)
        if city_grid is None:
            return None
        return {
            "name": name,
            "population": pop,
            "economy": economy,
            "grid": city_grid,
            "buildings": city_meta.get("buildings", []),
            "chunk_x": tx // 32,
            "chunk_y": ty // 32,
        }

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
        # Parse WFC grid and buildings
        grid = settlement["grid"]
        buildings = settlement.get("buildings", [])
        
        # Create rooms for every WFC tile
        rooms = {}
        rng = random.Random(self.seed + cx * 3001 + cy * 5003)
        
        # Group buildings by type for room generation
        building_map = {}
        for b in buildings:
            bx, by, bw, bh = b
            # Infer building type from WFC code
            # (This is a simplification — real WFC should include type)
            btype = "house"  # Default
            if bx == 15 and by == 1: btype = "gate"
            elif bx == 8 and by == 13: btype = "temple"
            elif bx == 21 and by == 13: btype = "guildhall"
            elif bx < 10: btype = "shop"
            elif bx > 20: btype = "farm"
            building_map[(bx, by)] = {"type": btype, "floors": rng.randint(1, 3)}
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                # Map WFC numeric codes to tile types
                tile_map = {
                    0: "empty",
                    1: "street",
                    2: "plaza",
                    3: "wall",
                    4: "house",
                    5: "shop",
                    6: "tavern",
                    7: "inn",
                    8: "temple",
                    9: "guildhall",
                    10: "manor",
                    11: "farm",
                    12: "docks",
                    13: "gate",
                }
                tile = grid[y][x]
                tile_type = tile_map.get(tile, "alley")
                room_id = f"r_{x}_{y}"
                room_name = f"{x},{y}"
                
                # Determine room type and exits
                exits = {}
                if x > 0: exits["west"] = f"r_{x-1}_{y}"
                if x < len(grid[y]) - 1: exits["east"] = f"r_{x+1}_{y}"
                if y > 0: exits["north"] = f"r_{x}_{y-1}"
                if y < len(grid) - 1: exits["south"] = f"r_{x}_{y+1}"
                
                # Check for building
                building = building_map.get((x, y))
                contents = []
                tags = []
                npcs = []
                if building:
                    btype = building["type"]
                    if btype == "house":
                        room_type = "house"
                        room_name = f"House {x},{y}"
                        tags = ["indoors", "house"]
                        contents = [{"name": "wooden table", "type": "furniture"}, {"name": "straw bed", "type": "furniture"}]
                    elif btype == "shop":
                        room_type = "shop"
                        room_name = f"{rng.choice(['General Store', 'Blacksmith', 'Apothecary', 'Tavern'])} {x},{y}"
                        tags = ["indoors", "shop"]
                        contents = [{"name": "counter", "type": "furniture"}, {"name": "shelves of wares", "type": "item"}]
                    elif btype == "tavern":
                        room_type = "tavern"
                        room_name = f"{rng.choice(['The Prancing Pony', 'The Rusty Nail', 'The Tipsy Griffin'])} {x},{y}"
                        tags = ["indoors", "tavern"]
                        contents = [{"name": "bar", "type": "furniture"}, {"name": "tables and chairs", "type": "furniture"}]
                    elif btype == "inn":
                        room_type = "inn"
                        room_name = f"{rng.choice(['The Sleeping Dragon', 'The Cozy Hearth'])} {x},{y}"
                        tags = ["indoors", "inn"]
                        contents = [{"name": "reception desk", "type": "furniture"}, {"name": "stairs to rooms", "type": "furniture"}]
                    elif btype == "temple":
                        room_type = "temple"
                        room_name = f"Temple of {rng.choice(['Light', 'Darkness', 'Nature', 'Storm'])} {x},{y}"
                        tags = ["indoors", "temple"]
                        contents = [{"name": "altar", "type": "furniture"}, {"name": "candles", "type": "item"}]
                    elif btype == "guildhall":
                        room_type = "guildhall"
                        room_name = f"{rng.choice(['Mages Guild', 'Thieves Guild', 'Fighters Guild'])} {x},{y}"
                        tags = ["indoors", "guildhall"]
                        contents = [{"name": "training dummy", "type": "item"}, {"name": "notice board", "type": "furniture"}]
                    elif btype == "manor":
                        room_type = "manor"
                        room_name = f"Manor of {rng.choice(['Lord Blackthorn', 'Lady Silverstream'])} {x},{y}"
                        tags = ["indoors", "manor"]
                        contents = [{"name": "grand table", "type": "furniture"}, {"name": "painting", "type": "decoration"}]
                    elif btype == "farm":
                        room_type = "farm"
                        room_name = f"Farmstead {x},{y}"
                        tags = ["outdoors", "farm"]
                        contents = [{"name": "plow", "type": "tool"}, {"name": "hay bale", "type": "item"}]
                    elif btype == "docks":
                        room_type = "docks"
                        room_name = f"Docks {x},{y}"
                        tags = ["outdoors", "docks"]
                        contents = [{"name": "fishing boat", "type": "vehicle"}, {"name": "net", "type": "tool"}]
                    elif btype == "gate":
                        room_type = "gate"
                        room_name = f"{zone_name} Gate"
                        tags = ["outdoors", "gate"]
                        # Add exit to wilderness
                        exits["out"] = "wilderness"
                    else:
                        room_type = "building"
                        room_name = f"Building {x},{y}"
                        tags = ["indoors", "building"]
                        contents = [{"name": "table", "type": "furniture"}]
                else:
                    # Street or plaza
                    if tile_type == "street":
                        room_type = "street"
                        room_name = f"Street {x},{y}"
                        tags = ["outdoors", "street"]
                        contents = [{"name": "cobblestones", "type": "ground"}]
                    elif tile_type == "plaza":
                        room_type = "plaza"
                        room_name = f"{zone_name} Plaza"
                        tags = ["outdoors", "plaza"]
                        contents = [{"name": "statue", "type": "decoration"}]
                    elif tile_type == "wall":
                        room_type = "wall"
                        room_name = f"{zone_name} Wall"
                        tags = ["outdoors", "wall"]
                        contents = [{"name": "stone wall", "type": "structure"}]
                    else:
                        room_type = "alley"
                        room_name = f"Alley {x},{y}"
                        tags = ["outdoors", "alley"]
                        contents = [{"name": "mud", "type": "ground"}]
                
                # Add stairs for multi-floor buildings
                if building and building.get("floors", 1) > 1:
                    if "up" not in exits:
                        exits["up"] = f"r_{x}_{y}_up"
                
                # Create room
                rooms[room_id] = Room(
                    room_id=room_id,
                    name=self._generate_room_name(tile_type, x, y),
                    description=self._generate_room_description(tile_type, zone_name, economy),
                    exits=exits,
                    contents=contents,
                    npcs=npcs,
                    tags=tags,
                )
        
        # Set entry room (town square or main plaza)
        entry_room = "r_15_15"  # Center of 30x30 grid
        if entry_room not in rooms:
            # Find first plaza or street
            for room_id, room in rooms.items():
                if "plaza" in room.tags or "street" in room.tags:
                    entry_room = room_id
                    break
        
        # Create zone
        zone = Zone(
            name=zone_name,
            zone_type="settlement",
            entry_room=entry_room,
            rooms=rooms,
        )
        zones[zone_name] = zone
        
        return zones
    def _generate_room_name(self, room_type: str, x: int, y: int) -> str:
        """Generate a human-readable name for a room based on its type and coordinates."""
        type_names = {
            "plaza": "Town Square", "street": "Street", "alley": "Alleyway",
            "house": "House", "shop": "Shop", "tavern": "Tavern", "inn": "Inn",
            "gate": "City Gate", "tower": "Watchtower", "wall": "City Wall",
            "dungeon_hall": "Dungeon Hall", "dungeon_room": "Dungeon Chamber",
            "basement": "Basement", "attic": "Attic",
        }
        return type_names.get(room_type, room_type.capitalize())

    def _generate_room_description(self, room_type: str, zone_name: str, economy: str) -> str:
        """Generate a description for a room based on its type and zone."""
        return f"A {room_type} in {zone_name}. The town's economy is based on {economy}."
        """Generate NPCs for a room based on its type and zone."""
        from .room import _generate_npcs as generate_npcs_for_room
        rng = random.Random(hash(room_type) + hash(zone_name) + hash(economy))
        
        # Determine biome for NPC names
        biome = "temperate"
        if "farm" in room_type:
            biome = "rural"
        elif "docks" in room_type:
            biome = "coastal"
        
        # Generate NPCs based on room type
        if room_type == "plaza":
            return generate_npcs_for_room("plaza", biome, 3, rng)
        elif room_type == "street":
            return generate_npcs_for_room("street", biome, 2, rng)
        elif room_type == "house":
            return generate_npcs_for_room("house", biome, 1, rng)
        elif room_type == "shop":
            return generate_npcs_for_room("shop", biome, 1, rng) + [{"name": "Shopkeeper", "title": "merchant", "dialog": "Welcome! How can I help you?"}]
        elif room_type == "tavern":
            return generate_npcs_for_room("tavern", biome, 3, rng) + [{"name": "Barkeep", "title": "innkeeper", "dialog": "What'll it be?"}]
        elif room_type == "inn":
            return generate_npcs_for_room("inn", biome, 2, rng) + [{"name": "Innkeeper", "title": "host", "dialog": "Room for the night?"}]
        elif room_type == "temple":
            return generate_npcs_for_room("temple", biome, 2, rng) + [{"name": "Priest", "title": "cleric", "dialog": "Blessings upon you."}]
        elif room_type == "guildhall":
            return generate_npcs_for_room("guildhall", biome, 3, rng) + [{"name": "Guildmaster", "title": "leader", "dialog": "What brings you to the guild?"}]
        elif room_type == "manor":
            return generate_npcs_for_room("manor", biome, 2, rng) + [{"name": "Steward", "title": "manager", "dialog": "The lord is not receiving visitors."}]
        elif room_type == "farm":
            return generate_npcs_for_room("farm", biome, 1, rng)
        elif room_type == "docks":
            return generate_npcs_for_room("docks", biome, 2, rng)
        elif room_type == "gate":
            return generate_npcs_for_room("gate", biome, 2, rng) + [{"name": "Guard", "title": "sentry", "dialog": "Halt! Who goes there?"}]
        else:
            return generate_npcs_for_room(room_type, biome, 1, rng)

        """Generate a description for a room based on its type and zone."""
        rng = random.Random(hash(room_type) + hash(zone_name) + hash(economy))
        
        if room_type == "plaza":
            return (
                f"The heart of {zone_name}, a bustling plaza where traders hawk their wares "
                f"and townsfolk gather. The cobblestones are worn smooth by countless feet. "
                f"{zone_name} has a {economy}-based economy. The air smells of fresh bread, spices, and smoke."
            )
        elif room_type == "street":
            return (
                f"A lively street in {zone_name}. Merchants call out their wares. "
                f"The air smells of fresh bread, spices, and smoke. "
                f"The town has a {economy}-based economy."
            )
        elif room_type == "house":
            return (
                f"A modest house in {zone_name}. The walls are made of timber and plaster. "
                f"A small hearth provides warmth. The town thrives on {economy}."
            )
        elif room_type == "shop":
            return (
                f"A shop in {zone_name}. Shelves line the walls, filled with goods. "
                f"The shopkeeper waits behind the counter. The town's economy is based on {economy}."
            )
        elif room_type == "tavern":
            return (
                f"A warm, smoky tavern in {zone_name}. Patrons drink, laugh, and share stories. "
                f"The barkeep polishes a mug behind the counter. The town thrives on {economy}."
            )
        elif room_type == "inn":
            return (
                f"A cozy inn in {zone_name}. Travelers rest here for the night. "
                f"The reception desk is manned by a friendly innkeeper. The town's economy is based on {economy}."
            )
        elif room_type == "temple":
            return (
                f"A sacred temple in {zone_name}. The air is thick with incense. "
                f"An altar stands at the center. The town thrives on {economy}."
            )
        elif room_type == "guildhall":
            return (
                f"A guildhall in {zone_name}. Members gather here to train and socialize. "
                f"The walls are lined with trophies and notices. The town's economy is based on {economy}."
            )
        elif room_type == "manor":
            return (
                f"A grand manor in {zone_name}. The walls are adorned with tapestries and paintings. "
                f"A grand table dominates the hall. The town thrives on {economy}."
            )
        elif room_type == "farm":
            return (
                f"A farmstead in {zone_name}. Fields stretch out in all directions. "
                f"Tools and produce are scattered about. The town's economy is based on {economy}."
            )
        elif room_type == "docks":
            return (
                f"The docks of {zone_name}. Boats bob in the water, and fishermen mend their nets. "
                f"The air smells of salt and fish. The town thrives on {economy}."
            )
        elif room_type == "gate":
            return (
                f"The {zone_name} gate. Guards stand watch, checking travelers. "
                f"Beyond lies the wilderness. The town's economy is based on {economy}."
            )
        elif room_type == "wall":
            return (
                f"The {zone_name} wall. Stone ramparts rise high, protecting the town. "
                f"The town thrives on {economy}."
            )
        elif room_type == "alley":
            return (
                f"A narrow alley in {zone_name}. The walls are close, and the ground is muddy. "
                f"The town's economy is based on {economy}."
            )
        else:
            return (
                f"A nondescript location in {zone_name}. The town thrives on {economy}."
            )
    def _city_to_zones(self, settlement: dict, cx: int, cy: int, name_override: str | None = None) -> dict[str, Zone]:
        """Convert a WFC city layout into MUD zones and rooms."""
        zones = {}
        zone_name = name_override or settlement["name"]
        economy = settlement.get("economy", "general")
        
        # Parse WFC grid and buildings
        grid = settlement["grid"]
        buildings = settlement.get("buildings", [])
        
        # Create rooms for every WFC tile
        rooms = {}
        rng = random.Random(self.seed + cx * 3001 + cy * 5003)
        
        # Group buildings by type for room generation
        building_map = {}
        for b in buildings:
            bx, by, bw, bh = b
            # Infer building type from WFC code
            # (This is a simplification — real WFC should include type)
            btype = "house"  # Default
            if bx == 15 and by == 1: btype = "gate"
            elif bx == 8 and by == 13: btype = "temple"
            elif bx == 21 and by == 13: btype = "guildhall"
            elif bx < 10: btype = "shop"
            elif bx > 20: btype = "farm"
            building_map[(bx, by)] = {"type": btype, "floors": rng.randint(1, 3)}
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                # Map WFC numeric codes to tile types
                tile_map = {
                    0: "empty",
                    1: "street",
                    2: "plaza",
                    3: "wall",
                    4: "house",
                    5: "shop",
                    6: "tavern",
                    7: "inn",
                    8: "temple",
                    9: "guildhall",
                    10: "manor",
                    11: "farm",
                    12: "docks",
                    13: "gate",
                }
                tile = grid[y][x]
                tile_type = tile_map.get(tile, "alley")
                room_id = f"r_{x}_{y}"
                room_name = f"{x},{y}"
                
                # Determine room type and exits
                exits = {}
                if x > 0: exits["west"] = f"r_{x-1}_{y}"
                if x < len(grid[y]) - 1: exits["east"] = f"r_{x+1}_{y}"
                if y > 0: exits["north"] = f"r_{x}_{y-1}"
                if y < len(grid) - 1: exits["south"] = f"r_{x}_{y+1}"
                
                # Check for building
                building = building_map.get((x, y))
                contents = []
                tags = []
                npcs = []
                if building:
                    btype = building["type"]
                    if btype == "house":
                        room_type = "house"
                        room_name = f"House {x},{y}"
                        tags = ["indoors", "house"]
                        contents = [{"name": "wooden table", "type": "furniture"}, {"name": "straw bed", "type": "furniture"}]
                    elif btype == "shop":
                        room_type = "shop"
                        room_name = f"{rng.choice(['General Store', 'Blacksmith', 'Apothecary', 'Tavern'])} {x},{y}"
                        tags = ["indoors", "shop"]
                        contents = [{"name": "counter", "type": "furniture"}, {"name": "shelves of wares", "type": "item"}]
                    elif btype == "tavern":
                        room_type = "tavern"
                        room_name = f"{rng.choice(['The Prancing Pony', 'The Rusty Nail', 'The Tipsy Griffin'])} {x},{y}"
                        tags = ["indoors", "tavern"]
                        contents = [{"name": "bar", "type": "furniture"}, {"name": "tables and chairs", "type": "furniture"}]
                    elif btype == "inn":
                        room_type = "inn"
                        room_name = f"{rng.choice(['The Sleeping Dragon', 'The Cozy Hearth'])} {x},{y}"
                        tags = ["indoors", "inn"]
                        contents = [{"name": "reception desk", "type": "furniture"}, {"name": "stairs to rooms", "type": "furniture"}]
                    elif btype == "temple":
                        room_type = "temple"
                        room_name = f"Temple of {rng.choice(['Light', 'Darkness', 'Nature', 'Storm'])} {x},{y}"
                        tags = ["indoors", "temple"]
                        contents = [{"name": "altar", "type": "furniture"}, {"name": "candles", "type": "item"}]
                    elif btype == "guildhall":
                        room_type = "guildhall"
                        room_name = f"{rng.choice(['Mages Guild', 'Thieves Guild', 'Fighters Guild'])} {x},{y}"
                        tags = ["indoors", "guildhall"]
                        contents = [{"name": "training dummy", "type": "item"}, {"name": "notice board", "type": "furniture"}]
                    elif btype == "manor":
                        room_type = "manor"
                        room_name = f"Manor of {rng.choice(['Lord Blackthorn', 'Lady Silverstream'])} {x},{y}"
                        tags = ["indoors", "manor"]
                        contents = [{"name": "grand table", "type": "furniture"}, {"name": "painting", "type": "decoration"}]
                    elif btype == "farm":
                        room_type = "farm"
                        room_name = f"Farmstead {x},{y}"
                        tags = ["outdoors", "farm"]
                        contents = [{"name": "plow", "type": "tool"}, {"name": "hay bale", "type": "item"}]
                    elif btype == "docks":
                        room_type = "docks"
                        room_name = f"Docks {x},{y}"
                        tags = ["outdoors", "docks"]
                        contents = [{"name": "fishing boat", "type": "vehicle"}, {"name": "net", "type": "tool"}]
                    elif btype == "gate":
                        room_type = "gate"
                        room_name = f"{zone_name} Gate"
                        tags = ["outdoors", "gate"]
                        # Add exit to wilderness
                        exits["out"] = "wilderness"
                    else:
                        room_type = "building"
                        room_name = f"Building {x},{y}"
                        tags = ["indoors", "building"]
                        contents = [{"name": "table", "type": "furniture"}]
                else:
                    # Street or plaza
                    if tile_type == "street":
                        room_type = "street"
                        room_name = f"Street {x},{y}"
                        tags = ["outdoors", "street"]
                        contents = [{"name": "cobblestones", "type": "ground"}]
                    elif tile_type == "plaza":
                        room_type = "plaza"
                        room_name = f"{zone_name} Plaza"
                        tags = ["outdoors", "plaza"]
                        contents = [{"name": "statue", "type": "decoration"}]
                    elif tile_type == "wall":
                        room_type = "wall"
                        room_name = f"{zone_name} Wall"
                        tags = ["outdoors", "wall"]
                        contents = [{"name": "stone wall", "type": "structure"}]
                    else:
                        room_type = "alley"
                        room_name = f"Alley {x},{y}"
                        tags = ["outdoors", "alley"]
                        contents = [{"name": "mud", "type": "ground"}]
                
                # Add stairs for multi-floor buildings
                if building and building.get("floors", 1) > 1:
                    if "up" not in exits:
                        exits["up"] = f"r_{x}_{y}_up"
                
                # Create room
                rooms[room_id] = Room(
                    room_id=room_id,
                    name=self._generate_room_name(tile_type, x, y),
                    description=self._generate_room_description(tile_type, zone_name, economy),
                    exits=exits,
                    contents=contents,
                    npcs=npcs,
                    tags=tags,
                )
        
        # Set entry room (town square or main plaza)
        entry_room = "r_15_15"  # Center of 30x30 grid
        if entry_room not in rooms:
            # Find first plaza or street
            for room_id, room in rooms.items():
                if "plaza" in room.tags or "street" in room.tags:
                    entry_room = room_id
                    break
        
        # Create zone
        zone = Zone(
            name=zone_name,
            zone_type="settlement",
            entry_room=entry_room,
            rooms=rooms,
        )
        zones[zone_name] = zone
        
        return zones
    def _generate_room_name(self, room_type: str, x: int, y: int) -> str:
        """Generate a human-readable name for a room based on its type and coordinates."""
        # Map room types to human-readable names
        type_names = {
            "plaza": "Town Square",
            "street": "Street",
            "alley": "Alleyway",
            "house": "House",
            "shop": "Shop",
            "tavern": "Tavern",
            "inn": "Inn",
            "gate": "City Gate",
            "tower": "Watchtower",
            "wall": "City Wall",
            "dungeon_hall": "Dungeon Hall",
            "dungeon_room": "Dungeon Chamber",
            "basement": "Basement",
            "attic": "Attic",
        }
        
        base_name = type_names.get(room_type, room_type.capitalize())
