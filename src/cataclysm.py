"""
wyrd — Cataclysmic Events (Phase 13).

Catastrophic events reshape the world — earthquakes, volcanic eruptions,
legendary plagues, tsunamis, meteor strikes. These are very rare events
that permanently alter terrain, destroy settlements, and create landmarks.

Seed-deterministic: same seed + same parameters → same outcome.
"""

import random
import math
from dataclasses import dataclass, field
from .world import World, TERRAIN, Landmark


# ── Cataclysm Types ──────────────────────────────────────────────────

CATASTROPHE_TYPES = [
    "earthquake",
    "volcanic_eruption",
    "great_plague",
    "tsunami",
    "meteor_strike",
    "great_fire",
    "magical_cataclysm",
]

# Probability per year per world (baseline, modified by chaos_factor)
CATASTROPHE_BASE_PROB = 0.003  # 0.3% per year — roughly 1 per 333 years

# Terrain mutation tables: maps (cataclysm_type, original_terrain) → (new_terrain, weight)
# Higher weight = more likely to produce this result

TERRAIN_MUTATIONS = {
    "earthquake": {
        "mountains": [("hills", 80), ("mountains", 20)],
        "hills":      [("grass", 70), ("hills", 30)],
        "grass":      [("grass", 85), ("sand", 10), ("shallow", 5)],
        "forest":     [("grass", 60), ("forest", 40)],
        "sand":       [("sand", 80), ("shallow", 20)],
        "snow":       [("mountains", 50), ("hills", 50)],
    },
    "volcanic_eruption": {
        "mountains": [("mountains", 80), ("hills", 20)],  # becomes rougher
        "hills":      [("mountains", 40), ("hills", 60)],
        "grass":      [("hills", 50), ("grass", 35), ("sand", 15)],
        "forest":     [("hills", 45), ("grass", 35), ("sand", 20)],
        "sand":       [("sand", 60), ("shallow", 40)],
        "snow":       [("mountains", 80), ("snow", 20)],
    },
    "meteor_strike": {
        # Creates a crater: deep_water at center, sand/shallow around rim
        "mountains": [("hills", 50), ("grass", 30), ("sand", 20)],
        "hills":      [("grass", 50), ("sand", 30), ("shallow", 20)],
        "grass":      [("shallow", 40), ("sand", 30), ("grass", 30)],
        "forest":     [("shallow", 35), ("sand", 30), ("grass", 35)],
        "sand":       [("shallow", 50), ("sand", 50)],
    },
    "great_fire": {
        "forest":     [("grass", 80), ("hills", 15), ("sand", 5)],
        "grass":      [("grass", 85), ("sand", 15)],
        "hills":      [("hills", 70), ("grass", 30)],
    },
    "tsunami": {
        "sand":       [("shallow", 60), ("sand", 40)],
        "grass":      [("sand", 50), ("shallow", 30), ("grass", 20)],
        "forest":     [("grass", 40), ("sand", 30), ("shallow", 30)],
        "shallow":    [("shallow", 50), ("deep_water", 50)],
    },
    "magical_cataclysm": {
        "mountains": [("hills", 40), ("grass", 30), ("mountains", 30)],
        "hills":      [("grass", 60), ("hills", 40)],
        "grass":      [("grass", 40), ("sand", 30), ("forest", 30)],
        "forest":     [("grass", 40), ("hills", 30), ("forest", 30)],
        "sand":       [("sand", 40), ("grass", 30), ("shallow", 30)],
    },
    "great_plague": {
        # Plague doesn't change terrain, but may change forest slightly
        "forest":     [("forest", 90), ("grass", 10)],
    },
}

# ── Landmark name generation ─────────────────────────────────────────

