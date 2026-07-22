"""
wyrd — TTRPG Campaign Export (Phase 6).

Produce a Foundry/WorldAnvil-ready JSON document from any snapshot year.
Includes campaign settings, settlement statblocks, NPC rosters, quest hooks,
faction relationships, encounter tables, and random tables.

Usage:
    wyrd export --seed 42 --year 127 --format ttrpg
"""

import json
import math
from datetime import date
from typing import Optional

from .world import World, Region, Settlement, TERRAIN, BIOMES, ADVENTURE_ZONE_TYPES
from .religion import Deity

# Adventure zone treasure tiers (mirrors adventure.py for TTRPG export)
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


def _terrain_percentages(world: World) -> dict[str, float]:
    """Calculate the percentage of each terrain type in the world."""
    counts: dict[str, int] = {}
    total = 0
    for row in world.terrain:
        for t in row:
            counts[t] = counts.get(t, 0) + 1
            total += 1
    return {k: round(v / total * 100, 1) for k, v in sorted(counts.items())}


def _biome_percentages(world: World) -> dict[str, float]:
    """Calculate biome area percentages across regions."""
    biome_counts: dict[str, float] = {}
    total = 0
    for r in world.regions:
        if r.name in getattr(world.lore, 'cultures', {}):
            biome = r.biome
            biome_counts[biome] = biome_counts.get(biome, 0) + 1
            total += 1
    if total == 0:
        return {}
    return {b: round(c / total * 100, 1) for b, c in sorted(biome_counts.items())}


def _map_stats(world: World) -> dict:
    """Return map dimension and land/water stats."""
    land = sum(
        1 for row in world.terrain for t in row
        if t not in ("deep_water", "shallow")
    )
    return {
        "dimensions": f"{world.width}×{world.height}",
        "land_percentage": round(land / world.tiles * 100, 1),
        "water_percentage": round((world.tiles - land) / world.tiles * 100, 1),
        "tiles": world.tiles,
    }


