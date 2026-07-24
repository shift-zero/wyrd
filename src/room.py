"""
wyrd — Seed-based room generation system (Phase 26.2).

Each settlement in the world gets procedurally generated rooms based on:
- Settlement size (population)
- Economy type (farming → granary, mining → smithy)
- Region culture (affects room names and descriptions)

Everything is seed-deterministic: same seed → same rooms, always.
"""

import random
from dataclasses import dataclass, field
from collections import namedtuple
from typing import Optional

from .world import World, TERRAIN
from .sim import SettlementSnapshot

# ── Room Data Models ─────────────────────────────────────────────────


@dataclass
class Room:
    """A single room/location within a zone."""
    name: str
    description: str
    exits: dict[str, str]       # direction -> room_id (e.g. {"n": "town_square", "s": "market"})
    contents: list[dict] = field(default_factory=list)  # items on the ground
    npcs: list[dict] = field(default_factory=list)      # NPCs present
    room_id: str = ""
    tags: list[str] = field(default_factory=list)        # e.g. ["indoors", "shop", "tavern"]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "exits": self.exits,
            "contents": self.contents,
            "npcs": self.npcs,
            "room_id": self.room_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        return cls(**data)


@dataclass
class Zone:
    """A collection of rooms — one per settlement, plus wilderness zones."""
    name: str
    rooms: dict[str, Room] = field(default_factory=dict)  # room_id -> Room
    entry_room: str = ""                                   # which room you start in
    zone_type: str = "settlement"                          # "settlement", "wilderness", "dungeon"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rooms": {k: v.to_dict() for k, v in self.rooms.items()},
            "entry_room": self.entry_room,
            "zone_type": self.zone_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Zone":
        zone = cls(name=data["name"], entry_room=data["entry_room"], zone_type=data.get("zone_type", "settlement"))
        zone.rooms = {k: Room.from_dict(v) for k, v in data["rooms"].items()}
        return zone


# ── Common Names for Rooms ──────────────────────────────────────────

