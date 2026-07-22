"""
wyrd — Narrative Engine (Phase 4).

Characters generated from the world's cultures, event chains that unfold
over time, and quests grounded in geography and politics.
All seed-deterministic: same seed + same world → same narrative, always.
"""

import random
from dataclasses import dataclass, field
from typing import Optional
from .world import World


# ── Templates ─────────────────────────────────────────────────────────

CHARACTER_NAMES_MALE = [
    "Aldric", "Bran", "Cedric", "Darian", "Eldon", "Finn", "Garret",
    "Hadrian", "Ivor", "Jorik", "Kael", "Leoric", "Maren", "Niall",
    "Orin", "Peregrin", "Quillan", "Roric", "Soren", "Torian", "Ulric",
    "Valen", "Wulfric", "Xander", "Yorick", "Zephyr",
]

CHARACTER_NAMES_FEMALE = [
    "Aelwen", "Briar", "Caelia", "Dara", "Elara", "Fenna", "Gwyn",
    "Hestia", "Ilara", "Juna", "Kira", "Lyra", "Mira", "Niamh",
    "Oriana", "Phaedra", "Riven", "Sylva", "Thalia", "Una", "Veda",
    "Willow", "Xanthe", "Yara", "Zelda",
]

SURNAMES = [
    "Ashwood", "Blackthorn", "Crowheart", "Deepwell", "Emberfall",
    "Fairwind", "Greycloak", "Holloway", "Ironhand", "Jadehelm",
    "Keenblade", "Longmere", "Mistborne", "Nightwalker", "Oakenshield",
    "Proudfoot", "Quickarrow", "Redmane", "Shadowmere", "Thornwood",
    "Underhill", "Valebrook", "Whitehart", "Wyrmbane",
]

OCCUPATIONS = [
    "farmer", "blacksmith", "innkeeper", "merchant", "hunter",
    "fisher", "carpenter", "mason", "weaver", "potter",
    "herbalist", "soldier", "guard", "ranger", "scout",
    "priest", "sage", "alchemist", "scholar", "cartographer",
    "miner", "tanner", "baker", "brewer", "miller",
    "shipwright", "sailor", "trader", "healer", "bard",
]

NOBLE_OCCUPATIONS = [
    "chieftain", "lord", "lady", "governor", "eldest",
    "warlord", "councilor", "judge", "harbormaster", "seneschal",
]

PERSONALITY_TRAITS = [
    "brave", "cunning", "wise", "reckless", "kind", "stern",
    "curious", "proud", "humble", "silent", "eloquent", "fierce",
    "gentle", "ambitious", "loyal", "deceitful", "honorable",
    "mysterious", "cheerful", "brooding", "generous", "greedy",
]

BACKSTORY_ELEMENTS = [
    "Born during a {event}, they {action}.",
    "As a child, they {childhood_event}.",
    "They once {past_deed}, earning {reputation}.",
    "After {tragedy}, they swore to {vow}.",
    "Trained under {mentor}, they became known for {skill}.",
    "A {mysterious_event} set them on their current path.",
]

BACKSTORY_EVENTS = [
    "great storm", "blood moon", "harvest festival",
    "border raid", "dragon sighting", "winter of ice",
    "summer of fire", "plague of whispers", "time of feasting",
    "year of the comet",
]

BACKSTORY_ACTIONS = [
    "learned to survive by wit alone",
    "discovered a hidden talent for healing",
    "witnessed the fall of a great house",
    "forged their first blade before reaching adulthood",
    "read every scroll in the settlement's library",
    "learned to read the land's secrets",
    "mastered the art of silence and observation",
    "earned the trust of the village elders",
]

CHILDHOOD_EVENTS = [
    "found a wounded animal and nursed it back to health",
    "got lost in the woods for three days",
    "saved a friend from drowning in the river",
    "climbed the tallest tree in the region",
    "stole a pie from the baker's window",
    "learned to fish before learning to read",
    "befriended a travelling merchant",
    "saw a ghost in the old ruins",
]