def _build_encounter_tables(world: World) -> dict:
    """
    Build encounter tables derived from the world's terrain distribution.
    Different terrains suggest different encounter types.
    """
    terrain_pct = _terrain_percentages(world)

    ENCOUNTER_POOL = {
        "deep_water": {
            "theme": "Sea & Coast",
            "encounters": [
                "Merchant cog blown off course",
                "Sunken wreck with salvageable cargo",
                "Kraken tentacles breach the surface",
                "Floating debris — remnants of a battle",
                "Shoal of luminescent fish",
                "Pirate longship flying false colours",
                "Whale pod migrating south",
                "Sea serpent basking on the surface",
                "Derelict vessel — crew vanished",
                "Mermaid singing from a rocky outcrop",
            ],
        },
        "shallow": {
            "theme": "Coastal Shallows",
            "encounters": [
                "Fisherfolk hauling in an unusual catch",
                "Tidal pools with rare shellfish",
                "Abandoned fishing weir",
                "Smugglers' cave entrance at low tide",
                "Hermit living on a tidal islet",
                "Stranded sea turtle",
                "Salt-flat causeway to a small island",
                "Driftwood shrine to a sea god",
                "Sea foam bubbles with an unnatural phosphorescence",
                "Half-buried anchor — a shipwreck offshore",
            ],
        },
        "grass": {
            "theme": "Grasslands & Plains",
            "encounters": [
                "Wandering merchant caravan",
                "Wild horse herd stampeding",
                "Abandoned farmstead — door ajar",
                "Travel-worn pilgrim seeking directions",
                "Ruined watchtower on a hill",
                "Bandits ambushing a trade wagon",
                "Shepherd with a flock of sheep",
                "Megalithic stone circle",
                "Patrol of mounted soldiers",
                "Gypsy camp with storytelling and music",
            ],
        },
        "forest": {
            "theme": "Forest & Woodland",
            "encounters": [
                "Fallen tree blocking the path",
                "Hunter tracking a wounded stag",
                "Abandoned forester's hut",
                "Goblin raiding party",
                "Sacred grove with ancient carvings",
                "Herbalist gathering rare moss",
                "Will-o'-the-wisp leading astray",
                "Bear foraging for berries",
                "Hidden cache of poacher's traps",
                "Elven patrol — wary but polite",
            ],
        },
        "hills": {
            "theme": "Hills & Highlands",
            "encounters": [
                "Abandoned mine entrance",
                "Goat herder on the slopes",
                "Ruined hillfort — old battle scars",
                "Bandit camp in a sheltered valley",
                "Dwarven trading post",
                "Fog rolling in — visibility dropping",
                "Ancient standing stone with runes",
                "Eagle's nest with eggs visible",
                "Landslide blocking the mountain pass",
                "Hermit's cave with a warm fire inside",
            ],
        },
        "mountains": {
            "theme": "Mountains & Peaks",
            "encounters": [
                "Narrow pass with avalanche risk",
                "Giant's lair — bones scattered outside",
                "Abandoned monastery clinging to cliffs",
                "Crystal cave entrance glowing faintly",
                "Griffon nest on a high ledge",
                "Mountain shrine with offerings",
                "Frost giant patrol",
                "Hot spring — safe but territorial wildlife nearby",
                "Old dwarven highway — collapsed sections",
                "Storm gathering around the peak",
            ],
        },
        "snow": {
            "theme": "Snow & Tundra",
            "encounters": [
                "Frozen corpse half-buried in snow",
                "Ice cave with strange carvings",
                "Yeti tracks in the fresh snow",
                "Abandoned sled with supplies",
                "Aurora borealis — unsettling beauty",
                "Frozen lake — thin ice danger",
                "Snow-blind traveller begging for shelter",
                "Woolly mammoth herd migrating",
                "Ancient ice-entombed structure",
                "White dragon scale — shed recently",
            ],
        },
        "river": {
            "theme": "Rivers & Waterways",
            "encounters": [
                "Ferryman demanding toll",
                "Logjam blocking navigation",
                "Fishing village with a mysterious catch",
                "River spirit demanding an offering",
                "Broken bridge — ford or swim",
                "Watermill with a dark secret",
                "Canoe with fishing gear — owner nearby?",
                "Abandoned river shrine half-submerged",
                "Trading barge selling odd wares",
                "Nixie trying to lure a traveller",
            ],
        },
    }

    # Build tables from terrain that actually exists in this world
    tables = {}
    for terrain_key, pct in sorted(terrain_pct.items()):
        if pct < 0.5:
            continue
        pool = ENCOUNTER_POOL.get(terrain_key)
        if pool is None:
            continue
        tables[terrain_key] = {
            "theme": pool["theme"],
            "coverage_pct": pct,
            "d10_encounters": pool["encounters"],
        }
    return tables


