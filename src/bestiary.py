"""
wyrd — Bestiary / Monster Ecology (Phase 12).

Procedural creature generation grounded in biomes, terrain, and world ecology.
Connects to adventure zones, factions, and TTRPG export with stat blocks,
encounter tables, and creature behaviors.

Usage:
    wyrd bestiary --seed 42            # List all creatures
    wyrd bestiary --seed 42 --id 0     # Detail for a specific creature
"""

import random
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World

# ── Creature Types ─────────────────────────────────────────────────────

CREATURE_TYPES = [
    "beast", "monstrosity", "undead", "dragon", "fey",
    "elemental", "aberration", "construct", "giant", "humanoid_bandit",
]

# ── Body Plans ─────────────────────────────────────────────────────────

BODY_PLANS = {
    "beast": ["Quadrupedal", "Serpentine", "Avian", "Aquatic", "Insectoid"],
    "monstrosity": ["Chimeric", "Twisted Form", "Grotesque", "Multi-limbed", "Crystalline"],
    "undead": ["Skeletal", "Putrid Corpse", "Ghostly", "Mummified", "Bone Construct"],
    "dragon": ["Wyrm", "Drake", "Wyvern", "True Dragon", "Lindwyrm"],
    "fey": ["Humanoid with animal features", "Shimmering ethereal", "Winged sprite", "Plant-like"],
    "elemental": ["Living flame", "Crystalline sentinel", "Whirling storm", "Earthen colossus"],
    "aberration": ["Many-eyed", "Tentacled", "Amorphous", "Geometric horror", "Reality-warping"],
    "construct": ["Clockwork", "Stone golem", "Iron guardian", "Bone-scavenger", "Crystal automaton"],
    "giant": ["Cyclops", "Mountain giant", "Frost giant", "Hill giant", "Stone giant"],
    "humanoid_bandit": ["Human", "Goblinoid", "Orcish", "Dwarven renegade", "Elven exile"],
}

# ── Sizes ──────────────────────────────────────────────────────────────

SIZES = ["tiny", "small", "medium", "large", "huge", "gargantuan"]

TIER_SIZE_MAP = {
    1: ["tiny", "small", "medium"],
    2: ["small", "medium", "large"],
    3: ["medium", "large"],
    4: ["large", "huge"],
    5: ["huge", "gargantuan"],
}

# ── Behaviors ─────────────────────────────────────────────────────────

BEHAVIOR_TYPES = [
    "aggressive", "territorial", "ambush", "pack_hunter",
    "solitary", "defensive", "migratory", "nocturnal",
    "docile", "curious", "cunning", "patient",
]

# ── Special Abilities Pool ─────────────────────────────────────────────

SPECIAL_ABILITIES = [
    "Venomous bite (DC 12, 2d6 poison)", "Petrifying gaze", "Camouflage in natural terrain",
    "Regeneration (10 HP/round)", "Fire breath (30 ft cone, 4d6 fire)", "Acid spray",
    "Invisibility in shadows", "Web entanglement", "Telepathic communication",
    "Terrifying roar (frightened 1 min)", "Fey charm", "Phase through solid matter",
    "Poisonous spines (ranged)", "Paralytic sting", "Sonic screech (deafening)",
    "Swallow whole (medium or smaller)", "Pack tactics (advantage when ally nearby)",
    "Keen senses (advantage on Perception)", "Rapid burrowing", "Flight (hover)",
    "Mirror image (3 illusory duplicates)", "Darkness aura (15 ft radius)",
    "Life drain (necrotic damage, heal half)", "Summon lesser versions",
    "Reflective hide (spell resistance)", "Toxic blood (splash on melee hit)",
    "Blood frenzy (advantage when wounded)", "Shadow step (teleport 30 ft)",
    "Elemental affinity (immune to one element)", "Magnetic pull (metal objects)",
]

# ── Loot Tables by Tier ────────────────────────────────────────────────

