"""
wyrd — Pantheon & Religion System (Phase 9: The Pantheon).

Generate a world's pantheon of deities, religious traditions, holy sites,
and clergy — all grounded in the world's biomes, cultures, and geography.

Seed-deterministic: same seed + same world → same pantheon, always.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from .world import World


# ── Divine Domains ─────────────────────────────────────────────────────

ALL_DOMAINS = [
    {
        "name": "War",
        "description": "Battle, strategy, courage, and conflict",
        "default_alignment": "neutral",
        "symbols": ["Crossed swords", "Shield with a scar", "Bloodied axe"],
        "holy_animals": ["Wolf", "Hawk", "Boar"],
    },
    {
        "name": "Nature",
        "description": "Forests, beasts, growth, and the wild",
        "default_alignment": "neutral",
        "symbols": ["Oak leaf", "Antlered crown", "Green flame"],
        "holy_animals": ["Stag", "Bear", "Owl"],
    },
    {
        "name": "Knowledge",
        "description": "Wisdom, memory, secrets, and invention",
        "default_alignment": "good",
        "symbols": ["Open tome", "All-seeing eye", "Quill and scroll"],
        "holy_animals": ["Raven", "Fox", "Owl"],
    },
    {
        "name": "Death",
        "description": "Mortality, passage, ancestors, and repose",
        "default_alignment": "neutral",
        "symbols": ["Skull and hourglass", "Scythe", "White mask"],
        "holy_animals": ["Raven", "Moth", "Snake"],
    },
    {
        "name": "Trickery",
        "description": "Deception, luck, change, and shadows",
        "default_alignment": "chaotic",
        "symbols": ["Mask with two faces", "Dice", "Forked tongue"],
        "holy_animals": ["Fox", "Rat", "Spider"],
    },
    {
        "name": "Forge",
        "description": "Craft, creation, fire, and labor",
        "default_alignment": "good",
        "symbols": ["Hammer and anvil", "Ring of fire", "Cog and gear"],
        "holy_animals": ["Badger", "Horse", "Bee"],
    },
    {
        "name": "Life",
        "description": "Healing, family, harvest, and renewal",
        "default_alignment": "good",
        "symbols": ["Wheat sheaf", "Healing hands", "Sunrise crest"],
        "holy_animals": ["Dove", "Rabbit", "Swan"],
    },
    {
        "name": "Tempest",
        "description": "Storms, sea, sky, and destruction",
        "default_alignment": "chaotic",
        "symbols": ["Lightning bolt", "Crashing wave", "Hurricane eye"],
        "holy_animals": ["Eagle", "Shark", "Dragon"],
    },
    {
        "name": "Twilight",
        "description": "Dusk, dawn, transition, and guardianship",
        "default_alignment": "lawful",
        "symbols": ["Setting sun", "Silver shield", "Lantern in fog"],
        "holy_animals": ["Wolf", "Firefly", "Stag"],
    },
    {
        "name": "Wealth",
        "description": "Trade, gold, ambition, and negotiation",
        "default_alignment": "neutral",
        "symbols": ["Golden coin", "Scales balanced", "Open chest"],
        "holy_animals": ["Raven", "Fox", "Bee"],
    },
    {
        "name": "Fate",
        "description": "Destiny, prophecy, time, and weaving",
        "default_alignment": "lawful",
        "symbols": ["Three spindles", "Endless knot", "Hourglass"],
        "holy_animals": ["Spider", "Owl", "Turtle"],
    },
    {
        "name": "Wilderness",
        "description": "Hunting, survival, solitude, and the untamed",
        "default_alignment": "neutral",
        "symbols": ["Bow and arrow", "Claw mark", "Moon silhouette"],
        "holy_animals": ["Wolf", "Falcon", "Lynx"],
    },
]

DEITY_TITLE_PREFIXES = [
    "The", "The Great", "The Eternal", "The Silent", "The Golden",
    "The Crimson", "The Ashen", "The Iron", "The Jade", "The Silver",
    "The Watcher", "The Keeper", "The Lord of", "The Lady of",
]

DEITY_TITLE_SUFFIXES = [
    "Shadows", "Flame", "the Deep", "Thunder", "Bones",
    "the Wild", "Stars", "the Forge", "Tides", "Roots",
    "the Gale", "Silver", "the Dawn", "the Veil",
]

DEITY_NAMES_MALE = [
    "Aethon", "Baelor", "Caelum", "Durnir", "Ephynor",
    "Faelan", "Gorim", "Haelos", "Ithron", "Jorund",
    "Kaelos", "Lorath", "Maelos", "Nyrion", "Orik",
    "Paelon", "Rallor", "Sulian", "Theron", "Valdris",
    "Wylen", "Xalos", "Yrdin", "Zephyron",
]

DEITY_NAMES_FEMALE = [
    "Aelindra", "Brynn", "Caelia", "Dhalia", "Ephyra",
    "Faelwen", "Glyndra", "Hestara", "Ilyana", "Jorina",
    "Kaelith", "Lyralla", "Mirael", "Nymira", "Orith",
    "Phaedra", "Rilya", "Sylindra", "Thalia", "Unae",
    "Vaela", "Wynna", "Xylia", "Yndra",
]

DEITY_SURNAMES = [
    "the Flame-Keeper", "the Shadow-Walker", "the Storm-Bringer",
    "the Earth-Shaker", "the Star-Reader", "the Tide-Turner",
    "the Bone-Weaver", "the Truth-Speaker", "the Gate-Opener",
    "the Fate-Spinner", "the Frost-Hearted", "the Sun-Born",
    "the Night-Watcher", "the Wind-Rider", "the Deep-Dweller",
]

CLERGY_TITLES = {
    "War": ["Warlord-Priest", "Battle-Chanter", "Iron-Speaker", "Siege-Master"],
    "Nature": ["Druid-Elder", "Green-Warden", "Root-Speaker", "Wild-Heart"],
    "Knowledge": ["Sage-Pontiff", "Truth-Seeker", "Arch-Librarian", "Oracle"],
    "Death": ["Bone-Keeper", "Soul-Herder", "Grave-Warden", "Ancestor-Voice"],
    "Trickery": ["Shadow-Priest", "Mask-Bearer", "Whisperer", "Chance-Weaver"],
    "Forge": ["Hearth-Priest", "Anvil-Chanter", "Forge-Master", "Spark-Tender"],
    "Life": ["Sun-Priest", "Healing-Hand", "Harvest-Blesser", "Life-Giver"],
    "Tempest": ["Storm-Caller", "Sea-Priest", "Sky-Watcher", "Thunder-Speaker"],
    "Twilight": ["Dusk-Warden", "Dawn-Singer", "Gate-Keeper", "Twilight-Guardian"],
    "Wealth": ["Coin-Priest", "Trade-Lord", "Gold-Speaker", "Bargain-Maker"],
    "Fate": ["Weaver", "Time-Keeper", "Prophecy-Speaker", "Thread-Spinner"],
    "Wilderness": ["Hunt-Master", "Solitude-Priest", "Trail-Blossom", "Beast-Tongue"],
}

HOLY_DAY_NAMES = [
    "The {season} Conclave",
    "Feast of {deity}",
    "Night of {domain}",
    "The {deity}'s Vigil",
    "Day of Ashes",
    "The Great Weaving",
    "Sun-Turning",
    "Moon-Dance",
    "The {season} Sacrifice",
    "Bone-Fire Night",
]

TEMPLE_NAMES = [
    "Sanctum of {deity}",
    "{deity}'s Hall",
    "The {adj} Temple",
    "Temple of the {domain}",
    "Shrine of {deity}",
    "The {adj} Cathedral",
    "Monastery of {domain}",
    "The {deity}'s Vigil",
]

TEMPLE_ADJECTIVES = [
    "Golden", "Silver", "Crimson", "Ashen", "Jade",
    "Amber", "Sapphire", "Ivory", "Obsidian", "Crystal",
    "Verdant", "Sun-Blessed", "Moon-Touched", "Iron-Wrought",
]

RELIGION_NAMES = [
    "The {deity} Creed",
    "The Way of {domain}",
    "The Circle of {deity}",
    "{adjective} Faith",
    "The Church of {deity}",
]

RELIGION_ADJECTIVES = [
    "Orthodox", "Reformed", "Ancient", "True", "High",
    "Northern", "Southern", "Eastern", "Western", "Hidden",
]

TENETS_POOL = [
    "Honor the earth that sustains you",
    "Speak truth even when it burns",
    "Protect the weak without expectation of reward",
    "Knowledge is the light that conquers darkness",
    "Death is not an end, but a passage",
    "Change is the only constant — embrace it",
    "What is built with skill honors the divine",
    "Life is sacred in all its forms",
    "The storm cleanses what stagnation corrupts",
    "Guard the thresholds between worlds",
    "Wealth is a tool, not a master",
    "The wild teaches what civilization forgets",
    "Every thread of fate has purpose",
    "The strong must guide the lost",
    "Silence holds truths that words cannot carry",
]


# ── Data Models ─────────────────────────────────────────────────────────


@dataclass
class Deity:
    """A single deity in the world's pantheon."""
    name: str
    surname: str
    domains: list[str]
    alignment: str
    symbol: str
    holy_animal: str
    description: str
    clergy_title: str
    is_primary: bool = False