PAST_DEEDS = [
    "defended a village from raiders", "negotiated a peace between feuding families",
    "discovered a hidden spring", "mapped an unmapped valley",
    "rebuilt the old watchtower", "tamed a wild horse",
    "brewed the strongest ale in three counties",
    "carved a statue that still stands in the town square",
]

REPUTATIONS = [
    "the respect of their peers", "the title 'the Unbroken'",
    "a fearsome reputation", "the gratitude of the elders",
    "a bounty on their head", "a loyal following",
    "the nickname 'the Wise'", "a place in the council",
]

TRAGEDIES = [
    "a fire claimed their home", "their family was lost to disease",
    "a betrayal cost them everything", "a flood washed away their livelihood",
    "their mentor disappeared without a trace",
    "a war took everyone they loved",
]

VOWS = [
    "never again let harm come to the innocent",
    "find the truth, no matter the cost",
    "protect the old ways from the encroaching world",
    "rebuild what was lost, stone by stone",
    "wander until they find meaning",
    "write down every story before it is forgotten",
]

MENTORS = [
    "a wandering sage", "a grizzled veteran", "the village elder",
    "a mysterious stranger", "a master craftsperson",
    "an exiled noble", "a retired adventurer",
]

SKILLS = [
    "swordsmanship beyond their years", "unmatched herbal knowledge",
    "the ability to read ancient script", "exceptional craftsmanship",
    "a silver tongue and quick wit", "flawless navigation",
]

MYSTERIOUS_EVENTS = [
    "a dream of a sunken city", "an encounter with a spectral wolf",
    "finding a sealed letter from a forgotten war",
    "a stranger whispered their true name to them",
    "surviving a night in the haunted barrow",
]


# ── Event Chain Templates ────────────────────────────────────────────

EVENT_TYPES = [
    "conflict", "discovery", "natural", "political", "cultural",
]

EVENT_TEMPLATES = {
    "conflict": (
        "The {aggressor} launched an attack on {target} over {cause}. "
        "The {outcome}."
    ),
    "discovery": (
        "Explorers from {discoverer} uncovered {discovery_noun} "
        "in {location}. {reaction}."
    ),
    "natural": (
        "A {disaster} struck {affected_region}, "
        "{disaster_effect}. {aftermath}."
    ),
    "political": (
        "The ruler of {ruler_region} {political_action}. "
        "{political_outcome}."
    ),
    "cultural": (
        "The {festival_name} was held in {festival_settlement}, "
        "drawing attendees from across the region. {festival_outcome}."
    ),
}

AGGRESSORS = [
    "northern raiders", "a rival faction", "mercenaries from the east",
    "a discontented noble's army", "pirates from the coast",
    "a religious crusade", "the Iron Legion",
]

CAUSES_CONFLICT = [
    "disputed territory", "an old blood feud", "control of the river",
    "theft of a sacred relic", "a broken trade agreement",
    "a perceived insult to their chieftain",
]

OUTCOMES = [
    "attack was repelled after heavy losses on both sides",
    "invaders were driven back to their own lands",
    "a stalemate was reached, leaving a scarred borderland",
    "defenders were forced to cede a portion of their territory",
    "the conflict ended in a fragile truce",
]

DISCOVERIES = [
    "an ancient ruin beneath the hills", "a vein of pure crystal",
    "a natural spring with healing properties",
    "a cache of old weapons and armour",
    "the entrance to a vast underground cavern",
    "fossilized bones of a giant creature",
]

DISCOVERY_REACTIONS = [
    "word spread quickly, drawing scholars and treasure-seekers",
    "the elders declared the site sacred and restricted access",
    "a dispute over ownership arose between neighbouring settlements",
    "it was kept secret for fear of attracting unwanted attention",
]

DISASTERS = [
    "severe drought", "unprecedented flood", "great wildfire",
    "earthquake", "volcanic eruption", "blight upon the crops",
    "plague of locusts", "landslide blocking the mountain pass",
]

