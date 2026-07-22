"""
wyrd — Magic System Generation (Phase 8: The Web Awakens).

Procedurally generate magic systems, schools of magic, and magical
traditions tied to world biomes, cultures, and geography.
Seed-deterministic: same seed + same world → same magic system, always.
"""

import random
from dataclasses import dataclass, field
from typing import Optional
from .world import World


# ── Magic Sources ───────────────────────────────────────────────────────

MAGIC_SOURCES = {
    "arcane": {
        "name_format": "The {adj} Weave",
        "adjectives": ["Arcane", "Ethereal", "Astral", "Luminous", "Veiled", "Infinite", "Prismatic"],
        "description": "Raw magical energy drawn from the fabric of reality itself. Studied through years of disciplined scholarship.",
        "practitioners": "Mages, Wizards, Arcanists, Sages",
        "biome_affinities": ["temperate", "arid"],
    },
    "divine": {
        "name_format": "The {adj} Breath",
        "adjectives": ["Sacred", "Hallowed", "Celestial", "Blessed", "Radiant", "Divine", "Golden"],
        "description": "Power granted by gods, spirits, or cosmic forces. Channeled through faith and devotion.",
        "practitioners": "Priests, Clerics, Paladins, Oracles",
        "biome_affinities": ["temperate", "tundra"],
    },
    "natural": {
        "name_format": "The {adj} Song",
        "adjectives": ["Wild", "Green", "Living", "Primal", "Verdant", "Ancient", "Rooted"],
        "description": "The pulse of life that flows through every living thing. Druids and rangers attune to this rhythm.",
        "practitioners": "Druids, Rangers, Wardens, Shamans",
        "biome_affinities": ["forest", "tropical", "temperate"],
    },
    "elemental": {
        "name_format": "The {adj} Convergence",
        "adjectives": ["Elemental", "Raging", "Primordial", "Unbound", "Titanic", "Shattered", "Fulminant"],
        "description": "The primal forces of fire, water, earth, and air, harnessed through will and ritual.",
        "practitioners": "Elementalists, Geomancers, Pyromancers, Hydromancers",
        "biome_affinities": ["arid", "mountains", "hills"],
    },
    "shadow": {
        "name_format": "The {adj} Thread",
        "adjectives": ["Shadow", "Dark", "Twilight", "Obsidian", "Umbral", "Void", "Silent"],
        "description": "Magic born from the spaces between — shadows, secrets, and the forgotten. Dangerous and alluring.",
        "practitioners": "Warlocks, Necromancers, Illusionists, Nightblades",
        "biome_affinities": ["deep_water", "mountains"],
    },
    "blood": {
        "name_format": "The {adj} Bond",
        "adjectives": ["Blood", "Iron", "Ancestral", "Flesh", "Crimson", "Bone", "Sanguine"],
        "description": "Power inherited through lineage, traded in sacrifice, or awakened by trauma. Costs always have a price.",
        "practitioners": "Blood Mages, Hexblades, Ritualists, Vessels",
        "biome_affinities": ["arid", "hills", "tundra"],
    },
    "celestial": {
        "name_format": "The {adj} Chorus",
        "adjectives": ["Stellar", "Celestial", "Astral", "Cosmic", "Orbital", "Star-Forged", "Nebular"],
        "description": "Magic drawn from the movement of stars, the phases of moons, and the alignment of celestial bodies.",
        "practitioners": "Astrologers, Star-Priests, Lunamancers, Sky-Watchers",
        "biome_affinities": ["snow", "mountains", "temperate"],
    },
}

# ── Schools of Magic ────────────────────────────────────────────────────