ROOM_NAMES_BY_CULTURE = {
    "temperate": {
        "town_square": ["Town Square", "Village Green", "The Crossroads", "The Commons"],
        "tavern": ["The Green Dragon", "The Sleeping Fox", "The Wanderer's Rest", "The Golden Tankard"],
        "market": ["Market Square", "The Trading Post", "The Bazaar", "Merchant's Row"],
        "temple": ["The Chapel of Light", "The Sunlit Shrine", "The Quiet Sanctuary", "The Old Abbey"],
        "leader": ["The Mayor's Hall", "The Elder's House", "The Council Chambers", "Longhouse"],
        "smithy": ["The Iron Anvil", "The Hammer's Fall", "The Forge", "Smith's Workshop"],
        "granary": ["The Grain House", "The Harvest Store", "The Silo", "The Breadbasket"],
        "docks": ["The River Dock", "The Wharf", "The Pier", "The Landing"],
        "guard_post": ["The Watchtower", "The Guardhouse", "The Garrison", "The Watch Post"],
        "library": ["The Archive", "The Scriptorium", "The Library of Records", "The Book Hall"],
        "empty_house": ["Abandoned Cottage", "Derelict Hut", "Ruined House", "Fallow Home"],
    },
    "arid": {
        "town_square": ["The Dust Plaza", "The Sun-Baked Square", "The Oasis Court", "Caravan Circle"],
        "tavern": ["The Thirsty Camel", "The Sand Viper", "The Oasis Taproom", "The Dusty Flagon"],
        "market": ["The Spice Market", "The Silk Bazaar", "The Caravan Exchange", "The Trade Circle"],
        "temple": ["The Sun Temple", "The Shrine of Sands", "The Scorched Altar", "The Desert Monastery"],
        "leader": ["The Khan's Tent", "The Sultan's Court", "The Emir's Palace", "The Council Tent"],
        "smithy": ["The Scorched Anvil", "The Desert Forge", "The Blade-Wright", "The Iron Tent"],
        "granary": ["The Grain Cache", "The Desert Silo", "The Waterless Store", "The Provision Vault"],
        "docks": ["The Salt Wharf", "The Oasis Landing", "The Dry Dock", "The Sand Harbor"],
        "guard_post": ["The Sand Watch", "The Desert Gate", "The Wall Tower", "The Garrison Keep"],
        "library": ["The Sand-Scroll Archive", "The Desert Library", "The Hall of Tablets", "The Scribe's Retreat"],
        "empty_house": ["Sand-Choked Home", "Ruined Hovel", "Abandoned Tent", "Bleak House"],
    },
    "tundra": {
        "town_square": ["The Frost Square", "The Snow Circle", "The Ice Commons", "The Cold Market"],
        "tavern": ["The Frostbite Inn", "The Howling Wolf", "The Snowdrift Tavern", "The Frozen Mug"],
        "market": ["The Ice Market", "The Fur Exchange", "The Cold Trading Post", "The Snow Bazaar"],
        "temple": ["The Ice Chapel", "The Shrine of White", "The Frozen Sanctuary", "The Snow Cathedral"],
        "leader": ["The Chieftain's Longhouse", "The Jarl's Hall", "The Frost-King's Seat", "The Council of Elders"],
        "smithy": ["The Frozen Forge", "The Ice-Hard Anvil", "The Cold Smithy", "The Northern Forge"],
        "granary": ["The Ice Store", "The Frozen Larder", "The Permafrost Cellar", "The Winter Reserve"],
        "docks": ["The Ice Wharf", "The Frozen Landing", "The Cold Harbor", "The Snow Dock"],
        "guard_post": ["The Frost Watch", "The Snow Tower", "The Ice Garrison", "The Northern Gate"],
        "library": ["The Frost-Scribed Archive", "The Rune Hall", "The Saga Library", "The Snow-Scroll Depository"],
        "empty_house": ["Frost-Bitten Hut", "Abandoned Longhouse", "Snow-Buried Home", "Ruined Croft"],
    },
    "tropical": {
        "town_square": ["The Jungle Plaza", "The Canopy Circle", "The Village Green", "The Gathering Grove"],
        "tavern": ["The Parrot's Perch", "The Jungle Tap", "The Canopy Rest", "The Hummingbird Inn"],
        "market": ["The Fruit Market", "The Jungle Bazaar", "The Canopy Exchange", "The Spice Grove"],
        "temple": ["The Leaf-Shrouded Temple", "The Sunken Shrine", "The Jungle Sanctuary", "The Stone Pyramid"],
        "leader": ["The Chief's Hut", "The Longhouse", "The Council Grove", "The Elder's Stilt-House"],
        "smithy": ["The Jungle Forge", "The Green Anvil", "The Iron Leaf", "The Vitae Smithy"],
        "granary": ["The Fruit Store", "The Canopy Silo", "The Harvest Hut", "The Root Cellars"],
        "docks": ["The River Wharf", "The Jungle Landing", "The Canoe Dock", "The Mangrove Pier"],
        "guard_post": ["The Lookout Platform", "The Gate Tower", "The Jungle Watch", "The Thorn Wall"],
        "library": ["The Tree-Scroll Archive", "The Wisdom Hut", "The Leaf Library", "The Story Grove"],
        "empty_house": ["Vine-Choked Hut", "Ruined Stilt-House", "Jungle-Covered Home", "Abandoned Croft"],
    },
}

# Default (falls back to these if culture not found)
ROOM_NAMES_DEFAULT = ROOM_NAMES_BY_CULTURE["temperate"]


# ── Room Description Templates ──────────────────────────────────────