DISASTER_EFFECTS = [
    "forcing many to abandon their homes",
    "destroying a season's harvest",
    "cutting off trade routes for months",
    "leaving a scar upon the landscape that will last generations",
    "testing the resilience of the local population",
]

AFTERMATHS = [
    "Neighbouring settlements sent aid.",
    "The people rebuilt, stronger than before.",
    "Some saw it as an omen and left the region.",
    "A new leader emerged from the crisis.",
    "The scars remained, but so did the stories.",
]

POLITICAL_ACTIONS = [
    "declared a new tax on trade goods",
    "forged an alliance with a neighbouring power",
    "banished a rival faction from the court",
    "opened the borders to foreign merchants",
    "ordered the construction of a new road and waystation",
    "dissolved the old council and appointed loyalists",
]

POLITICAL_OUTCOMES = [
    "The move strengthened their hold on power.",
    "It sparked unrest among the common folk.",
    "Neighbouring regions took note and adjusted their strategies.",
    "The decision was celebrated as a wise one.",
    "Time would tell whether it was folly or foresight.",
]

CULTURAL_FESTIVALS = [
    "Rite of Blossoms", "Bonefire Night", "Feast of Falling Leaves",
    "Dance of the Masks", "Lantern Festival", "Solstice Gathering",
    "Harvest Home", "Starfall Celebration",
]

CULTURAL_OUTCOMES = [
    "trading partnerships were formed under the festive truce",
    "a famous bard debuted a new song that spread across the land",
    "the event strengthened cultural bonds between settlements",
    "a friendly competition fostered goodwill among the youth",
    "old grievances were set aside, at least for the duration",
]


# ── Quest Templates ──────────────────────────────────────────────────

QUEST_TYPES = [
    "exploration", "combat", "diplomacy", "gathering", "intrigue",
]

QUEST_TEMPLATES = {
    "exploration": (
        "Venture into {target_description} to {objective}. "
        "The location is said to be {difficulty_detail}."
    ),
    "combat": (
        "{threat} has been troubling {target_place}. "
        "{quest_giver} seeks {help_wanted} to {objective}. "
        "Reward: {reward}."
    ),
    "diplomacy": (
        "{quest_giver} needs a message delivered to {target_settlement} "
        "regarding {subject}. The {context}."
    ),
    "gathering": (
        "{quest_giver} requires {item} from {location}. "
        "{urgency} {additional_detail}."
    ),
    "intrigue": (
        "Strange {phenomenon} around {location}. "
        "{quest_giver} suspects {suspicion}. "
        "Investigate discreetly."
    ),
}

TARGET_DESCRIPTIONS = [
    "the Whispering Woods", "the Sunken Grotto",
    "the ruins of an old watchtower", "the Crystalline Caverns",
    "the Drowned Chapel", "the Ashen Fields",
    "the Raven's Perch", "the Hollow Hill",
]

DIFFICULTY_DETAILS = [
    "treacherous and largely unexplored",
    "guarded by ancient wards and wild beasts",
    "a place where few return from",
    "hidden, but the locals know the way",
    "dangerous only if you don't know what to look for",
]

OBJECTIVES_EXPLORE = [
    "map its depths and report back", "retrieve a relic from the heart of it",
    "confirm the rumours of strange lights", "find a safe passage through",
]

THREATS = [
    "A pack of wolves", "A band of outlaws", "A territorial beast",
    "Raiders from the hills", "Restless spirits",
    "A rogue sorcerer", "Corrupted wildlife",
]

HELP_WANTED = [
    "a capable warrior", "a small band of adventurers",
    "anyone brave enough", "someone with steady hands and a strong heart",
]

OBJECTIVES_COMBAT = [
    "clear the area and restore peace", "escort a supply caravan through the territory",
    "defend the settlement from the next attack", "hunt down the source of the trouble",
]

