"""
wyrd — Chronicles Engine (Phase 5).

Generative world history. Not a static dump — a causally linked timeline
of eras that shaped the world into what it is. Each era describes the
state of the world, key events, legendary participants (drawn from the
narrative engine), and permanent world-state modifiers.

All seed-deterministic: same seed + same world → same chronicles, always.
"""

import random
from dataclasses import dataclass, field
from typing import Optional


# ── Era Templates ─────────────────────────────────────────────────────

ERA_TYPES = [
    "founding", "golden_age", "cataclysm", "dark_age",
    "age_of", "decline", "rebirth", "schism",
]

ERA_TEMPLATES = {
    "founding": (
        "In the beginning, {people} {action}. "
        "The first settlements of {region} {grew}."
    ),
    "golden_age": (
        "A time of {prosperity}. {culture_name} {achievement}. "
        "The {feature} became a symbol of {value}."
    ),
    "cataclysm": (
        "{disaster} swept across the land. {affected_settlement} "
        "was {fate}. The {consequence}."
    ),
    "dark_age": (
        "After the {prior_event}, {description}. "
        "{culture_name} {struggle}. {recovery}."
    ),
    "age_of": (
        "The {theme} defined this era. {culture_name} {innovation}. "
        "{notable_event}."
    ),
    "decline": (
        "{cause} weakened {region}. {settlement_fate}. "
        "The {institution} crumbled."
    ),
    "rebirth": (
        "From the ashes of {old_era}, {new_beginning}. "
        "{hero} {redeeming_act}. {new_tradition}."
    ),
    "schism": (
        "Division tore through {region}. {disagreement}. "
        "{faction_a} and {faction_b} {split_outcome}."
    ),
}

ERA_NAMES = [
    "The {adj} {noun}",
    "The {noun} of {era_noun}",
    "The {adj} Years",
    "{adj} Century",
    "The Time of {era_noun}",
    "The {adj} Age",
    "Era of the {era_noun}",
    "The {adj} Turning",
]

ERA_ADJS = [
    "First", "Broken", "Golden", "Iron", "Silent", "Burning",
    "Crimson", "Fading", "Rising", "Fallen", "Ashen", "Dawning",
    "Shattered", "Weeping", "Hollow", "Kindled", "Eternal",
]

ERA_NOUNS = [
    "Embers", "Stone", "Bone", "Thorns", "Stars", "Tides",
    "Shadows", "Blades", "Roots", "Ash", "Crowns", "Oaths",
    "Wolves", "Serpents", "Bellows", "Mirrors", "Rivers",
]

ERA_ERA_NOUNS = [
    "Embers", "Stone", "Thorns", "Stars", "Tides",
    "Shadows", "Roots", "Ash", "Crowns", "Oaths",
    "Serpents", "Bellows", "Mirrors", "Rivers", "Kings",
    "Giants", "Wonders", "Dreams",
]

PROSPERITY_DESCRIPTORS = [
    "unprecedented prosperity and cultural flowering",
    "great works of art and architecture",
    "peace that let the population flourish",
    "trade routes spanning the known world",
    "knowledge and learning beyond measure",
    "abundance that seemed inexhaustible",
]

ACHIEVEMENTS = [
    "raised the Great Library of {settlement}",
    "forged the {item} in the fires of {feature}",
    "discovered the {discovery} beneath the hills",
    "built the {structure} that still stands today",
    "mapped the {region} passes and opened trade",
]

ACHIEVEMENT_ITEMS = [
    "Crystal Crown", "Iron Pact", "Silver Accord",
    "Bone Gate", "Star Compass", "Hollow Shield",
    "Ember Sceptre",
]

ACHIEVEMENT_DISCOVERIES = [
    "Deepvein", "Sunken Library", "Crystal Caverns",
    "Starfall Crater", "Whispering Vault",
]

ACHIEVEMENT_STRUCTURES = [
    "Sunstone Citadel", "Bridge of Sighs", "Watchtower of the Dawn",
    "Spire of Voices", "Grand Aqueduct", "Hanging Gardens of {settlement}",
]

DISASTERS = [
    "The Great Fire", "The Crimson Plague", "The Withering Blight",
    "The Sundering Earthquake", "The Ash Winter", "The Drowning Tide",
    "The Starfall", "The Silent Death",
]

FATES = [
    "reduced to rubble and ash",
    "abandoned by its people",
    "consumed by the calamity",
    "forever scarred by what happened",
    "buried beneath the shifting earth",
]