LOOT_TABLES = {
    1: ["Copper pieces (2d10)", "Rat tail (arcane component)", "Broken weapon scrap",
        "Nothing of value", "Spoiled rations", "Old bone necklace"],
    2: ["Silver pieces (3d8)", "Healing herb bundle", "Good quality hide", "Lockbox (stuck)",
        "Strange carved idol", "Traveler's journal fragment"],
    3: ["Gold pieces (4d10)", "Gemstone (worth 50gp)", "Fine weapon (silvered)",
        "Spell scroll (level 1)", "Potion of Healing", "Enchanted trinket"],
    4: ["Gold pieces (6d12)", "Gemstone cluster (worth 200gp)", "Magic weapon (+1)",
        "Spell scroll (level 3)", "Potion of Greater Healing", "Rare component"],
    5: ["Gold pieces (10d20)", "Precious gem (worth 500gp+)", "Legendary weapon shard",
        "Spell scroll (level 5+)", "Potion of Invisibility", "Artifact piece"],
}

# ── Biome/Habitat Creature Templates ───────────────────────────────────

BIOME_BEASTS = {
    "temperate": {
        "common": [
            "Timber Wolf", "Forest Bear", "Red Deer", "Wild Boar",
            "Mountain Lion", "Grey Fox", "Badger",
        ],
        "uncommon": [
            "Dire Boar", "Phase Cat", "Elder Stag", "Giant Badger",
        ],
        "rare": [
            "Winter Wolf (albino)", "Celestial Stag", "Emerald Serpent",
        ],
    },
    "arid": {
        "common": [
            "Sand Viper", "Dune Runner (lizard)", "Scorpion (giant)",
            "Desert Hare", "Coyote",
        ],
        "uncommon": [
            "Giant Scorpion", "Sand Wyrmling", "Mirage Hound",
            "Crystal Beetle",
        ],
        "rare": [
            "Ash Drake", "Sun Elemental", "Obsidian Hydra",
        ],
    },
    "tundra": {
        "common": [
            "Snow Fox", "Arctic Hare", "Mountain Goat", "Snowy Owl",
        ],
        "uncommon": [
            "Frost Bear", "Yeti", "Ice Spider", "Woolly Mammoth",
        ],
        "rare": [
            "Winter Wraith", "Frost Wyrm", "Glacier Elemental",
        ],
    },
    "tropical": {
        "common": [
            "Jungle Cat", "Monitor Lizard", "Poison Dart Frog",
            "Tropical Boa", "Howler Monkey",
        ],
        "uncommon": [
            "Giant Constrictor", "Venomous Wyvern", "Mantis Stalker",
            "Spore Zombie (fungal infected)",
        ],
        "rare": [
            "Jungle Hydra", "Crystal Moth (dreamweaver)", "Ancient Treant",
        ],
    },
    "swamp": {
        "common": [
            "Moccasin Snake", "Marsh Frog (giant)", "Leech Swarm",
            "Crane", "Swamp Boar",
        ],
        "uncommon": [
            "Giant Leech", "Bog Wraith", "Will-o'-Wisp", "Poison Toad",
        ],
        "rare": [
            "Hydra (swamp variety)", "Black Dragon Whelp", "Blight Treant",
        ],
    },
    "desert": {
        "common": [
            "Sand Viper", "Dune Runner (lizard)", "Scorpion (giant)",
            "Jackal", "Desert Hawk",
        ],
        "uncommon": [
            "Giant Scorpion", "Sand Wyrmling", "Mirage Hound",
            "Crystal Beetle", "Dust Devil",
        ],
        "rare": [
            "Ash Drake", "Sun Elemental", "Obsidian Hydra", "Sphinx",
        ],
    },
}

# ── Faction-Attuned Creatures ─────────────────────────────────────────