ROOM_DESCRIPTIONS = {
    "town_square": [
        "The heart of {settlement}, where cobblestones bear the marks of countless feet. {extra}",
        "A broad open space at the center of {settlement}. {extra}",
        "The gathering place of {settlement}, surrounded by the everyday bustle of life. {extra}",
    ],
    "tavern": [
        "Warm firelight spills from the hearth as travelers and locals share tales over foaming mugs. The air smells of roasted meat and spilled ale. {extra}",
        "A sturdy building with a creaking sign, filled with the low murmur of conversation and the clink of tankards. {extra}",
        "The common room is packed with rough-hewn tables. A bard tunes a lute in the corner while the innkeeper wipes down the bar. {extra}",
    ],
    "market": [
        "Stalls line the square, heaped with goods from near and far. Vendors call out their wares, haggling with passersby. {extra}",
        "The air is thick with the scents of spices, fresh bread, and leather. Merchants display their finest goods on colorful cloths. {extra}",
        "A lively trading post where barter and coin change hands. Everything from farm tools to fine silks can be found here. {extra}",
    ],
    "temple": [
        "Sunlight streams through high windows, illuminating dust motes dancing above worn pews. The smell of incense lingers. {extra}",
        "A quiet place of worship, its walls adorned with faded murals depicting scenes of divine intervention. {extra}",
        "The altar stands at the far end, draped in cloth of gold. Candles flicker in the stillness. {extra}",
    ],
    "leader": [
        "The seat of {settlement}'s governance. Maps and ledgers cover a heavy oak table, evidence of the burdens of leadership. {extra}",
        "A sturdy building that serves as both home and office for {settlement}'s leader. The walls are lined with decrees and records. {extra}",
        "The largest building in {settlement}, its great hall used for councils, judgments, and celebrations. {extra}",
    ],
    "smithy": [
        "The ring of hammer on anvil echoes through the workshop. Sparks fly as the smith shapes glowing metal with practiced skill. {extra}",
        "Heat washes over you as you enter. Tools hang from every wall, and a half-finished blade rests in the forge. {extra}",
    ],
    "granary": [
        "Sacks of grain are stacked high, the fruits of the harvest stored against leaner times. The air is dusty and warm. {extra}",
        "A stout building built to keep the harvest safe from rot and vermin. The smell of dry straw fills the air. {extra}",
    ],
    "docks": [
        "The smell of saltwater and tar fills the air. Boats bob at their moorings, and fishermen mend their nets on the pier. {extra}",
        "Wooden planks creak underfoot as you walk along the wharf. Cargo is being unloaded from a recently arrived vessel. {extra}",
    ],
    "guard_post": [
        "Armed men and women keep watch from this post, their armor gleaming in the light. A captain barks orders at a fresh patrol. {extra}",
        "The guard post is a hub of military readiness. Weapons racks line the walls, and a watch roster hangs by the door. {extra}",
    ],
    "library": [
        "Shelves upon shelves of scrolls and codices fill this hall of learning. Scholars hunch over desks, lost in study. {extra}",
        "The quiet is profound here, broken only by the rustle of parchment and the scratch of quills. Centuries of knowledge line the walls. {extra}",
    ],
    "empty_house": [
        "Dust and shadows fill this abandoned dwelling. A broken chair lies overturned, and cobwebs drape the empty hearth. {extra}",
        "This building has been empty for some time. The roof sags in places, and wind whistles through gaps in the walls. {extra}",
        "The former inhabitants left in haste — a child's doll lies forgotten in a corner, and the door hangs askew. {extra}",
    ],
}


# ── Wilderness Terrain Descriptions ─────────────────────────────────

WILDERNESS_DESCRIPTIONS = {
    "deep_water": [
        "Endless blue stretches to the horizon. Waves roll beneath a grey sky.",
        "The deep waters are dark and cold. Swells rise and fall with ancient rhythm.",
        "Open ocean — no land in sight. The water is a deep, dark blue.",
    ],
    "shallow": [
        "The water is clear enough to see the sandy bottom below. Small fish dart between rocks.",
        "Shallow waters with a gentle current. The coastline is visible nearby.",
    ],
    "sand": [
        "A sandy beach stretches along the water's edge. Driftwood and shells dot the shore.",
        "Fine golden sand meets the water. The wind carries a salty tang.",
        "Warm sand underfoot, the sound of gentle waves nearby. A peaceful stretch of coastline.",
    ],
    "grass": [
        "Rolling grasslands stretch as far as the eye can see, swaying in the breeze.",
        "Golden-green grass covers the landscape, punctuated by the occasional wildflower.",
        "A sea of grass, rippling like water under the wind. The horizon is a clean line.",
    ],
    "forest": [
        "Ancient trees tower overhead, their canopy filtering the sunlight into dappled patterns on the forest floor.",
        "The woods are alive with birdsong and rustling leaves. A narrow trail winds between mossy trunks.",
        "Deep forest surrounds you. The air is cool and smells of earth and growing things.",
    ],
    "hills": [
        "Gentle rolls of green rise and fall around you. The path winds between grassy slopes.",
        "Hills stretch in every direction, their rounded backs carpeted in green and gold.",
    ],
    "mountains": [
        "Towering peaks rise before you, their slopes dotted with hardy pines and tumbled rock.",
        "The air is thin and cold. Jagged peaks cut into the sky, their shoulders cloaked in snow.",
        "A rocky path ascends into the mountains. The wind howls through narrow passes.",
    ],
    "snow": [
        "An expanse of pure white stretches in all directions. The cold bites at exposed skin.",
        "Snow-covered peaks rise in silent majesty. Nothing moves but the wind-scoured snow.",
    ],
    "river": [
        "A river flows swiftly beside the path, its waters clear and cold. The current murmurs over smooth stones.",
        "The river bends around a rocky outcrop, forming a small pool where fish can be seen circling.",
    ],
    "swamp": [
        "Murky water and twisted roots create a labyrinth of islands and channels. The air is thick with the smell of decay.",
        "Mist hangs low over the swamp. Strange sounds echo from the gloom between gnarled trees.",
        "The ground squelches underfoot. Dragonflies hover over stagnant pools thick with algae.",
    ],
    "desert": [
        "Endless dunes of golden sand stretch to the horizon, sculpted by the wind into graceful curves.",
        "The heat shimmers off the sand. Not a cloud in the sky — just the unrelenting sun.",
        "A vast arid waste of rock and sand. A lone cactus stands sentinel against the blazing sky.",
    ],
}