CONSEQUENCES_CATACLYSM = [
    "survivors scattered to the winds",
    "old knowledge was lost for generations",
    "the land itself was changed forever",
    "a shadow fell over the world that did not lift for a century",
    "the old order collapsed, and something new took its place",
]

PRIOR_EVENTS = [
    "fall of the old kingdoms",
    "great war that exhausted the land",
    "plague that emptied the cities",
    "famine that withered the fields",
    "exodus of the learned ones",
]

DARK_DESCRIPTIONS = [
    "the people turned inward, distrusting all strangers",
    "knowledge became scarce, hoarded by the few",
    "the roads fell into disrepair, isolating settlements",
    "old enemies grew bold in the chaos",
    "the land grew wild, reclaiming what had been tamed",
]

STRUGGLES = [
    "held onto the old ways with fierce determination",
    "forged new alliances to survive the hard times",
    "learned to live with less, and found strength in simplicity",
    "fought bitterly over the remaining resources",
    "preserved what they could, passing stories through the dark",
]

RECOVERIES = [
    "Slowly, the seeds of a new age were planted.",
    "A new generation arose that knew only the hope of dawn.",
    "Trade resumed, tentatively at first, then with confidence.",
    "The old wounds healed, though the scars remained.",
    "From the darkness, unlikely heroes emerged.",
]

THEMES = [
    "exploration and discovery",
    "conquest and expansion",
    "art and enlightenment",
    "faith and revelation",
    "innovation and craft",
    "unity and cooperation",
]

INNOVATIONS = [
    "perfected the art of {craft}",
    "developed {technology}",
    "unlocked the secrets of {secret}",
    "invented {invention}",
    "mastered {discipline}",
]

CRAFTS = [
    "steel-forging", "glass-blowing", "stone-carving",
    "weapon-smithing", "ship-building", "weave-working",
]

TECHNOLOGIES = [
    "advanced irrigation systems", "celestial navigation",
    "the water-powered mill", "the wind furnace",
    "distillation and preservation",
]

SECRETS = [
    "herbal healing", "metal alloying", "masonry without mortar",
    "underground cultivation", "permanent ink and dye",
]

INVENTIONS = [
    "the longbow", "the plow", "the kiln", "the loom",
    "the pulley system", "the aqueduct arch",
]

DISCIPLINES = [
    "agriculture", "astronomy", "cartography",
    "herbalism", "engineering",
]

NOTABLE_EVENTS = [
    "A {event_type} was sighted for the first time.",
    "The {structure} was completed after {years} years of labour.",
    "A delegation from {far_place} arrived with gifts and knowledge.",
    "The {order} was founded by {founder}.",
    "A {animal} of pure white was born in {settlement}.",
]

NOTABLE_EVENT_TYPES = [
    "comet", "dragon", "ghost ship", "winged lion", "silver stag",
]

NOTABLE_STRUCTURES = [
    "Wall of {region}", "Great Observatory", "Pilgrim's Cathedral",
    "Iron Bridge", "Sunken Amphitheatre",
]

NOTABLE_ORDERS = [
    "Order of the {symbol}", "Knights of the {symbol}",
    "Keepers of the {symbol}", "Circle of the {symbol}",
]

SYMBOLS = [
    "Dawn", "Rose", "Crown", "Star", "Oak", "Flame", "Tide", "Compass",
]

NOTABLE_ANIMALS = [
    "deer", "wolf", "stag", "bear", "fox", "hawk", "horse",
]

FAR_PLACES = [
    "the Jade Empire", "the Obsidian Isles", "the Sunken Kingdom",
    "the Silver Marches", "the Crystal City",
]

DECLINE_CAUSES = [
    "overextended trade routes", "a succession crisis",
    "repeated crop failures", "the exhaustion of vital resources",
    "internal corruption and decay",
]

SETTLEMENT_FATES = [
    "The great market fell silent, stall by stall.",
    "The harbour silted up, and the ships stopped coming.",
    "The mines ran dry, and the people drifted away.",
    "The temples stood empty, their priests gone.",
    "The walls crumbled from neglect.",
]

INSTITUTIONS = [
    "old council", "merchant guild", "royal lineage",
    "scholar's academy", "temple hierarchy",
]