@dataclass
class HolySite:
    """A sacred location tied to a deity."""
    name: str
    deity_name: str
    settlement: str
    region: str
    site_type: str  # temple, shrine, monastery, oracle, grove
    description: str


@dataclass
class Religion:
    """A structured religious tradition within the world."""
    name: str
    description: str
    pantheon: list[Deity] = field(default_factory=list)
    clergy_titles: list[str] = field(default_factory=list)
    holy_days: list[str] = field(default_factory=list)
    tenets: list[str] = field(default_factory=list)
    primary_deity: Optional[str] = None
    holy_sites: list[HolySite] = field(default_factory=list)


@dataclass
class PantheonSystem:
    """The complete religious landscape of a world."""
    seed: int
    religions: list[Religion] = field(default_factory=list)
    region_religion: dict[str, str] = field(default_factory=dict)
    # Maps region name → religion name

    @property
    def total_deities(self) -> int:
        return sum(len(r.pantheon) for r in self.religions)

    @property
    def total_holy_sites(self) -> int:
        return sum(len(r.holy_sites) for r in self.religions)

    @property
    def dominant_religion(self) -> Optional[Religion]:
        """Return the religion with the most adherent regions."""
        if not self.religions:
            return None
        return max(self.religions, key=lambda r: list(self.region_religion.values()).count(r.name))


