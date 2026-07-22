"""
wyrd — Adventure Zone Generation (Phase 10).

Places points of interest across the world map — dungeons, caves, ruins,
towers, groves, lairs, shrines, and mines — with descriptions, inhabitants,
difficulty ratings, and quest hooks.

Usage:
    wyrd zones --seed 42              # List all adventure zones on the map
    wyrd zones --seed 42 --detail     # Full descriptions for each zone
"""

import random
from .world import World, AdventureZone, ADVENTURE_ZONE_TYPES, ADVENTURE_DIFFICULTIES

# ── Zone Names ───────────────────────────────────────────────────────

DUNGEON_NAMES = [
    "Tomb of the {adj} King", "Caverns of {noun}", "The {adj} Depths",
    "Pits of {noun}", "The {adj} Labyrinth", "Halls of the {adj} One",
    "The Sunless {noun}", "Catacombs of {noun}", "The {adj} Warren",
    "Crypt of the {adj} Serpent", "Vaults of {noun}",
    "The {adj} Maw", "Darkness of {noun}",
]

CAVE_NAMES = [
    "The {adj} Cavern", "{noun}'s Grotto", "Crystal Cave of {noun}",
    "The Echoing Depths", "{adj} Hollow", "The Singing Cave",
    "Bat Caverns of {noun}", "The {adj} Chasm",
]

RUIN_NAMES = [
    "Ruins of {noun}", "The {adj} Remains", "Fallen {noun}",
    "Shattered {noun} Tower", "The {adj} Foundations",
    "Lost City of {noun}", "Crumbled {noun}",
]

TOWER_NAMES = [
    "Tower of the {adj} {noun}", "{noun}'s Spire",
    "The {adj} Watchtower", "Ivory Tower of {noun}",
    "The {adj} Observatory",
]

GROVE_NAMES = [
    "The {adj} Grove", "{noun}'s Sanctuary",
    "Whispering {noun}", "The {adj} Thicket",
    "Grove of the {adj} Spirit",
]

LAIR_NAMES = [
    "The {adj} Den", "{noun}'s Lair",
    "Nest of the {adj} Beast", "The {adj} Warren",
    "Lair of the {adj} Serpent",
]

SHRINE_NAMES = [
    "Shrine of the {adj} {noun}", "{noun}'s Altar",
    "The {adj} Sanctum", "Temple of the {adj} One",
    "The {adj} Offering",
]

MINE_NAMES = [
    "The {adj} Mines", "{noun}'s Dig",
    "Deep {noun} Excavation", "The {adj} Quarry",
    "Abandoned {noun} Works",
]

ZONE_NAMES = {
    "dungeon": DUNGEON_NAMES,
    "cave": CAVE_NAMES,
    "ruin": RUIN_NAMES,
    "tower": TOWER_NAMES,
    "grove": GROVE_NAMES,
    "lair": LAIR_NAMES,
    "shrine": SHRINE_NAMES,
    "mine": MINE_NAMES,
}

ZONE_ADJECTIVES = [
    "Ancient", "Forgotten", "Cursed", "Sunken", "Hidden",
    "Burning", "Frozen", "Emerald", "Crimson", "Shadow",
    "Silver", "Golden", "Dark", "Lost", "Shattered",
    "Eternal", "Silent", "Bleak", "Glimmering", "Ashen",
    "Verdant", "Empty", "Wailing", "Black", "White",
]

ZONE_NOUNS = [
    "Sorrow", "Ashes", "Thorns", "Bones", "Mist",
    "Winter", "Thunder", "Obsidian", "Copper", "Salt",
    "Marble", "Iron", "Crystal", "Ember", "Frost",
    "Star", "Moon", "Sun", "Storm", "Shadow",
]

# ── Inhabitant Descriptions ──────────────────────────────────────────