def _build_random_tables(world: World) -> dict:
    """Build random tables useful for TTRPG sessions, grounded in the world."""
    # Settlement name parts
    settlement_prefixes = [
        "Oak", "Ash", "Fern", "Mist", "Sun", "Star", "Moon", "Raven",
        "Fox", "Wolf", "Bear", "Deer", "Hawk", "Eagle", "Stone",
        "Iron", "Copper", "Gold", "Silver", "Crystal", "Briar",
        "Thorn", "Rush", "Brook", "Dun", "Red", "White", "Grey",
        "Black", "Green", "Moss", "Pine",
    ]
    settlement_suffixes = [
        "dale", "ford", "gate", "grove", "haven", "holt", "keep",
        "mere", "moor", "reach", "ridge", "run", "shire", "stead",
        "vale", "wall", "watch", "wood", "field", "brook",
        "burgh", "bury", "ham", "wick", "worth",
    ]

    # Character names from the world's narrative engine
    character_name_male = [
        "Aldric", "Bran", "Cedric", "Darian", "Eldon", "Finn", "Garret",
        "Hadrian", "Ivor", "Jorik", "Kael", "Leoric", "Maren", "Niall",
        "Orin", "Peregrin", "Quillan", "Roric", "Soren", "Torian", "Ulric",
        "Valen", "Wulfric", "Xander", "Yorick", "Zephyr",
    ]
    character_name_female = [
        "Aelwen", "Briar", "Caelia", "Dara", "Elara", "Fenna", "Gwyn",
        "Hestia", "Ilara", "Juna", "Kira", "Lyra", "Mira", "Niamh",
        "Oriana", "Phaedra", "Riven", "Sylva", "Thalia", "Una", "Veda",
        "Willow", "Xanthe", "Yara", "Zelda",
    ]
    surnames = [
        "Ashwood", "Blackthorn", "Crowheart", "Deepwell", "Emberfall",
        "Fairwind", "Greycloak", "Holloway", "Ironhand", "Jadehelm",
        "Keenblade", "Longmere", "Mistborne", "Nightwalker", "Oakenshield",
        "Proudfoot", "Quickarrow", "Redmane", "Shadowmere", "Thornwood",
        "Underhill", "Valebrook", "Whitehart", "Wyrmbane",
    ]

    # Derive world-specific rumour fragments from the world's regions and features
    rumour_subjects = []
    for region in world.regions:
        rumour_subjects.append(f"ruins in {region.name}")
        if region.settlements:
            rumour_subjects.append(f"the elders of {region.settlements[0].name}")
    if world.lore:
        for feat in world.lore.features[:5]:
            rumour_subjects.append(f"strange lights near {feat['name']}")

    # Random weather table — adapted to world biomes
    weather_options = [
        "Clear and bright — good travelling weather",
        "Overcast with a chance of rain",
        "Heavy rain — roads turn to mud",
        "Fog so thick you can barely see ten feet",
        "Wind howling — ranged attacks at disadvantage",
        "Sweltering heat — exhaustion risk",
        "Bitter cold — need shelter by nightfall",
        "Thunderstorm — lightning strikes nearby",
        "Drizzle and mist — eerie silence",
        "Perfect, still air — almost too quiet",
    ]

    tavern_names = [
        "The {adj} {noun}",
        "The {adj} Inn",
        "The {noun} and {noun2}",
        "{adj} {noun} Tavern",
    ]
    tavern_adjs = [
        "Dancing", "Stumbling", "Golden", "Silver", "Crimson",
        "Laughing", "Sleepy", "Roaring", "Quiet", "Broken",
        "Wandering", "Tipsy", "Merry", "Stubborn",
    ]
    tavern_nouns = [
        "Dragon", "Stag", "Fox", "Bear", "Wolf", "Crown",
        "Lantern", "Cask", "Bowl", "Harp", "Moon", "Star",
        "Bard", "Tankard", "Boot", "Key",
    ]

    return {
        "settlement_names": {
            "description": "Generate new settlement names for founding events",
            "tables": {
                "prefixes": settlement_prefixes,
                "suffixes": settlement_suffixes,
                "example_combinations": [
                    p + s for p, s in
                    [("Oak", "dale"), ("Fox", "ford"), ("Raven", "gate"),
                     ("Iron", "haven"), ("Silver", "wood"), ("Mist", "brook"),
                     ("Wolf", "shire"), ("Stone", "bridge"), ("Black", "moor"),
                     ("Green", "field"), ("Red", "keep"), ("White", "wall"),
                     ("Star", "fall"), ("Copper", "worth")]
                ],
            },
        },
        "character_names": {
            "description": "Generate NPC names on the fly",
            "tables": {
                "male_first_names": character_name_male,
                "female_first_names": character_name_female,
                "surnames": surnames,
            },
        },
        "rumours": {
            "description": "Random rumours the party might overhear in a tavern",
            "world_specific_subjects": rumour_subjects[:10],
        },
        "weather": {
            "description": "Daily weather for travel",
            "d10_table": weather_options,
        },
        "tavern_names": {
            "description": "Generate tavern names for any settlement",
            "templates": tavern_names,
            "adjectives": tavern_adjs,
            "nouns": tavern_nouns,
        },
    }


def _build_settlement_statblocks(world: World) -> list[dict]:
    """Build statblocks for every settlement, using sim state if available."""
    statblocks = []
    for region in world.regions:
        for s in region.settlements:
            # Determine notable features based on kind and region
            features = []
            if s.population >= 2000:
                features.append("City walls and gates")
                features.append("Guild halls and markets")
            elif s.population >= 800:
                features.append("Fortified keep or town hall")
                features.append("Weekly market")
            elif s.population >= 200:
                features.append("Watchtower or palisade")
            else:
                features.append("Small shrine or meeting hall")

            # Determine governing body
            if s.population >= 2000:
                governance = "Ruling council with elected mayor"
            elif s.population >= 800:
                governance = f"Local lord or appointed magistrate"
            elif s.population >= 200:
                governance = "Village elder and council"
            else:
                governance = "Head of household or informal leader"

            statblocks.append({
                "name": s.name,
                "kind": s.kind,
                "region": region.name,
                "biome": region.biome,
                "population": s.population,
                "coords": {"x": s.x, "y": s.y},
                "population_tier": s.char,
                "governance": governance,
                "notable_features": features,
                "defenses": _settlement_defenses(s),
                "economy": _settlement_economy(s, region),
            })
    return statblocks