# ── Room Contents Generation ────────────────────────────────────────

CONTENT_POOL = {
    "town_square": [
        {"type": "fountain", "name": "stone fountain"},
        {"type": "notice_board", "name": "notice board"},
        {"type": "bench", "name": "wooden bench"},
        {"type": "statue", "name": "weathered statue"},
    ],
    "tavern": [
        {"type": "barrel", "name": "barrel of ale"},
        {"type": "table", "name": "oak table"},
        {"type": "hearth", "name": "roaring hearth"},
        {"type": "board_game", "name": "well-worn game board"},
    ],
    "market": [
        {"type": "crate", "name": "stack of crates"},
        {"type": "scales", "name": "merchant's scales"},
        {"type": "fabric", "name": "colorful fabric bolts"},
        {"type": "pottery", "name": "painted pottery"},
    ],
    "temple": [
        {"type": "altar", "name": "stone altar"},
        {"type": "candle", "name": "votive candle rack"},
        {"type": "offering", "name": "offering bowl"},
        {"type": "holy_symbol", "name": "carved holy symbol"},
    ],
    "leader": [
        {"type": "throne", "name": "leader's chair"},
        {"type": "map", "name": "large map of the region"},
        {"type": "ledger", "name": "leather-bound ledger"},
        {"type": "seal", "name": "official seal"},
    ],
    "smithy": [
        {"type": "anvil", "name": "heavy iron anvil"},
        {"type": "forge", "name": "glowing forge"},
        {"type": "tools", "name": "smithing tools"},
        {"type": "weapon_rack", "name": "weapon rack"},
    ],
    "granary": [
        {"type": "sack", "name": "sack of grain"},
        {"type": "scales", "name": "weighing scales"},
        {"type": "barrel", "name": "barrel of salted meat"},
    ],
    "docks": [
        {"type": "anchor", "name": "rusted anchor"},
        {"type": "net", "name": "fishing net"},
        {"type": "rope", "name": "coiled rope"},
        {"type": "crate", "name": "waterproof crate"},
    ],
    "guard_post": [
        {"type": "weapon_rack", "name": "weapon rack"},
        {"type": "armor", "name": "spare armor stand"},
        {"type": "torch", "name": "wall torch"},
        {"type": "signal_horn", "name": "signal horn"},
    ],
    "library": [
        {"type": "bookshelf", "name": "tall bookshelf"},
        {"type": "desk", "name": "reading desk"},
        {"type": "lectern", "name": "ornate lectern"},
        {"type": "scroll", "name": "stack of scrolls"},
    ],
}


# ── NPC Generation ──────────────────────────────────────────────────

NPC_NAME_POOLS = {
    "temperate": [
        "Aldric", "Beorn", "Cedric", "Doran", "Eldon",
        "Finn", "Gareth", "Hakon", "Ivar", "Kael",
        "Elara", "Freya", "Greta", "Hilda", "Ingrid",
        "Mira", "Nora", "Runa", "Saga", "Tova",
    ],
    "arid": [
        "Amir", "Basil", "Darius", "Farid", "Jamil",
        "Karim", "Malik", "Nasir", "Rashid", "Zahir",
        "Aisha", "Fatima", "Jalila", "Khadija", "Layla",
        "Nadia", "Rashida", "Samira", "Zahra", "Zainab",
    ],
    "tundra": [
        "Bjorn", "Erik", "Gunnar", "Halfdan", "Ivar",
        "Leif", "Olaf", "Ragnar", "Sigurd", "Torsten",
        "Astrid", "Freydis", "Gudrun", "Helga", "Kara",
        "Liv", "Sigrid", "Solveig", "Thyra", "Ulla",
    ],
    "tropical": [
        "Ari", "Batu", "Chandra", "Dewi", "Gajah",
        "Kadek", "Laksmi", "Maya", "Naga", "Putra",
        "Ratna", "Sari", "Surya", "Wayan", "Yani",
        "Anak", "Bayu", "Cinta", "Dayu", "Gita",
    ],
}