INHABITANTS = {
    "dungeon": [
        "Undead guardians raised centuries ago",
        "Deep-dwelling troglodytes and their war beasts",
        "Cultists performing forbidden rites",
        "Elemental creatures bound to the deep earth",
        "Mind flayer colony in the lower levels",
    ],
    "cave": [
        "Colony of giant bats and blind cave fish",
        "Troll lair — stench of old kills",
        "Fungal grove with aggressive spore clouds",
        "Bear den — mother with cubs",
        "Deep one worshipers from the sunless sea",
    ],
    "ruin": [
        "Bandits using the ruins as a hideout",
        "Ghosts of the original inhabitants",
        "Goblin scavengers picking through old bones",
        "Nest of giant spiders in the collapsed hall",
        "Hermit scholar studying ancient inscriptions",
    ],
    "tower": [
        "Reclusive wizard with questionable ethics",
        "Haunted by the spirit of its former master",
        "Occupied by a coven of hags",
        "Abandoned — but the wards still hold",
        "Observatory used by astral diviners",
    ],
    "grove": [
        "Dryads and treants protecting sacred ground",
        "Fey creatures dancing under moonlight",
        "Druidic circle tending ancient growth",
        "Corrupted — blighted plants and twisted animals",
        "Sacred to local spirits — offerings left regularly",
    ],
    "lair": [
        "Mated pair of wyverns guarding a clutch of eggs",
        "Basilisk — its gaze turns prey to stone",
        "Pack of displacer beasts hunting the region",
        "Young dragon hoarding treasure and secrets",
        "Chimera — three heads, three hungers",
    ],
    "shrine": [
        "Order of monks maintaining eternal vigil",
        "Pilgrims travelling to pay homage",
        "Oracular entity speaking in riddles",
        "Abandoned — the god has fallen silent",
        "Sacred spring with healing properties",
    ],
    "mine": [
        "Deranged miner king and his followers",
        "Earth elemental unleashed by deep digging",
        "Collapsed tunnels — treasure buried within",
        "Crystal golems defending the vein",
        "Mind-altering ore drives miners mad",
    ],
}

# ── Descriptions ─────────────────────────────────────────────────────

DESCRIPTIONS = {
    "dungeon": [
        "Entrance hidden beneath a weathered stone slab, worn runes marking the threshold.",
        "A yawning stairwell descends into perfect darkness, cold air rising from below.",
        "Iron gates, rusted but still sturdy, bar the entrance to the underground complex.",
        "Carved directly into the cliff face, the tunnel mouth is flanked by weathered statues.",
    ],
    "cave": [
        "Water drips from the ceiling, echoing through a cavern filled with glittering stalactites.",
        "The cave mouth is half-hidden by creeping vines and moss-covered boulders.",
        "A narrow crack in the rock leads to a vast underground chamber lit by bioluminescent fungi.",
        "The cave opens into a cathedral-like space with a sunken pool at its centre.",
    ],
    "ruin": [
        "Walls of faded stone rise from the undergrowth, roofs long since collapsed.",
        "A single crumbling archway marks what was once a grand entrance.",
        "Weathered pillars stand like skeletal fingers against the sky.",
        "Foundations overgrown with moss, the old road still faintly visible.",
    ],
    "tower": [
        "A slender spire rises against the sky, its peak lost in low cloud.",
        "The tower leans slightly, as if weary from centuries of wind.",
        "Faint light flickers in the uppermost window — someone or something is home.",
        "Cracks spiderweb up the stonework, but the structure remains sound.",
    ],
    "grove": [
        "Ancient oaks form a natural cathedral, sunlight filtering through dense canopy.",
        "Flowers of every colour carpet the forest floor, filling the air with perfume.",
        "A circle of standing stones surrounds a pool of impossibly clear water.",
        "The trees here are older than any settlement — their trunks wider than houses.",
    ],
    "lair": [
        "The ground is littered with bones and fragments of armour — old meals.",
        "A powerful musky scent hangs in the air, marking territorial boundaries.",
        "Scratch marks scar the surrounding trees, marking this territory as claimed.",
        "The entrance to the lair is a dark maw in the hillside, breath misting from within.",
    ],
    "shrine": [
        "A small altar sits beneath an overhanging branch, fresh offerings laid before it.",
        "Carved into the living rock, the shrine faces the rising sun.",
        "Incense still smoulders on the altar — recently visited by devotees.",
        "The shrine is built around a natural spring, its waters cool and clear.",
    ],
    "mine": [
        "Rail tracks lead into the darkness, ore carts rusted and overturned.",
        "Timber supports groan under the weight of the mountain above.",
        "Tools lie scattered where they were dropped — the miners left in haste.",
        "The entrance is boarded up, warning signs posted in faded paint.",
    ],
}