NEW_BEGINNINGS = [
    "a new settlement was founded by {founder}",
    "the scattered people reunited under {leader}",
    "a forgotten craft was rediscovered",
    "a new faith took root in the old groves",
    "the land began to heal, and people returned",
]

REDEEMING_ACTS = [
    "led the rebuilding of {settlement}",
    "rekindled the sacred flame",
    "reopened the old trade route",
    "negotiated peace between the feuding houses",
    "recovered the lost chronicles from the ruins",
]

NEW_TRADITIONS = [
    "The Festival of {festival} was first celebrated.",
    "A new council was formed to govern the land.",
    "The {structure} was built to commemorate the renewal.",
    "An alliance was sworn under the {symbol}.",
]

SCHEMA_ERAS = [
    "Age of Embers", "Last Dawn", "First Winter",
]

DISAGREEMENTS = [
    "a dispute over the succession",
    "a rift over religious doctrine",
    "an argument over resource distribution",
    "a conflict of ancient vs new traditions",
    "a betrayal that shattered old alliances",
]

FACTIONS = [
    "The {adj} Faction", "The {noun} Party", "The {adj} Alliance",
    "Keepers of the {noun}", "The {noun} Circle",
]

SPLIT_OUTCOMES = [
    "went their separate ways, each guarding their own truth",
    "became bitter enemies, their feud lasting generations",
    "drew boundaries that would become new kingdoms",
    "maintained an uneasy peace, neither trusting the other",
]

FOUNDER_NAMES = [
    "Aldric the Bold", "Elara of the {region}", "Kael Stonehand",
    "Mira Bellwake", "Torian Ironfoot", "Sylva Farwalker",
    "Roric the Unbroken", "Lyra Swiftwater",
]

LEADER_NAMES = [
    "High Chieftain {name}", "Elder {name}", "Governor {name}",
    "Lord {name} of {settlement}", "Queen {name}",
    "King {name}", "Chief {name}",
]

ERA_FESTIVALS = [
    "Reunification", "First Harvest", "New Dawn",
    "The Mending", "Ash Bloom",
]


# ── Data Models ───────────────────────────────────────────────────────


@dataclass
class Era:
    """A distinct era in the world's history."""
    name: str
    era_type: str
    start_year: int
    end_year: int
    description: str
    events: list[dict] = field(default_factory=list)
    world_modifiers: list[str] = field(default_factory=list)

    @property
    def duration(self) -> int:
        return self.end_year - self.start_year

    is_present: bool = False


@dataclass
class Chronicles:
    """Complete world history — a causally linked timeline of eras."""
    seed: int
    eras: list[Era] = field(default_factory=list)
    world_age: int = 1000

    @property
    def num_eras(self) -> int:
        return len(self.eras)

    @property
    def present_era(self) -> Optional[Era]:
        if self.eras:
            return self.eras[-1]
        return None


# ── Generation Functions ──────────────────────────────────────────────


def _make_era_name(rng: random.Random, region_name: str = "") -> str:
    """Generate a unique era name."""
    tpl = rng.choice(ERA_NAMES)
    adj = rng.choice(ERA_ADJS)
    noun = rng.choice(ERA_NOUNS)
    era_noun = rng.choice(ERA_ERA_NOUNS)
    name = tpl.format(adj=adj, noun=noun, era_noun=era_noun)
    return name


def _make_faction_name(rng: random.Random) -> str:
    """Generate a faction name."""
    tpl = rng.choice(FACTIONS)
    adj = rng.choice(ERA_ADJS)
    noun = rng.choice(SYMBOLS)
    return tpl.format(adj=adj, noun=noun)