LANDMARK_NAMES = {
    "earthquake": [
        "The {adj} Chasm",
        "The {adj} Rift",
        "{adj} Scar",
        "The Shattered {noun}",
        "The {adj} Fault",
    ],
    "volcanic_eruption": [
        "{adj} Pyre",
        "The {adj} Peak",
        "The Ash Wastes of {noun}",
        "{adj}'s Maw",
        "The Cinder {noun}",
    ],
    "meteor_strike": [
        "The {adj} Crater",
        "The Star-Fall {noun}",
        "{adj}'s Impact",
        "The Shattered {noun}",
        "The {adj} Basin",
    ],
    "great_fire": [
        "The {adj} Burn",
        "The Scorched {noun}",
        "{adj}'s Pyre",
        "The Ashen {noun}",
    ],
    "tsunami": [
        "The {adj} Shallows",
        "The Drowned {noun}",
        "The Salt {noun}",
        "{adj}'s Wake",
    ],
    "magical_cataclysm": [
        "The {adj} Wastes",
        "The {adj} Confluence",
        "The Warped {noun}",
        "{adj}'s Legacy",
        "The Untuned {noun}",
    ],
    "great_plague": [
        "The {adj} Fields",
        "The {adj} Barrows",
        "The Withered {noun}",
        "The Silent {noun}",
    ],
}

LANDMARK_ADJECTIVES = [
    "Sorrow", "Crimson", "Bleak", "Fallen", "Shattered",
    "Ash", "Bone", "Withered", "Ashen", "Drowned",
    "Howling", "Silent", "Black", "Scorched", "Forsaken",
    "Star-Born", "Riven", "Desolate", "Bleeding", "Cinder",
]

LANDMARK_NOUNS = [
    "Mouth", "Throat", "Bones", "Gate", "Reach",
    "Floor", "Tongue", "Breach", "Gulf", "Pass",
    "March", "Plain", "Ridge", "Field", "Heath",
]

# ── Cataclysm Descriptions ───────────────────────────────────────────

CATASTROPHE_DESCRIPTIONS = {
    "earthquake": [
        "The ground trembles and tears apart near {settlement}. A great chasm opens, swallowing roads and homes.",
        "A violent earthquake shakes {region}. Buildings collapse and the landscape is ripped asunder.",
        "The earth convulses violently across {region}. Hills are flattened, valleys rise, and rivers are diverted.",
    ],
    "volcanic_eruption": [
        "Mount {feature} erupts with fury, spewing ash and fire across {region}. The sky darkens for months.",
        "A volcano awakens in {region}, raining cinders upon the land. Lava flows reshape the countryside.",
        "Fire erupts from the earth near {settlement}. Ash buries fields and the sun is blotted out.",
    ],
    "great_plague": [
        "A horrific plague sweeps across {region}, far worse than any before. The afflicted wither and die within days.",
        "The Crimson Plague descends upon {region}. Half the population perishes as healers work without rest.",
        "An ancient pestilence awakens in {region}. The sick cough blood and the dead outnumber the living.",
    ],
    "tsunami": [
        "A monstrous wave crashes against the shores of {region}. Coastal lands are swallowed by the sea.",
        "The ocean rises with terrible fury, washing over {region}'s coastline. Entire villages vanish beneath the water.",
        "A wall of water taller than any building strikes {region}. The sea claims what was land.",
    ],
    "meteor_strike": [
        "A blazing star falls from the heavens, striking {region} with apocalyptic force. The impact crater smokes for years.",
        "The sky tears open and fire rains down upon {region}. A meteor of impossible size carves a wound into the earth.",
        "A celestial body crashes into {region}. The shockwave flattens forests and the land boils.",
    ],
    "great_fire": [
        "An unstoppable inferno rages through {region}. Forests become ash, and even rivers seem to burn.",
        "Fire sweeps across {region}, consuming everything in its path. The smoke blots out the sun for weeks.",
        "A great fire born from {cause} consumes {region}'s woodlands. The land will not recover for generations.",
    ],
    "magical_cataclysm": [
        "The very weave of magic tears in {region}. Reality bends, warps, and reshapes itself in impossible ways.",
        "A magical catastrophe in {region} twists the land into unnatural forms. The sky glows with eerie light.",
        "The arcane foundations of {region} rupture. Colour bleeds from the world and the land reshapes itself.",
    ],
}

