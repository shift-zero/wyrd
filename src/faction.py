"""
wyrd — Faction System (Phase 11).

Political, economic, and cultural entities that shape the world.
Factions have territories, leaders, goals, relationships, and influence.
"""

import random
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World

# ── Faction Types ──────────────────────────────────────────────────

FACTION_TYPES = {
    "kingdom": {
        "desc": "Sovereign realm with a hereditary ruler",
        "color": 226,  # gold
        "icon": "♛",
    },
    "duchy": {
        "desc": "Territory ruled by a duke or duchess",
        "color": 220,
        "icon": "♚",
    },
    "merchant_guild": {
        "desc": "Trade consortium controlling commerce",
        "color": 172,  # orange
        "icon": "⚖",
    },
    "arcane_order": {
        "desc": "Mages and scholars pursuing magical knowledge",
        "color": 99,   # purple
        "icon": "✦",
    },
    "religious_order": {
        "desc": "Devotees spreading faith and doctrine",
        "color": 226,  # gold
        "icon": "†",
    },
    "druidic_circle": {
        "desc": "Nature guardians preserving the wilds",
        "color": 34,   # green
        "icon": "♣",
    },
    "thieves_guild": {
        "desc": "Underground network of rogues and spies",
        "color": 240,  # dark grey
        "icon": "◈",
    },
    "mercenary_company": {
        "desc": "Soldiers-for-hire with shifting loyalties",
        "color": 196,  # red
        "icon": "⚔",
    },
    "cult": {
        "desc": "Secretive sect worshipping forbidden powers",
        "color": 160,  # dark red
        "icon": "◉",
    },
    "barbarian_clan": {
        "desc": "Fierce warrior tribe beyond the settled lands",
        "color": 130,  # brown
        "icon": "▲",
    },
    "noble_house": {
        "desc": "Aristocratic family with political influence",
        "color": 205,  # pink
        "icon": "◇",
    },
    "mining_consortium": {
        "desc": "Industrial concern exploiting mineral wealth",
        "color": 172,  # dark yellow
        "icon": "▣",
    },
}

FACTION_TYPE_KEYS = list(FACTION_TYPES.keys())

# ── Faction Goals ──────────────────────────────────────────────────

FACTION_GOALS = {
    "kingdom": [
        "Expand territorial borders into neighboring regions",
        "Secure trade routes and protect merchant caravans",
        "Defeat rival kingdoms in a war of unification",
        "Build a mighty fortress to project power",
        "Forge lasting alliances through strategic marriages",
    ],
    "duchy": [
        "Win favor with the crown through loyal service",
        "Suppress rebellion in the hinterlands",
        "Develop rich agricultural lands for prosperity",
        "Marry into the royal bloodline for prestige",
    ],
    "merchant_guild": [
        "Establish a monopoly on a valuable trade good",
        "Build guild halls in every major settlement",
        "Undermine rival guilds through economic warfare",
        "Secure exclusive trade rights with foreign powers",
    ],
    "arcane_order": [
        "Discover a lost school of magic",
        "Recruit the most promising magic-users",
        "Build the largest magical library in the world",
        "Uncover ancient arcane artifacts of power",
    ],
    "religious_order": [
        "Convert the unbelievers through pilgrimage and preaching",
        "Build grand temples in every city",
        "Root out heresy and corruption",
        "Discover a holy relic of immense power",
    ],
    "druidic_circle": [
        "Protect ancient forests from the spread of civilization",
        "Restore blighted lands to their natural state",
        "Maintain the balance between nature and mortal ambition",
        "Guard sacred groves from desecration",
    ],
    "thieves_guild": [
        "Infiltrate every level of government and commerce",
        "Eliminate rival criminal organizations",
        "Control the black market in major cities",
        "Amass secret leverage over influential figures",
    ],
    "mercenary_company": [
        "Secure a lucrative long-term contract with a kingdom",
        "Build a reputation as the finest soldiers in the land",
        "Accumulate enough wealth to buy land and settle",
        "Seize control of a small territory through conquest",
    ],
    "cult": [
        "Summon a dark entity into the mortal world",
        "Gather ancient relics for a forbidden ritual",
        "Recruit powerful figures into the fold",
        "Bring about a prophesied age of darkness",
    ],
    "barbarian_clan": [
        "Prove martial superiority through raids and battles",
        "Unite the scattered clans under a single war-chief",
        "Claim fertile lands from settled kingdoms",
        "Honour the ancestors with glorious deeds in battle",
    ],
    "noble_house": [
        "Secure a seat on the ruling council",
        "Arrange advantageous marriages for political gain",
        "Amass enough wealth to rival the crown",
        "Expose and eliminate rival houses' secrets",
    ],
    "mining_consortium": [
        "Discover a rich new vein of precious ore",
        "Expand mining operations into untapped mountains",
        "Develop advanced smelting techniques",
        "Crush competition through price wars and sabotage",
    ],
}