def _settlement_defenses(s: Settlement) -> list[str]:
    """Describe defenses appropriate to settlement size."""
    if s.population >= 2000:
        return ["Stone walls", "Garrison of professional soldiers", "City gates with portcullis"]
    elif s.population >= 800:
        return ["Palisade or stone wall", "Militia force", "Watchtowers"]
    elif s.population >= 200:
        return ["Wooden palisade", "Local militia"]
    return ["Alert residents", "Sturdy doors"]


def _settlement_economy(s: Settlement, region: Region) -> list[str]:
    """Describe economic activities based on region biome."""
    biome_economies = {
        "temperate": ["Agriculture", "Timber", "Milling"],
        "arid": ["Trade caravans", "Mining", "Salt harvesting"],
        "tundra": ["Fur trapping", "Fishing", "Ivory carving"],
        "tropical": ["Fruit plantations", "Spice gathering", "Shipbuilding"],
    }
    base = biome_economies.get(region.biome, ["Agriculture", "Trade"])
    if s.population >= 800:
        base.append("Craftsmanship and guilds")
    if s.population >= 2000:
        base.append("International trade")
    return base


def _build_npc_roster(world: World) -> list[dict]:
    """Build character roster from the world's narrative engine."""
    if not world.narrative:
        return []
    npcs = []
    for c in world.narrative.characters:
        npc = {
            "name": c.full_name,
            "age": c.age,
            "gender": c.gender,
            "occupation": c.occupation,
            "personality": c.personality_traits,
            "home_region": c.home_region,
            "home_settlement": c.home_settlement,
            "backstory": c.backstory,
            "status": c.status,
        }
        # Build a simple stat block for TTRPG integration
        npc["ttrpg_stats"] = _npc_to_ttrpg_stats(c)
        npcs.append(npc)
    return npcs


def _npc_to_ttrpg_stats(c) -> dict:
    """Infer approximate TTRPG stats from a character's occupation and traits."""
    # Simple 1-20 stat array based on occupation archetype
    base = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}

    occupation_bonuses = {
        "farmer": {"STR": 2, "CON": 2},
        "blacksmith": {"STR": 3, "CON": 2},
        "innkeeper": {"CHA": 2, "WIS": 1},
        "merchant": {"CHA": 2, "INT": 1},
        "hunter": {"DEX": 2, "WIS": 2},
        "fisher": {"DEX": 1, "CON": 2},
        "carpenter": {"STR": 1, "DEX": 2},
        "mason": {"STR": 2, "CON": 2},
        "weaver": {"DEX": 2, "INT": 1},
        "potter": {"DEX": 2, "WIS": 1},
        "herbalist": {"WIS": 2, "INT": 2},
        "soldier": {"STR": 2, "CON": 2, "DEX": 1},
        "guard": {"STR": 2, "CON": 1, "WIS": 1},
        "ranger": {"DEX": 2, "WIS": 2},
        "scout": {"DEX": 3, "WIS": 1},
        "priest": {"WIS": 3, "CHA": 1},
        "sage": {"INT": 3, "WIS": 1},
        "alchemist": {"INT": 3, "DEX": 1},
        "scholar": {"INT": 3, "WIS": 1},
        "cartographer": {"INT": 2, "DEX": 1},
        "miner": {"STR": 2, "CON": 2},
        "tanner": {"CON": 1, "DEX": 1},
        "baker": {"CON": 1, "CHA": 1},
        "brewer": {"CON": 1, "INT": 1},
        "miller": {"STR": 1, "INT": 1},
        "shipwright": {"STR": 2, "DEX": 2},
        "sailor": {"DEX": 2, "CON": 2},
        "trader": {"CHA": 2, "INT": 1},
        "healer": {"WIS": 3, "INT": 1},
        "bard": {"CHA": 3, "DEX": 1},
        "chieftain": {"STR": 2, "CHA": 2},
        "lord": {"CHA": 2, "INT": 1},
        "lady": {"CHA": 2, "WIS": 1},
        "governor": {"INT": 2, "CHA": 2},
        "eldest": {"WIS": 2, "INT": 1},
        "warlord": {"STR": 3, "CON": 2, "CHA": 1},
        "councilor": {"INT": 2, "CHA": 2},
        "judge": {"INT": 2, "WIS": 2},
        "harbormaster": {"INT": 1, "CHA": 1},
        "seneschal": {"INT": 2, "CHA": 1},
    }
    bonuses = occupation_bonuses.get(c.occupation.lower(), {})
    for stat, bonus in bonuses.items():
        base[stat] = min(20, base[stat] + bonus)
    return base