CATASTROPHE_CAUSES = [
    "a dry lightning storm", "careless campfires", "dragon-fire",
    "a forge explosion", "a lightning strike", "ritual sacrifice",
]

# ── Data Models ──────────────────────────────────────────────────────


@dataclass
class CataclysmEvent:
    """A catastrophic event that occurred during simulation."""
    year: int
    cataclysm_type: str
    description: str
    epicenter_x: int
    epicenter_y: int
    affected_settlements: list[str] = field(default_factory=list)
    affected_regions: list[str] = field(default_factory=list)
    settlements_destroyed: list[str] = field(default_factory=list)
    terrain_changes: int = 0
    landmarks_created: list[str] = field(default_factory=list)
    cascade_triggered: str | None = None
    death_toll: int = 0


# ── Terrain Mutation Helpers ─────────────────────────────────────────


def _mutate_terrain(
    world: World,
    cx: int, cy: int,
    radius: int,
    cataclysm_type: str,
    rng: random.Random,
) -> int:
    """
    Mutate terrain within a radius around the epicentre.

    Returns the number of cells changed.
    """
    mutations = TERRAIN_MUTATIONS.get(cataclysm_type, {})
    changes = 0

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if not (0 <= x < world.width and 0 <= y < world.height):
                continue
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > radius:
                continue
            original = world.terrain[y][x]
            if original == "river":
                continue  # rivers are persistent features
            if original in ("deep_water",) and cataclysm_type not in ("tsunami", "meteor_strike"):
                continue  # don't mutate deep ocean except by special events

            table = mutations.get(original)
            if not table:
                continue

            # Weighted random choice
            terrains, weights = zip(*table)
            new_terrain = rng.choices(terrains, weights=weights, k=1)[0]

            if new_terrain != original:
                world.terrain[y][x] = new_terrain
                changes += 1

    # Invalidate precomputed resource maps since terrain changed
    if changes > 0:
        world.capacity_map = None
        world.food_map = None
        world.wealth_map = None

    return changes


def _count_nearby_regions(world: World, cx: int, cy: int, radius: int) -> list[str]:
    """Get all region names within the blast radius."""
    regions = set()
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < world.width and 0 <= y < world.height:
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius:
                    for region in world.regions:
                        # Check if point is in this region's bounding area
                        # Approximate: use region's settlement proximity
                        for s in region.settlements:
                            if abs(s.x - x) < 5 and abs(s.y - y) < 5:
                                regions.add(region.name)
    return list(regions)


def _is_coastal(world: World, cx: int, cy: int, radius: int = 3) -> bool:
    """Check if the epicentre is near deep_water or shallow."""
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < world.width and 0 <= y < world.height:
                if world.terrain[y][x] in ("deep_water", "shallow"):
                    return True
    return False


# ── Landmark Creation ────────────────────────────────────────────────