FACTION_CREATURES = {
    "kingdom": {
        "beast": "Royal Griffon", "monstrosity": "Chimera of the Crown",
        "undead": "Spectral Knight", "construct": "Royal Clockwork Guard",
    },
    "arcane_order": {
        "elemental": "Arcane Sentinel", "construct": "Living Spellbook",
        "aberration": "Void Seep (reality bleed)", "beast": "Enchanted Familiar",
    },
    "religious_order": {
        "celestial_adjacent": "Avenging Angel", "undead": "Penitent Wraith",
        "beast": "Sacred Hound", "fey": "Miracle Serpent",
    },
    "druidic_circle": {
        "beast": "Elder Treant", "fey": "Forest Warden",
        "elemental": "Verdant Colossus", "monstrosity": "Corrupted Beast (blight)",
    },
    "thieves_guild": {
        "beast": "Shadow Cat", "construct": "Clockwork Spy",
        "humanoid_bandit": "Guild Assassin", "monstrosity": "Alchemical Horror",
    },
    "cult": {
        "aberration": "Deep One Spawn", "undead": "Bone Golem",
        "monstrosity": "Blood Carver", "elemental": "Void Tendril",
    },
    "barbarian_clan": {
        "beast": "Frost Bear (war-trained)", "giant": "Mountain Giant Ally",
        "dragon": "Lesser Wyrm", "humanoid_bandit": "Berserker War Band",
    },
    "mercenary_company": {
        "beast": "War Mastiff", "giant": "Ogre Bodyguard",
        "humanoid_bandit": "Veteran Soldier", "monstrosity": "Siege Beast",
    },
}

# ── Combat Tactics ────────────────────────────────────────────────────

COMBAT_TACTICS = [
    "Charges the strongest foe first",
    "Attacks from ambush, then retreats",
    "Uses hit-and-run tactics",
    "Protects its territory at all costs",
    "Targets spellcasters and ranged attackers",
    "Fights to the death — no retreat",
    "Attempts to flank and surround",
    "Uses environment for cover",
    "Attempts to kidnap a party member",
    "Calls for reinforcements when bloodied",
]


# ── Dataclass ─────────────────────────────────────────────────────────

@dataclass
class Creature:
    """A procedurally generated creature in the world's ecology."""
    name: str
    tier: int  # 1-5 (power level)
    creature_type: str  # one of CREATURE_TYPES
    habitat: str  # biome or terrain
    description: str
    behavior: str  # one of BEHAVIOR_TYPES
    faction_affiliation: str = ""  # faction name if connected
    body_plan: str = "Quadrupedal"
    challenge_rating: float = 1.0  # TTRPG CR equivalent (0.125 - 30)
    special_abilities: list[str] = field(default_factory=list)
    loot: list[str] = field(default_factory=list)
    is_unique: bool = False
    combat_tactics: str = "Engages directly"
    variant: str = ""
    size: str = "medium"
    suggested_level_range: str = ""
    encounters: str = "1d4"  # standard encounter size

    @property
    def cr_label(self) -> str:
        """Human-readable challenge rating label."""
        if self.challenge_rating < 1:
            return f"CR {self.challenge_rating:.2f}"
        return f"CR {int(self.challenge_rating)}"

    @property
    def tier_label(self) -> str:
        names = {1: "Common", 2: "Uncommon", 3: "Dangerous", 4: "Legendary", 5: "Mythic"}
        return names.get(self.tier, f"Tier {self.tier}")

    @property
    def stat_block(self) -> dict:
        """Generate TTRPG-style stats based on tier and type."""
        base_hp = {1: 15, 2: 45, 3: 85, 4: 150, 5: 250}.get(self.tier, 50)
        base_ac = {1: 12, 2: 14, 3: 16, 4: 18, 5: 20}.get(self.tier, 14)
        base_damage = {1: "1d6+2", 2: "2d6+3", 3: "3d6+4", 4: "4d6+5", 5: "5d6+6"}.get(self.tier, "1d6+2")

        # Size modifiers
        size_hp_map = {"tiny": -5, "small": 0, "medium": 0, "large": 15, "huge": 40, "gargantuan": 80}
        size_ac_map = {"tiny": 2, "small": 1, "medium": 0, "large": -1, "huge": -2, "gargantuan": -4}

        # Creature type modifiers
        type_hp_map = {"beast": 0, "monstrosity": 10, "undead": 5, "dragon": 30,
                        "fey": -5, "elemental": 15, "aberration": 10, "construct": 20,
                        "giant": 25, "humanoid_bandit": -5}

        hp = base_hp + size_hp_map.get(self.size, 0) + type_hp_map.get(self.creature_type, 0)
        ac = base_ac + size_ac_map.get(self.size, 0)

        return {
            "armor_class": max(8, ac),
            "hit_points": max(5, hp),
            "damage_per_round": base_damage,
            "size": self.size,
            "type": self.creature_type,
            "abilities": self.special_abilities[:3],
            "tactics": self.combat_tactics,
        }