# ── Treasure Tiers ───────────────────────────────────────────────────

TREASURE_TIERS = [
    {"tier": 1, "desc": "Modest", "value_range": "10-50 gp", "items": "Coins, simple tools, basic supplies"},
    {"tier": 2, "desc": "Notable", "value_range": "50-200 gp", "items": "Gemstones, fine weapons, art objects"},
    {"tier": 3, "desc": "Valuable", "value_range": "200-800 gp", "items": "Magic items, rare tomes, jewellery"},
    {"tier": 4, "desc": "Priceless", "value_range": "800-3000 gp", "items": "Enchanted weapons, ancient relics"},
    {"tier": 5, "desc": "Legendary", "value_range": "3000+ gp", "items": "Artifacts, crown jewels, dragon hoard"},
]

DIFFICULTY_DESCRIPTIONS = {
    "trivial": "Safe for a party of 1st-level adventurers",
    "easy": "Suitable for 2nd-3rd level parties",
    "moderate": "Challenging for 3rd-5th level parties",
    "hard": "Dangerous — recommended for 5th-8th level parties",
    "deadly": "Extreme threat — only for experienced adventurers (8th+)",
}

# ── Zone Count Scaling ───────────────────────────────────────────────

def _num_zones(width: int, height: int, rng: random.Random) -> int:
    """Determine how many adventure zones to place based on world size."""
    tiles = width * height
    if tiles < 500:
        return rng.randint(2, 4)
    elif tiles < 1000:
        return rng.randint(4, 7)
    elif tiles < 2000:
        return rng.randint(6, 10)
    else:
        return rng.randint(8, 15)


# ── Placement ────────────────────────────────────────────────────────

def _find_placement(
    world: World,
    zone_type: str,
    rng: random.Random,
) -> tuple[int, int, str] | None:
    """Find a suitable location for a zone of the given type.

    Returns (x, y, region_name) or None if no suitable spot found.
    """
    preferred = ADVENTURE_ZONE_TYPES[zone_type]["preferred_terrain"]

    # Build list of candidate cells
    candidates = []
    for y in range(world.height):
        for x in range(world.width):
            terrain_key = world.terrain[y][x]
            if terrain_key not in preferred:
                continue

            # Must not overlap with settlements
            has_settlement = False
            for region in world.regions:
                for s in region.settlements:
                    if s.x == x and s.y == y:
                        has_settlement = True
                        break
                if has_settlement:
                    break
            if has_settlement:
                continue

            # Must not overlap with existing adventure zones
            has_zone = any(z.x == x and z.y == y for z in world.adventure_zones)
            if has_zone:
                continue

            # Determine region
            region_name = _region_at(world, x, y)
            if region_name is None:
                continue

            candidates.append((x, y, region_name))

    if not candidates:
        return None

    return rng.choice(candidates)


def _region_at(world: World, x: int, y: int) -> str | None:
    """Find the region name at a given coordinate."""
    for region in world.regions:
        for s in region.settlements:
            # Simple proximity check: a cell belongs to a region if near a settlement
            if abs(s.x - x) <= 5 and abs(s.y - y) <= 5:
                return region.name
    # Fallback: nearest settlement by distance
    best_dist = float("inf")
    best_region = None
    for region in world.regions:
        for s in region.settlements:
            dist = (s.x - x)**2 + (s.y - y)**2
            if dist < best_dist:
                best_dist = dist
                best_region = region.name
    return best_region


# ── Name Generation ──────────────────────────────────────────────────

def _generate_zone_name(zone_type: str, rng: random.Random) -> str:
    """Generate a name for a zone."""
    templates = ZONE_NAMES.get(zone_type, DUNGEON_NAMES)
    template = rng.choice(templates)
    adj = rng.choice(ZONE_ADJECTIVES)
    noun = rng.choice(ZONE_NOUNS)
    return template.format(adj=adj, noun=noun)


# ── Difficulty Assignment ────────────────────────────────────────────