NPC_TITLES = {
    "town_square": ["town crier", "street sweeper", "loiterer", "courier", "herald"],
    "tavern": ["innkeeper", "barmaid", "bard", "patron", "drunken farmer", "traveling merchant"],
    "market": ["merchant", "vendor", "haggler", "scales-keeper", "appraiser", "shopper"],
    "temple": ["priest", "acolyte", "pilgrim", "monk", "devotee", "novice"],
    "leader": ["mayor", "clerk", "page", "advisor", "messenger", "steward"],
    "smithy": ["blacksmith", "apprentice", "armorer", "farrier", "iron-monger"],
    "granary": ["storekeeper", "miller", "baker", "grader"],
    "docks": ["fisherman", "dockhand", "shipwright", "sailor", "harbomaster"],
    "guard_post": ["guard", "captain", "watchman", "sentry", "sergeant"],
    "library": ["scribe", "scholar", "loremaster", "archivist", "sage", "student"],
    "empty_house": [],
}

NPC_SURNAMES = [
    "Blackthorn", "Ironhand", "Stonehelm", "Windwalker", "Oakheart",
    "Ravenwood", "Silverstream", "Thornfield", "Goldmire", "Stormbringer",
    "Ashford", "Briarwood", "Copperfield", "Dustmoor", "Ebonhart",
    "Flintlock", "Greymantle", "Holloway", "Ironwood", "Jadevale",
]


# ── Zone Type Determination ─────────────────────────────────────────

# Map terrain to room types for wilderness description
TERRAIN_TAGS: dict[str, list[str]] = {
    "grass": ["open", "fields"],
    "forest": ["wooded", "dense"],
    "hills": ["elevated", "rolling"],
    "mountains": ["high", "rocky", "cold"],
    "swamp": ["wet", "marshy", "fetid"],
    "desert": ["arid", "dry", "hot"],
    "sand": ["coastal", "warm"],
    "tundra": ["cold", "barren"],
    "snow": ["cold", "icy", "treacherous"],
    "river": ["water", "flowing"],
    "deep_water": ["water", "deep"],
    "shallow": ["water", "coastal"],
}


# ── Room Generation Logic ───────────────────────────────────────────


def _determine_room_types(
    settlement_population: int,
    economy_type: str | None,
    biome: str,
    has_region_religion: bool,
    has_scholarly_era: bool,
    rng: random.Random,
) -> list[str]:
    """Determine which room types a settlement should have, based on its attributes.

    Always: town_square, tavern, market, leader
    Conditional: temple, smithy, granary, docks, guard_post, library, empty_house
    """
    room_types = ["town_square", "tavern", "market", "leader"]

    # Determine size-based room count
    if settlement_population < 200:
        # Small (hamlet): 3-5 total rooms
        count = rng.randint(2, 3)  # additional rooms beyond the 4 core
    elif settlement_population < 800:
        # Medium (village): 5-8 rooms
        count = rng.randint(1, 4)
    elif settlement_population < 2000:
        # Large (town): 8-10 rooms
        count = rng.randint(4, 6)
    else:
        # City: 10-12 rooms
        count = rng.randint(6, 8)

    # Pool of optional rooms
    optional_rooms = []

    # Temple — if region has religion
    if has_region_religion:
        optional_rooms.append("temple")

    # Smithy — if mining economy or large population
    if economy_type == "mining" or settlement_population >= 500:
        optional_rooms.append("smithy")

    # Granary — if farming economy
    if economy_type == "farming":
        optional_rooms.append("granary")

    # Docks — coastal settlements
    if economy_type == "fishing":
        optional_rooms.append("docks")

    # Guard post — large pop or aggressive culture
    if settlement_population >= 400:
        optional_rooms.append("guard_post")

    # Library — if scholarly era occurred
    if has_scholarly_era and settlement_population >= 200:
        optional_rooms.append("library")

    # Empty houses — abandoned settlements or sim decay
    if settlement_population < 100:
        optional_rooms.append("empty_house")

    # Add more randomness for variety
    extra_pool = ["smithy", "guard_post", "temple", "empty_house"]
    rng.shuffle(extra_pool)

    # Fill up to count with a mix of guaranteed and random extras
    selected = list(room_types)  # always have the core 4
    rng.shuffle(optional_rooms)

    # Take from optional first, then random pool
    selected.extend(optional_rooms[:max(0, count)])

    if len(selected) - 4 < count:
        remaining = count - (len(selected) - 4)
        for rtype in extra_pool:
            if rtype not in selected and remaining > 0:
                selected.append(rtype)
                remaining -= 1

    # Ensure we don't exceed reasonable count
    if len(selected) > 12:
        selected = selected[:12]

    return selected