# ── Creature Name Parts ───────────────────────────────────────────────

CREATURE_ADJECTIVES = [
    "Elder", "Dire", "Frost", "Shadow", "Crystal", "Ember", "Venom",
    "Thunder", "Silver", "Blood", "Stone", "Mist", "Verdant", "Ashen",
    "Crimson", "Spectral", "Ancient", "Twilight", "Savage",
]

CREATURE_PREFIXES = [
    "Iron", "Wild", "Deep", "Dark", "Fire", "Ice", "Storm",
    "Bone", "Rock", "Wind", "Sun", "Moon",
]


# ── CR Calculation ────────────────────────────────────────────────────

def _tier_to_cr(tier: int, rng: random.Random) -> float:
    """Convert a tier (1-5) to a TTRPG challenge rating."""
    cr_map = {
        1: [0.125, 0.25, 0.5, 1, 2],
        2: [2, 3, 4, 5, 6],
        3: [5, 6, 7, 8, 9, 10],
        4: [10, 12, 14, 16, 18],
        5: [18, 20, 24, 28, 30],
    }
    options = cr_map.get(tier, [1])
    return rng.choice(options)


# ── Description Generation ────────────────────────────────────────────

DESCRIPTION_TEMPLATES = [
    "A {size} {body_plan} creature with {feature1}.",
    "This {behavior} predator hunts the {habitat}, distinguished by {feature1}.",
    "Legends speak of a {size} {creature_type} dwelling in the {habitat}, {feature1}.",
    "A {size} specimen with {feature1} and {feature2} — unmistakable once seen.",
    "Natives warn travellers about the {size} {creature_type} that stalks the {habitat}.",
]

FEATURES = [
    "scales that shimmer like liquid metal",
    "eyes that glow with an inner light",
    "a hide covered in crystalline growths",
    "multiple rows of razor-sharp teeth",
    "a bioluminescent pattern along its flanks",
    "feathers that shift colour in the light",
    "a forked tongue that tastes the air constantly",
    "massive curved horns adorned with trophies",
    "ichor that drips from its maw",
    "a mane of spectral fire",
    "wings that seem to absorb light",
    "a tail tipped with a venomous stinger",
    "armoured plating across its back",
    "tentacles writhing from its shoulders",
    "a third eye glowing on its forehead",
]


# ── Name Generation ───────────────────────────────────────────────────

def _generate_creature_name(creature_type: str, habitat: str, rng: random.Random) -> str:
    """Generate a procedurally appropriate creature name."""
    # Biome-specific named templates
    biome_named = {
        "temperate": [
            "Woodland {base}", "Vale {base}", "Glen {base}", "Forest {base}",
        ],
        "arid": [
            "Sand {base}", "Dune {base}", "Ash {base}", "Waste {base}",
        ],
        "tundra": [
            "Frost {base}", "Ice {base}", "Snow {base}", "Glacier {base}",
        ],
        "tropical": [
            "Jungle {base}", "Moss {base}", "Canopy {base}", "Verdant {base}",
        ],
        "swamp": [
            "Bog {base}", "Marsh {base}", "Swamp {base}", "Fen {base}",
        ],
        "desert": [
            "Sand {base}", "Dune {base}", "Ash {base}", "Waste {base}",
            "Scorched {base}",
        ],
    }

    bases = {
        "beast": ["Wolf", "Bear", "Stag", "Panther", "Boar", "Fox", "Lynx", "Serpent"],
        "monstrosity": ["Hydra", "Manticore", "Behir", "Basilisk", "Chimera", "Wyvern"],
        "undead": ["Wraith", "Ghoul", "Skeleton", "Wight", "Banshee", "Lich Spawn"],
        "dragon": ["Drake", "Wyrm", "Whelp", "Dragon"],
        "fey": ["Sprite", "Pixie", "Dryad", "Satyr", "Nixie"],
        "elemental": ["Elemental", "Sentinel", "Wisp", "Colossus"],
        "aberration": ["Horror", "Abomination", "Elderling", "Watcher"],
        "construct": ["Golem", "Automaton", "Guardian", "Scarab"],
        "giant": ["Giant", "Cyclops", "Titan"],
        "humanoid_bandit": ["Raider", "Berserker", "Outlaw", "Marauder"],
    }

    base = rng.choice(bases.get(creature_type, ["Creature"]))

    # 40% chance of a named template
    if rng.random() < 0.4:
        templates = biome_named.get(habitat, biome_named["temperate"])
        return rng.choice(templates).format(base=base)

    # 30% chance of adjectival prefix
    if rng.random() < 0.5:
        adj = rng.choice(CREATURE_ADJECTIVES)
        return f"{adj} {base}"

    # Plain name
    return base