# ── Leadership Titles ──────────────────────────────────────────────

LEADER_TITLES = {
    "kingdom": ["King", "Queen"],
    "duchy": ["Duke", "Duchess"],
    "merchant_guild": ["Guildmaster", "Guildmistress", "High Merchant"],
    "arcane_order": ["Archmage", "Grand Sorcerer", "Magus"],
    "religious_order": ["High Priest", "High Priestess", "Patriarch", "Matriarch"],
    "druidic_circle": ["Archdruid", "Elder", "Guardian"],
    "thieves_guild": ["Shadowmaster", "Guildmaster", "The Unseen"],
    "mercenary_company": ["Captain-General", "Warlord", "Commander"],
    "cult": ["Dark Prophet", "High Priest", "Oracle of Whispers"],
    "barbarian_clan": ["Chieftain", "War-Chief", "Khan"],
    "noble_house": ["Lord", "Lady", "Count", "Countess"],
    "mining_consortium": ["Foreman-Executive", "Excavator Prime", "Ore Baron"],
}

# ── Relationship Types ─────────────────────────────────────────────

RELATIONSHIP_TYPES = [
    "alliance",
    "trade_agreement",
    "vassalage",
    "rivalry",
    "hostility",
    "non_aggression",
    "cultural_ties",
    "religious_affinity",
]

RELATIONSHIP_ICONS = {
    "alliance": "⚝",
    "trade_agreement": "⇄",
    "vassalage": "→",
    "rivalry": "⚔",
    "hostility": "✗",
    "non_aggression": "—",
    "cultural_ties": "♫",
    "religious_affinity": "†",
}

RELATIONSHIP_COLORS = {
    "alliance": 33,
    "trade_agreement": 28,
    "vassalage": 130,
    "rivalry": 196,
    "hostility": 160,
    "non_aggression": 240,
    "cultural_ties": 213,
    "religious_affinity": 99,
}


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class FactionRelationship:
    """A relationship between two factions."""
    faction_a: str
    faction_b: str
    rel_type: str  # one of RELATIONSHIP_TYPES
    description: str = ""


@dataclass
class Faction:
    """A political, economic, or cultural entity in the world."""
    name: str
    faction_type: str  # one of FACTION_TYPES keys
    territory: list[str] = field(default_factory=list)  # region names
    leader_name: str = ""
    leader_title: str = ""
    influence: int = 50       # 0-100
    wealth: int = 50          # 0-100
    military: int = 50        # 0-100
    stability: int = 50       # 0-100
    reputation: str = "neutral"  # benevolent, respected, neutral, feared, hated
    goals: list[str] = field(default_factory=list)
    description: str = ""
    color: int = 226

    @property
    def type_info(self) -> dict:
        return FACTION_TYPES.get(self.faction_type, {"desc": "Unknown", "color": 250, "icon": "?"})

    @property
    def icon(self) -> str:
        return self.type_info.get("icon", "?")

    @property
    def power_score(self) -> int:
        """Overall power rating (0-300) combining influence, wealth, military."""
        return self.influence + self.wealth + self.military