def _pick_difficulty(zone_type: str, rng: random.Random) -> str:
    """Pick an appropriate difficulty for a zone."""
    weights = {
        "dungeon": [0.05, 0.15, 0.35, 0.30, 0.15],
        "cave": [0.15, 0.30, 0.30, 0.20, 0.05],
        "ruin": [0.20, 0.30, 0.30, 0.15, 0.05],
        "tower": [0.10, 0.20, 0.30, 0.25, 0.15],
        "grove": [0.20, 0.25, 0.30, 0.20, 0.05],
        "lair": [0.05, 0.10, 0.30, 0.35, 0.20],
        "shrine": [0.30, 0.30, 0.25, 0.10, 0.05],
        "mine": [0.15, 0.25, 0.30, 0.20, 0.10],
    }
    w = weights.get(zone_type, [0.2, 0.2, 0.3, 0.2, 0.1])
    return rng.choices(ADVENTURE_DIFFICULTIES, weights=w, k=1)[0]


# ── Quest Hook Generation ───────────────────────────────────────────

QUEST_HOOKS = [
    "A local merchant seeks adventurers to investigate.",
    "Strange lights have been reported at night by nearby farmers.",
    "A villager's child went missing near this location.",
    "The elders council has posted a bounty for clearing the site.",
    "Travelers have been disappearing on the road nearby.",
    "An old map found in a library marked this location with a warning.",
    "A dying messenger gasped a description of this place.",
    "Local legend speaks of great treasure hidden within.",
    "A powerful artefact is rumored to be sealed away here.",
    "The town's priest had a vision of danger emanating from this place.",
    "Rival adventurers were hired for this job but never returned.",
    "Strange weather patterns centre on this location.",
]

def _generate_quest_hook(zone_name: str, rng: random.Random) -> str:
    """Generate a quest hook referencing the zone."""
    hook = rng.choice(QUEST_HOOKS)
    return f"{zone_name}: {hook}"


# ── Main Generation Function ────────────────────────────────────────

def generate_adventure_zones(world: World) -> list[AdventureZone]:
    """Generate adventure zones across the world.

    Places a terrain-appropriate number of zones (dungeons, caves, ruins,
    towers, groves, lairs, shrines, mines) using the world's seed + a
    deterministic offset for reproducibility.
    """
    rng = random.Random(world.seed + 10000)  # deterministic offset
    zones = []

    zone_types = list(ADVENTURE_ZONE_TYPES.keys())
    num = _num_zones(world.width, world.height, rng)

    for _ in range(num * 3):  # try more times for better coverage
        if len(zones) >= num:
            break

        zone_type = rng.choice(zone_types)
        placement = _find_placement(world, zone_type, rng)
        if placement is None:
            continue

        x, y, region_name = placement
        name = _generate_zone_name(zone_type, rng)
        difficulty = _pick_difficulty(zone_type, rng)
        inhabitants = rng.choice(INHABITANTS.get(zone_type, ["Unknown creatures"]))
        description = rng.choice(DESCRIPTIONS.get(zone_type, ["An unexplored location."]))
        treasure_tier = ADVENTURE_DIFFICULTIES.index(difficulty) + 1
        quest_hook = _generate_quest_hook(name, rng)

        zones.append(AdventureZone(
            name=name,
            zone_type=zone_type,
            x=x,
            y=y,
            region=region_name,
            difficulty=difficulty,
            inhabitants=inhabitants,
            description=description,
            treasure_tier=treasure_tier,
            is_cleared=False,
            quest_hook=quest_hook,
        ))

    return zones


# ── Rendering ────────────────────────────────────────────────────────

from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, ANSI_ITALIC, _color