def _build_room_name(room_type: str, biome: str, settlement_name: str, rng: random.Random) -> str:
    """Generate a room name based on its type, biome, and settlement."""
    culture_names = ROOM_NAMES_BY_CULTURE.get(biome, ROOM_NAMES_DEFAULT)
    options = culture_names.get(room_type, [f"{room_type.replace('_', ' ').title()}"])
    return rng.choice(options)


def _build_room_description(
    room_type: str,
    settlement_name: str,
    settlement_population: int,
    economy_type: str | None,
    biome: str,
    rng: random.Random,
) -> str:
    """Generate a room description with contextual flavor."""
    templates = ROOM_DESCRIPTIONS.get(room_type, ["{extra}"])
    template = rng.choice(templates)

    # Generate extra flavor based on settlement attributes
    extras = []

    if settlement_population > 500:
        extras.append("The thrum of a thriving community is palpable.")
    elif settlement_population < 50:
        extras.append("A quiet stillness hangs in the air — this place has seen better days.")

    if economy_type == "farming":
        extras.append("The scent of fresh hay and earth drifts in from nearby fields.")
    elif economy_type == "mining":
        extras.append("Distant echoes of pickaxes on stone remind you of the settlement's purpose.")
    elif economy_type == "fishing":
        extras.append("A faint salt breeze finds its way here, carrying the cry of gulls.")
    elif economy_type == "trading":
        extras.append("Merchants and their laden pack animals pass through with purpose.")

    if biome == "arid":
        extras.append("The relentless sun beats down, baking the ground to a pale gold.")
    elif biome == "tundra":
        extras.append("A biting cold seeps through every crack and crevice.")
    elif biome == "tropical":
        extras.append("Humidity wraps around you like a warm blanket, rich with the smell of foliage.")
    elif biome == "temperate":
        extras.append("A gentle breeze carries the scent of wildflowers and turned earth.")

    if not extras:
        extras.append("Life continues its steady rhythm here.")

    extra = rng.choice(extras)

    desc = template.replace("{settlement}", settlement_name).replace("{extra}", extra)
    return desc


def _generate_room_contents(room_type: str, rng: random.Random, zone_name: str) -> list[dict]:
    """Generate items that may be in a room."""
    pool = CONTENT_POOL.get(room_type, [])
    if not pool:
        return []

    # 50% chance of having 1-2 contents
    if rng.random() < 0.5:
        n = rng.randint(1, min(2, len(pool)))
        selected = rng.sample(pool, n)
        return [dict(item) for item in selected]
    return []


def _generate_npcs(room_type: str, biome: str, rng: random.Random, is_abandoned: bool = False) -> list[dict]:
    """Generate NPCs present in a room."""
    if is_abandoned:
        return []

    titles = NPC_TITLES.get(room_type, [])
    if not titles:
        return []

    # 40% chance of having 1-2 NPCs
    if rng.random() < 0.4:
        n = rng.randint(1, min(2, len(titles)))
        selected_titles = rng.sample(titles, n) if n <= len(titles) else titles[:n]

        npcs = []
        name_pool = NPC_NAME_POOLS.get(biome, NPC_NAME_POOLS["temperate"])
        surname = rng.choice(NPC_SURNAMES)

        for title in selected_titles:
            first_name = rng.choice(name_pool)
            npcs.append({
                "name": f"{first_name} {surname}",
                "title": title,
                "role": room_type,
                "dialog": _generate_dialog(title, rng),
            })
        return npcs
    return []


def _generate_dialog(title: str, rng: random.Random) -> str:
    """Generate a bit of dialog for an NPC."""
    dialog_pool = [
        "Greetings, traveler. What brings you here?",
        "A fine day for business, wouldn't you say?",
        "You look like you've traveled far. Rest a while.",
        "If you need anything, just ask.",
        "The world beyond these walls is dangerous. Be careful.",
        "News travels slowly here. What word from the outside?",
        "I've lived here all my life. Seen it change, I have.",
        "There's talk of strange happenings in the wilderness.",
        "Mind your purse — there are those who'd lighten it for you.",
        "The ale's good and the company's better. Sit awhile.",
    ]
    return rng.choice(dialog_pool)