def _capitalize(s: str) -> str:
    """Capitalize the first letter of a string."""
    if not s:
        return s
    return s[0].upper() + s[1:]


# ── Name Generation ────────────────────────────────────────────────

FACTION_PREFIXES = ["The Grand", "The Crimson", "The Free", "The Iron",
                    "The Silver", "The Golden", "The Ancient", "The Shadow",
                    "The Eternal", "The Northern", "The Southern", "The Eastern",
                    "The Western", "The High", "The Deep", "The Verdant"]

FACTION_NOUNS = ["Covenant", "Compact", "Alliance", "Brotherhood", "Conclave",
                 "Council", "Dominion", "Guild", "Order", "Sisterhood",
                 "Sovereignty", "Syndicate", "Union", "League", "Circle"]

KINGDOM_NOUNS = ["Kingdom", "Realm", "Dominion", "Crownlands", "Sovereignty",
                 "March", "Protectorate", "Territory"]


def _generate_faction_name(faction_type: str, rng: random.Random) -> str:
    """Generate a faction name appropriate to its type."""
    if faction_type == "kingdom":
        prefix = rng.choice(["Kingdom of", "Realm of", "Crown of", "Dominion of"])
        noun = rng.choice(FACTION_PREFIXES).replace("The ", "")
        return f"{prefix} {noun}"
    elif faction_type == "duchy":
        prefix = rng.choice(["Duchy of", "Dukedom of", "March of"])
        noun = rng.choice(FACTION_PREFIXES).replace("The ", "")
        return f"{prefix} {noun}"
    elif faction_type == "noble_house":
        prefix = "House"
        name = rng.choice(["Ashford", "Blackwood", "Casterly", "Drakon", "Ebonheart",
                           "Frostvale", "Greyhaven", "Holloway", "Ironcrest", "Jadehall",
                           "Knighton", "Lionheart", "Moonshadow", "Nightfall"])
        return f"{prefix} {name}"
    elif faction_type in ("barbarian_clan",):
        names = ["Bloodaxe", "Frostmane", "Ironhide", "Skullcrusher", "Thunderhoof",
                 "Wolfheart", "Bearclaw", "Ravenshadow", "Stormbringer"]
        name = rng.choice(names)
        return f"The {name} Clan"
    elif faction_type == "cult":
        names = ["The Veiled Hand", "The Sunless Choir", "The Crimson Communion",
                 "The Obsidian Tongue", "The Bleeding Star", "The Whispers Below",
                 "The Ashen Covenant", "The Dusk Vigil"]
        return rng.choice(names)
    elif faction_type == "druidic_circle":
        names = ["The Emerald Circle", "The Root and Stone", "The Wildheart Pact",
                 "The Verdant Vigil", "The Thornbound", "The Ash Guardians",
                 "The Glenwardens"]
        return rng.choice(names)

    # Default patterns
    adj = rng.choice(FACTION_PREFIXES)
    noun = rng.choice(FACTION_NOUNS)
    return f"{adj} {noun}"


def _generate_leader_name(faction_type: str, rng: random.Random) -> tuple[str, str]:
    """Generate a leader name and title for a faction."""
    titles = LEADER_TITLES.get(faction_type, ["Leader"])
    title = rng.choice(titles)

    # Generate a simple name
    first_names = ["Aldric", "Brynn", "Cassian", "Dorian", "Elara", "Finn",
                   "Genevieve", "Harlan", "Isolde", "Jasper", "Kaelen",
                   "Lyra", "Marius", "Nyx", "Orin", "Petra", "Quinn",
                   "Rowan", "Seraphine", "Thorne", "Ursa", "Vesper",
                   "Wren", "Xara", "Yarrow", "Zephyr"]

    surnames = ["Blackthorn", "Crowley", "Darkmoor", "Embervale", "Frosthold",
                 "Greymane", "Holloway", "Ironwood", "Jadeheart", "Knightsbridge",
                 "Lionfeld", "Moonshadow", "Nightbreath", "Oakenshield",
                 "Paledusk", "Ravencrest", "Silverkeep", "Thornwood",
                 "Underhill", "Wolfsbane", "Wyrmheart"]

    first = rng.choice(first_names)
    surname = rng.choice(surnames)
    return f"{first} {surname}", title


