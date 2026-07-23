"""
wyrd — Lore Engine (Phase 2).

Procedural generation of culture names, geographical features,
history snippets, and settlement relationships.
All seed-deterministic: same seed → same lore, always.
"""

import random
from dataclasses import dataclass, field
from typing import Optional
from .world import World, Region


# ── Culture Templates ────────────────────────────────────────────────

CULTURES = {
    "temperate": {
        "name_patterns": [
            "The {adj} {noun}",
            "{noun}folk",
            "The {noun} Valley",
            "{adj} Realms",
            "The {noun} Compact",
        ],
        "adjectives": [
            "Green", "Golden", "High", "Free", "Old", "Grey", "Silver",
            "Bright", "Deep", "Fair", "Pale", "Verdant", "Amber", "Misty",
        ],
        "nouns": [
            "Meadow", "Glen", "Vale", "Wood", "Field", "Brook", "Dell",
            "March", "Shire", "Heath", "Thicket", "Copse", "Weald",
        ],
        "descriptors": [
            "known for their rich soil and bountiful harvests",
            "whose hedgerows mark ancient boundaries",
            "who gather at stone circles under the full moon",
            "masters of timber and stone",
            "who sing ballads of forgotten kings",
            "weavers of intricate wool and linen",
            "whose alehouses welcome all travellers",
        ],
    },
    "arid": {
        "name_patterns": [
            "The {adj} Sands",
            "{noun} Expanse",
            "{adj} {noun}",
            "The {noun} Waste",
            "The {adj} Tribes",
        ],
        "adjectives": [
            "Scorched", "Bleak", "Crimson", "Dust", "Cracked", "Bone",
            "Flint", "Withered", "Ash", "Ember", "Iron", "Salt", "Copper",
        ],
        "nouns": [
            "Dune", "Badland", "Mesa", "Gorge", "Steppe", "Waste",
            "Scar", "Dryland", "Dustbowl", "Ravine", "Canyon",
        ],
        "descriptors": [
            "who follow the hidden springs through the wastes",
            "crafters of intricate sand-etched glass",
            "who trade in salt and rare metals",
            "whose caravans thread the dry riverbeds",
            "guardians of oases sacred to forgotten gods",
            "horsemen who know every stone in the expanse",
            "whose woven tents withstand the fiercest storms",
        ],
    },
    "tundra": {
        "name_patterns": [
            "The {adj} {noun}",
            "{noun} Clans",
            "The {adj} Reach",
            "{noun} Tundra",
            "The {adj} Expanse",
        ],
        "adjectives": [
            "Frozen", "White", "Bitter", "Cold", "Silent", "Pale",
            "Bleak", "Hard", "Endless", "Hoar", "Grey", "North",
        ],
        "nouns": [
            "Frost", "Snow", "Ice", "Winter", "Wind", "Glacier",
            "Permafrost", "Tundra", "Star", "Mist", "Shadow",
        ],
        "descriptors": [
            "who hunt the great white elk across the ice",
            "cavers who shelter in geothermal vaults",
            "who craft saga-knots from walrus ivory",
            "whose sled-dogs know the safe paths through the snow",
            "shamans who read omens in the aurora",
            "who trade in furs and carved bone",
            "whose oral histories reach back to the first frost",
        ],
    },
    "tropical": {
        "name_patterns": [
            "The {adj} {noun}",
            "{noun} Dominion",
            "The {adj} Isles",
            "{noun} Coast",
            "The {adj} Canopy",
        ],
        "adjectives": [
            "Emerald", "Verdant", "Jade", "Vibrant", "Lush", "Crimson",
            "Teal", "Coral", "Dew", "Feathered", "Wild", "Sun",
        ],
        "nouns": [
            "Jungle", "Canopy", "Reef", "Lagoon", "Delta", "Mangrove",
            "Fern", "Cascade", "Harbour", "Strand", "Croft",
        ],
        "descriptors": [
            "who navigate the canopy on rope-bridges",
            "painters who use crushed shells and flowers",
            "who dive for pearls in the barrier reef",
            "whose fruit wines are famous across the continent",
            "builders of tree-top sanctuaries",
            "storytellers who weave epic poems from palm fibre",
            "whose boats bear carved prows of sacred beasts",
        ],
    },
}