ALL_SCHOOLS = [
    {
        "name": "Pyromancy",
        "description": "The school of fire — destruction, light, and transformation.",
        "spell_examples": ["Firebolt", "Flame Shield", "Wall of Fire", "Meteor Storm"],
        "alignment": "neutral",
        "biome_affinity": "arid",
    },
    {
        "name": "Hydromancy",
        "description": "The school of water — healing, divination, and emotion.",
        "spell_examples": ["Healing Spring", "Tidal Wave", "Scrying Pool", "Water Breathing"],
        "alignment": "good",
        "biome_affinity": "deep_water",
    },
    {
        "name": "Geomancy",
        "description": "The school of earth — protection, endurance, and structure.",
        "spell_examples": ["Stone Skin", "Earthquake", "Wall of Stone", "Meld with Stone"],
        "alignment": "neutral",
        "biome_affinity": "mountains",
    },
    {
        "name": "Aeromancy",
        "description": "The school of air — movement, illusion, and freedom.",
        "spell_examples": ["Wind Walk", "Invisibility", "Levitation", "Storm Call"],
        "alignment": "chaotic",
        "biome_affinity": "hills",
    },
    {
        "name": "Necromancy",
        "description": "The school of death and undeath — spirits, decay, and the forbidden.",
        "spell_examples": ["Animate Dead", "Speak with Spirit", "Life Drain", "Soul Cage"],
        "alignment": "evil",
        "biome_affinity": "tundra",
    },
    {
        "name": "Illusion",
        "description": "The school of perception — deception, dreams, and hidden truths.",
        "spell_examples": ["Minor Illusion", "Phantom Steed", "Mirage Arcane", "Dream Walk"],
        "alignment": "chaotic",
        "biome_affinity": "shallow",
    },
    {
        "name": "Abjuration",
        "description": "The school of protection — wards, barriers, and dispelling.",
        "spell_examples": ["Shield", "Magic Circle", "Dispel Magic", "Antimagic Field"],
        "alignment": "lawful",
        "biome_affinity": "temperate",
    },
    {
        "name": "Divination",
        "description": "The school of knowledge — foresight, truth, and revelation.",
        "spell_examples": ["Detect Magic", "Augury", "Clairvoyance", "True Seeing"],
        "alignment": "good",
        "biome_affinity": "snow",
    },
    {
        "name": "Enchantment",
        "description": "The school of influence — charm, compulsion, and persuasion.",
        "spell_examples": ["Charm Person", "Hold Monster", "Dominate Person", "Mass Suggestion"],
        "alignment": "neutral",
        "biome_affinity": "grass",
    },
    {
        "name": "Transmutation",
        "description": "The school of change — transformation, alchemy, and reshaping.",
        "spell_examples": ["Polymorph", "Fabricate", "Stone to Flesh", "Shape Change"],
        "alignment": "neutral",
        "biome_affinity": "tropical",
    },
    {
        "name": "Conjuration",
        "description": "The school of summoning — creation, transportation, and calling.",
        "spell_examples": ["Summon Familiar", "Teleportation Circle", "Planar Ally", "Gate"],
        "alignment": "neutral",
        "biome_affinity": "forest",
    },
    {
        "name": "Evocation",
        "description": "The school of raw energy — destruction, force, and direct power.",
        "spell_examples": ["Magic Missile", "Fireball", "Chain Lightning", "Power Word Kill"],
        "alignment": "neutral",
        "biome_affinity": "arid",
    },
]

# ── Tradition Templates ─────────────────────────────────────────────────

TRADITION_ORIGINS = [
    "ancient",
    "secret",
    "forgotten",
    "forbidden",
    "revered",
    "wandering",
    "monastic",
    "tribal",
    "courtly",
    "scholarly",
]

TRADITION_ADJECTIVES = [
    "Whispering", "Crimson", "Silver", "Ashen", "Amber",
    "Sapphire", "Violet", "Crystal", "Ember", "Frost",
    "Thunder", "Storm", "Dusk", "Dawn", "Twilight",
    "Hollow", "Iron", "Jade", "Obsidian", "Pearl",
]

TRADITION_NOUNS = [
    "Circle", "Order", "Coven", "School", "Path",
    "Guild", "Sect", "Brotherhood", "Sisterhood", "College",
    "Conclave", "Sanctum", "Academy", "Ring", "Cloister",
]


# ── Data Models ─────────────────────────────────────────────────────────


@dataclass
class MagicSchool:
    name: str
    description: str
    spell_examples: list[str] = field(default_factory=list)
    alignment: str = "neutral"


@dataclass
class MagicTradition:
    name: str
    description: str
    origin: str
    region: str
    practitioners: str = ""


@dataclass
class MagicSystem:
    """A complete magic system for a world."""
    name: str
    source: str  # arcane, divine, natural, elemental, shadow, blood, celestial
    description: str
    practitioners: str = ""
    schools: list[MagicSchool] = field(default_factory=list)
    traditions: list[MagicTradition] = field(default_factory=list)


# ── Generation ──────────────────────────────────────────────────────────