def _generate_description(faction_type: str, name: str, territory: list[str],
                           leader: str, title: str, rng: random.Random) -> str:
    """Generate a description for a faction."""
    type_info = FACTION_TYPES.get(faction_type, {"desc": "organization"})
    type_desc = type_info["desc"]
    region_str = ", ".join(territory) if territory else "a contested region"

    templates = [
        f"A {type_desc} that holds sway over {region_str}.",
        f"{name} commands the loyalty of {region_str}, with {title} {leader} at its helm.",
        f"Founded in ages past, {name} draws its strength from {region_str}.",
        f"{title} {leader} rules {name} with an iron will from their seat in {region_str}.",
        f"The {type_desc} known as {name} maintains a presence throughout {region_str}.",
    ]

    return rng.choice(templates)


# ── Main Generation ───────────────────────────────────────────────

def generate_factions(world: 'World') -> list[Faction]:
    """Generate factions for a world based on its regions and seed."""
    rng = random.Random(world.seed + 30000)  # deterministic offset

    factions = []
    num_factions = max(2, min(len(world.regions) + rng.randint(0, 2), 8))

    # Assign each region to at least one faction
    available_regions = [r.name for r in world.regions]
    rng.shuffle(available_regions)

    # Always create a kingdom or duchy as the dominant faction
    dominant_type = rng.choice(["kingdom", "kingdom", "duchy"])
    dom_name = _generate_faction_name(dominant_type, rng)
    dom_territory = [available_regions[0]] if available_regions else []
    dom_leader, dom_title = _generate_leader_name(dominant_type, rng)
    dom_goals = rng.sample(FACTION_GOALS.get(dominant_type, FACTION_GOALS["kingdom"]),
                           min(3, len(FACTION_GOALS.get(dominant_type, FACTION_GOALS["kingdom"]))))

    dom_faction = Faction(
        name=dom_name,
        faction_type=dominant_type,
        territory=dom_territory,
        leader_name=dom_leader,
        leader_title=dom_title,
        influence=rng.randint(60, 90),
        wealth=rng.randint(50, 85),
        military=rng.randint(55, 90),
        stability=rng.randint(50, 80),
        reputation=rng.choice(["respected", "benevolent", "neutral"]),
        goals=dom_goals,
        description=_generate_description(dominant_type, dom_name, dom_territory,
                                           dom_leader, dom_title, rng),
        color=FACTION_TYPES.get(dominant_type, {}).get("color", 226),
    )
    factions.append(dom_faction)

    # Generate additional factions
    for i in range(1, min(num_factions, len(available_regions) + 1)):
        # Pick a type different from the dominant one
        f_type = rng.choice([t for t in FACTION_TYPE_KEYS if t != dominant_type])
        f_name = _generate_faction_name(f_type, rng)
        f_territory = [available_regions[i]] if i < len(available_regions) else []
        f_leader, f_title = _generate_leader_name(f_type, rng)
        f_goals = rng.sample(FACTION_GOALS.get(f_type, FACTION_GOALS["merchant_guild"]),
                             min(2, len(FACTION_GOALS.get(f_type, FACTION_GOALS["merchant_guild"]))))

        faction = Faction(
            name=f_name,
            faction_type=f_type,
            territory=f_territory,
            leader_name=f_leader,
            leader_title=f_title,
            influence=rng.randint(20, 70),
            wealth=rng.randint(20, 80),
            military=rng.randint(15, 75),
            stability=rng.randint(30, 75),
            reputation=rng.choice(["respected", "neutral", "feared", "neutral"]),
            goals=f_goals,
            description=_generate_description(f_type, f_name, f_territory,
                                               f_leader, f_title, rng),
            color=FACTION_TYPES.get(f_type, {}).get("color", 250),
        )
        factions.append(faction)

    # Generate relationships between factions
    relationships = _generate_relationships(factions, rng)
    world.faction_relationships = relationships

    return factions