# ── Geographical Feature Templates ──────────────────────────────────

MOUNTAIN_FEATURES = [
    "{adj} Mountains", "{adj} Ridge", "{adj} Range", "{adj} Spine",
    "{adj} Peaks", "The {adj} Horns", "{adj} Crest", "{adj} Teeth",
    "The {adj} Highlands", "{adj} Massif",
]

MOUNTAIN_ADJS = [
    "Iron", "Dragon", "Bone", "Crystal", "Storm", "Thunder",
    "Fang", "Razor", "Grey", "White", "Dark", "Silver", "Red",
    "Cloud", "Sunset", "Ashen", "Frozen", "Eagle", "Wyrm",
]

RIVER_FEATURES = [
    "{adj} River", "The {adj} Flow", "{adj} Water", "River {adj}",
    "{adj} Run", "The {adj} Rush",
]

RIVER_ADJS = [
    "Winding", "Silver", "Deep", "Swift", "Crystal", "Dark",
    "Broad", "Quiet", "Red", "Black", "Clear", "Wandering",
    "Golden", "Misty", "Singing",
]

BAY_FEATURES = [
    "{adj} Bay", "{adj} Sound", "{adj} Inlet", "{adj} Harbour",
    "The {adj} Gulf", "{adj} Firth",
]

BAY_ADJS = [
    "Sheltered", "Wide", "Deep", "Quiet", "Rough", "Silver",
    "Pearl", "Coral", "Grey", "Emerald", "Hidden",
]

FOREST_FEATURES = [
    "{adj} Forest", "{adj} Wood", "The {adj} Woods",
    "{adj} Thicket", "{adj} Copse", "The {adj} Timberland",
]

FOREST_ADJS = [
    "Dark", "Whispering", "Deep", "Old", "Shadow", "Emerald",
    "Tangle", "High", "Silent", "Green", "Ancient", "Murk",
]

SWAMP_FEATURES = [
    "{adj} Bog", "{adj} Marsh", "{adj} Fen", "{adj} Wetlands",
    "{adj} Mire", "{adj} Swamp", "The {adj} Morass",
]

SWAMP_ADJS = [
    "Choking", "Bleak", "Murky", "Black", "Still", "Stagnant",
    "Whispering", "Veiled", "Drowned", "Sunken", "Hissing",
]

DESERT_FEATURES = [
    "{adj} Wastes", "{adj} Desert", "{adj} Sands", "{adj} Dunes",
    "{adj} Expanse", "{adj} Barrens", "The {adj} Dust",
]

DESERT_ADJS = [
    "Scorching", "Endless", "Bleak", "Crimson", "Silent", "Burning",
    "Ashen", "Shifting", "Salt", "Obsidian", "Forgotten",
]


# ── History Templates ───────────────────────────────────────────────

REGION_HISTORIES = [
    "Founded during the {era}, {region} was once {past_state}. "
    "Today it {present_state}.",

    "In the {era}, settlers from the {origin} arrived and "
    "established {region}. {pivot_event}.",

    "{region} has stood since the {era}. "
    "Its people remember when {memory}.",

    "The {era} saw {region} rise from {past_state} to "
    "become {present_state}. {pivot_event}.",

    "Legends say {region} was {origin_story}. "
    "Whether truth or legend, it now {present_state}.",
]

ERAS = [
    "Age of Embers", "First Bloom", "Reckoning of Stones",
    "Duskfall", "Serpent's Era", "Time of Weeping", "Golden Age",
    "Shadow Years", "Iron Century", "Age of Ashes",
]