# ── Main Generation ───────────────────────────────────────────────────

def _get_habitats(world: 'World') -> list[str]:
    """Get the set of biomes present in the world, plus special terrain habitats."""
    biomes = set()
    for region in world.regions:
        biomes.add(region.biome)
    # Scan terrain for special habitats (swamp, desert) not covered by biomes
    if hasattr(world, 'terrain') and world.terrain:
        has_swamp = any(
            world.terrain[y][x] == "swamp"
            for y in range(world.height)
            for x in range(world.width)
        )
        has_desert = any(
            world.terrain[y][x] == "desert"
            for y in range(world.height)
            for x in range(world.width)
        )
        if has_swamp:
            biomes.add("swamp")
        if has_desert:
            biomes.add("desert")
    return list(biomes)


def _pick_creature_type(habitat: str, rng: random.Random) -> str:
    """Pick a creature type weighted by habitat."""
    base_weights = [0.35, 0.20, 0.08, 0.05, 0.07, 0.07, 0.05, 0.05, 0.03, 0.05]
    habitat_biases = {
        "temperate": [0.35, 0.15, 0.10, 0.05, 0.10, 0.05, 0.03, 0.05, 0.02, 0.10],
        "arid": [0.25, 0.25, 0.08, 0.05, 0.02, 0.10, 0.08, 0.05, 0.07, 0.05],
        "tundra": [0.20, 0.15, 0.15, 0.08, 0.05, 0.10, 0.05, 0.02, 0.15, 0.05],
        "tropical": [0.30, 0.25, 0.05, 0.05, 0.15, 0.05, 0.08, 0.02, 0.02, 0.03],
        "swamp": [0.25, 0.25, 0.10, 0.05, 0.08, 0.05, 0.08, 0.02, 0.02, 0.10],
        "desert": [0.20, 0.25, 0.08, 0.05, 0.02, 0.12, 0.08, 0.05, 0.10, 0.05],
    }
    weights = habitat_biases.get(habitat, base_weights)
    return rng.choices(CREATURE_TYPES, weights=weights, k=1)[0]