def _build_faction_relationships(world: World) -> list[dict]:
    """Build faction relationships from the world's lore."""
    if not world.lore:
        return []
    return [
        {
            "source": rel.get("source"),
            "source_region": rel.get("source_region"),
            "target": rel.get("target"),
            "target_region": rel.get("target_region"),
            "type": rel.get("type"),
            "description": rel.get("description"),
            "ttrpg_disposition": _relationship_to_disposition(rel.get("type", "trade")),
        }
        for rel in world.lore.relationships
    ]


def _relationship_to_disposition(rel_type: str) -> str:
    """Map relationship type to a TTRPG-friendly disposition label."""
    disposition_map = {
        "trade": "Friendly — open to commerce",
        "rivalry": "Hostile — competing interests",
        "alliance": "Friendly — bound by treaty",
        "feud": "Hostile — active conflict",
        "vassalage": "Unequal — tribute relationship",
        "marriage_tie": "Friendly — bound by family",
        "religious": "Friendly — shared faith",
        "cultural": "Neutral — shared traditions",
    }
    return disposition_map.get(rel_type, "Unknown")


def _build_recent_history(world: World, sim_events: Optional[list] = None) -> list[dict]:
    """Build recent history from sim events, falling back to narrative events."""
    history = []

    # Try simulation events first (most recent, most granular)
    if sim_events:
        # Sort by year descending, take last 30
        sorted_events = sorted(sim_events, key=lambda e: e.year, reverse=True)
        for e in sorted_events[:30]:
            history.append({
                "year": e.year,
                "type": e.event_type,
                "description": e.description,
                "affected_settlements": e.affected_settlements,
                "affected_regions": e.affected_regions,
            })
        return history

    # Fallback to narrative events
    if world.narrative and world.narrative.events:
        sorted_events = sorted(world.narrative.events, key=lambda e: e.year, reverse=True)
        for e in sorted_events:
            history.append({
                "year": e.year,
                "type": e.event_type,
                "description": e.description,
                "characters_involved": e.characters_involved,
            })
        return history

    return history


def _build_quest_hooks(world: World) -> list[dict]:
    """Build quest hooks from the world's narrative."""
    if not world.narrative or not world.narrative.quests:
        return []
    return [
        {
            "name": q.name,
            "type": q.quest_type,
            "difficulty": q.difficulty,
            "description": q.description,
            "giver": q.giver_character,
            "location": q.giver_settlement,
            "target_region": q.target_region,
            "rewards": q.rewards,
            "is_active": q.is_active,
            "suggested_level": _difficulty_to_level(q.difficulty),
        }
        for q in world.narrative.quests
    ]


def _difficulty_to_level(difficulty: str) -> str:
    """Map quest difficulty to suggested character level."""
    mapping = {
        "trivial": "1-2",
        "easy": "1-3",
        "moderate": "3-5",
        "hard": "5-8",
        "epic": "8+",
    }
    return mapping.get(difficulty, "Any")


def _build_geography(world: World) -> dict:
    """Build a comprehensive geography section."""
    regions = []
    for region in world.regions:
        settlements = [
            {
                "name": s.name,
                "kind": s.kind,
                "population": s.population,
                "coords": {"x": s.x, "y": s.y},
            }
            for s in region.settlements
        ]
        region_data = {
            "name": region.name,
            "biome": region.biome,
            "biome_description": BIOMES.get(region.biome, {}).get("desc", "Unknown"),
            "settlements": settlements,
        }

        # Add lore if available
        if world.lore:
            if region.name in world.lore.region_descriptions:
                region_data["description"] = world.lore.region_descriptions[region.name]
            if region.name in world.lore.histories:
                region_data["history"] = world.lore.histories[region.name]
            if region.name in world.lore.cultures:
                region_data["culture_name"] = world.lore.cultures[region.name]
            if region.name in world.lore.culture_descriptions:
                region_data["culture_descriptors"] = world.lore.culture_descriptions[region.name]

            # Attach features belonging to this region
            region_data["features"] = [
                {
                    "type": f["type"],
                    "name": f["name"],
                    "description": f.get("desc", ""),
                }
                for f in world.lore.features
                if f.get("region") == region.name
            ]

        regions.append(region_data)

    # Terrain summary
    terrain_pct = _terrain_percentages(world)
    biomes = _biome_percentages(world)

    return {
        "map": _map_stats(world),
        "regions": regions,
        "terrain_distribution": terrain_pct,
        "biome_distribution": biomes,
        "terrain_legend": {
            key: {"char": info["char"], "description": info["desc"]}
            for key, info in TERRAIN.items()
        },
    }