PAST_STATES = [
    "a scattering of hunter-gatherer camps",
    "a contested frontier between warring clans",
    "a sacred burial ground of an earlier people",
    "an abandoned outpost of a fallen empire",
    "a peaceful federation of hill-forts",
    "a haven for outcasts and exiles",
    "a pilgrimage site for sun-worshippers",
    "a network of cave-dwellings and tunnels",
]

PRESENT_STATES = [
    "prospers under the rule of an elected council of elders",
    "maintains its ancient traditions despite outside pressure",
    "guards its borders fiercely, trusting no outsider",
    "has become a crossroads of trade and culture",
    "endures hard times but its people remain resilient",
    "thrives on the rich resources of the land",
    "keeps the old ways, guided by oracles and seers",
    "is known for its festivals, music, and art",
]

PIVOT_EVENTS = [
    "A great fire reshaped its destiny",
    "A stranger brought knowledge of metal-working",
    "The old king died without heir, and the people chose their own way",
    "A plague swept through, and only half survived",
    "A neighbouring power attempted conquest and was repelled",
    "The river changed course, stranding the old port",
    "A wandering prophet foretold prosperity, and it came to pass",
    "A dragon was slain in the nearby mountains",
    "A child found a buried cache of ancient tools",
    "A flood washed away the old quarter, and a new one rose",
]

ORIGIN_STORIES = [
    "born from the union of a mortal and a spirit of the land",
    "carved from the living rock by giants in ancient times",
    "where a falling star kindled the first hearth-fire",
    "founded where two rivers meet, a sacred place",
    "first settled by those who followed a migrating herd",
    "built atop the ruins of an even older settlement",
]

ORIGIN_PLACES = [
    "Sunken Kingdom", "Crystal City", "Iron Coast", "Far Isles",
    "Hollow Mountain", "Ember Plains", "Silver Marches",
    "Obsidian Gates", "Thousand Pillars", "White Vale",
]


# ── Settlement Relationships ────────────────────────────────────────

RELATIONSHIP_TYPES = [
    "trade", "rivalry", "alliance", "feud", "vassalage",
    "marriage_tie", "religious", "cultural",
]

RELATIONSHIP_TEMPLATES = {
    "trade": "{source} and {target} {exchange} via the {route}.",
    "rivalry": "{source} and {target} have long {dispute}.",
    "alliance": "The {treaty} binds {source} and {target} together.",
    "feud": "Blood has been spilled between {source} and {target} since {cause}.",
    "vassalage": "{source} pays tribute to {target} each {period}.",
    "marriage_tie": "The ruling families of {source} and {target} are joined by marriage.",
    "religious": "{source} and {target} share the shrine of {shrine}.",
    "cultural": "{source} and {target} celebrate the {festival} together each year.",
}

EXCHANGES = [
    "trade grain for iron tools", "exchange timber for woven cloth",
    "barter salt-cured fish for leather", "swap livestock for pottery",
    "deal in rare herbs and remedies", "trade ore for finished goods",
]

ROUTES = [
    "Old Dirt Road", "Coastal Trading Route", "Pilgrim's Path",
    "Northern Trace", "Salt Road", "Timber Trail",
]

DISPUTES = [
    "quarrelled over fishing rights in the lake",
    "disputed the border meadow for generations",
    "competed for control of the mountain pass",
    "argued over access to the sacred grove",
    "fought over the old watchtower and its lands",
]

TREATIES = [
    "Iron Compact", "Pact of Shared Waters", "Oath of the Grove",
    "Bond of Amber", "Covenant of the Dawn", "Treaty of the Ford",
]

CAUSES = [
    "the theft of a sacred relic", "a disputed inheritance",
    "a betrayal at a wedding feast", "the assassination of a chieftain",
    "a massacre at the border market",
]

PERIODS = [
    "harvest moon", "winter solstice", "spring equinox",
    "autumn gathering", "new year's dawn",
]

SHRINES = [
    "the Weeping Stone", "the Altar of Stars", "the Sunken Chapel",
    "the Oracle's Pool", "the Cave of Whispers",
]