def _build_creature(world: 'World', habitat: str, rng: random.Random,
                    creature_type: Optional[str] = None,
                    tier: Optional[int] = None,
                    faction: Optional[str] = None) -> Creature:
    """Generate a single creature with full details."""
    if creature_type is None:
        creature_type = _pick_creature_type(habitat, rng)

    if tier is None:
        # Weight tier by rarity (most are tier 1-2)
        tier = rng.choices([1, 2, 3, 4, 5], weights=[0.40, 0.30, 0.18, 0.08, 0.04], k=1)[0]

    name = _generate_creature_name(creature_type, habitat, rng)

    size = rng.choice(TIER_SIZE_MAP.get(tier, ["medium"]))
    body_plan = rng.choice(BODY_PLANS.get(creature_type, ["Quadrupedal"]))
    behavior = rng.choice(BEHAVIOR_TYPES)
    cr = _tier_to_cr(tier, rng)

    # Special abilities (1-3 based on tier)
    num_abilities = min(tier, 3)
    abilities = rng.sample(SPECIAL_ABILITIES, k=num_abilities)

    # Loot based on tier
    loot_options = LOOT_TABLES.get(tier, LOOT_TABLES[1])
    num_loot = rng.randint(1, min(tier + 1, len(loot_options)))
    loot = rng.sample(loot_options, k=num_loot)

    # Description
    template = rng.choice(DESCRIPTION_TEMPLATES)
    num_features = 2 if rng.random() < 0.3 else 1
    features = rng.sample(FEATURES, k=num_features)
    description = template.format(
        size=size, body_plan=body_plan, behavior=behavior,
        habitat=habitat, creature_type=creature_type,
        feature1=features[0],
        feature2=features[1] if len(features) > 1 else features[0],
    )

    tactics = rng.choice(COMBAT_TACTICS)
    is_unique = tier >= 4 or rng.random() < 0.05

    # Suggested level range
    level_map = {1: "1-3", 2: "3-5", 3: "5-8", 4: "8-12", 5: "12+"}

    # Encounter size
    enc_sizes = {1: "2d4", 2: "1d4+1", 3: "1d4", 4: "1d2", 5: "1"}
    encounters = enc_sizes.get(tier, "1d4")

    # Variant
    variant = ""
    if rng.random() < 0.15:
        variant = rng.choice(["Alpha", "Albino", "Elder", "Corrupted", "Blessed", "Infernal"])

    return Creature(
        name=name,
        tier=tier,
        creature_type=creature_type,
        habitat=habitat,
        description=description,
        behavior=behavior,
        faction_affiliation=faction or "",
        body_plan=body_plan,
        challenge_rating=cr,
        special_abilities=abilities,
        loot=loot,
        is_unique=is_unique,
        combat_tactics=tactics,
        variant=variant,
        size=size,
        suggested_level_range=level_map.get(tier, "1-3"),
        encounters=encounters,
    )


def _assign_faction_creatures(world: 'World', rng: random.Random) -> list[Creature]:
    """Generate creatures tied to world factions."""
    if not world.factions:
        return []

    creatures = []
    for faction in world.factions[:4]:  # Limit to top 4 factions
        ftype = faction.faction_type
        pool = FACTION_CREATURES.get(ftype, {})
        if not pool:
            continue

        # Pick 1-2 creature types for this faction
        num = rng.randint(1, min(2, len(pool)))
        keys = rng.sample(list(pool.keys()), k=num)

        for key in keys:
            ctype = key
            if key == "celestial_adjacent":
                ctype = "fey"
            name = pool[key]
            size = rng.choice(["medium", "large"])
            cr_map = {"beast": 2, "monstrosity": 4, "undead": 3, "dragon": 5,
                       "fey": 3, "elemental": 4, "aberration": 4, "construct": 3,
                       "giant": 4, "humanoid_bandit": 2}
            tier = cr_map.get(ctype, 2)

            creatures.append(Creature(
                name=name,
                tier=tier,
                creature_type=ctype if ctype in CREATURE_TYPES else "beast",
                habitat="various",
                description=f"Closely tied to {faction.name}, this creature serves the {faction.faction_type}'s interests.",
                behavior=rng.choice(BEHAVIOR_TYPES),
                faction_affiliation=faction.name,
                body_plan=rng.choice(BODY_PLANS.get(ctype if ctype in CREATURE_TYPES else "beast", ["Quadrupedal"])),
                challenge_rating=_tier_to_cr(tier, rng),
                special_abilities=rng.sample(SPECIAL_ABILITIES, k=min(tier, 3)),
                loot=rng.sample(LOOT_TABLES.get(tier, LOOT_TABLES[1]), k=min(tier, 3)),
                is_unique=tier >= 4,
                combat_tactics=rng.choice(COMBAT_TACTICS),
                size=size,
                suggested_level_range={1: "1-3", 2: "3-5", 3: "5-8", 4: "8-12", 5: "12+"}.get(tier, "1-3"),
                encounters="1d4",
            ))

    return creatures