def _pick_magic_source(world: World, rng: random.Random) -> tuple[str, dict]:
    """
    Pick a magic source weighted by the world's biome distribution.
    Also factor in the seed for variety.
    """
    # Count biomes
    biome_counts: dict[str, int] = {}
    for region in world.regions:
        b = region.biome
        biome_counts[b] = biome_counts.get(b, 0) + 1

    # Score each source by biome affinity match
    scores = {}
    for source_key, source_data in MAGIC_SOURCES.items():
        score = 1
        affinities = source_data["biome_affinities"]
        for biome, count in biome_counts.items():
            if biome in affinities:
                score += count * 2  # Strong affinity bonus
            # Also check if biome maps to a terrain-based affinity
        scores[source_key] = score

    # Add some randomness so same world can have different sources
    # (but still seed-deterministic via rng)
    for key in scores:
        scores[key] += rng.random() * 3  # Small random factor

    best = max(scores, key=scores.get)
    return best, MAGIC_SOURCES[best]


def _generate_system_name(source_key: str, source_data: dict, world: World, rng: random.Random) -> str:
    """Generate a name for the magic system, grounded in world cultures."""
    fmt = source_data["name_format"]
    adj = rng.choice(source_data["adjectives"])

    # Use a culture name from the world if available
    suffix = ""
    if world.lore and world.lore.cultures:
        culture_names = list(world.lore.cultures.values())
        # Deduplicate
        seen = set()
        unique = []
        for c in culture_names:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        if unique:
            culture = rng.choice(unique)
            suffix = f" of {culture}"

    name = fmt.format(adj=adj) + suffix
    return name


def _select_schools(source_key: str, world: World, rng: random.Random) -> list[MagicSchool]:
    """Select schools that fit the source and world biomes."""
    # Determine which biomes are present
    present_biomes = set(r.biome for r in world.regions)

    # Score each school
    scored = []
    for school in ALL_SCHOOLS:
        score = 0
        # Biome affinity
        if school["biome_affinity"] in present_biomes:
            score += 3
        # Always include some core schools
        if school["name"] in ("Abjuration", "Evocation", "Transmutation"):
            score += 1
        scored.append((score, school))

    scored.sort(key=lambda x: (-x[0], rng.random()))

    # Pick top 3-6 schools
    num_schools = rng.randint(3, min(6, len(scored)))
    selected = scored[:num_schools]

    return [
        MagicSchool(
            name=s["name"],
            description=s["description"],
            spell_examples=s["spell_examples"],
            alignment=s["alignment"],
        )
        for _, s in selected
    ]


def _generate_traditions(world: World, rng: random.Random) -> list[MagicTradition]:
    """Generate magical traditions grounded in the world's regions and cultures."""
    traditions = []
    num_traditions = min(rng.randint(2, 5), len(world.regions))

    # Pick regions to attach traditions to
    trad_regions = rng.sample(world.regions, num_traditions)

    for region in trad_regions:
        origin = rng.choice(TRADITION_ORIGINS)
        adj = rng.choice(TRADITION_ADJECTIVES)
        noun = rng.choice(TRADITION_NOUNS)

        culture_name = ""
        if world.lore and region.name in world.lore.cultures:
            culture_name = world.lore.cultures[region.name]

        name = f"{adj} {noun}"
        if culture_name:
            name = f"{adj} {noun} of {culture_name}"

        biome_desc = {
            "temperate": "the temperate forests and fields",
            "arid": "the sun-scorched wastes",
            "tundra": "the frozen wastes",
            "tropical": "the lush jungles",
        }.get(region.biome, region.biome)

        desc = f"A {origin} tradition practiced in the {region.name} region, amidst {biome_desc}."

        traditions.append(MagicTradition(
            name=name,
            description=desc,
            origin=origin,
            region=region.name,
            practitioners=f"Practitioners of {name}",
        ))

    return traditions


def generate_magic_system(world: World, seed: Optional[int] = None) -> MagicSystem:
    """
    Generate a magic system for a world.
    Seed-deterministic: same world + same seed → same magic system.
    """
    rng = random.Random(seed if seed is not None else world.seed)

    source_key, source_data = _pick_magic_source(world, rng)
    system_name = _generate_system_name(source_key, source_data, world, rng)
    description = source_data["description"]
    practitioners = source_data["practitioners"]

    schools = _select_schools(source_key, world, rng)
    traditions = _generate_traditions(world, rng)

    return MagicSystem(
        name=system_name,
        source=source_key,
        description=description,
        practitioners=practitioners,
        schools=schools,
        traditions=traditions,
    )