FESTIVALS = [
    "Lantern Festival", "Bonefire Night", "Rite of Blossoms",
    "Feast of Falling Leaves", "Dance of the Masks",
]


# ── Lore Generation ─────────────────────────────────────────────────

@dataclass
class Lore:
    """Complete lore for a generated world."""
    seed: int
    region_descriptions: dict[str, str] = field(default_factory=dict)
    cultures: dict[str, str] = field(default_factory=dict)
    culture_descriptions: dict[str, list[str]] = field(default_factory=dict)
    features: list[dict] = field(default_factory=list)
    histories: dict[str, str] = field(default_factory=dict)
    relationships: list[dict] = field(default_factory=list)


def _make_name(rng: random.Random, templates: list[str],
               adjectives: list[str], nouns: list[str]) -> str:
    """Generate a name from a template list."""
    tpl = rng.choice(templates)
    adj = rng.choice(adjectives)
    noun = rng.choice(nouns)
    return tpl.format(adj=adj, noun=noun)


def generate_lore(world: World) -> Lore:
    """
    Generate complete lore for a world.
    Seed-deterministic: same seed, regions, and biome → same lore.
    """
    lore_seed = world.seed + 1000000  # offset from terrain seed
    rng = random.Random(lore_seed)
    lore = Lore(seed=lore_seed)

    # ── 1. Per-region lore ─────────────────────────────────────────
    for i, region in enumerate(world.regions):
        reg_seed = lore_seed + i * 500
        reg_rng = random.Random(reg_seed)

        biome = region.biome
        culture_data = CULTURES.get(biome, CULTURES["temperate"])

        # Culture name
        culture_name = _make_name(
            reg_rng,
            culture_data["name_patterns"],
            culture_data["adjectives"],
            culture_data["nouns"],
        )
        lore.cultures[region.name] = culture_name

        # Culture description (1-2 descriptors)
        num_desc = reg_rng.randint(1, 2)
        descriptors = reg_rng.sample(culture_data["descriptors"], num_desc)
        lore.culture_descriptions[region.name] = descriptors

        # Region description
        settlement_count = len(region.settlements)
        settle_plural = "s" if settlement_count != 1 else ""
        settle_verb = "dot" if settlement_count != 1 else "dots"
        settlement_part = (
            f"Its {settlement_count} settlement{settle_plural} "
            f"{settle_verb} the landscape."
        )
        lore.region_descriptions[region.name] = settlement_part

        # History snippet
        history_tpl = reg_rng.choice(REGION_HISTORIES)
        era = reg_rng.choice(ERAS)
        past_state = reg_rng.choice(PAST_STATES)
        present_state = reg_rng.choice(PRESENT_STATES)
        pivot = reg_rng.choice(PIVOT_EVENTS)
        memory = f"the {reg_rng.choice(ERAS).lower()}, {reg_rng.choice(PAST_STATES)}"
        origin_story = reg_rng.choice(ORIGIN_STORIES)
        origin = reg_rng.choice(ORIGIN_PLACES)

        history = history_tpl.format(
            era=era,
            region=region.name,
            past_state=past_state,
            present_state=present_state,
            pivot_event=pivot,
            memory=memory,
            origin_story=origin_story,
            origin=origin,
        )
        lore.histories[region.name] = history

        # Named features per region (1-3 features)
        # Check what terrain types exist in this region's approximate area
        num_features = reg_rng.randint(1, 3)
        # Determine which feature types are relevant based on biome and terrain
        feature_options = ["mountain", "river", "forest"]
        if region.biome != "tundra":
            # Coastal biomes can have bays; deserts can appear in arid regions
            feature_options.append("bay")
        if region.biome in ("temperate", "tropical"):
            feature_options.append("swamp")
        if region.biome in ("arid",):
            feature_options.append("desert")
        for _ in range(num_features):
            feature_type = reg_rng.choice(feature_options)
            if feature_type == "mountain":
                name = _make_name(reg_rng, MOUNTAIN_FEATURES, MOUNTAIN_ADJS, [""])
                name = name.replace("  ", " ").strip()
                lore.features.append({
                    "type": "mountain_range",
                    "name": name,
                    "region": region.name,
                    "desc": f"A range of peaks that shapes the weather of {region.name}.",
                })
            elif feature_type == "river":
                name = _make_name(reg_rng, RIVER_FEATURES, RIVER_ADJS, [""])
                name = name.replace("  ", " ").strip()
                lore.features.append({
                    "type": "river",
                    "name": name,
                    "region": region.name,
                    "desc": f"The life-giving waters that flow through {region.name}.",
                })
            elif feature_type == "bay":
                name = _make_name(reg_rng, BAY_FEATURES, BAY_ADJS, [""])
                name = name.replace("  ", " ").strip()
                lore.features.append({
                    "type": "bay",
                    "name": name,
                    "region": region.name,
                    "desc": f"A coastal inlet bordering {region.name}.",
                })
            elif feature_type == "forest":
                name = _make_name(reg_rng, FOREST_FEATURES, FOREST_ADJS, [""])
                name = name.replace("  ", " ").strip()
                lore.features.append({
                    "type": "forest",
                    "name": name,
                    "region": region.name,
                    "desc": f"A dense woodland within {region.name}'s domain.",
                })
            elif feature_type == "swamp":
                name = _make_name(reg_rng, SWAMP_FEATURES, SWAMP_ADJS, [""])
                name = name.replace("  ", " ").strip()
                lore.features.append({
                    "type": "swamp",
                    "name": name,
                    "region": region.name,
                    "desc": f"A vast wetland that dominates the lowlands of {region.name}.",
                })
            elif feature_type == "desert":
                name = _make_name(reg_rng, DESERT_FEATURES, DESERT_ADJS, [""])
                name = name.replace("  ", " ").strip()
                lore.features.append({
                    "type": "desert",
                    "name": name,
                    "region": region.name,
                    "desc": f"A scorched expanse stretching across {region.name}.",
                })

    # ── 2. Settlement relationships ─────────────────────────────────
    all_settlements = []
    for region in world.regions:
        for s in region.settlements:
            # Use (region_name, settlement_name) as unique key
            all_settlements.append((region.name, s.name, f"{s.name} ({region.name})"))

    num_relationships = min(len(all_settlements) * 2, 12)
    used_pairs: set[frozenset[tuple[str, str]]] = set()
    if len(all_settlements) >= 2:
        for _ in range(num_relationships):
            rel_rng = random.Random(lore_seed + _ * 100 + 999)
            source_region, source_name, source_label = rel_rng.choice(all_settlements)
            target_pool = [(r, n, l) for r, n, l in all_settlements
                           if r != source_region or n != source_name]
            if not target_pool:
                continue
            target_region, target_name, target_label = rel_rng.choice(target_pool)

            # Deduplicate: skip if we've already got this pair in either direction
            pair = frozenset([(source_region, source_name), (target_region, target_name)])
            if pair in used_pairs:
                continue
            used_pairs.add(pair)

            rel_type = rel_rng.choice(RELATIONSHIP_TYPES)
            tpl = RELATIONSHIP_TEMPLATES[rel_type]

            rel_text = tpl.format(
                source=source_label,
                target=target_label,
                exchange=rel_rng.choice(EXCHANGES),
                route=rel_rng.choice(ROUTES),
                dispute=rel_rng.choice(DISPUTES),
                treaty=rel_rng.choice(TREATIES),
                cause=rel_rng.choice(CAUSES),
                period=rel_rng.choice(PERIODS),
                shrine=rel_rng.choice(SHRINES),
                festival=rel_rng.choice(FESTIVALS),
            )

            lore.relationships.append({
                "source": source_name,
                "source_region": source_region,
                "target": target_name,
                "target_region": target_region,
                "type": rel_type,
                "description": rel_text,
            })

    return lore