def _create_landmark(
    world: World,
    cataclysm_type: str,
    cx: int, cy: int,
    region_name: str | None,
    year: int,
    rng: random.Random,
) -> Landmark | None:
    """Create a named landmark for the cataclysm."""
    templates = LANDMARK_NAMES.get(cataclysm_type, [])
    if not templates:
        return None

    adj = rng.choice(LANDMARK_ADJECTIVES)
    noun = rng.choice(LANDMARK_NOUNS)
    template = rng.choice(templates)
    name = template.format(adj=adj, noun=noun)

    # Determine landmark type from cataclysm type
    type_map = {
        "earthquake": rng.choice(["chasm", "rift", "scar"]),
        "volcanic_eruption": rng.choice(["ash_waste", "magma_field", "scar"]),
        "meteor_strike": "crater",
        "great_fire": "ash_waste",
        "tsunami": "drowned_coast",
        "magical_cataclysm": rng.choice(["scar", "rift", "crater"]),
        "great_plague": "petrified_forest",
    }
    landmark_type = type_map.get(cataclysm_type, "scar")

    # Distance from epicentre for interesting placement
    dx = rng.randint(-3, 3)
    dy = rng.randint(-3, 3)
    lx = max(0, min(world.width - 1, cx + dx))
    ly = max(0, min(world.height - 1, cy + dy))

    descriptions = {
        "crater": f"A vast crater gouged into the earth, its edges still smoking.",
        "chasm": f"A deep fissure in the earth, plunging into darkness.",
        "ash_waste": f"A bleak expanse of ash and cinders, where nothing grows.",
        "magma_field": f"Glowing rivers of molten rock have carved new paths through the land.",
        "drowned_coast": f"What was once land now lies beneath the waves.",
        "sinkhole": f"The ground has collapsed into a vast hollow, revealing ancient stone beneath.",
        "petrified_forest": f"A forest turned to stone, silent and grey.",
        "rift": f"A wound in the world, where the very fabric of reality seems thin.",
        "scar": f"A lasting mark on the landscape, a reminder of the catastrophe.",
    }
    description = descriptions.get(landmark_type, f"Evidence of the great {cataclysm_type}.")

    landmark = Landmark(
        name=name,
        landmark_type=landmark_type,
        x=lx,
        y=ly,
        region=region_name,
        description=description,
        cataclysm_year=year,
        cataclysm_type=cataclysm_type,
    )
    world.landmarks.append(landmark)
    return landmark


# ── Settlement Destruction ───────────────────────────────────────────


def _destroy_settlements_in_radius(
    world: World,
    state: "SimState",  # noqa: F821
    cx: int, cy: int,
    radius: int,
    rng: random.Random,
) -> tuple[list[str], list[str], int]:
    """
    Destroy settlements within the blast radius.

    Returns (settlements_destroyed, refugees_from, death_toll).
    """
    from .sim import SettlementSnapshot

    destroyed: list[str] = []
    refugees_from: list[str] = []
    total_deaths = 0

    for s_name, s in list(state.settlements.items()):
        if not s.is_active:
            continue
        dist = math.sqrt((s.x - cx) ** 2 + (s.y - cy) ** 2)
        if dist > radius:
            continue

        # Closer to epicentre = more complete destruction
        kill_fraction = 1.0 - (dist / radius) * 0.7  # 30%-100% population loss
        deaths = max(1, int(s.population * rng.uniform(kill_fraction - 0.2, kill_fraction)))
        deaths = min(deaths, s.population - 1)  # leave at least 1
        total_deaths += deaths
        s.population -= deaths

        if s.population <= 1 or rng.random() < 0.7:
            # Settlement destroyed
            s.is_active = False
            s.population = 0
            destroyed.append(s_name)
        else:
            # Settlement survives but devastated
            s.prosperity = max(0.0, s.prosperity - rng.uniform(0.4, 0.8))
            s.health = max(0.05, s.health - rng.uniform(0.3, 0.6))
            s.food_stores *= rng.uniform(0.1, 0.3)
            # Some survivors become refugees
            refugees = max(1, int(s.population * rng.uniform(0.2, 0.5)))
            s.population -= refugees
            survivors = s.population
            if survivors >= 1:
                refugees_from.append(s_name)

    return destroyed, refugees_from, total_deaths


# ── Cascade Events ───────────────────────────────────────────────────


CASCADE_MAP = {
    "earthquake": ["tsunami", "great_fire"],
    "volcanic_eruption": ["earthquake", "great_fire"],
    "meteor_strike": ["great_fire", "earthquake"],
    "great_fire": [],  # Fire doesn't cascade into other major types
    "tsunami": [],     # Tsunami is end of chain
    "great_plague": [],
    "magical_cataclysm": ["great_fire", "earthquake"],
}