QUEST_REWARDS = [
    "a pouch of silver coins", "a plot of fertile land",
    "a rare herb for alchemy", "the gratitude of the settlement",
    "a well-crafted weapon", "a favour from the local lord",
    "a map to a hidden location", "a year's supply of grain",
]

QUEST_SUBJECTS = [
    "the upcoming trade agreement", "a boundary dispute",
    "a proposed marriage alliance", "shared use of the mill",
    "an invitation to the harvest festival",
]

QUEST_CONTEXTS = [
    "roads are dangerous, and a trusted courier is needed",
    "message must be delivered by hand as a sign of respect",
    "timing is critical — the matter cannot wait",
]

QUEST_ITEMS = [
    "a bundle of moonbloom petals", "a vial of deep well water",
    "the tooth of a cave bear", "a pinch of powdered starstone",
    "a lock of hair from the white stag",
]

QUEST_URGENCIES = [
    "There is no rush, but the reward is better if delivered soon.",
    "Time is of the essence — the season is nearly past.",
    "Take care, for the item is fragile and precious.",
]

ADDITIONAL_DETAILS = [
    "The locals can point you to the last known location.",
    "The old hermit beyond the ridge knows where to look.",
    "A map in the town hall marks the general area.",
]

PHENOMENA = [
    "lights have been seen in the old cemetery",
    "laughter echoes from the abandoned mill at midnight",
    "crops are wilting in a perfect circle",
    "a shadow moves between the trees without a source",
]

SUSPICIONS = [
    "sabotage by a rival settlement",
    "something ancient waking beneath the earth",
    "a secret cult operating in the shadows",
    "nothing good — and wants answers before it is too late",
]


# ── Data Models ───────────────────────────────────────────────────────

@dataclass
class Character:
    """A character living in the world."""
    name: str
    surname: str
    age: int
    gender: str
    occupation: str
    personality_traits: list[str]
    home_region: str
    home_settlement: str
    backstory: str
    status: str = "alive"

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"


@dataclass
class EventChain:
    """An event that occurred in the world."""
    name: str
    year: int
    event_type: str
    description: str
    regions_involved: list[str]
    settlements_involved: list[str]
    characters_involved: list[str]
    consequences: list[str]


@dataclass
class Quest:
    """A quest available in the world."""
    name: str
    quest_type: str
    difficulty: str
    description: str
    giver_character: Optional[str]
    giver_settlement: str
    target_region: str
    rewards: list[str]
    is_active: bool = True


@dataclass
class Narrative:
    """Complete narrative for a generated world."""
    seed: int
    characters: list[Character] = field(default_factory=list)
    events: list[EventChain] = field(default_factory=list)
    quests: list[Quest] = field(default_factory=list)
    current_year: int = 1000


# ── Generation Functions ──────────────────────────────────────────────

def _pick_unique(rng: random.Random, pool: list, used: set, max_attempts: int = 20) -> str:
    """Pick a unique item from a pool, logging if pool exhausted."""
    for _ in range(max_attempts):
        item = rng.choice(pool)
        if item not in used:
            used.add(item)
            return item
    # Fallback: return a random item (will have dupes, but won't crash)
    return rng.choice(pool)