def _build_chronicles_eras(world: World) -> list[dict]:
    """Build era timeline from chronicles if available."""
    if not world.chronicles:
        return []
    return [
        {
            "name": era.name,
            "era_type": era.era_type,
            "years": f"{era.start_year}–{era.end_year}",
            "description": era.description,
            "events": era.events,
            "world_modifiers": era.world_modifiers,
        }
        for era in world.chronicles.eras
    ]


def export_world_ttrpg(
    world: World,
    snapshot_year: Optional[int] = None,
    sim_events: Optional[list] = None,
) -> str:
    """
    Export a world as a TTRPG-ready JSON document.

    Args:
        world: The world to export (may already have sim state applied)
        snapshot_year: The simulation year this world represents (if any)
        sim_events: Simulation events to include in the history section

    Returns:
        JSON string formatted for Foundry VTT / WorldAnvil import
    """
    total_pop = sum(s.population for r in world.regions for s in r.settlements)

    # Current era from chronicles
    current_era = None
    if world.chronicles and world.chronicles.eras:
        present_eras = [e for e in world.chronicles.eras if e.is_present]
        if present_eras:
            current_era = present_eras[0].name
        else:
            current_era = world.chronicles.eras[-1].name

    document = {
        # Metadata
        "meta": {
            "format": "wyrd-ttrpg",
            "wyrd_version": "0.1.0",
            "generated": date.today().isoformat(),
            "seed": world.seed,
            "snapshot_year": snapshot_year,
            "description": (
                f"TTRPG campaign export for wyrd #{world.seed}"
                + (f" at year {snapshot_year}" if snapshot_year is not None else "")
            ),
        },

        # Campaign Settings
        "campaign_settings": {
            "name": f"wyrd #{world.seed}",
            "seed": world.seed,
            "current_year": snapshot_year or 0,
            "current_era": current_era,
            "total_population": total_pop,
            "total_settlements": sum(len(r.settlements) for r in world.regions),
            "region_count": len(world.regions),
            "world_modifiers": getattr(world, 'world_modifiers', []),
        },

        # Geography
        "geography": _build_geography(world),

        # Chronicles / Eras
        "chronicles": _build_chronicles_eras(world),

        # Settlement Statblocks
        "settlements": _build_settlement_statblocks(world),

        # NPC Roster
        "npcs": _build_npc_roster(world),

        # Faction Relationships
        "factions": _build_faction_relationships(world),

        # Quest Hooks
        "quests": _build_quest_hooks(world),

        # Recent History
        "history": _build_recent_history(world, sim_events),

        # Encounter Tables (grounded in terrain)
        "encounters": _build_encounter_tables(world),

        # Random Tables (for GM use during sessions)
        "random_tables": _build_random_tables(world),

        # Pantheon & Religion
        "pantheon": _build_pantheon_section(world),

        # Adventure Zones
        "adventure_zones": _build_adventure_zones(world),
    }

    return json.dumps(document, indent=2, ensure_ascii=False)


def _build_adventure_zones(world: World) -> list[dict]:
    """Build adventure zones section for TTRPG export."""
    if not world.adventure_zones:
        return []
    zones = []
    for z in world.adventure_zones:
        info = ADVENTURE_ZONE_TYPES.get(z.zone_type, {})
        tier = TREASURE_TIERS[z.treasure_tier - 1] if 1 <= z.treasure_tier <= 5 else TREASURE_TIERS[0]
        difficulty_desc = DIFFICULTY_DESCRIPTIONS.get(z.difficulty, "")
        zones.append({
            "name": z.name,
            "type": z.zone_type,
            "type_description": info.get("desc", ""),
            "location": {"region": z.region, "x": z.x, "y": z.y},
            "difficulty": z.difficulty,
            "difficulty_description": difficulty_desc,
            "inhabitants": z.inhabitants,
            "description": z.description,
            "treasure_tier": tier,
            "is_cleared": z.is_cleared,
            "quest_hook": z.quest_hook,
        })
    return zones