def _maybe_cascade(world, state, cataclysm_type, cx, cy, rng, year):
    """
    Check if this cataclysm triggers a follow-up event.

    Returns a CataclysmEvent if cascade occurs, else None.
    """
    possible = CASCADE_MAP.get(cataclysm_type, [])
    if not possible:
        return None

    cascade_type = rng.choice(possible)

    # Only cascade if conditions make sense
    if cascade_type == "tsunami" and not _is_coastal(world, cx, cy):
        return None

    if rng.random() < 0.15:  # 15% cascade chance
        # Use the cataclysm's epicentre with slight offset
        cascade_x = max(0, min(world.width - 1, cx + rng.randint(-3, 3)))
        cascade_y = max(0, min(world.height - 1, cy + rng.randint(-3, 3)))

        cascade_event = _execute_single_cataclysm(
            world, state, cascade_type, cascade_x, cascade_y, year, rng,
        )
        cascade_event.cascade_triggered = cataclysm_type
        return cascade_event

    return None


# ── Core Cataclysm Execution ─────────────────────────────────────────


def _execute_single_cataclysm(
    world: World,
    state: "SimState",  # noqa: F821
    cataclysm_type: str,
    cx: int, cy: int,
    year: int,
    rng: random.Random,
) -> CataclysmEvent:
    """Execute a single cataclysmic event at the given coordinates."""
    # Determine radius based on cataclysm type
    radius_map = {
        "earthquake": rng.randint(5, 12),
        "volcanic_eruption": rng.randint(6, 15),
        "great_plague": rng.randint(8, 20),
        "tsunami": rng.randint(4, 10),
        "meteor_strike": rng.randint(3, 8),
        "great_fire": rng.randint(5, 12),
        "magical_cataclysm": rng.randint(4, 10),
    }
    radius = radius_map.get(cataclysm_type, 5)

    # 1. Mutate terrain
    terrain_changes = _mutate_terrain(world, cx, cy, radius, cataclysm_type, rng)

    # 2. Destroy settlements
    destroyed, refugees_from, death_toll = _destroy_settlements_in_radius(
        world, state, cx, cy, radius, rng
    )

    # 3. Find affected regions
    regions_affected = _count_nearby_regions(world, cx, cy, radius)
    # Also include regions from destroyed settlements
    for s_name in destroyed:
        s = state.settlements.get(s_name)
        if s and s.region not in regions_affected:
            regions_affected.append(s.region)

    # 4. Create landmark
    region_name = regions_affected[0] if regions_affected else None
    landmark = _create_landmark(world, cataclysm_type, cx, cy, region_name, year, rng)
    landmarks_created = [landmark.name] if landmark else []

    # 5. Generate description
    settlement_ref = destroyed[0] if destroyed else (refugees_from[0] if refugees_from else "the wilds")
    feature_ref = "the mountains" if region_name else "the land"
    templates = CATASTROPHE_DESCRIPTIONS.get(cataclysm_type, [])
    if templates:
        desc = rng.choice(templates).format(
            settlement=settlement_ref,
            region=region_name or "the land",
            feature=feature_ref,
            cause=rng.choice(CATASTROPHE_CAUSES),
        )
    else:
        desc = f"A catastrophic {cataclysm_type} strikes {region_name or 'the land'}."

    # Add death toll and landmark info
    if death_toll > 0:
        desc += f" {death_toll} perish."
    if landmarks_created:
        desc += f" The event creates {landmarks_created[0]}."
    if destroyed:
        desc += f" {', '.join(destroyed[:3])} {'is' if len(destroyed) == 1 else 'are'} destroyed."

    return CataclysmEvent(
        year=year,
        cataclysm_type=cataclysm_type,
        description=desc,
        epicenter_x=cx,
        epicenter_y=cy,
        affected_settlements=destroyed + refugees_from,
        affected_regions=regions_affected,
        settlements_destroyed=destroyed,
        terrain_changes=terrain_changes,
        landmarks_created=landmarks_created,
        cascade_triggered=None,
        death_toll=death_toll,
    )