def _build_exit_graph(
    room_types: list[str],
    room_ids: list[str],
    rng: random.Random,
    has_wilderness: bool = True,
) -> dict[str, dict[str, str]]:
    """Build a coherent room graph. Town square is the hub.

    Returns dict[room_id, dict[direction, target_room_id]]
    """
    exits: dict[str, dict[str, str]] = {}

    # Town square is always first — it's the hub
    hub_id = room_ids[0]
    exits[hub_id] = {}

    # Connect town square to all other rooms (hub-and-spoke)
    for rid in room_ids[1:]:
        direction = rng.choice(["n", "s", "e", "w"])
        exits[hub_id][direction] = rid
        exits[rid] = {"s" if direction == "n" else "n" if direction == "s" else "w" if direction == "e" else "e": hub_id}

    # Add some side connections: 20% chance for rooms to connect to each other
    side_rooms = room_ids[1:]
    if len(side_rooms) >= 2:
        # Try 1-2 additional connections
        num_extra = rng.randint(1, min(2, len(side_rooms) - 1))
        for _ in range(num_extra):
            r1, r2 = rng.sample(side_rooms, 2)
            # Only add if not already connected
            if r2 not in exits.get(r1, {}):
                direction = rng.choice(["n", "s", "e", "w"])
                # Make sure we're not overwriting an existing exit
                while direction in exits.get(r1, {}):
                    direction = rng.choice(["n", "s", "e", "w"])
                exits[r1][direction] = r2
                exits[r2][{"n": "s", "s": "n", "e": "w", "w": "e"}[direction]] = r1

    # Add wilderness exit from town square (exit the settlement)
    if has_wilderness:
        wilderness_dir = rng.choice(["n", "s", "e", "w"])
        # Make sure it doesn't conflict
        while wilderness_dir in exits[hub_id]:
            wilderness_dir = rng.choice(["n", "s", "e", "w"])
        exits[hub_id][wilderness_dir] = "wilderness"

    return exits


def _get_biome_for_settlement(world: World, settlement_name: str, settlement_x: int, settlement_y: int) -> str:
    """Determine the biome/culture for a settlement based on its region."""
    for region in world.regions:
        for s in region.settlements:
            if s.name.lower() == settlement_name.lower():
                return region.biome
    # Fallback: look at terrain
    if 0 <= settlement_y < len(world.terrain) and 0 <= settlement_x < len(world.terrain[0]):
        t = world.terrain[settlement_y][settlement_x]
        biome_map = {
            "grass": "temperate", "forest": "temperate", "hills": "temperate",
            "mountains": "tundra", "snow": "tundra",
            "desert": "arid", "sand": "arid",
            "swamp": "tropical", "river": "temperate",
            "deep_water": "temperate", "shallow": "temperate",
        }
        return biome_map.get(t, "temperate")
    return "temperate"


def _has_religion_in_region(world: World, region_name: str) -> bool:
    """Check if a region has an active religion."""
    if world.pantheon:
        # Check if any deity's seat or influence matches this region
        for deity in world.pantheon.deities:
            if region_name.lower() in deity.domains or region_name.lower() in deity.seat_of_power.lower():
                return True
    return False


def _has_scholarly_era(chronicles) -> bool:
    """Check if chronicles contain a scholarly/age_of era type."""
    if chronicles is None:
        return False
    for era in getattr(chronicles, "eras", []):
        if era.era_type == "age_of" and any(
            word in str(era.name).lower() for word in ["wisdom", "knowledge", "scroll", "lore", "scholar"]
        ):
            return True
    return False


def _settlement_is_abandoned(world: World, settlement_name: str, sim_state=None) -> bool:
    """Check if a settlement has been abandoned in the simulation."""
    if sim_state is None:
        return False
    snap = sim_state.settlements.get(settlement_name)
    if snap is None:
        return False
    return not snap.is_active


# ── Public API ──────────────────────────────────────────────────────