def _generate_relationships(factions: list[Faction],
                             rng: random.Random) -> list[FactionRelationship]:
    """Generate relationships between factions."""
    relationships = []
    for i in range(len(factions)):
        for j in range(i + 1, len(factions)):
            # Determine relationship type based on faction types and randomness
            fa, fb = factions[i], factions[j]

            # Same-type factions are often rivals
            if fa.faction_type == fb.faction_type:
                rel_type = rng.choices(
                    ["rivalry", "alliance", "non_aggression", "hostility"],
                    weights=[0.4, 0.1, 0.3, 0.2],
                    k=1
                )[0]
            # Kingdoms and duchies often have vassal relationships
            elif (fa.faction_type == "kingdom" and fb.faction_type == "duchy") or \
                 (fb.faction_type == "kingdom" and fa.faction_type == "duchy"):
                rel_type = rng.choice(["vassalage", "alliance", "rivalry"])
            # Religious orders and kingdoms often have religious ties
            elif "religious" in [fa.faction_type, fb.faction_type]:
                rel_type = rng.choices(
                    ["religious_affinity", "alliance", "non_aggression", "hostility"],
                    weights=[0.3, 0.2, 0.3, 0.2],
                    k=1
                )[0]
            else:
                rel_type = rng.choice(RELATIONSHIP_TYPES)

            desc = _describe_relationship(fa.name, fb.name, rel_type)
            relationships.append(FactionRelationship(
                faction_a=fa.name,
                faction_b=fb.name,
                rel_type=rel_type,
                description=desc,
            ))

    return relationships


def _describe_relationship(name_a: str, name_b: str, rel_type: str) -> str:
    """Generate a description for a relationship."""
    templates = {
        "alliance": [
            f"{name_a} and {name_b} are bound by a mutual defense pact.",
            f"A formal alliance unites {name_a} and {name_b}.",
            f"{name_a} and {name_b} have sworn to support each other in times of war.",
        ],
        "trade_agreement": [
            f"Merchants of {name_a} and {name_b} enjoy favourable trade terms.",
            f"A trade agreement keeps commerce flowing between {name_a} and {name_b}.",
            f"{name_a} supplies resources to {name_b} in exchange for finished goods.",
        ],
        "vassalage": [
            f"{name_a} owes fealty to {name_b}.",
            f"{name_b} holds dominion over {name_a} as a vassal state.",
            f"Through treaty and tribute, {name_a} serves {name_b}.",
        ],
        "rivalry": [
            f"Centuries of competition have bred deep resentment between {name_a} and {name_b}.",
            f"{name_a} and {name_b} vie for the same resources and influence.",
            f"A bitter rivalry divides {name_a} and {name_b}.",
        ],
        "hostility": [
            f"Open conflict rages between {name_a} and {name_b}.",
            f"Blood has been spilled — {name_a} and {name_b} are at war.",
            f"Raids and skirmishes are common between {name_a} and {name_b}.",
        ],
        "non_aggression": [
            f"{name_a} and {name_b} have agreed to mutual non-interference.",
            f"A pact of non-aggression keeps the peace between {name_a} and {name_b}.",
        ],
        "cultural_ties": [
            f"Shared cultural heritage binds {name_a} and {name_b}.",
            f"{name_a} and {name_b} celebrate the same festivals and traditions.",
        ],
        "religious_affinity": [
            f"{name_a} and {name_b} share a common faith and worship.",
            f"Shared religious practices unite {name_a} and {name_b}.",
        ],
    }

    selected = templates.get(rel_type, [f"{name_a} and {name_b} have a {rel_type} relationship."])
    import random as _random
    return _random.Random(hash(name_a + name_b + rel_type)).choice(selected)