def generate_characters(world: World, rng: random.Random) -> list[Character]:
    """Generate characters for a world, grounded in its regions and cultures."""
    characters: list[Character] = []
    used_names_male: set = set()
    used_names_female: set = set()
    used_surnames: set = set()

    # Guarantee at least one notable character per settlement
    for region in world.regions:
        for settlement in region.settlements:
            # 1-3 characters per settlement
            num = rng.randint(1, 3)
            for _ in range(num):
                gender = rng.choice(["male", "female"])
                if gender == "male":
                    name = _pick_unique(rng, CHARACTER_NAMES_MALE, used_names_male)
                else:
                    name = _pick_unique(rng, CHARACTER_NAMES_FEMALE, used_names_female)
                surname = _pick_unique(rng, SURNAMES, used_surnames)

                age = rng.randint(18, 75)

                # High-population settlements get nobles; others get ordinary occupations
                if settlement.population >= 1500 and rng.random() < 0.5:
                    occupation = rng.choice(NOBLE_OCCUPATIONS)
                elif settlement.population >= 500 and rng.random() < 0.3:
                    occupation = rng.choice(OCCUPATIONS + NOBLE_OCCUPATIONS)
                else:
                    occupation = rng.choice(OCCUPATIONS)

                traits = rng.sample(PERSONALITY_TRAITS, k=rng.randint(2, 3))

                # Build backstory from templates
                btpl = rng.choice(BACKSTORY_ELEMENTS)
                backstory = btpl.format(
                    event=rng.choice(BACKSTORY_EVENTS),
                    action=rng.choice(BACKSTORY_ACTIONS),
                    childhood_event=rng.choice(CHILDHOOD_EVENTS),
                    past_deed=rng.choice(PAST_DEEDS),
                    reputation=rng.choice(REPUTATIONS),
                    tragedy=rng.choice(TRAGEDIES),
                    vow=rng.choice(VOWS),
                    mentor=rng.choice(MENTORS),
                    skill=rng.choice(SKILLS),
                    mysterious_event=rng.choice(MYSTERIOUS_EVENTS),
                )

                characters.append(Character(
                    name=name,
                    surname=surname,
                    age=age,
                    gender=gender,
                    occupation=occupation,
                    personality_traits=traits,
                    home_region=region.name,
                    home_settlement=settlement.name,
                    backstory=backstory,
                ))

    return characters


def generate_events(world: World, characters: list[Character],
                    rng: random.Random) -> list[EventChain]:
    """Generate a series of events that have shaped the world."""
    events: list[EventChain] = []
    num_events = rng.randint(3, 8)
    used_names: set = set()
    year = rng.randint(950, 1000) - num_events  # spread back in time

    for i in range(num_events):
        event_type = rng.choice(EVENT_TYPES)
        tpl = EVENT_TEMPLATES[event_type]
        year += rng.randint(1, 20)

        # Pick regions and settlements
        region = rng.choice(world.regions)
        settlement = rng.choice(region.settlements) if region.settlements else None
        other_region = rng.choice([r for r in world.regions if r.name != region.name]) if len(world.regions) > 1 else region

        # Pick characters for this event
        involved_characters = []
        char_pool = [c for c in characters if c.home_region == region.name]
        if char_pool and rng.random() < 0.6:
            involved_characters.append(rng.choice(char_pool).full_name)

        description = tpl.format(
            aggressor=rng.choice(AGGRESSORS),
            target=settlement.name if settlement else region.name,
            cause=rng.choice(CAUSES_CONFLICT),
            outcome=rng.choice(OUTCOMES),
            discoverer=rng.choice([region.name, settlement.name if settlement else region.name]),
            discovery_noun=rng.choice(DISCOVERIES),
            location=f"the {region.name} area",
            reaction=rng.choice(DISCOVERY_REACTIONS),
            disaster=rng.choice(DISASTERS),
            affected_region=region.name,
            disaster_effect=rng.choice(DISASTER_EFFECTS),
            aftermath=rng.choice(AFTERMATHS),
            ruler_region=region.name,
            political_action=rng.choice(POLITICAL_ACTIONS),
            political_outcome=rng.choice(POLITICAL_OUTCOMES),
            festival_name=rng.choice(CULTURAL_FESTIVALS),
            festival_settlement=settlement.name if settlement else region.name,
            festival_outcome=rng.choice(CULTURAL_OUTCOMES),
        )

        # Generate 1-2 consequences
        consequences = rng.sample(AFTERMATHS, k=rng.randint(1, 2))

        # Unique event name
        event_nouns = ["Conflict", "Discovery", "Disaster", "Pact", "Festival",
                        "Raid", "Expedition", "Crisis"]
        en = rng.choice(event_nouns)
        loc = settlement.name if settlement else region.name
        event_name = f"The {loc} {en}"
        if event_name in used_names:
            event_name = f"The {region.name} {en}"

        events.append(EventChain(
            name=event_name,
            year=year,
            event_type=event_type,
            description=description,
            regions_involved=list(set([region.name, other_region.name])),
            settlements_involved=[settlement.name] if settlement else [],
            characters_involved=involved_characters,
            consequences=consequences,
        ))

    return events