def generate_zones(
    world: World,
    seed: int,
    sim_state=None,
) -> dict[str, Zone]:
    """Generate room zones for all settlements in the world.

    Args:
        world: The generated World object.
        seed: World seed (used for deterministic room generation).
        sim_state: Optional SimState for checking abandonment/prosperity.

    Returns:
        dict[str, Zone]: Mapping of settlement name -> Zone.
    """
    zones: dict[str, Zone] = {}
    rng = random.Random(seed + 1000000)  # Offset seed so rooms don't match world

    for region in world.regions:
        biome = region.biome
        has_religion = _has_religion_in_region(world, region.name)
        has_scholarly = _has_scholarly_era(world.chronicles)

        for settlement in region.settlements:
            zone_name = settlement.name
            zone_rng = random.Random(seed + hash(zone_name) % (2**31))

            # Get settlement sim state for economy type and abandonment
            economy_type = None
            is_abandoned = False
            if sim_state and zone_name in sim_state.settlements:
                snap = sim_state.settlements[zone_name]
                economy_type = snap.economy_type
                is_abandoned = not snap.is_active

            # Check terrain for coastal fishing if no economy assigned
            if economy_type is None:
                if _is_near_water(world, settlement.x, settlement.y):
                    economy_type = "fishing"
                else:
                    # Fallback based on terrain
                    t = world.terrain[settlement.y][settlement.x] if (
                        0 <= settlement.y < len(world.terrain)
                        and 0 <= settlement.x < len(world.terrain[0])
                    ) else "grass"
                    if t in ("grass", "forest"):
                        economy_type = "farming"
                    elif t in ("hills", "mountains"):
                        economy_type = "mining"
                    else:
                        economy_type = "trading"

            # Determine room types
            room_types = _determine_room_types(
                settlement.population,
                economy_type,
                biome,
                has_religion,
                has_scholarly,
                zone_rng,
            )

            # Generate rooms
            rooms: dict[str, Room] = {}
            room_ids: list[str] = []

            for i, rtype in enumerate(room_types):
                rid = f"{zone_name.lower()}_{rtype}" if i > 0 else f"{zone_name.lower()}_square"
                if i == 0:
                    rid = f"{zone_name.lower()}_square"
                elif rid in rooms:
                    rid = f"{zone_name.lower()}_{rtype}_{i}"

                room_ids.append(rid)

                room_name = _build_room_name(rtype, biome, settlement.name, zone_rng)
                room_desc = _build_room_description(
                    rtype, settlement.name, settlement.population, economy_type, biome, zone_rng
                )

                room = Room(
                    name=room_name,
                    description=room_desc,
                    exits={},
                    contents=_generate_room_contents(rtype, zone_rng, settlement.name),
                    npcs=_generate_npcs(rtype, biome, zone_rng, is_abandoned),
                    room_id=rid,
                    tags=[rtype, biome, "indoors" if rtype != "town_square" else "outdoors"],
                )
                rooms[rid] = room

            # Build exit graph
            has_wild = True
            exit_graph = _build_exit_graph(room_types, room_ids, zone_rng, has_wild)

            # Apply exits to rooms
            for rid, exit_dict in exit_graph.items():
                if rid in rooms:
                    rooms[rid].exits = exit_dict

            # Override "wilderness" exit direction to point to a special exit marker
            hub_id = room_ids[0]
            # Find the wilderness exit and tag it properly
            for direction, target in list(rooms[hub_id].exits.items()):
                if target == "wilderness":
                    rooms[hub_id].exits[direction] = f"{zone_name.lower()}_to_wilderness"
                    break

            zone = Zone(
                name=zone_name,
                rooms=rooms,
                entry_room=room_ids[0],
                zone_type="settlement",
            )
            zones[zone_name] = zone

    return zones


def generate_wilderness_zone(world: World, seed: int) -> Zone:
    """Generate a wilderness zone based on the world's terrain grid.

    Each terrain tile has a description based on its type.
    """
    rng = random.Random(seed + 2000000)
    zone = Zone(name="Wilderness", zone_type="wilderness")

    # We don't generate all tiles — just provide a way to describe any tile
    # The wilderness zone has a "wilderness" room that dynamically describes the area
    room = Room(
        name="Wilderness",
        description="The wild lands stretch before you.",
        exits={},
        room_id="wilderness",
        tags=["outdoors", "wilderness"],
    )
    zone.rooms["wilderness"] = room
    zone.entry_room = "wilderness"
    return zone


def get_wilderness_description(terrain_type: str, rng: random.Random) -> str:
    """Get a description for a wilderness terrain type."""
    templates = WILDERNESS_DESCRIPTIONS.get(terrain_type, ["Unknown terrain."])
    return rng.choice(templates)


def describe_terrain(terrain_type: str, rng_seed: int) -> str:
    """Get a deterministic description for a terrain type."""
    rng = random.Random(rng_seed)
    return get_wilderness_description(terrain_type, rng)


def _is_near_water(world: World, x: int, y: int, radius: int = 3) -> bool:
    """Check if a tile is near water (for coastal detection)."""
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = x + dx, y + dy
            if 0 <= ny < world.height and 0 <= nx < world.width:
                if world.terrain[ny][nx] in ("deep_water", "shallow"):
                    return True
    return False


# ── CommandResult for MUD command handler ──────────────────────────

CommandResult = namedtuple('CommandResult', ['output', 'new_room', 'char_changed', 'events'])