# ── Epicentre Selection ──────────────────────────────────────────────


def _pick_epicentre_in_world(world: World, cataclysm_type: str, rng: random.Random) -> tuple[int, int]:
    """
    Pick appropriate coordinates for the cataclysm epicentre.

    Different cataclysm types prefer different terrain:
    - earthquakes: anywhere on land
    - volcanic: near mountains/hills
    - tsunami: near coast
    - meteor: anywhere
    - great_fire: near forest
    - magical: anywhere
    - plague: near settlements
    """
    for _ in range(100):
        x = rng.randint(2, world.width - 3)
        y = rng.randint(2, world.height - 3)
        terrain = world.terrain[y][x]

        if terrain in ("deep_water",):
            continue

        if cataclysm_type == "tsunami" and not _is_coastal(world, x, y):
            continue
        if cataclysm_type == "volcanic_eruption" and terrain not in ("mountains", "hills"):
            continue
        if cataclysm_type == "great_fire" and terrain not in ("forest", "grass"):
            continue
        if cataclysm_type == "earthquake" and terrain in ("sand", "shallow"):
            continue

        return (x, y)

    # Fallback: any land tile
    for _ in range(200):
        x = rng.randint(2, world.width - 3)
        y = rng.randint(2, world.height - 3)
        if world.terrain[y][x] not in ("deep_water", "shallow"):
            return (x, y)

    return (world.width // 2, world.height // 2)


# ── Main Entry Point ─────────────────────────────────────────────────


def _simulate_cataclysm_tick(
    world: World,
    state: "SimState",  # noqa: F821
    rng: random.Random,
    year: int,
    chaos_factor: float = 0.1,
) -> list["CataclysmEvent"]:  # noqa: F821
    """
    Simulate potential cataclysmic events for one year.

    Very rare events (0.1-0.5% per year depending on chaos_factor)
    that permanently change terrain, destroy settlements, and create landmarks.

    Args:
        world: The world (terrain mutated in-place)
        state: Current simulation state (settlements mutated in-place)
        rng: Seeded RNG for determinism
        year: Current simulation year
        chaos_factor: How much random chaos to apply (0.0-1.0)

    Returns:
        List of CataclysmEvent objects generated this year
    """
    from .sim import SimEvent

    cataclysms: list[CataclysmEvent] = []

    # Check probability: very rare
    prob = CATASTROPHE_BASE_PROB * chaos_factor
    # Slightly more likely in older worlds (land becomes unstable)
    prob += (year / 5000) * 0.005 * chaos_factor

    if rng.random() >= prob:
        return cataclysms

    # Pick cataclysm type
    cataclysm_type = rng.choice(CATASTROPHE_TYPES)

    # Pick epicentre
    cx, cy = _pick_epicentre_in_world(world, cataclysm_type, rng)

    # Execute
    cataclysm = _execute_single_cataclysm(world, state, cataclysm_type, cx, cy, year, rng)
    cataclysms.append(cataclysm)

    # Check for cascade
    cascade = _maybe_cascade(world, state, cataclysm_type, cx, cy, rng, year)
    if cascade:
        cataclysms.append(cascade)

    # Generate SimEvent entries from CataclysmEvents (for the sim event log)
    # Refugees and exodus events were already created above

    return cataclysms


def cataclysm_to_sim_event(cataclysm: CataclysmEvent) -> "SimEvent":  # noqa: F821
    """Convert a CataclysmEvent to a SimEvent for the simulation event log."""
    from .sim import SimEvent

    return SimEvent(
        year=cataclysm.year,
        event_type=cataclysm.cataclysm_type,
        description=cataclysm.description,
        affected_settlements=cataclysm.affected_settlements,
        affected_regions=cataclysm.affected_regions,
    )