# ── Generation ──────────────────────────────────────────────────────────


def _select_domains_for_world(world: World, rng: random.Random) -> list[dict]:
    """Select domains that fit the world's biomes and cultures."""
    present_biomes = set(r.biome for r in world.regions)
    num_settlements = sum(len(r.settlements) for r in world.regions)

    # Biome-to-domain affinity
    biome_affinity = {
        "temperate": ["Life", "Knowledge", "Forge", "Twilight"],
        "arid": ["War", "Death", "Wealth", "Tempest"],
        "tundra": ["Death", "Wilderness", "Fate", "Twilight"],
        "tropical": ["Nature", "Life", "Wilderness", "Trickery"],
    }

    scored_domains = []
    for domain in ALL_DOMAINS:
        score = rng.random() * 3  # baseline randomness
        # Biome affinity bonus
        for biome in present_biomes:
            if domain["name"] in biome_affinity.get(biome, []):
                score += 3
        # Cultural diversity bonus
        if world.lore and len(world.lore.cultures) > 3:
            score += 1  # more cultures → more divine aspects
        # Large worlds get more domains
        if num_settlements > 15:
            score += 1
        scored_domains.append((score, domain))

    scored_domains.sort(key=lambda x: (-x[0], rng.random()))

    # Pick 4-8 domains for the pantheon
    num_domains = rng.randint(4, min(8, len(scored_domains)))
    return [d for _, d in scored_domains[:num_domains]]


def _generate_deity_name(rng: random.Random, gender: Optional[str] = None) -> tuple[str, str]:
    """Generate a deity name with surname."""
    if gender is None:
        gender = rng.choice(["male", "female"])
    if gender == "male":
        first = rng.choice(DEITY_NAMES_MALE)
    else:
        first = rng.choice(DEITY_NAMES_FEMALE)
    surname = rng.choice(DEITY_SURNAMES)
    return first, surname