def _pick_era_type(rng: random.Random, used_types: set[str]) -> str:
    """Pick an era type, ensuring variety."""
    # Weight types for a natural-feeling progression
    weights = {
        "founding": 15,
        "golden_age": 20,
        "cataclysm": 15,
        "dark_age": 10,
        "age_of": 25,
        "decline": 10,
        "rebirth": 15,
        "schism": 10,
    }
    pool = []
    for t, w in weights.items():
        # Reduce weight if already used
        if t in used_types:
            w = max(1, w // 3)
        pool.extend([t] * w)
    return rng.choice(pool)


def generate_chronicles(world, narrative=None):
    """
    Generate complete world chronicles from a generated world.
    
    Builds on top of the narrative engine's characters and events to
    create a causally linked timeline of eras.
    """
    from .world import World  # late import to avoid circular
    from .narrative import Narrative

    chronicles_seed = world.seed + 3000000  # offset from terrain, lore, narrative
    rng = random.Random(chronicles_seed)
    chronicles = Chronicles(seed=chronicles_seed)

    # Gather raw material from the world
    regions = [r.name for r in world.regions]
    settlements = [(r.name, s.name) for r in world.regions for s in r.settlements]

    # Gather narrative data if available
    characters_list = []
    if narrative and hasattr(narrative, 'characters'):
        characters_list = [
            {
                "name": c.full_name,
                "home_region": c.home_region,
                "home_settlement": c.home_settlement,
                "occupation": c.occupation,
            }
            for c in narrative.characters
        ]

    events_list = []
    if narrative and hasattr(narrative, 'events'):
        events_list = [
            {
                "name": e.name,
                "year": e.year,
                "description": e.description,
                "regions_involved": e.regions_involved,
                "characters_involved": e.characters_involved,
            }
            for e in narrative.events
        ]

    # Determine world age and era span
    world_age = 1000
    if narrative and hasattr(narrative, 'current_year'):
        world_age = narrative.current_year

    chronicles.world_age = world_age

    # Generate 4-8 eras spanning the world's history
    num_eras = rng.randint(4, 8)
    used_era_names: set = set()
    used_era_types: set = set()
    eras: list[Era] = []

    # Distribute eras across the timeline
    era_span = max(world_age, 500)
    year_step = era_span // (num_eras + 1)
    current_year = 0

    for i in range(num_eras):
        era_type = _pick_era_type(rng, used_era_types)
        used_era_types.add(era_type)

        # Generate era name
        era_name = _make_era_name(rng)
        while era_name in used_era_names:
            era_name = _make_era_name(rng)
        used_era_names.add(era_name)

        # Era duration (20-40% of the timeline for founding; shorter for cataclysms)
        if era_type == "cataclysm":
            duration = rng.randint(1, 15)
        elif era_type == "founding":
            duration = rng.randint(50, 150)
        else:
            duration = rng.randint(30, 120)

        start = current_year
        end = min(start + duration, world_age)
        current_year = end

        # Pick a region and settlement for this era's focus
        focus_region = rng.choice(regions) if regions else "the known world"
        focus_settlement_name = ""
        if settlements:
            r_sel, s_sel = rng.choice(settlements)
            focus_settlement_name = s_sel

        # Pick characters for this era
        era_characters = []
        if characters_list:
            pool = [c for c in characters_list if c["home_region"] == focus_region]
            if not pool:
                pool = characters_list
            num_chars = rng.randint(1, min(3, len(pool)))
            era_characters = rng.sample(pool, num_chars)

        # Find narrative events that fall within this era's timespan
        era_narrative_events = [
            ev for ev in events_list
            if start <= ev["year"] <= end
        ]

        # Build description based on era type
        tpl = ERA_TEMPLATES.get(era_type, ERA_TEMPLATES["age_of"])
        culture_name = focus_region
        feature_name = f"{rng.choice(ERA_ADJS)} {rng.choice(['Hills', 'River', 'Forest', 'Pass', 'Vale', 'Peak'])}"

        # Pick a character name for placeholders
        hero_name = ""
        if era_characters:
            hero_name = era_characters[0]["name"]
        elif characters_list:
            hero_name = rng.choice(characters_list)["name"]
        else:
            hero_name = rng.choice(FOUNDER_NAMES).format(region=focus_region)

        # Format template
        description = tpl.format(
            people=culture_name,
            action=rng.choice([
                "emerged from the wilderness to claim the land",
                "settled along the river valleys",
                "raised the first walls against the unknown",
                "kindled the first hearth-fires in the region",
                "carved a home from the untamed wilds",
            ]),
            region=focus_region,
            grew=rng.choice([
                "grew from scattered camps into proper villages",
                "became centres of a new way of life",
                "drew traders and travellers from afar",
                "were fortified against the dangers of the land",
                "flourished under the guidance of wise leaders",
            ]),
            prosperity=rng.choice(PROSPERITY_DESCRIPTORS),
            culture_name=culture_name,
            achievement=rng.choice(ACHIEVEMENTS).format(
                settlement=focus_settlement_name,
                item=rng.choice(ACHIEVEMENT_ITEMS),
                feature=feature_name,
                discovery=rng.choice(ACHIEVEMENT_DISCOVERIES),
                region=focus_region,
                structure=rng.choice(ACHIEVEMENT_STRUCTURES).format(
                    settlement=focus_settlement_name
                ),
            ),
            feature=feature_name,
            value=rng.choice(["hope", "strength", "wisdom", "unity", "endurance", "faith"]),
            disaster=rng.choice(DISASTERS),
            affected_settlement=focus_settlement_name or focus_region,
            fate=rng.choice(FATES),
            consequence=rng.choice(CONSEQUENCES_CATACLYSM),
            prior_event=rng.choice(PRIOR_EVENTS),
            description=rng.choice(DARK_DESCRIPTIONS),
            struggle=rng.choice(STRUGGLES),
            recovery=rng.choice(RECOVERIES),
            theme=rng.choice(THEMES),
            innovation=rng.choice(INNOVATIONS).format(
                craft=rng.choice(CRAFTS),
                technology=rng.choice(TECHNOLOGIES),
                secret=rng.choice(SECRETS),
                invention=rng.choice(INVENTIONS),
                discipline=rng.choice(DISCIPLINES),
            ),
            notable_event=rng.choice(NOTABLE_EVENTS).format(
                event_type=rng.choice(NOTABLE_EVENT_TYPES),
                structure=rng.choice(NOTABLE_STRUCTURES).format(region=focus_region),
                years=rng.randint(5, 50),
                far_place=rng.choice(FAR_PLACES),
                order=rng.choice(NOTABLE_ORDERS).format(symbol=rng.choice(SYMBOLS)),
                founder=hero_name,
                animal=rng.choice(NOTABLE_ANIMALS),
                settlement=focus_settlement_name or focus_region,
            ),
            cause=rng.choice(DECLINE_CAUSES),
            settlement_fate=rng.choice(SETTLEMENT_FATES),
            institution=rng.choice(INSTITUTIONS),
            old_era=rng.choice(list(used_era_names)) if used_era_names else "the old world",
            new_beginning=rng.choice(NEW_BEGINNINGS).format(
                founder=hero_name,
                leader=rng.choice(LEADER_NAMES).format(
                    name=hero_name.split()[0] if hero_name else "Aldric",
                    settlement=focus_settlement_name or focus_region,
                ),
            ),
            hero=hero_name,
            redeeming_act=rng.choice(REDEEMING_ACTS).format(
                settlement=focus_settlement_name or focus_region,
            ),
            new_tradition=rng.choice(NEW_TRADITIONS).format(
                festival=rng.choice(ERA_FESTIVALS),
                structure=rng.choice(ACHIEVEMENT_STRUCTURES).format(
                    settlement=focus_settlement_name or focus_region
                ),
                symbol=rng.choice(SYMBOLS),
            ),
            disagreement=rng.choice(DISAGREEMENTS),
            faction_a=_make_faction_name(rng),
            faction_b=_make_faction_name(rng),
            split_outcome=rng.choice(SPLIT_OUTCOMES),
        )

        # Generate world modifiers based on era type
        world_modifiers = []
        if era_type == "cataclysm":
            world_modifiers.append(f"Ruins scattered across {focus_region}")
            if rng.random() < 0.5:
                world_modifiers.append(f"Abandoned settlements in {focus_region}")
        elif era_type == "golden_age":
            world_modifiers.append(f"Great monuments in {focus_region}")
            if rng.random() < 0.4:
                world_modifiers.append(f"Expanded trade networks reaching {focus_region}")
        elif era_type == "dark_age":
            world_modifiers.append(f"Fallow fields and crumbling roads in {focus_region}")
            world_modifiers.append(f"Lost knowledge from the {focus_region} libraries")
        elif era_type == "decline":
            world_modifiers.append(f"Ruined fortifications in {focus_region}")
        elif era_type == "founding":
            world_modifiers.append(f"Ancient foundations beneath {focus_region}")
        elif era_type == "schism":
            world_modifiers.append(f"Contested borders around {focus_region}")
        elif era_type == "rebirth":
            world_modifiers.append(f"Rebuilt structures in {focus_region}")
            if rng.random() < 0.3:
                world_modifiers.append(f"New roads connecting {focus_region}")

        # Build era event list
        era_events = []
        for ev in era_narrative_events:
            era_events.append({
                "name": ev["name"],
                "year": ev["year"],
                "description": ev["description"],
                "source": "narrative",
            })

        # Add legendary events (bigger than narrative events)
        num_legendary = rng.randint(1, 3)
        for le in range(num_legendary):
            le_rng = random.Random(chronicles_seed + i * 100 + le * 37)
            le_type = le_rng.choice(["battle", "founding", "discovery", "natural", "pact"])
            le_year = le_rng.randint(start, end)

            le_desc_templates = {
                "battle": "The {army} clashed with {enemy} at {location}. {outcome}.",
                "founding": "{figure} established {place} as a {purpose}.",
                "discovery": "{explorer} discovered {thing} in {area}.",
                "natural": "The {phenomenon} reshaped {area} forever.",
                "pact": "The {pact_name} was sworn by {parties} at {location}.",
            }

            le_army = le_rng.choice([
                f"the {le_rng.choice(ERA_ADJS)} Legion",
                f"{hero_name}'s Host",
                f"the {le_rng.choice(ERA_NOUNS)} of {focus_region}",
                f"{_make_faction_name(le_rng)}",
            ])
            le_enemy = le_rng.choice([
                f"the {le_rng.choice(ERA_ADJS)} Horde",
                f"{_make_faction_name(le_rng)}",
                f"raiders from {le_rng.choice(FAR_PLACES)}",
            ])
            le_location = le_rng.choice([
                f"the {le_rng.choice(ERA_ADJS)} {le_rng.choice(['Fields', 'Ford', 'Pass', 'Shore', 'Valley'])}",
                focus_settlement_name or focus_region,
            ])
            le_outcome_desc = le_rng.choice([
                "The battle was decisive, changing the course of history",
                "Both sides withdrew, battered but unbroken",
                "The victory was pyrrhic, costing more than it gained",
                "The legends say the ground still remembers the blood",
            ])

            _rng_num = lambda: le_rng  # noqa

            le_char_name = hero_name
            if era_characters and le_rng.random() < 0.6:
                le_char_pick = le_rng.choice(era_characters)
                le_char_name = le_char_pick["name"]

            le_desc = le_desc_templates[le_type].format(
                army=le_army,
                enemy=le_enemy,
                location=le_location,
                outcome=le_outcome_desc,
                figure=le_char_name,
                place=le_rng.choice([
                    f"the {le_rng.choice(ERA_ADJS)} {le_rng.choice(['Keep', 'Tower', 'Hall', 'Sanctuary'])}",
                    f"{focus_settlement_name}'s {le_rng.choice(['Citadel', 'Academy', 'Forge'])}" if focus_settlement_name else f"{focus_region}'s {le_rng.choice(['Heartland', 'Capitol', 'Shrine'])}",
                ]),
                purpose=le_rng.choice([
                    "beacon of knowledge and learning",
                    "final refuge against the darkness",
                    "watchtower against the eastern threat",
                    "meeting place for the council of elders",
                    "forge for the weapons of the age",
                ]),
                explorer=le_char_name,
                thing=le_rng.choice([
                    f"the {le_rng.choice(ERA_ADJS)} {le_rng.choice(['Portal', 'Vault', 'Grotto', 'Wellspring'])}",
                    "the remains of an ancient civilization",
                    f"a {le_rng.choice(['crystal', 'metal', 'stone'])} unlike any known",
                ]),
                area=focus_region,
                phenomenon=le_rng.choice([
                    "Great Earthquake", "Tidal Wave", "Fire Rain",
                    "Long Winter", "River That Turned to Blood",
                    "Mountain That Breathed Smoke",
                ]),
                pact_name=le_rng.choice([
                    f"The {le_rng.choice(ERA_ADJS)} Compact",
                    f"The {le_rng.choice(SYMBOLS)} Accord",
                    "The Oath of Shared Waters",
                ]),
                parties=f"{le_char_name} and the {_make_faction_name(le_rng)}",
            )

            era_events.append({
                "name": f"The {le_rng.choice(['Battle', 'Founding', 'Discovery', 'Covenant', 'Cataclysm'])} at {le_location}",
                "year": le_year,
                "description": le_desc,
                "source": "legendary",
                "characters": [le_char_name] if le_char_name else [],
                "type": le_type,
            })

        # Sort events chronologically
        era_events.sort(key=lambda ev: ev["year"])

        era = Era(
            name=era_name,
            era_type=era_type,
            start_year=start,
            end_year=end,
            description=description,
            events=era_events,
            world_modifiers=world_modifiers,
        )
        eras.append(era)

    # Mark the last era as present
    if eras:
        eras[-1].is_present = True

    chronicles.eras = eras
    return chronicles