def generate_bestiary(world: 'World') -> list[Creature]:
    """Generate the bestiary for a world based on its biomes and factions.

    Produces 8-16 creatures covering the world's habitats, plus faction-attuned
    creatures. Uses world.seed + 40000 for deterministic generation.
    """
    rng = random.Random(world.seed + 40000)
    creatures = []
    seen_names_global: set[str] = set()

    habitats = _get_habitats(world)
    if not habitats:
        # Fallback: use all biomes
        habitats = ["temperate", "arid", "tundra", "tropical"]

    num_creatures_per_habitat = max(2, 6 // len(habitats))

    for habitat in habitats:
        seen_names: set[str] = set()
        attempts = 0
        while len([c for c in creatures if c.habitat == habitat]) < num_creatures_per_habitat and attempts < 20:
            attempts += 1
            creature = _build_creature(world, habitat, rng)
            if creature.name not in seen_names and creature.name not in seen_names_global:
                seen_names.add(creature.name)
                seen_names_global.add(creature.name)
                creatures.append(creature)

    # Add faction-attuned creatures
    faction_creatures = _assign_faction_creatures(world, rng)
    for fc in faction_creatures:
        if fc.name not in seen_names_global:
            seen_names_global.add(fc.name)
            creatures.append(fc)

    # Add a few rare/unique creatures
    for _ in range(rng.randint(1, 3)):
        rare_type = rng.choice(CREATURE_TYPES)
        rare_habitat = rng.choice(habitats)
        rare = _build_creature(world, rare_habitat, rng, creature_type=rare_type, tier=4)
        rare.is_unique = True
        # Generate a distinctive name for unique creatures
        rare.name = f"{rng.choice(CREATURE_ADJECTIVES)} {rare.name} of {rng.choice(CREATURE_PREFIXES)}{rng.choice(['-', ' '])}{rng.choice(['Woe', 'Bane', 'Dread', 'Sorrow', 'Ruin'])}" if rng.random() < 0.5 else rare.name
        # Ensure unique creature name is globally unique
        base_name = rare.name
        counter = 1
        while rare.name in seen_names_global:
            rare.name = f"{base_name} {chr(64 + counter)}"  # A, B, C...
            counter += 1
        seen_names_global.add(rare.name)
        creatures.append(rare)

    return creatures


def generate_creature_for_zone(zone, world: 'World', rng: Optional[random.Random] = None) -> Optional[Creature]:
    """Generate a creature appropriate for a specific adventure zone.

    Used to populate adventure zones with specific bestiary entries.
    Returns None if no suitable creature can be generated.
    """
    if rng is None:
        from .world import World
        rng = random.Random(world.seed + 40001 + hash(zone.name) % 100000)

    # Map zone types to creature types
    zone_creature_map = {
        "dungeon": ["undead", "aberration", "construct", "monstrosity"],
        "cave": ["beast", "monstrosity", "elemental", "aberration"],
        "ruin": ["undead", "humanoid_bandit", "monstrosity"],
        "tower": ["construct", "fey", "aberration", "humanoid_bandit"],
        "grove": ["fey", "beast", "elemental"],
        "lair": ["dragon", "monstrosity", "beast"],
        "shrine": ["fey", "elemental", "undead"],
        "mine": ["construct", "elemental", "monstrosity", "beast"],
    }

    # Find the nearest region to determine habitat
    habitat = "temperate"
    for region in world.regions:
        for s in region.settlements:
            if abs(s.x - zone.x) <= 5 and abs(s.y - zone.y) <= 5:
                habitat = region.biome
                break

    candidates = zone_creature_map.get(zone.zone_type, CREATURE_TYPES)
    ctype = rng.choice(candidates)
    tier = min(4, max(1, ["trivial", "easy", "moderate", "hard", "deadly"].index(zone.difficulty) + 1))

    return _build_creature(world, habitat, rng, creature_type=ctype, tier=tier)