def _generate_deity(domain: dict, rng: random.Random, is_primary: bool = False) -> Deity:
    """Generate a single deity from a domain template."""
    gender = rng.choice(["male", "female"])
    first, surname = _generate_deity_name(rng, gender)
    symbol = rng.choice(domain["symbols"])
    holy_animal = rng.choice(domain["holy_animals"])

    # Clergy title
    clergy_pool = CLERGY_TITLES.get(domain["name"], ["Priest"])
    clergy_title = rng.choice(clergy_pool)

    # Description
    dominion_desc = domain["description"].lower()
    alignment_desc = {
        "good": "benevolent",
        "evil": "malevolent",
        "lawful": "just and orderly",
        "chaotic": "unpredictable",
        "neutral": "balanced",
    }.get(domain["default_alignment"], "mysterious")

    desc = (
        f"{first} {surname} is the {alignment_desc} deity of {dominion_desc}. "
        f"Their sacred symbol is {symbol.lower()}, and the {holy_animal.lower()} "
        f"is their holy creature."
    )

    return Deity(
        name=first,
        surname=surname,
        domains=[domain["name"]],
        alignment=domain["default_alignment"],
        symbol=symbol,
        holy_animal=holy_animal,
        description=desc,
        clergy_title=clergy_title,
        is_primary=is_primary,
    )


def _generate_holy_sites(
    religion_name: str,
    deities: list[Deity],
    world: World,
    rng: random.Random,
) -> list[HolySite]:
    """Generate holy sites tied to settlements in the world."""
    sites = []
    all_settlements = [
        (s, r.name) for r in world.regions for s in r.settlements
    ]

    if not all_settlements:
        return sites

    # Pick a subset of settlements to have holy sites
    num_sites = min(rng.randint(len(deities), len(all_settlements)), len(all_settlements))
    selected = rng.sample(all_settlements, num_sites)

    site_types = ["temple", "shrine", "monastery", "oracle", "grove", "sanctuary"]

    for i, (settlement, region_name) in enumerate(selected):
        deity = deities[i % len(deities)]
        site_type = rng.choice(site_types)
        adj = rng.choice(TEMPLE_ADJECTIVES)

        name_templates = [
            f"{adj} Temple of {deity.name}",
            f"{deity.name}'s {site_type.title()}",
            f"Shrine of {deity.name} at {settlement.name}",
            f"{adj} Hall of {deity.name}",
        ]
        name = rng.choice(name_templates)

        # Generate description based on site type
        type_descriptions = {
            "temple": f"A grand {adj.lower()} temple dedicated to {deity.name} {deity.surname}, serving as the spiritual heart of {settlement.name}.",
            "shrine": f"A humble shrine to {deity.name} at the edge of {settlement.name}, where locals leave offerings.",
            "monastery": f"A secluded monastery of {deity.name}'s clergy, nestled near {settlement.name}. Monks study {', '.join(deity.domains).lower()}.",
            "oracle": f"An oracle-sanctum of {deity.name} in {settlement.name}, where diviners interpret signs and portents.",
            "grove": f"A sacred grove consecrated to {deity.name} near {settlement.name}. Ancient trees bear devotional carvings.",
            "sanctuary": f"A sanctuary of {deity.name} in {settlement.name}, offering refuge to those in need.",
        }

        sites.append(HolySite(
            name=name,
            deity_name=deity.name,
            settlement=settlement.name,
            region=region_name,
            site_type=site_type,
            description=type_descriptions.get(site_type, f"A holy site of {deity.name} in {settlement.name}."),
        ))

    return sites


def _generate_religion_name(deity: Deity, rng: random.Random) -> str:
    """Generate a name for a religion based on its primary deity."""
    template = rng.choice(RELIGION_NAMES)
    adjective = rng.choice(RELIGION_ADJECTIVES)
    return template.format(
        deity=deity.name,
        domain=deity.domains[0],
        adjective=adjective,
    )


def _generate_holy_days(deities: list[Deity], rng: random.Random) -> list[str]:
    """Generate holy day names for a religion's calendar."""
    seasons = ["Spring", "Summer", "Autumn", "Winter"]
    num_days = rng.randint(2, 5)
    days = []
    for _ in range(num_days):
        deity = rng.choice(deities)
        season = rng.choice(seasons)
        template = rng.choice(HOLY_DAY_NAMES)
        days.append(template.format(
            deity=deity.name,
            domain=deity.domains[0],
            season=season,
        ))
    return days