def render_zones(world: World, detail: bool = False) -> str:
    """Render a list of all adventure zones in the world."""
    if not world.adventure_zones:
        return f"{ANSI_DIM}(no adventure zones generated){ANSI_RESET}"

    lines = []
    lines.append(f"{ANSI_BOLD}═══ Adventure Zones of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    # Group by region
    by_region: dict[str, list[AdventureZone]] = {}
    for z in world.adventure_zones:
        by_region.setdefault(z.region, []).append(z)

    for region_name, rzones in sorted(by_region.items()):
        lines.append(f"{ANSI_BOLD}{region_name}{ANSI_RESET}")
        for z in sorted(rzones, key=lambda z: z.name):
            info = ADVENTURE_ZONE_TYPES.get(z.zone_type, {})
            col = _color(info.get("color", 250))
            char = info.get("char", "?")

            status = "✦" if not z.is_cleared else "✓"
            diff_colors = {
                "trivial": _color(28), "easy": _color(34),
                "moderate": _color(220), "hard": _color(202),
                "deadly": _color(196),
            }
            diff_col = diff_colors.get(z.difficulty, _color(250))

            lines.append(
                f"  {col}{ANSI_BOLD}{char}{ANSI_RESET}  "
                f"{ANSI_BOLD}{z.name}{ANSI_RESET}  "
                f"[{diff_col}{z.difficulty}{ANSI_RESET}] "
                f"{ANSI_DIM}({info.get('desc', '')}){ANSI_RESET}"
                f"  {ANSI_DIM}✦{ANSI_RESET}" if not z.is_cleared else ""
            )

            if detail:
                lines.append(f"     {ANSI_ITALIC}{z.description}{ANSI_RESET}")
                lines.append(f"     {ANSI_DIM}Inhabitants:{ANSI_RESET} {z.inhabitants}")
                lines.append(f"     {ANSI_DIM}Treasure:{ANSI_RESET} {TREASURE_TIERS[z.treasure_tier - 1]['desc']} ({TREASURE_TIERS[z.treasure_tier - 1]['value_range']})")
                if z.quest_hook:
                    lines.append(f"     {ANSI_DIM}Quest:{ANSI_RESET} {z.quest_hook}")
                lines.append("")
        lines.append("")

    # Summary
    total = len(world.adventure_zones)
    by_type = {}
    for z in world.adventure_zones:
        by_type[z.zone_type] = by_type.get(z.zone_type, 0) + 1
    type_summary = " · ".join(f"{ADVENTURE_ZONE_TYPES[t]['char']} {c}× {t}" for t, c in sorted(by_type.items()))
    lines.append(f"{ANSI_DIM}{total} adventure zones: {type_summary}{ANSI_RESET}")

    return "\n".join(lines)


def render_zone_detail(zone: AdventureZone) -> str:
    """Render detailed information about a single adventure zone."""
    info = ADVENTURE_ZONE_TYPES.get(zone.zone_type, {})
    col = _color(info.get("color", 250))
    char = info.get("char", "?")
    diff_colors = {
        "trivial": _color(28), "easy": _color(34),
        "moderate": _color(220), "hard": _color(202),
        "deadly": _color(196),
    }
    diff_col = diff_colors.get(zone.difficulty, _color(250))
    tier = TREASURE_TIERS[zone.treasure_tier - 1] if 1 <= zone.treasure_tier <= 5 else TREASURE_TIERS[0]

    lines = []
    lines.append(f"{col}{ANSI_BOLD}{char}{ANSI_RESET}  {ANSI_BOLD}{zone.name}{ANSI_RESET}")
    lines.append(f"  {ANSI_DIM}Type:{ANSI_RESET}       {info.get('desc', 'Unknown')}")
    lines.append(f"  {ANSI_DIM}Location:{ANSI_RESET}   ({zone.x}, {zone.y}) in {zone.region}")
    lines.append(f"  {ANSI_DIM}Difficulty:{ANSI_RESET} {diff_col}{zone.difficulty}{ANSI_RESET} — {DIFFICULTY_DESCRIPTIONS.get(zone.difficulty, '')}")
    lines.append(f"  {ANSI_DIM}Status:{ANSI_RESET}     {'Cleared ✓' if zone.is_cleared else 'Undisturbed ✦'}")
    lines.append("")
    if zone.description:
        lines.append(f"  {zone.description}")
        lines.append("")
    if zone.inhabitants:
        lines.append(f"  {ANSI_BOLD}Inhabitants:{ANSI_RESET} {zone.inhabitants}")
    lines.append(f"  {ANSI_BOLD}Treasure:{ANSI_RESET} {tier['desc']} ({tier['value_range']}) — {tier['items']}")
    if zone.quest_hook:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Quest Hook:{ANSI_RESET}")
        lines.append(f"  {zone.quest_hook}")

    return "\n".join(lines)