def generate_quests(world: World, characters: list[Character],
                    rng: random.Random) -> list[Quest]:
    """Generate quests grounded in the world's geography and politics."""
    quests: list[Quest] = []
    num_quests = rng.randint(3, 6)
    used_names: set = set()

    difficulty_labels = ["trivial", "easy", "moderate", "hard", "epic"]

    for i in range(num_quests):
        quest_type = rng.choice(QUEST_TYPES)
        tpl = QUEST_TEMPLATES[quest_type]
        difficulty = rng.choice(difficulty_labels)

        region = rng.choice(world.regions)
        settlement = rng.choice(region.settlements) if region.settlements else None
        target_settlement = None
        other_regions = [r for r in world.regions if r.name != region.name]
        if other_regions:
            target_region = rng.choice(other_regions)
            if target_region.settlements:
                target_settlement = rng.choice(target_region.settlements)

        # Pick a quest giver
        giver = None
        char_pool = [c for c in characters if c.home_region == region.name and c.home_settlement == (settlement.name if settlement else "")]
        if char_pool:
            giver = rng.choice(char_pool)
        elif characters:
            giver = rng.choice(characters)

        description = tpl.format(
            target_description=rng.choice(TARGET_DESCRIPTIONS),
            objective=rng.choice(OBJECTIVES_EXPLORE + OBJECTIVES_COMBAT),
            difficulty_detail=rng.choice(DIFFICULTY_DETAILS),
            threat=rng.choice(THREATS),
            target_place=settlement.name if settlement else region.name,
            quest_giver=giver.full_name if giver else "The council",
            help_wanted=rng.choice(HELP_WANTED),
            reward=rng.choice(QUEST_REWARDS),
            target_settlement=target_settlement.name if target_settlement else "a neighbouring settlement",
            subject=rng.choice(QUEST_SUBJECTS),
            context=rng.choice(QUEST_CONTEXTS),
            item=rng.choice(QUEST_ITEMS),
            location=f"the {region.name} area",
            urgency=rng.choice(QUEST_URGENCIES),
            additional_detail=rng.choice(ADDITIONAL_DETAILS),
            phenomenon=rng.choice(PHENOMENA),
            suspicion=rng.choice(SUSPICIONS),
        )

        rewards = rng.sample(QUEST_REWARDS, k=rng.randint(1, 2))

        # Quest name
        qnouns = ["Errand", "Mission", "Task", "Journey", "Expedition",
                   "Venture", "Enterprise", "Quest"]
        qn = rng.choice(qnouns)
        loc = settlement.name if settlement else region.name
        quest_name = f"The {loc} {qn}"
        if quest_name in used_names:
            quest_name = f"{rng.choice(CHARACTER_NAMES_MALE)}'s {qn}"

        quests.append(Quest(
            name=quest_name,
            quest_type=quest_type,
            difficulty=difficulty,
            description=description,
            giver_character=giver.full_name if giver else None,
            giver_settlement=settlement.name if settlement else region.name,
            target_region=region.name,
            rewards=rewards,
        ))

    return quests


def generate_narrative(world: World) -> Narrative:
    """Generate complete narrative for a world."""
    narrative_seed = world.seed + 2000000  # offset from terrain and lore seeds
    rng = random.Random(narrative_seed)
    narrative = Narrative(seed=narrative_seed)

    # Compose: lore affects character generation context
    narrative.characters = generate_characters(world, rng)
    narrative.events = generate_events(world, narrative.characters, rng)
    narrative.quests = generate_quests(world, narrative.characters, rng)

    # Calculate current year based on events
    if narrative.events:
        narrative.current_year = max(e.year for e in narrative.events)

    return narrative