def _generate_tenets(rng: random.Random) -> list[str]:
    """Select a set of core religious tenets."""
    num_tenets = rng.randint(3, 6)
    return rng.sample(TENETS_POOL, min(num_tenets, len(TENETS_POOL)))


def generate_pantheon(world: World, seed: Optional[int] = None) -> PantheonSystem:
    """
    Generate a complete pantheon and religious landscape for a world.

    Seed-deterministic: same world + same seed → same pantheon.

    Args:
        world: The world to generate a pantheon for
        seed: Optional override seed (defaults to world.seed)

    Returns:
        A PantheonSystem with religions, deities, and holy sites
    """
    rng = random.Random(seed if seed is not None else world.seed)

    # Select divine domains based on world biomes
    selected_domains = _select_domains_for_world(world, rng)

    # Generate deities from domains
    deities = []
    for i, domain in enumerate(selected_domains):
        is_primary = (i == 0)
        deity = _generate_deity(domain, rng, is_primary=is_primary)
        deities.append(deity)

    # Split into 1-2 religions based on alignment/cultural divides
    num_religions = rng.randint(1, min(2, len(deities)))
    if num_religions == 1:
        pantheon_groups = [deities]
    else:
        # Split: try to divide by alignment
        lawful_neutral = [d for d in deities if d.alignment in ("lawful", "neutral", "good")]
        chaotic_evil = [d for d in deities if d.alignment in ("chaotic", "evil")]
        rng.shuffle(lawful_neutral)
        rng.shuffle(chaotic_evil)

        if chaotic_evil and lawful_neutral:
            # Ensure each gets at least 2 deities
            if len(lawful_neutral) >= 2 and len(chaotic_evil) >= 2:
                pantheon_groups = [lawful_neutral, chaotic_evil]
            else:
                # Uneven split — mix them
                rng.shuffle(deities)
                split = len(deities) // 2
                pantheon_groups = [deities[:split], deities[split:]]
        else:
            rng.shuffle(deities)
            split = len(deities) // 2
            pantheon_groups = [deities[:split], deities[split:]]

    # Build religions
    religions = []
    for group in pantheon_groups:
        if not group:
            continue
        primary = group[0]
        religion_name = _generate_religion_name(primary, rng)
        primary.domains[0] = primary.domains[0]  # already set

        # Generate religion description
        domain_names = ", ".join(d.domains[0] for d in group[:3])
        if len(group) > 3:
            domain_names += f", and {len(group) - 3} other domains"
        desc = (
            f"The {religion_name} reveres {primary.name} {primary.surname} "
            f"as its chief deity, alongside {len(group) - 1} other divine "
            f"aspects encompassing {domain_names}. "
            f"{'It is the dominant faith of the realm.' if religions == [] else 'A separate tradition with distinct practices.'}"
        )

        holy_days = _generate_holy_days(group, rng)
        tenets = _generate_tenets(rng)

        # Clergy titles for this religion
        clergy_titles = list(set(d.clergy_title for d in group))
        rng.shuffle(clergy_titles)

        # Holy sites
        holy_sites = _generate_holy_sites(religion_name, group, world, rng)

        religion = Religion(
            name=religion_name,
            description=desc,
            pantheon=group,
            clergy_titles=clergy_titles,
            holy_days=holy_days,
            tenets=tenets,
            primary_deity=primary.name,
            holy_sites=holy_sites,
        )
        religions.append(religion)

    # Assign religions to regions
    region_religion = {}
    for region in world.regions:
        if num_religions > 1 and len(religions) > 1:
            # Try to assign based on biome/alignment affinity
            biome_preference = {
                "temperate": 0,
                "arid": 1 if len(religions) > 1 else 0,
                "tundra": 0,
                "tropical": 1 if len(religions) > 1 else 0,
            }
            pref = biome_preference.get(region.biome, 0)
            if pref < len(religions):
                region_religion[region.name] = religions[pref].name
            else:
                region_religion[region.name] = religions[0].name
        else:
            region_religion[region.name] = religions[0].name if religions else "Unknown"

    return PantheonSystem(
        seed=seed if seed is not None else world.seed,
        religions=religions,
        region_religion=region_religion,
    )