def _build_pantheon_section(world: World) -> dict:
    """Build a comprehensive pantheon section for TTRPG export."""
    pantheon = getattr(world, 'pantheon', None)
    if not pantheon or not pantheon.religions:
        return {
            "religions": [],
            "total_deities": 0,
            "total_holy_sites": 0,
        }

    religions_data = []
    for religion in pantheon.religions:
        # Deities
        deities_data = []
        for d in religion.pantheon:
            deity_entry = {
                "name": d.name,
                "surname": d.surname,
                "full_name": f"{d.name} {d.surname}",
                "domains": d.domains,
                "alignment": d.alignment,
                "symbol": d.symbol,
                "holy_animal": d.holy_animal,
                "description": d.description,
                "clergy_title": d.clergy_title,
                "is_primary": d.is_primary,
            }
            # Add TTRPG stat block for the deity (conceptually)
            deity_entry["ttrpg_stats"] = _deity_to_ttrpg_stats(d)
            deities_data.append(deity_entry)

        # Holy sites
        sites_data = []
        for s in religion.holy_sites:
            sites_data.append({
                "name": s.name,
                "deity": s.deity_name,
                "settlement": s.settlement,
                "region": s.region,
                "site_type": s.site_type,
                "description": s.description,
                "suggested_encounter_level": _site_to_encounter_level(s.site_type),
            })

        # Region adherence
        adherent_regions = [
            rn for rn, rel_name in pantheon.region_religion.items()
            if rel_name == religion.name
        ]

        religions_data.append({
            "name": religion.name,
            "description": religion.description,
            "primary_deity": religion.primary_deity,
            "deities": deities_data,
            "clergy_titles": religion.clergy_titles,
            "holy_days": religion.holy_days,
            "tenets": religion.tenets,
            "holy_sites": sites_data,
            "adherent_regions": adherent_regions,
            "adherent_region_count": len(adherent_regions),
        })

    return {
        "religions": religions_data,
        "region_religion_map": pantheon.region_religion,
        "total_deities": pantheon.total_deities,
        "total_holy_sites": pantheon.total_holy_sites,
        "dominant_religion": pantheon.dominant_religion.name if pantheon.dominant_religion else None,
    }


def _deity_to_ttrpg_stats(d: Deity) -> dict:
    """Generate TTRPG-style stats for a deity based on domains."""
    base = {"STR": 18, "DEX": 18, "CON": 18, "INT": 18, "WIS": 18, "CHA": 18}

    domain_bonuses = {
        "War": {"STR": 2, "CON": 2},
        "Nature": {"WIS": 2, "CON": 1},
        "Knowledge": {"INT": 2, "WIS": 1},
        "Death": {"WIS": 2, "INT": 1},
        "Trickery": {"DEX": 2, "CHA": 2},
        "Forge": {"STR": 2, "CON": 2},
        "Life": {"WIS": 2, "CHA": 1},
        "Tempest": {"STR": 1, "CON": 2},
        "Twilight": {"WIS": 2, "DEX": 1},
        "Wealth": {"INT": 2, "CHA": 2},
        "Fate": {"WIS": 2, "INT": 2},
        "Wilderness": {"DEX": 2, "WIS": 1},
    }

    for domain in d.domains:
        bonuses = domain_bonuses.get(domain, {})
        for stat, bonus in bonuses.items():
            base[stat] = min(30, base[stat] + bonus)

    # Deities are beyond mortal limits — boost primary stats
    base["WIS"] = min(30, base["WIS"] + 2)
    base["INT"] = min(30, base["INT"] + 2)

    return base


def _site_to_encounter_level(site_type: str) -> str:
    """Suggest an encounter level range based on holy site type."""
    levels = {
        "temple": "3-7",
        "shrine": "1-3",
        "monastery": "5-9",
        "oracle": "5-10",
        "grove": "2-6",
        "sanctuary": "1-5",
    }
    return levels.get(site_type, "Any")
