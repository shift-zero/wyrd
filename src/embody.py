"""
wyrd — Embodied Play Mode (Phase 17: Living Worlds).

`wyrd embody --seed 42` drops you into the world as a character.
Not god-mode spectator — you *live* in the world. News arrives,
you travel, you age, and the world changes around you.

Usage:
    wyrd embody --seed 42
    wyrd embody --seed 42 --name "Rikard Blackthorn"
    wyrd embody --seed 42 --years 500
"""

import json
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Optional

from .world import World
from .sim import (
    initialize_sim_state, _simulate_tick, _simulate_month_tick, SimState, SimEvent,
    apply_sim_state_to_world,
)

from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color

# Skill names and their XP thresholds
SKILL_NAMES = ["combat", "trade", "persuasion", "survival", "crafting"]


def _make_skills() -> dict[str, int]:
    """Create default skill levels (all start at 1)."""
    return {s: 1 for s in SKILL_NAMES}


def _make_skill_xp() -> dict[str, int]:
    """Create default skill XP (all start at 0)."""
    return {s: 0 for s in SKILL_NAMES}


def _xp_for_level(level: int) -> int:
    """XP needed to reach a given level (level 1 = 0, level 2 = 15, etc.)."""
    if level <= 1:
        return 0
    return int((level * (level - 1) / 2) * 15)


def _xp_to_next_level(current_level: int) -> int:
    """XP needed from current level to reach next level."""
    return _xp_for_level(current_level + 1) - _xp_for_level(current_level)


def _skill_level_from_xp(total_xp: int) -> int:
    """Determine skill level from total XP (max 10)."""
    for level in range(10, 0, -1):
        if total_xp >= _xp_for_level(level):
            return level
    return 1


def _skill_bonus(char: "PlayerCharacter", skill: str) -> float:
    """Get the outcome bonus for a skill (0.0 to 0.5 based on level 1-10)."""
    level = char.skills.get(skill, 1)
    return (level - 1) * 0.05  # +5% per level over 1


def _gain_skill_xp(char: "PlayerCharacter", skill: str, amount: int) -> None:
    """Grant XP to a skill and auto-level-up if threshold reached."""
    if skill not in char.skills:
        return
    old_level = char.skills[skill]
    char.skill_xp[skill] = char.skill_xp.get(skill, 0) + amount
    new_level = _skill_level_from_xp(char.skill_xp[skill])
    char.skills[skill] = min(new_level, 10)
    if char.skills[skill] > old_level:
        print(f"  {_color(46)}⚡ {skill.capitalize()} increased to level {char.skills[skill]}!{ANSI_RESET}")


def _change_reputation(char: "PlayerCharacter", settlement: str, delta: int) -> str:
    """Change reputation for a settlement (-10 to +10 range). Returns a flavor string."""
    current = char.reputation.get(settlement, 0)
    new_val = max(-10, min(10, current + delta))
    char.reputation[settlement] = new_val
    if delta > 0:
        return f"  {_color(46)}Your standing in {settlement} improves.{ANSI_RESET}"
    elif delta < 0:
        return f"  {_color(196)}Your standing in {settlement} suffers.{ANSI_RESET}"
    return ""


# ── Player Character ──────────────────────────────────────────────────


@dataclass
class PlayerCharacter:
    """A character the player embodies in the world."""
    name: str
    settlement: str
    region: str
    profession: str
    gold: int = 100
    health: int = 100
    age: int = 18
    year: int = 0
    month: int = 0  # 0-11, for sub-year time tracking
    alive: bool = True
    inventory: list[str] = field(default_factory=list)
    sim_year_advanced: int = 0  # Total sim years that have been ticked
    # Life legacy tracking (Phase 17 Items 3 & 6)
    legacy_events: list[str] = field(default_factory=list)  # Major life events
    settlements_visited: list[str] = field(default_factory=list)  # Places lived/visited
    total_gold_earned: int = 0
    total_gold_spent: int = 0
    deeds: list[str] = field(default_factory=list)  # Notable accomplishments
    parent_name: str | None = None  # For multi-generational tracking
    # Phase 18 — Skill system & reputation
    skills: dict[str, int] = field(default_factory=_make_skills)
    skill_xp: dict[str, int] = field(default_factory=_make_skill_xp)
    reputation: dict[str, int] = field(default_factory=dict)  # settlement -> -10..+10

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "name": self.name,
            "settlement": self.settlement,
            "region": self.region,
            "profession": self.profession,
            "gold": self.gold,
            "health": self.health,
            "age": self.age,
            "year": self.year,
            "alive": self.alive,
            "inventory": self.inventory,
            "sim_year_advanced": self.sim_year_advanced,
            "legacy_events": self.legacy_events,
            "settlements_visited": self.settlements_visited,
            "total_gold_earned": self.total_gold_earned,
            "total_gold_spent": self.total_gold_spent,
            "deeds": self.deeds,
            "parent_name": self.parent_name,
            "skills": self.skills,
            "skill_xp": self.skill_xp,
            "reputation": self.reputation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerCharacter":
        """Deserialize from a dict."""
        return cls(**{k: data.get(k, v)
                       for k, v in cls.__dataclass_fields__.items()
                       if k in data})  # type: ignore


_OCCUPATIONS = [
    "farmer", "merchant", "blacksmith", "hunter", "fisher",
    "carpenter", "priest", "scholar", "soldier", "thief",
    "innkeeper", "miller", "shepherd", "miner", "potter",
    "alchemist", "ranger", "sailor", "scribe", "tailor",
    "tanner", "healer", "herbalist", "bard", "mason",
    "weaver", "guard", "trader", "baker", "brewer",
    "cartographer", "scout", "sage",
]

# ── Helpers ───────────────────────────────────────────────────────────


def _find_settlement_in_world(world: World, name: str) -> Optional[tuple]:
    """Find a settlement by name. Returns (region, settlement) or None."""
    for region in world.regions:
        for s in region.settlements:
            if s.name.lower() == name.lower():
                return region, s
    return None


def _pick_starting_settlement(world: World, rng: random.Random) -> tuple:
    """Pick a random settlement with decent population."""
    candidates = []
    for region in world.regions:
        for s in region.settlements:
            # Prefer settlements with population > 0
            if s.population > 0:
                candidates.append((region, s))
    if not candidates:
        # Fallback to any settlement
        for region in world.regions:
            for s in region.settlements:
                candidates.append((region, s))
    return rng.choice(candidates)


def _generate_character(world: World, rng: random.Random,
                        name: str | None = None) -> PlayerCharacter:
    """Generate or find a player character grounded in the world."""
    region, settlement = _pick_starting_settlement(world, rng)

    # Try to use an existing narrative character if available
    if world.narrative and world.narrative.characters:
        candidates = [
            c for c in world.narrative.characters
            if c.home_settlement.lower() == settlement.name.lower()
               and c.status == "alive"
        ]
        if candidates:
            char = rng.choice(candidates)
            return PlayerCharacter(
                name=char.full_name if name is None else name,
                settlement=char.home_settlement,
                region=char.home_region,
                profession=char.occupation,
                gold=rng.randint(50, 300),
                health=rng.randint(60, 100),
                age=rng.randint(16, 45),
                year=0,
            )

    # Generate a random character
    if name is None:
        first = rng.choice(["Aldric", "Beorn", "Cedric", "Doran", "Eldon",
                            "Finn", "Gareth", "Hakon", "Ivar", "Jarl",
                            "Kael", "Leif", "Merek", "Niall", "Orin",
                            "Rikard", "Sigurd", "Torin", "Ulf", "Vidar",
                            "Elara", "Freya", "Greta", "Hilda", "Ingrid",
                            "Kara", "Lena", "Mira", "Nora", "Olga",
                            "Runa", "Saga", "Tova", "Ursa", "Vera",
                            "Astrid", "Brynn", "Dagny", "Eira", "Frida"])
        surname = rng.choice(["Blackthorn", "Ironhand", "Stonehelm",
                              "Windwalker", "Oakheart", "Ravenwood",
                              "Silverstream", "Thornfield", "Goldmire",
                              "Stormbringer"])
        name = f"{first} {surname}"

    profession = rng.choice(_OCCUPATIONS)

    return PlayerCharacter(
        name=name,
        settlement=settlement.name,
        region=region.name,
        profession=profession,
        gold=rng.randint(50, 300),
        health=rng.randint(60, 100),
        age=rng.randint(16, 45),
        year=0,
    )


# ── Rendering ─────────────────────────────────────────────────────────


def _status_line(char: PlayerCharacter) -> str:
    """Render the character's status line."""
    health_color = _color(46) if char.health >= 70 else (
        _color(226) if char.health >= 40 else _color(196))
    gold_color = _color(220)
    name_str = f"{ANSI_BOLD}{char.name}{ANSI_RESET}"
    age_str = f"{ANSI_DIM}age {char.age}{ANSI_RESET}"
    health_str = f"{health_color}{'❤' * (char.health // 10)}{ANSI_RESET}"
    gold_str = f"{gold_color}✦ {char.gold}{ANSI_RESET}"
    prof_str = f"{ANSI_DIM}{char.profession}{ANSI_RESET}"

    # Location
    loc_str = f"📍 {char.region} → {char.settlement}"

    line = f"{name_str} | {prof_str} | {age_str} | {health_str} | {gold_str} | Y{char.year:>4}"
    divider = "━" * min(72, len(line) + 2)
    return f"\n{divider}\n  {line}\n{divider}\n  {loc_str}\n"


def _render_welcome(char: PlayerCharacter, world: World,
                    region_name: str) -> str:
    """Render the welcome message when entering play."""
    lines = []
    lines.append(f"\n  {ANSI_BOLD}{_color(45)}═══ wyrd — Embodied Play ═══{ANSI_RESET}")
    lines.append("")
    lines.append(f"  You are {ANSI_BOLD}{char.name}{ANSI_RESET}, "
                 f"a {ANSI_DIM}{char.profession}{ANSI_RESET} in "
                 f"{ANSI_BOLD}{char.settlement}{ANSI_RESET}.")
    lines.append(f"  The world of seed {ANSI_BOLD}{world.seed}{ANSI_RESET} "
                 f"stretches before you.")
    lines.append("")
    lines.append(f"  {_color(226)}►{ANSI_RESET} {ANSI_BOLD}n{ANSI_RESET} next year  "
                 f"{ANSI_BOLD}s{ANSI_RESET} status  {ANSI_BOLD}m{ANSI_RESET} market  "
                 f"{ANSI_BOLD}t{ANSI_RESET} talk  {ANSI_BOLD}r{ANSI_RESET} roam  {ANSI_BOLD}q{ANSI_RESET} quit")
    lines.append(f"  {ANSI_DIM}  Skills grow with use — fight, trade, persuade, survive, craft.{ANSI_RESET}")
    lines.append("")
    return "\n".join(lines)


def _render_news(events: list[SimEvent], char: PlayerCharacter,
                 year: int) -> str:
    """Render recent events in the character's region."""
    # Filter events relevant to the player's region or nearby
    nearby_events = [
        e for e in events
        if e.year == year and (
            char.region in (e.affected_regions or [])
            or char.settlement in (e.affected_settlements or [])
        )
    ]

    # Also show major world events (war, cataclysm, founding)
    major_events = [
        e for e in events
        if e.year == year and e.event_type in (
            "war", "founding", "abandonment",
            "earthquake", "volcanic_eruption", "great_plague",
            "tsunami", "meteor_strike", "great_fire", "magical_cataclysm",
            "faction_war", "faction_collapse",
            "plague", "famine", "discovery",
        ) and e not in nearby_events
    ]

    if not nearby_events and not major_events:
        return f"  {ANSI_DIM}The year passes quietly. Nothing of note reaches your ears.{ANSI_RESET}"

    lines = []
    if nearby_events:
        lines.append(f"  {ANSI_BOLD}Near you:{ANSI_RESET}")
        for ev in nearby_events[:5]:
            lines.append(f"    {_EVENT_ICON.get(ev.event_type, '•')} "
                         f"{ev.description[:100]}")
    if major_events:
        dim_prefix = "  " if not nearby_events else ""
        lines.append(f"  {ANSI_DIM}Distant:{ANSI_RESET}")
        for ev in major_events[:5]:
            lines.append(f"    {_EVENT_ICON.get(ev.event_type, '•')} "
                         f"{ev.description[:80]}")

    return "\n".join(lines)


_EVENT_ICON = {
    "plague": "☠", "famine": "🌾", "war": "⚔", "discovery": "✦",
    "prosperity": "↑", "disaster": "🌋", "exodus": "→",
    "founding": "▲", "abandonment": "✗", "trade_boom": "💰",
    "religious_tension": "✞", "divine_blessing": "✧",
    "holy_pilgrimage": "🚶", "heresy": "🔥",
    "faction_war": "🏴", "faction_alliance": "🤝",
    "faction_power_shift": "⬇", "faction_collapse": "💀",
    "faction_peace_treaty": "☮", "faction_leadership_change": "👑",
    "faction_trade_pact": "📦", "faction_vassal_revolt": "⚡",
    "faction_coup": "🗡",
    "earthquake": "〰", "volcanic_eruption": "🌋",
    "great_plague": "💀", "tsunami": "🌊",
    "meteor_strike": "☄", "great_fire": "🔥",
    "magical_cataclysm": "🌀",
    "trade_collapse": "📉",
}


# ── Interactive Event Choices (Phase 17, Item 4) ──────────────────────


@dataclass
class EventChoiceData:
    """A choice the player can make in response to an event."""
    prompt: str
    event_type: str  # For tracking/logging
    icon: str = "•"


@dataclass
class ChoiceOutcome:
    """Result of the player making a choice."""
    description: str
    gold_delta: int = 0
    health_delta: int = 0
    inventory_add: str | None = None
    travel_dest: str | None = None  # If choice causes travel


def _pick_fallback_settlement(char: PlayerCharacter, world: World | None,
                               rng: random.Random) -> str | None:
    """Pick a random settlement (not the player's current one)."""
    if world is None:
        return None
    candidates = []
    for region in world.regions:
        for s in region.settlements:
            if s.name != char.settlement and s.population > 0:
                candidates.append(s.name)
    if candidates:
        return rng.choice(candidates)
    return None


def _maybe_stranger_scenario(char: PlayerCharacter, world: World,
                              rng: random.Random,
                              events: list) -> EventChoiceData | None:
    """A mysterious stranger arrives in your settlement. ~15% chance."""
    if rng.random() > 0.15:
        return None
    names = ["a hooded traveler", "a scarred old soldier",
             "a merchant with a broken cart", "a ragged messenger",
             "a cloaked stranger"]
    visitor = rng.choice(names)
    return EventChoiceData(
        prompt=f"A stranger arrives — {visitor}. They seek shelter for the night.",
        event_type="stranger",
        icon="🚪",
    )


def _maybe_plague_scenario(char: PlayerCharacter, world: World,
                           rng: random.Random,
                           events: list[SimEvent]) -> EventChoiceData | None:
    """Plague or famine hits - offer choices."""
    has_event = any(
        e.year == char.year
        and e.event_type in ("plague", "famine", "great_plague")
        and (char.settlement in (e.affected_settlements or [])
             or char.region in (e.affected_regions or []))
        for e in events
    )
    if not has_event:
        return None
    return EventChoiceData(
        prompt=f"A {_find_event_type(events, ('plague','famine','great_plague'), char.year)} "
               f"strikes {char.settlement}! The sick fill the streets.",
        event_type="plague",
        icon="☠",
    )


def _maybe_war_scenario(char: PlayerCharacter, world: World,
                        rng: random.Random,
                        events: list[SimEvent]) -> EventChoiceData | None:
    """War in the region - offer choices."""
    has_event = any(
        e.year == char.year
        and e.event_type in ("war", "faction_war", "faction_coup", "faction_vassal_revolt")
        and (char.region in (e.affected_regions or []))
        for e in events
    )
    if not has_event:
        return None
    return EventChoiceData(
        prompt=f"War drums echo through {char.region}! The lord's herald "
               f"calls for able-bodied folk to take up arms.",
        event_type="war",
        icon="⚔",
    )


def _find_event_type(events: list[SimEvent], types: tuple[str, ...],
                     year: int = 0) -> str:
    """Find first matching event type name in recent events for a given year."""
    for e in events:
        if e.year == year and e.event_type in types:
            return e.event_type.replace("_", " ")
    return types[0].replace("_", " ")


def _maybe_merchant_scenario(char: PlayerCharacter, world: World,
                             rng: random.Random,
                             events: list) -> EventChoiceData | None:
    """A merchant offers a deal. ~12% chance, higher in prosperous s'ments."""
    has_trade_event = any(
        e.year == char.year and e.event_type in ("trade_boom", "prosperity")
        for e in events
    )
    # Get prosperity from sim state if available
    base_chance = 0.18 if has_trade_event else 0.10
    if rng.random() > base_chance:
        return None
    goods = rng.choice(["rare spices", "foreign silks", "ancient scrolls",
                        "exotic herbs", "fine steel", "jeweled trinkets"])
    return EventChoiceData(
        prompt=f"A traveling merchant offers you a deal on "
               f"{goods} — a shipment of opportunity.",
        event_type="merchant",
        icon="💰",
    )


def _maybe_discovery_scenario(char: PlayerCharacter, world: World,
                              rng: random.Random,
                              events: list[SimEvent]) -> EventChoiceData | None:
    """Discovery event in the region."""
    has_event = any(
        e.year == char.year
        and e.event_type == "discovery"
        and (char.region in (e.affected_regions or []))
        for e in events
    )
    if not has_event:
        return None
    return EventChoiceData(
        prompt=f"Rumors spread of a discovery in {char.region}! "
               f"Adventurers speak of ancient ruins and hidden treasure.",
        event_type="discovery",
        icon="✦",
    )


def _maybe_religious_scenario(char: PlayerCharacter, world: World,
                              rng: random.Random,
                              events: list[SimEvent]) -> EventChoiceData | None:
    """Religious event or pilgrimage arrives."""
    has_event = any(
        e.year == char.year
        and e.event_type in ("religious_tension", "divine_blessing",
                             "holy_pilgrimage", "heresy")
        and (char.settlement in (e.affected_settlements or [])
             or char.region in (e.affected_regions or []))
        for e in events
    )
    has_pantheon = hasattr(world, 'pantheon') and world.pantheon is not None
    # Chance even without event if world has religion
    if not has_event and (not has_pantheon or rng.random() > 0.08):
        return None
    # Name a deity if we have one
    deity = ""
    if has_pantheon and world.pantheon.deities:
        deity = f" of {rng.choice(world.pantheon.deities).name}"
    return EventChoiceData(
        prompt=f"A procession of faithful{deity} passes through "
               f"{char.settlement}, inviting all to join.",
        event_type="religious",
        icon="✞",
    )


def _maybe_exodus_scenario(char: PlayerCharacter, world: World,
                           rng: random.Random,
                           events: list[SimEvent]) -> EventChoiceData | None:
    """Exodus or abandonment in the region."""
    has_event = any(
        e.year == char.year
        and e.event_type in ("exodus", "abandonment")
        and (char.settlement in (e.affected_settlements or [])
             or char.region in (e.affected_regions or []))
        for e in events
    )
    if not has_event:
        return None
    return EventChoiceData(
        prompt=f"Neighbors pack their carts and flee {char.settlement}. "
               f"The exodus has begun.",
        event_type="exodus",
        icon="→",
    )


# ── Phase 18 — New Scenarios ──────────────────────────────────────────


def _maybe_bandit_raid(char: PlayerCharacter, world: World,
                       rng: random.Random,
                       events: list[SimEvent]) -> EventChoiceData | None:
    """Bandits raid the settlement or nearby road. ~12% base chance, higher in war."""
    war_afoot = any(
        e.year == char.year
        and e.event_type in ("war", "faction_war", "faction_collapse")
        for e in events
    )
    base_chance = 0.18 if war_afoot else 0.10
    if rng.random() > base_chance:
        return None
    targets = ["the outskirts of", "the main road near", "the farms outside"]
    return EventChoiceData(
        prompt=f"Bandits are raiding {rng.choice(targets)} {char.settlement}! "
               f"Smoke rises from the fields.",
        event_type="bandit",
        icon="🗡",
    )


def _maybe_festival(char: PlayerCharacter, world: World,
                    rng: random.Random,
                    events: list[SimEvent]) -> EventChoiceData | None:
    """Festival or celebration. ~10% chance, higher in prosperous times."""
    prosperity_afoot = any(
        e.year == char.year
        and e.event_type in ("prosperity", "trade_boom", "divine_blessing")
        for e in events
    )
    base_chance = 0.18 if prosperity_afoot else 0.08
    if rng.random() > base_chance:
        return None
    festivities = [
        "harvest festival", "founding day", "great market fair",
        "midsummer celebration", "winter solstice feast",
    ]
    return EventChoiceData(
        prompt=f"A {rng.choice(festivities)} begins in {char.settlement}! "
               f"The streets fill with music, food, and laughter.",
        event_type="festival",
        icon="🎉",
    )


def _maybe_monster_hunt(char: PlayerCharacter, world: World,
                        rng: random.Random,
                        events: list[SimEvent]) -> EventChoiceData | None:
    """A dangerous creature threatens the area. Based on world bestiary. ~8%."""
    bestiary = getattr(world, 'bestiary', None)
    if not bestiary:
        return None
    if rng.random() > 0.08:
        return None
    # Pick a threatening creature native to the region biome
    region_obj = next((r for r in world.regions if r.name == char.region), None)
    biome = region_obj.biome if region_obj else "temperate"
    candidates = [c for c in bestiary
                  if c.habitat == biome and c.behavior in ("aggressive", "cunning", "territorial")]
    if not candidates:
        candidates = [c for c in bestiary if c.behavior in ("aggressive", "territorial")]
    if not candidates:
        return None
    creature = rng.choice(candidates)
    return EventChoiceData(
        prompt=f"A {ANSI_BOLD}{creature.name}{ANSI_RESET} has been sighted near "
               f"{char.settlement}! The elders offer a bounty for its head.",
        event_type="monster_hunt",
        icon="🐉",
    )


_SCENARIOS = [
    _maybe_stranger_scenario,
    _maybe_plague_scenario,
    _maybe_war_scenario,
    _maybe_merchant_scenario,
    _maybe_discovery_scenario,
    _maybe_religious_scenario,
    _maybe_exodus_scenario,
    _maybe_bandit_raid,
    _maybe_festival,
    _maybe_monster_hunt,
]


def _get_interactive_events(char: PlayerCharacter, world: World,
                            rng: random.Random,
                            events: list[SimEvent]) -> list[EventChoiceData]:
    """Build a list of interactive events from sim events + random chance.

    Each scenario generates a choice prompt for the player.
    At most 2 events per year, prioritizing triggered (non-random) ones.
    """
    choices: list[EventChoiceData] = []
    for scenario_fn in _SCENARIOS:
        result = scenario_fn(char, world, rng, events)
        if result is not None:
            choices.append(result)
            if len(choices) >= 2:
                break
    return choices


def _resolve_choice(scenario: EventChoiceData, option_index: int,
                    char: PlayerCharacter, world: World,
                    rng: random.Random) -> tuple[ChoiceOutcome, str]:
    """Given a scenario type and player choice index, apply consequences.

    Returns (ChoiceOutcome, option_label_text).
    """
    et = scenario.event_type
    opt = option_index  # 0, 1, or 2

    if et == "stranger":
        if opt == 0:  # Shelter them
            _gain_skill_xp(char, "persuasion", 5)
            shelter_chance = 0.4 + _skill_bonus(char, "persuasion")
            if rng.random() < shelter_chance:
                item = rng.choice(["an old map", "a cryptic note", "a healing salve",
                                   "a pouch of herbs", "a carved talisman"])
                _change_reputation(char, char.settlement, 1)
                return (ChoiceOutcome(
                    description=f"You share your hearth. In thanks, the stranger leaves you "
                                f"{item}.",
                    inventory_add=item,
                    gold_delta=-5,
                ), "Offer shelter")
            else:
                return (ChoiceOutcome(
                    description="You share your hearth. The stranger leaves at dawn "
                                "with a grateful nod. A quiet encounter.",
                    gold_delta=-3,
                ), "Offer shelter")
        elif opt == 1:  # Turn away
            return (ChoiceOutcome(
                description="You close the door. The stranger moves on into the night."
            ), "Turn them away")
        else:  # Rob them
            _gain_skill_xp(char, "combat", 4)
            _change_reputation(char, char.settlement, -2)
            loot = rng.randint(10, 30)
            return (ChoiceOutcome(
                description=f"You overpower the stranger and take {loot} gold. "
                            f"Your conscience weighs heavy.",
                gold_delta=loot,
                health_delta=-10,
            ), "Rob the stranger")

    elif et == "plague":
        if opt == 0:  # Help the sick
            return (ChoiceOutcome(
                description="You tend to the sick day and night. Some recover. "
                            "The community remembers your courage.",
                health_delta=-15,
            ), "Help the sick")
        elif opt == 1:  # Flee
            dest = _pick_fallback_settlement(char, world, rng)
            if dest:
                return (ChoiceOutcome(
                    description=f"You flee the plague and travel to {dest}.",
                    travel_dest=dest,
                    health_delta=-5,
                ), "Flee the settlement")
            return (ChoiceOutcome(
                description="You try to flee but find no safe destination. "
                            "You shelter in place.",
                health_delta=-5,
            ), "Flee (but no safe haven)")
        else:  # Hoard supplies
            return (ChoiceOutcome(
                description="You stockpile food and medicine and wait out "
                            "the sickness behind locked doors.",
                gold_delta=-10,
            ), "Hoard supplies")

    elif et == "war":
        if opt == 0:  # Join the fight
            weapon = rng.choice(["a battered sword", "a sturdy spear",
                                 "a short bow", "a war axe"])
            _gain_skill_xp(char, "combat", 10)
            survive_base = 0.6 + _skill_bonus(char, "combat")
            survive = rng.random() < survive_base
            if survive:
                reward = rng.randint(20, 60)
                return (ChoiceOutcome(
                    description=f"You fight bravely with {weapon}. After the battle, "
                                f"you return with {reward} gold as your share.",
                    gold_delta=reward,
                    health_delta=-20,
                    inventory_add=weapon,
                ), "Take up arms")
            return (ChoiceOutcome(
                description=f"You fight with {weapon} but are wounded badly. "
                            f"You survive, barely.",
                health_delta=-35,
                inventory_add=weapon,
            ), "Take up arms")
        elif opt == 1:  # Provide supplies
            _gain_skill_xp(char, "trade", 5)
            return (ChoiceOutcome(
                description="You contribute supplies to the war effort. "
                            "The quartermaster thanks you.",
                gold_delta=-30,
            ), "Send supplies")
        else:  # Flee
            _gain_skill_xp(char, "survival", 5)
            dest = _pick_fallback_settlement(char, world, rng)
            if dest:
                return (ChoiceOutcome(
                    description=f"You flee the war-torn lands and arrive in {dest}.",
                    travel_dest=dest,
                    gold_delta=-10,
                ), "Flee the region")
            return (ChoiceOutcome(
                description="You hide in the cellar until the fighting passes.",
                health_delta=-5,
            ), "Hide and wait")

    elif et == "merchant":
        if opt == 0:  # Invest
            _gain_skill_xp(char, "trade", 8)
            # Trade skill shifts profit outcomes: higher = less loss, more gain
            trade_bonus = _skill_bonus(char, "trade")
            if trade_bonus > 0.15:
                profit_pool = [-10, 20, 50, 80, 120, 180]
            elif trade_bonus > 0.05:
                profit_pool = [-20, -5, 30, 60, 100, 150]
            else:
                profit_pool = [-30, -10, 20, 50, 100, 150]
            profit = rng.choice(profit_pool)
            if profit > 0:
                return (ChoiceOutcome(
                    description=f"You invest 50 gold. The venture pays off — "
                                f"you earn {profit} gold!",
                    gold_delta=profit,
                ), "Invest 50 gold")
            return (ChoiceOutcome(
                description=f"You invest 50 gold but the deal sours. "
                            f"You lose {-profit} gold.",
                gold_delta=profit,  # negative
            ), "Invest 50 gold")
        elif opt == 1:  # Decline
            return (ChoiceOutcome(
                description="You politely decline. The merchant moves on."
            ), "Decline")
        else:  # Rob
            loot = rng.randint(20, 50)
            return (ChoiceOutcome(
                description=f"You rob the merchant and escape with {loot} gold! "
                            f"Your reputation suffers.",
                gold_delta=loot,
                health_delta=-10,
            ), "Rob the merchant")

    elif et == "discovery":
        if opt == 0:  # Explore
            _gain_skill_xp(char, "survival", 10)
            # Survival skill yields better finds
            surv_bonus = _skill_bonus(char, "survival")
            item_pool = ["an ancient relic", "a golden amulet",
                         "a sealed scroll", "a gemstone",
                         "a mysterious orb", "a silver ring"]
            if surv_bonus > 0.15:
                item_pool.extend(["a dragon-scale", "a crown of stars", "a rune-etched blade"])
            item = rng.choice(item_pool)
            find_gold = rng.randint(10, 40) + int(surv_bonus * 40)
            return (ChoiceOutcome(
                description=f"You brave the ruins and find {item} worth "
                            f"{find_gold} gold!",
                gold_delta=find_gold,
                health_delta=-10,
                inventory_add=item,
            ), "Explore the site")
        elif opt == 1:  # Report
            reward = rng.randint(10, 30)
            return (ChoiceOutcome(
                description=f"You report the discovery to the authorities. "
                            f"They reward you with {reward} gold.",
                gold_delta=reward,
            ), "Report to authorities")
        else:
            return (ChoiceOutcome(
                description="You let others have their adventures. "
                            "The world turns without you."
            ), "Ignore it")

    elif et == "religious":
        if opt == 0:  # Join/Pray
            _gain_skill_xp(char, "persuasion", 5)
            healing = rng.randint(5, 20) + int(_skill_bonus(char, "persuasion") * 20)
            _change_reputation(char, char.settlement, 1)
            return (ChoiceOutcome(
                description=f"You join the procession and pray. "
                            f"You feel restored (+{healing} health).",
                health_delta=healing,
            ), "Join the procession")
        elif opt == 1:  # Donate
            _gain_skill_xp(char, "persuasion", 3)
            return (ChoiceOutcome(
                description="You make an offering to the faithful. "
                            "They bless your generosity.",
                gold_delta=-15,
                health_delta=5,
            ), "Make an offering")
        else:
            return (ChoiceOutcome(
                description="You watch from your window as the procession "
                            "passes by. The day continues."
            ), "Watch from afar")

    elif et == "exodus":
        if opt == 0:  # Join exodus
            _gain_skill_xp(char, "survival", 8)
            dest = _pick_fallback_settlement(char, world, rng)
            if dest:
                return (ChoiceOutcome(
                    description=f"You pack your belongings and join the exodus "
                                f"to {dest}. A new beginning.",
                    travel_dest=dest,
                    gold_delta=-15,
                ), "Join the exodus")
            return (ChoiceOutcome(
                description="You try to join the exodus but find nowhere to go. "
                            "You return home, shaken.",
                health_delta=-5,
            ), "Join (but lost)")
        elif opt == 1:  # Stay and rebuild
            _gain_skill_xp(char, "crafting", 8)
            return (ChoiceOutcome(
                description="You stay and help rebuild. "
                            "Those who remain band together.",
                gold_delta=-10,
                health_delta=5,
            ), "Stay and rebuild")
        else:  # Loot abandoned homes
            _gain_skill_xp(char, "survival", 5)
            loot = rng.randint(10, 25)
            return (ChoiceOutcome(
                description=f"You find abandoned goods worth {loot} gold.",
                gold_delta=loot,
                health_delta=-5,
            ), "Scavenge what remains")

    elif et == "bandit":
        if opt == 0:  # Fight the bandits
            _gain_skill_xp(char, "combat", 10)
            win_chance = 0.5 + _skill_bonus(char, "combat")
            if rng.random() < win_chance:
                reward = rng.randint(15, 50)
                _change_reputation(char, char.settlement, 2)
                return (ChoiceOutcome(
                    description=f"You drive off the bandits! The townsfolk "
                                f"reward your bravery with {reward} gold.",
                    gold_delta=reward,
                    health_delta=-rng.randint(5, 15),
                ), "Fight the bandits")
            return (ChoiceOutcome(
                description="The bandits overwhelm you. You're beaten and left "
                            "for dead, but somehow survive.",
                gold_delta=-rng.randint(10, 30),
                health_delta=-25,
            ), "Fight the bandits")
        elif opt == 1:  # Pay them off
            _gain_skill_xp(char, "trade", 5)
            cost = rng.randint(15, 40)
            return (ChoiceOutcome(
                description=f"You pay the bandits {cost} gold to leave you be. "
                            f"They take the gold and disappear into the shadows.",
                gold_delta=-cost,
            ), "Pay them off")
        else:  # Hide and wait
            _gain_skill_xp(char, "survival", 5)
            return (ChoiceOutcome(
                description="You hide in the cellar until the bandits move on. "
                            "The settlement is shaken but you survive.",
                health_delta=-5,
            ), "Hide and wait")

    elif et == "festival":
        if opt == 0:  # Join the celebration
            _gain_skill_xp(char, "persuasion", 5)
            _change_reputation(char, char.settlement, 1)
            gold_found = rng.randint(5, 20)
            health_gain = rng.randint(3, 10)
            return (ChoiceOutcome(
                description=f"You throw yourself into the festivities! You make "
                            f"friends, feast, and even win {gold_found} gold in "
                            f"the games. (+{health_gain} health)",
                gold_delta=gold_found,
                health_delta=health_gain,
            ), "Join the celebration")
        elif opt == 1:  # Help organize
            _gain_skill_xp(char, "crafting", 8)
            _change_reputation(char, char.settlement, 2)
            earnings = rng.randint(10, 30)
            return (ChoiceOutcome(
                description=f"You help organize the festival. Your efforts are "
                            f"noticed — the elders pay you {earnings} gold and "
                            f"thank you warmly.",
                gold_delta=earnings,
            ), "Help organize")
        else:  # Skip it
            return (ChoiceOutcome(
                description="You stay home while the settlement celebrates. "
                            "A quiet night."
            ), "Skip it")

    elif et == "monster_hunt":
        if opt == 0:  # Hunt the creature
            _gain_skill_xp(char, "combat", 12)
            hunt_chance = 0.4 + _skill_bonus(char, "combat") + _skill_bonus(char, "survival")
            if rng.random() < hunt_chance:
                bounty = rng.randint(30, 80)
                _change_reputation(char, char.settlement, 3)
                _record_deed(char, "Slayed a dangerous creature")
                return (ChoiceOutcome(
                    description=f"You track and slay the creature! The bounty of "
                                f"{bounty} gold is yours, and the settlement "
                                f"celebrates your heroism.",
                    gold_delta=bounty,
                    health_delta=-rng.randint(10, 25),
                ), "Hunt the creature")
            return (ChoiceOutcome(
                description="The creature proves too cunning. It wounds you "
                            "badly before escaping into the wilds.",
                health_delta=-30,
                gold_delta=-rng.randint(5, 15),
            ), "Hunt the creature")
        elif opt == 1:  # Hire a hunter
            _gain_skill_xp(char, "trade", 5)
            cost = rng.randint(20, 40)
            success = rng.random() < 0.6
            if success:
                return (ChoiceOutcome(
                    description=f"You hire a seasoned hunter for {cost} gold. "
                                f"They return with the creature's head! "
                                f"The settlement is safe.",
                    gold_delta=-cost,
                ), "Hire a hunter")
            return (ChoiceOutcome(
                description=f"You pay {cost} gold but the hunter returns empty-handed. "
                            f"The creature is still out there.",
                gold_delta=-cost,
            ), "Hire a hunter")
        else:  # Ignore
            return (ChoiceOutcome(
                description="You ignore the threat. Others will deal with it — "
                            "or not. The world turns."
            ), "Ignore the threat")

    # Fallback
    return (ChoiceOutcome(
        description="You do nothing. The moment passes.",
    ), "Do nothing")


def _render_interactive_event(choices: list[EventChoiceData]) -> str:
    """Render the choice prompt."""
    lines = []
    lines.append(f"\n  {_color(226)}{'═' * 40}{ANSI_RESET}")
    for i, sc in enumerate(choices):
        lines.append(f"  {sc.icon} {sc.prompt}")
        if i == 0:
            lines.append(f"    {_color(46)}1.{ANSI_RESET} {_label_for_event(sc.event_type, 0)}")
            lines.append(f"    {_color(226)}2.{ANSI_RESET} {_label_for_event(sc.event_type, 1)}")
            lines.append(f"    {_color(196)}3.{ANSI_RESET} {_label_for_event(sc.event_type, 2)}")
    lines.append(f"  {_color(226)}{'═' * 40}{ANSI_RESET}")
    return "\n".join(lines)


def _label_for_event(event_type: str, option_index: int) -> str:
    """Get the label text for a given event type + option index."""
    labels = {
        "stranger": ["Offer shelter", "Turn them away", "Rob the stranger"],
        "plague":   ["Help the sick", "Flee the settlement", "Hoard supplies"],
        "war":      ["Take up arms", "Send supplies", "Flee the region"],
        "merchant": ["Invest 50 gold", "Decline the offer", "Rob the merchant"],
        "discovery":["Explore the site", "Report to authorities", "Ignore it"],
        "religious":["Join the procession", "Make an offering", "Watch from afar"],
        "exodus":   ["Join the exodus", "Stay and rebuild", "Scavenge what remains"],
        "bandit":   ["Fight the bandits", "Pay them off", "Hide and wait"],
        "festival": ["Join the celebration", "Help organize", "Skip it"],
        "monster_hunt": ["Hunt the creature", "Hire a hunter", "Ignore the threat"],
    }
    opts = labels.get(event_type, ["Accept", "Decline", "Ignore"])
    if option_index < len(opts):
        return opts[option_index]
    return "Do nothing"


def _handle_interactive_events(char: PlayerCharacter, world: World,
                                rng: random.Random,
                                events: list[SimEvent]) -> None:
    """Check for interactive events and prompt the player for choices.
    
    Called after each year's sim tick. At most 2 scenarios per year.
    Tracks gold, deeds, and legacy events.
    """
    choices = _get_interactive_events(char, world, rng, events)
    if not choices:
        return

    print(_render_interactive_event(choices))

    for sc in choices:
        try:
            raw = input(f"  {_color(226)}►{ANSI_RESET} Your choice (1-3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raw = "1"  # Default: first option

        if raw not in ("1", "2", "3"):
            print(f"  {ANSI_DIM}You hesitate and choose the first option.{ANSI_RESET}")
            raw = "1"

        opt_idx = int(raw) - 1
        outcome, label = _resolve_choice(sc, opt_idx, char, world, rng)

        # Track gold before applying
        if outcome.gold_delta > 0:
            char.total_gold_earned += outcome.gold_delta
        elif outcome.gold_delta < 0:
            char.total_gold_spent += abs(outcome.gold_delta)

        # Apply consequences
        char.gold += outcome.gold_delta
        char.health = max(0, min(100, char.health + outcome.health_delta))
        if outcome.inventory_add:
            if outcome.inventory_add not in char.inventory:
                char.inventory.append(outcome.inventory_add)
        if outcome.travel_dest:
            char.settlement = outcome.travel_dest
            if outcome.travel_dest not in char.settlements_visited:
                char.settlements_visited.append(outcome.travel_dest)

        # Record deeds for notable choices
        if sc.event_type == "war" and opt_idx == 0:
            _record_deed(char, "Fought in a war")
        elif sc.event_type == "plague" and opt_idx == 0:
            _record_deed(char, "Helped the sick during a plague")
        elif sc.event_type == "discovery" and opt_idx == 0:
            _record_deed(char, "Explored ancient ruins")
        elif sc.event_type == "stranger" and opt_idx == 0:
            _record_deed(char, "Showed kindness to a stranger")
        elif sc.event_type == "exodus" and opt_idx == 0:
            _record_deed(char, "Joined an exodus to new lands")
        elif sc.event_type == "exodus" and opt_idx == 1:
            _record_deed(char, "Stayed to rebuild after an exodus")
        elif sc.event_type == "religious" and opt_idx == 0:
            _record_deed(char, "Joined a religious procession")
        elif sc.event_type == "merchant" and opt_idx == 0:
            _record_deed(char, "Invested in trade")
        elif sc.event_type == "bandit" and opt_idx == 0:
            _record_deed(char, "Fought off bandits")
        elif sc.event_type == "festival" and opt_idx == 0:
            _record_deed(char, "Joined a festival celebration")
        elif sc.event_type == "festival" and opt_idx == 1:
            _record_deed(char, "Organized a festival")
        elif sc.event_type == "monster_hunt" and opt_idx == 0:
            _record_deed(char, "Hunted a deadly creature")
        elif sc.event_type == "monster_hunt" and opt_idx == 1:
            _record_deed(char, "Hired a monster hunter")

        # Record legacy event
        _record_legacy_event(char, f"{label} — {outcome.description[:60]}")

        if outcome.health_delta < 0:
            color_fn = _color(196)
        elif outcome.health_delta > 0:
            color_fn = _color(46)
        else:
            color_fn = ""

        gold_str = ""
        if outcome.gold_delta > 0:
            gold_str = f" {_color(220)}+{outcome.gold_delta}g{ANSI_RESET}"
        elif outcome.gold_delta < 0:
            gold_str = f" {_color(196)}{outcome.gold_delta}g{ANSI_RESET}"
        health_str = ""
        if outcome.health_delta > 0:
            health_str = f" {_color(46)}+{outcome.health_delta}hp{ANSI_RESET}"
        elif outcome.health_delta < 0:
            health_str = f" {_color(196)}{outcome.health_delta}hp{ANSI_RESET}"

        suffix = f"{gold_str}{health_str}" if gold_str or health_str else ""
        print(f"  {label}: {outcome.description}{suffix}")

        # Check death from choice
        if char.health <= 0:
            char.alive = False
            print(f"\n  {ANSI_BOLD}{_color(196)}Your wounds prove fatal.{ANSI_RESET}")

        if outcome.travel_dest:
            print(f"  🚶 You arrive in {_color(45)}{outcome.travel_dest}{ANSI_RESET}.")

    # Check death
    if char.health <= 0:
        char.alive = False
        print(f"\n  {ANSI_BOLD}{_color(196)}You have died from your wounds.{ANSI_RESET}")


def _render_travel_options(char: PlayerCharacter,
                           world: World) -> list[str]:
    """List settlements the player can travel to."""
    # Find settlements in the same region
    options = []
    for region in world.regions:
        if region.name == char.region:
            for s in region.settlements:
                if s.name != char.settlement and s.population > 0:
                    options.append(s.name)
    # Also settlements in adjacent regions (simple: any other region)
    if not options:
        for region in world.regions:
            if region.name != char.region:
                for s in region.settlements:
                    if s.population > 0:
                        options.append(f"{s.name} ({region.name})")
    return options


# ── Main Game Loop ────────────────────────────────────────────────────


def _prompt(char: PlayerCharacter, world: World, state: SimState,
            events: list[SimEvent], rng: random.Random,
            chaos: float, max_years: int = 100) -> tuple[bool, int]:
    """One turn of the game loop.
    
    Returns (continue_playing, months_to_advance).
    months_to_advance is 0 if no time passes, >0 for time to pass.
    """
    print(_status_line(char))

    # Show recent news (matching current year)
    news = _render_news(events, char, char.year)
    if news:
        print(news)
        print()

    # Show current date
    seasons = ["Winter", "Spring", "Summer", "Autumn"]
    season = seasons[char.month // 3] if char.month < 12 else "Unknown"
    date_str = f"{ANSI_DIM}{season}, Year {char.year} — Month {char.month + 1}{ANSI_RESET}"
    print(f"  {date_str}")

    # Prompt — two-line layout
    print(f"  {ANSI_DIM}[n]ext  [1m] month  [1w] week  [s]tatus  [t]alk  [r]oam  "
          f"[q]uit{ANSI_RESET}")
    print(f"  {ANSI_DIM}[m]arket  [g]oals  [a]mbient{ANSI_RESET}")
    try:
        cmd = input(f"  {_color(226)}►{ANSI_RESET} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False, 0

    if cmd == "q":
        return False, 0
    elif cmd == "s":
        # Just re-display; the status is already shown
        print(f"  You are {ANSI_BOLD}{char.name}{ANSI_RESET}, "
              f"a {ANSI_DIM}{char.profession}{ANSI_RESET}.")
        print(f"  Current wealth: {_color(220)}{char.gold} gold{ANSI_RESET}")
        print(f"  Health: {char.health}/100")
        print(f"  Age: {char.age}")
        print(f"  Season: {season}, Month {char.month + 1}")
        print(f"  Inventory: {', '.join(char.inventory) if char.inventory else 'nothing yet'}")
        # Show skills
        skill_strs = [f"{_color(45)}{s.capitalize()}: {lvl}{ANSI_RESET}"
                      for s, lvl in char.skills.items()]
        print(f"  Skills: {', '.join(skill_strs)}")
        # Show reputation
        if char.reputation:
            rep_strs = [f"{s}: {v:+d}" for s, v in
                        sorted(char.reputation.items(), key=lambda x: -abs(x[1]))[:3]]
            print(f"  Reputation: {', '.join(rep_strs)}")
        if char.deeds:
            print(f"  Deeds: {', '.join(char.deeds[:3])}"
                  f"{'…' if len(char.deeds) > 3 else ''}")
        if char.settlements_visited:
            print(f"  Places: {', '.join(char.settlements_visited[:5])}"
                  f"{'…' if len(char.settlements_visited) > 5 else ''}")
        return True, 0
    elif cmd == "t":
        _handle_talk(char, world, rng)
        return True, 0
    elif cmd == "r":  # Roam (travel)
        _handle_travel(char, world, state, rng, chaos)
        return True, 0  # Travel already advanced time internally
    elif cmd == "g":
        _handle_quests(char, world)
        return True, 0
    elif cmd == "a":
        _handle_ambient(char, world, state, rng, chaos, max_years)
        return True, 0
    elif cmd == "m":
        _handle_market(char, world, state)
        return True, 0
    elif cmd in ("n", "next"):
        return True, 12  # Advance one full year (12 months)
    elif cmd in ("1m", "month"):
        return True, 1  # One month
    elif cmd in ("1w", "week"):
        return True, 0  # ~0.25 months — skip for now
    else:
        print(f"  {ANSI_DIM}Unknown: '{cmd}'. Try n, 1m, 1w, s, m, t, or q.{ANSI_RESET}")

    return True, 0


# ── Travel Creature Encounters ──────────────────────────────────────────


def _pick_creature_for_biome(world: World, biome: str) -> Optional["Creature"]:
    """Pick a creature from the world's bestiary matching a biome.

    Falls back to any creature if no biome match found.
    Returns None if bestiary is empty.
    """
    from .bestiary import Creature
    bestiary = getattr(world, 'bestiary', None)
    if not bestiary:
        return None
    candidates = [c for c in bestiary if c.habitat == biome and c.habitat != "various"]
    if not candidates:
        # Fallback: creatures from any habitat that aren't exclusive
        candidates = [c for c in bestiary if c.habitat != "various"]
    if not candidates:
        candidates = bestiary
    return random.choice(candidates) if candidates else None


def _resolve_travel_encounter(outcome: int, creature: "Creature",
                               char: PlayerCharacter,
                               rng: random.Random) -> str:
    """Resolve a creature encounter option and apply consequences.

    Args:
        outcome: 0 = fight, 1 = flee, 2 = negotiate
        creature: The encountered creature
        char: The player character
        rng: Random state

    Returns:
        A description string of what happened.
    """
    from .bestiary import Creature
    tier = creature.tier
    tier_factor = tier / 3.0  # 0.33 for tier 1, 1.0 for tier 3, 1.67 for tier 5

    if outcome == 0:  # Fight
        # Base survival chance: 70%, reduced by tier
        survive_chance = max(0.2, 0.7 - (tier - 1) * 0.1)
        if rng.random() < survive_chance:
            # Victory!
            gold_reward = rng.randint(5, 15) * tier
            health_cost = -rng.randint(5, 15) * int(tier_factor)
            from .shop import creature_loot
            loot_items = creature_loot(creature.creature_type, tier, rng)
            char.gold += gold_reward
            char.total_gold_earned += gold_reward
            char.health = max(0, min(100, char.health + health_cost))
            for li in loot_items:
                char.inventory.append(li["name"])
            _record_deed(char, f"Defeated a {creature.name} in combat")
            _record_legacy_event(char, f"Survived an encounter with {creature.name}")
            parts = [f"You draw your weapon and face the {creature.name}!"]
            parts.append(f"After a fierce struggle, you emerge victorious!")
            parts.append(f"You find {gold_reward} gold on the beast's remains.")
            if health_cost:
                parts.append(f"You are wounded ({health_cost} HP).")
            if loot_items:
                loot_names = [li["name"] for li in loot_items[:2]]
                parts.append(f"You recover: {', '.join(loot_names)}.")
                if len(loot_items) > 2:
                    parts.append(f"... and {len(loot_items) - 2} more items.")
            return "\n".join(parts)
        else:
            # Defeat
            dmg = -rng.randint(15, 30) * int(max(1, tier_factor))
            char.health = max(0, min(100, char.health + dmg))
            gold_loss = rng.randint(10, 30) * tier
            char.gold = max(0, char.gold - gold_loss)
            char.total_gold_spent += gold_loss
            _record_legacy_event(char, f"Barely survived an attack by {creature.name}")
            parts = [f"You draw your weapon and face the {creature.name}!"]
            parts.append(f"The creature is too strong! You are badly wounded.")
            if gold_loss > 0:
                parts.append(f"You lose {gold_loss} gold fleeing.")
            parts.append(f"You retreat, bloodied and battered.")
            return "\n".join(parts)

    elif outcome == 1:  # Flee
        flee_chance = max(0.3, 0.8 - (tier - 1) * 0.1)
        if rng.random() < flee_chance:
            return f"You slip away into the undergrowth. The {creature.name} loses your trail."
        else:
            dmg = -rng.randint(5, 15) * int(tier_factor)
            char.health = max(0, min(100, char.health + dmg))
            _record_legacy_event(char, f"Escaped from a {creature.name}")
            return (f"You try to flee but the {creature.name} catches you! "
                    f"You fend it off and escape, wounded ({abs(dmg)} HP lost).")

    else:  # Negotiate / Make noise / Distract
        if creature.behavior in ("docile", "curious", "defensive"):
            return (f"The {creature.name} regards you with cautious interest, "
                    f"then turns and disappears into the wild. A tense moment passes.")
        elif creature.behavior in ("cunning", "patient"):
            # Might trick you
            if rng.random() < 0.5:
                gold_loss = rng.randint(5, 20)
                char.gold = max(0, char.gold - gold_loss)
                char.total_gold_spent += gold_loss
                return (f"The {creature.name} feigns disinterest, then "
                        f"circles back and steals {gold_loss} gold from your pack!")
            return (f"The {creature.name} watches you from a distance, "
                    f"then vanishes into the shadows.")
        else:
            # Aggressive creatures don't negotiate
            dmg = -rng.randint(5, 15) * int(tier_factor)
            char.health = max(0, min(100, char.health + dmg))
            _record_legacy_event(char, f"Survived a {creature.name} ambush")
            return (f"The {creature.name} has no interest in negotiation! "
                    f"It attacks, catching you off guard ({abs(dmg)} HP lost).")


def _find_biome_for_settlement(world: World, settlement_name: str) -> str:
    """Find the biome for a given settlement name."""
    for region in world.regions:
        for s in region.settlements:
            if s.name.lower() == settlement_name.lower():
                return region.biome
    return "temperate"


def _maybe_travel_encounter(char: PlayerCharacter,
                            world: World) -> bool:
    """Check for a creature encounter during travel. ~30% chance.

    If an encounter occurs, it prompts the player with choices and
    resolves the outcome. Returns True if encounter happened.
    """
    # 30% base chance
    if random.random() > 0.30:
        return False

    # Find a creature matching the region biome
    biome = _find_biome_for_settlement(world, char.settlement)
    creature = _pick_creature_for_biome(world, biome)
    if creature is None:
        return False

    # Use a dedicated RNG for deterministic-ish outcomes
    import random as rnd
    rng = rnd.Random(hash((char.name, char.year, creature.name)) & 0xFFFFFFFF)

    print(f"\n  {_color(196)}{'═' * 40}{ANSI_RESET}")
    print(f"  {ANSI_BOLD}{_color(196)}⚠ ENCOUNTER!{ANSI_RESET}")
    unique_mark = f" {_color(226)}★{ANSI_RESET}" if creature.is_unique else ""
    print(f"  A {ANSI_BOLD}{_color(172)}{creature.name}{ANSI_RESET}{unique_mark} "
          f"bars your path!")
    print(f"  {ANSI_DIM}{creature.description[:100]}{ANSI_RESET}")
    print(f"  {ANSI_DIM}Tier {creature.tier} · {creature.behavior.replace('_', ' ')} · "
          f"{creature.size}{ANSI_RESET}")
    print(f"  {_color(196)}{'═' * 40}{ANSI_RESET}")

    try:
        raw = input(f"  {_color(226)}►{ANSI_RESET} [1] Fight  [2] Flee  [3] Distract: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raw = "2"  # Default: flee

    if raw not in ("1", "2", "3"):
        print(f"  {ANSI_DIM}You hesitate. The creature attacks!{ANSI_RESET}")
        raw = "1"  # Default: fight

    outcome_idx = int(raw) - 1
    result = _resolve_travel_encounter(outcome_idx, creature, char, rng)
    print(f"  {result}")

    # Check for death
    if char.health <= 0:
        char.alive = False
        print(f"\n  {ANSI_BOLD}{_color(196)}The {creature.name}'s attack proves fatal.{ANSI_RESET}")

    # Travel takes time regardless
    return True


def _handle_quests(char: PlayerCharacter, world: World) -> None:
    """Show quest log, milestones, and skill progression."""
    print(f"\n  {ANSI_BOLD}{_color(45)}═══ Quest Log & Milestones ═══{ANSI_RESET}")

    # Available quests from narrative engine
    narrative = getattr(world, 'narrative', None)
    quests = narrative.quests if narrative and hasattr(narrative, 'quests') else []
    local_quests = [q for q in quests if q.is_active and
                    (q.giver_settlement.lower() == char.settlement.lower())]

    if local_quests:
        print(f"\n  {ANSI_BOLD}Available Quests:{ANSI_RESET}")
        for q in local_quests[:5]:
            diff_color = _color(46) if q.difficulty == "easy" else (
                _color(226) if q.difficulty == "medium" else _color(196))
            print(f"    {ANSI_DIM}✦{ANSI_RESET} {ANSI_BOLD}{q.name}{ANSI_RESET}")
            print(f"      {ANSI_DIM}{q.description[:80]}{ANSI_RESET}")
            print(f"      {diff_color}{q.difficulty}{ANSI_RESET} "
                  f"· {ANSI_DIM}Reward: {', '.join(q.rewards[:2])}{ANSI_RESET}")
    else:
        print(f"\n  {ANSI_DIM}No quests available nearby. Explore to find opportunities.{ANSI_RESET}")

    # Skills with XP bars
    print(f"\n  {ANSI_BOLD}Skills:{ANSI_RESET}")
    for skill_name in SKILL_NAMES:
        level = char.skills.get(skill_name, 1)
        xp = char.skill_xp.get(skill_name, 0)
        next_xp = _xp_to_next_level(level)
        current_in_level = xp - _xp_for_level(level)
        bar_len = 10
        filled = min(bar_len, int((current_in_level / max(1, next_xp)) * bar_len))
        bar = f"{_color(46)}{'▓' * filled}{ANSI_DIM}{'░' * (bar_len - filled)}{ANSI_RESET}"
        print(f"    {ANSI_BOLD}{skill_name.capitalize()}:{ANSI_RESET} "
              f"Level {level} {bar} ({current_in_level}/{next_xp} XP)")

    # Deeds / Milestones
    if char.deeds:
        print(f"\n  {ANSI_BOLD}Deeds & Milestones ({len(char.deeds)}):{ANSI_RESET}")
        for i, deed in enumerate(char.deeds):
            print(f"    {ANSI_DIM}{'●' if i < 5 else '○'}{ANSI_RESET} {deed}")
            if i >= 9:
                print(f"    {ANSI_DIM}... and {len(char.deeds) - 10} more{ANSI_RESET}")
                break

    # Reputation
    if char.reputation:
        print(f"\n  {ANSI_BOLD}Reputation:{ANSI_RESET}")
        for s, v in sorted(char.reputation.items(), key=lambda x: -abs(x[1]))[:5]:
            rep_color = _color(46) if v > 0 else (_color(196) if v < 0 else _color(226))
            print(f"    {ANSI_DIM}{s}:{ANSI_RESET} {rep_color}{v:+d}{ANSI_RESET}")

    # Life stats
    print(f"\n  {ANSI_BOLD}Life Stats:{ANSI_RESET}")
    print(f"    Age: {char.age}  |  Year: {char.year}  |  Gold earned: {char.total_gold_earned}")
    print(f"    Settlements visited: {len(char.settlements_visited)}  "
          f"|  Legacy events: {len(char.legacy_events)}")
    print()


def _handle_ambient(char: PlayerCharacter, world: World,
                    state: SimState, rng: random.Random,
                    chaos: float, max_years: int) -> None:
    """Ambient time-flow mode — time passes automatically.

    - Space toggles slow (1 month/tick) ↔ fast (12 months/tick)
    - Auto-pauses on major events (war, founding, cataclysm, discovery)
    - Any other key returns to normal mode
    - ESC/q to quit
    """
    import sys as _sys

    # Terminal setup for raw input
    import tty
    import termios
    fd = _sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    speed = "slow"  # slow = 1 month/tick, fast = 12 months/tick
    tick_interval = 1.5  # seconds between ticks
    running = True

    print(f"\n  {ANSI_BOLD}{_color(45)}═══ Ambient Mode ═══{ANSI_RESET}")
    print(f"  {ANSI_DIM}Time passes automatically. "
          f"[Space] toggle speed  [any key] exit{ANSI_RESET}")

    try:
        tty.setraw(fd)
        while running and char.alive and char.year < max_years:
            # Status line
            seasons = ["Winter", "Spring", "Summer", "Autumn"]
            season = seasons[char.month // 3] if char.month < 12 else "Unknown"
            speed_label = f"{_color(46)}SLOW{ANSI_RESET}" if speed == "slow" else f"{_color(196)}FAST{ANSI_RESET}"
            print(f"\r  {ANSI_DIM}{season}, Y{char.year} M{char.month + 1}  "
                  f"{char.settlement}  ❤{char.health}  ✦{char.gold}  "
                  f"Speed: {speed_label}{ANSI_RESET}   ", end="", flush=True)

            # Advance time
            months = 1 if speed == "slow" else 12
            new_events = _advance_time(char, world, state, rng, chaos, months=months)
            _auto_save(char, world)

            # Check for auto-pause events
            pause_events = [e for e in new_events if e.event_type in (
                "war", "founding", "abandonment", "earthquake",
                "volcanic_eruption", "great_plague", "tsunami",
                "meteor_strike", "great_fire", "magical_cataclysm",
                "faction_war", "faction_collapse", "discovery",
            )]

            if pause_events:
                for ev in pause_events:
                    icon = _EVENT_ICON.get(ev.event_type, "⚡")
                    print(f"\n  {ANSI_BOLD}{_color(196)}{icon} EVENT!{ANSI_RESET} "
                          f"{ev.description[:80]}")
                    print(f"  {ANSI_DIM}Press any key to continue...{ANSI_RESET}")
                    # Wait for keypress
                    if _sys.stdin.read(1):
                        break

            # Check for keypress (non-blocking)
            import select
            dr, _, _ = select.select([_sys.stdin], [], [], tick_interval)
            if dr:
                key = _sys.stdin.read(1)
                if key == " ":
                    speed = "fast" if speed == "slow" else "slow"
                    tick_interval = 0.5 if speed == "fast" else 1.5
                elif key in ("q", "\x1b"):  # q or ESC
                    running = False
                else:
                    # Any other key exits ambient mode
                    running = False
    except Exception:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    _sys.stdout.write(f"\r  {ANSI_DIM}Ambient mode ended.{ANSI_RESET}  \n")


def _handle_travel(char: PlayerCharacter, world: World,
                   state: SimState, rng: random.Random,
                   chaos: float) -> None:
    """Handle travel to another settlement.
    
    Travel takes 1-2 months depending on distance.
    """
    options = _render_travel_options(char, world)
    if not options:
        print(f"  {ANSI_DIM}No destinations available. The world is thin here.{ANSI_RESET}")
        return

    print(f"\n  {ANSI_BOLD}Travel Destinations:{ANSI_RESET}")
    for i, opt in enumerate(options[:10]):
        print(f"    {i+1}. {opt}")
    if len(options) > 10:
        print(f"    ... and {len(options) - 10} more")

    try:
        choice = input(f"  {_color(226)}►{ANSI_RESET} Choose (0 to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice.isdigit() or int(choice) == 0:
        print(f"  {ANSI_DIM}Travel cancelled.{ANSI_RESET}")
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(options):
        print(f"  {ANSI_DIM}Invalid choice.{ANSI_RESET}")
        return

    dest = options[idx]
    # Parse destination name (may include region in parens)
    dest_name = dest.split(" (")[0].strip()

    print(f"  🚶 You travel to {ANSI_BOLD}{dest_name}{ANSI_RESET}...")

    # Creature encounter during travel
    encounter_happened = _maybe_travel_encounter(char, world)

    char.settlement = dest_name
    # Track visited settlement
    if dest_name not in char.settlements_visited:
        char.settlements_visited.append(dest_name)
        if len(char.settlements_visited) >= 3:
            _record_deed(char, f"Visited {len(char.settlements_visited)} settlements")

    # Travel takes 1-2 months (sub-year!)
    travel_months = 1 + (1 if encounter_happened else 0)
    _advance_time(char, world, state, rng, chaos, months=travel_months)

    if not encounter_happened:
        print(f"  You arrive safely. ({travel_months} month{'s' if travel_months != 1 else ''} pass)")
    else:
        print(f"  {ANSI_DIM}You eventually reach {ANSI_BOLD}{dest_name}{ANSI_RESET}{ANSI_DIM}.{ANSI_RESET}")


def _handle_talk(char: PlayerCharacter, world: World,
                 rng: random.Random) -> None:
    """Talk to NPCs in the current settlement.

    Finds narrative characters in the same settlement, lists them,
    and lets the player chat with one for flavor dialogue.
    """
    npcs = _find_npcs_in_settlement(world, char.settlement)
    if not npcs:
        print(f"  {ANSI_DIM}There's no one notable nearby to talk to.{ANSI_RESET}")
        return

    print(f"\n  {ANSI_BOLD}People nearby in {char.settlement}:{ANSI_RESET}")
    for i, npc in enumerate(npcs[:8]):
        traits_str = ", ".join(npc.personality_traits[:2])
        print(f"    {i+1}. {ANSI_BOLD}{npc.full_name}{ANSI_RESET} — "
              f"{ANSI_DIM}{npc.occupation} ({traits_str}){ANSI_RESET}")
    if len(npcs) > 8:
        print(f"    ... and {len(npcs) - 8} more.")

    try:
        choice = input(f"  {_color(226)}►{ANSI_RESET} Talk to # (0 to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice.isdigit() or int(choice) == 0:
        print(f"  {ANSI_DIM}You nod politely and move on.{ANSI_RESET}")
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(npcs):
        print(f"  {ANSI_DIM}No one by that number.{ANSI_RESET}")
        return

    npc = npcs[idx]
    _chat_with_npc(npc, char, rng)


def _find_npcs_in_settlement(world: World, settlement_name: str) -> list:
    """Find narrative characters in a settlement."""
    narrative = getattr(world, 'narrative', None)
    if not narrative or not narrative.characters:
        return []
    return [
        c for c in narrative.characters
        if c.home_settlement.lower() == settlement_name.lower()
        and c.status == "alive"
    ]


def _chat_with_npc(npc, char: PlayerCharacter,
                   rng: random.Random) -> None:
    """Generate a short conversation with an NPC based on personality/occupation."""
    import random as rnd_mod
    local_rng = rnd_mod.Random(hash((char.name, npc.full_name, char.year)) & 0xFFFFFFFF)

    # Greeting varies by personality
    warm_traits = {"kind", "gentle", "cheerful", "generous", "humble", "curious"}
    cool_traits = {"stern", "brooding", "silent", "proud", "deceitful", "greedy"}

    npc_traits = set(npc.personality_traits)
    if npc_traits & warm_traits:
        greetings = [
            f"\"Ah, a friendly face! Welcome, {char.name}.\"",
            f"\"Well met, traveler! Pull up a chair.\"",
            f"\"{ANSI_BOLD}{npc.full_name}{ANSI_RESET} smiles warmly. \"Good day to you!\"",
            f"\"It's good to see a new face in {char.settlement}.\"",
        ]
        tones = "warm"
    elif npc_traits & cool_traits:
        greetings = [
            f"\"{ANSI_BOLD}{npc.full_name}{ANSI_RESET} eyes you carefully. \"State your business.\"",
            f"\"Hmph. Another stranger. What do you want?\"",
            f"\"You have the look of someone who asks too many questions.\"",
        ]
        tones = "cool"
    else:
        greetings = [
            f"\"{ANSI_BOLD}{npc.full_name}{ANSI_RESET} nods in greeting. \"Afternoon.\"",
            f"\"Hello there, {char.name}. What brings you my way?\"",
            f"\"Good to meet you. I don't get many visitors.\"",
        ]
        tones = "neutral"

    print(f"\n  {_color(45)}{'─' * 44}{ANSI_RESET}")
    print(f"  {ANSI_BOLD}{npc.full_name}{ANSI_RESET} — {ANSI_DIM}{npc.occupation}{ANSI_RESET}")
    print(f"  {ANSI_DIM}{', '.join(npc.personality_traits)}{ANSI_RESET}")
    print(f"  {_color(45)}{'─' * 44}{ANSI_RESET}")
    print(f"  {local_rng.choice(greetings)}")

    # Generate occupation-flavored follow-up
    if tones == "warm":
        follow_ups = [
            f"\"I've been working as a {npc.occupation} for nigh on {npc.age - 15} years now. "
            f"Keeps me busy.\"",
            f"\"Being a {npc.occupation} in these parts means you see all sorts.\"",
            f"\"If you need anything from a {npc.occupation}, I'm your person.\"",
        ]
    elif tones == "cool":
        follow_ups = [
            f"\"I'm a {npc.occupation}. It pays the bills. What's it to you?\"",
            f"\"Don't let the {npc.occupation} title fool you. This town has its troubles.\"",
            f"\"You need a {npc.occupation}? Fine. Just don't waste my time.\"",
        ]
    else:
        follow_ups = [
            f"\"I've been the {npc.occupation} here for a while. It's honest work.\"",
            f"\"Being a {npc.occupation} means I hear things. People talk.\"",
            f"\"The life of a {npc.occupation} isn't glamorous, but it's mine.\"",
        ]

    print(f"  {local_rng.choice(follow_ups)}")

    # Offer a rumor or piece of info
    rumors = [
        f"\"I heard tell that {_rumor_topic(local_rng, char)}.\"",
        f"\"Word on the street is {_rumor_topic(local_rng, char)}.\"",
        f"\"Between you and me, {_rumor_topic(local_rng, char)}.\"",
        f"\"If you ask me, {_rumor_topic(local_rng, char)}.\"",
    ]
    print(f"  {local_rng.choice(rumors)}")

    # Player response options
    print(f"\n  {ANSI_DIM}[1] Ask about their work  [2] Ask about the area  [3] Say goodbye{ANSI_RESET}")
    try:
        reply = input(f"  {_color(226)}►{ANSI_RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        reply = "3"

    if reply == "1":
        work_answers = [
            f"\"{npc.occupation.capitalize()} work is steady. The harvest was decent, so folks have coin.\"",
            f"\"It's not always easy. Some days I wonder why I chose this path.\"",
            f"\"The {npc.occupation} trade has been good to me. Can't complain.\"",
        ]
        print(f"  {local_rng.choice(work_answers)}")
        _gain_skill_xp(char, "persuasion", 2)
    elif reply == "2":
        area_answers = [
            f"\"{char.region} is beautiful this time of year, but trouble brews in the east.\"",
            f"\"The lands around here are rich, but bandits make the roads dangerous.\"",
            f"\"There's an old ruin a few days north. Some say it's haunted.\"",
        ]
        print(f"  {local_rng.choice(area_answers)}")
        _gain_skill_xp(char, "survival", 2)
    else:
        farewells = [
            f"\"Safe travels, {char.name}. May the wyrd be kind.\"",
            f"\"Take care out there. The world is wider than you think.\"",
            f"\"Farewell! Don't be a stranger.\"",
        ]
        print(f"  {local_rng.choice(farewells)}")

    # Small gold/reputation gain for chatting
    char.gold += local_rng.randint(0, 2)
    rep_msg = _change_reputation(char, char.settlement, 1)
    if rep_msg:
        print(f"  {rep_msg}")
    char.total_gold_earned += 2
    print(f"  {_color(45)}You learned a little from the conversation.{ANSI_RESET}")


def _rumor_topic(rng: random.Random, char: PlayerCharacter) -> str:
    """Generate a rumor topic relevant to the world."""
    topics = [
        "the old road north is overrun with wolves",
        "a merchant caravan went missing near the eastern pass",
        "the baron's daughter is rumored to be a sorceress",
        "a ghost has been seen walking the battlements at night",
        "the price of iron is about to triple",
        "a stranger from across the sea brought strange news",
        "the harvest festival will be grander than ever this year",
        "someone's been stealing grain from the storehouses",
        "a hidden spring was discovered in the hills",
        "the old king's treasure was never found",
        "a traveling circus passed through last week",
        "the watchtower needs repairs but no one will fund it",
        "the river's been running low — old folk say it's a bad omen",
        "a marriage alliance is being negotiated with the next valley over",
    ]
    return rng.choice(topics)


def _handle_market(char: PlayerCharacter, world: World, state: SimState) -> None:
    """Open the settlement market. Player can buy/sell items."""
    from .shop import (
        shop_items_for_economy, render_shop_settlement_name,
        render_item_list, render_sell_inventory,
        estimate_item_value,
    )
    settlement_data = state.settlements.get(char.settlement)
    economy_type = settlement_data.economy_type if settlement_data else None
    population = settlement_data.population if settlement_data else 500

    rng = random.Random(
        world.seed + 6000000 + hash(char.settlement) % 100000 + char.year
    )
    items = shop_items_for_economy(economy_type or "trading", rng, population)

    while True:
        print()
        print(render_shop_settlement_name(char.settlement, economy_type, char.gold))
        print(f"  {ANSI_DIM}Your gold: {_color(220)}{char.gold}g"
              f"{ANSI_RESET}{ANSI_DIM}  Items: {len(char.inventory)}{ANSI_RESET}")
        print()
        for idx, item in enumerate(items):
            if item.get("stock", 0) > 0:
                print(render_item_list(item, idx))
        print()
        print(f"  {ANSI_DIM}[#] buy  [s]ell  [q]uit market{ANSI_RESET}")

        try:
            cmd = input(f"  {_color(226)}►{ANSI_RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break

        if cmd == "s":
            _handle_sell_items(char, rng)
            continue

        if cmd.isdigit():
            idx = int(cmd) - 1
            if 0 <= idx < len(items):
                item = items[idx]
                if item.get("stock", 0) <= 0:
                    print(f"  {ANSI_DIM}Out of stock.{ANSI_RESET}")
                elif char.gold < item["price"]:
                    print(f"  {ANSI_DIM}Need {item['price']}g, "
                          f"have {char.gold}g.{ANSI_RESET}")
                else:
                    char.gold -= item["price"]
                    char.total_gold_spent += item["price"]
                    char.inventory.append(item["name"])
                    item["stock"] = item.get("stock", 1) - 1
                    print(f"  {_color(46)}Bought {item['name']} "
                          f"({item['price']}g).{ANSI_RESET}")
                    _record_deed(char,
                                 f"Purchased at {char.settlement} market")
            else:
                print(f"  {ANSI_DIM}Invalid item.{ANSI_RESET}")
        else:
            print(f"  {ANSI_DIM}[#] buy  [s]ell  [q]uit{ANSI_RESET}")


def _handle_sell_items(char: PlayerCharacter, rng: random.Random) -> None:
    """Handle selling items from the player's inventory."""
    from .shop import estimate_item_value, render_sell_inventory

    while True:
        print()
        sell_lines = render_sell_inventory(char.inventory)
        for line in sell_lines:
            print(line)

        try:
            cmd = input(f"  {_color(226)}►{ANSI_RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break

        if cmd.isdigit():
            idx = int(cmd) - 1
            seen = list(dict.fromkeys(char.inventory))
            if 0 <= idx < len(seen):
                item_name = seen[idx]
                if item_name not in char.inventory:
                    continue
                value = estimate_item_value(item_name)
                sell_price = max(1, value // 2)
                char.inventory.remove(item_name)
                char.gold += sell_price
                char.total_gold_earned += sell_price
                print(f"  {_color(46)}Sold {item_name} for "
                      f"{sell_price}g.{ANSI_RESET}")
            else:
                print(f"  {ANSI_DIM}Invalid.{ANSI_RESET}")
        else:
            print(f"  {ANSI_DIM}[#] sell  [q] back{ANSI_RESET}")


def _advance_time(char: PlayerCharacter, world: World,
                  state: SimState, rng: random.Random,
                  chaos: float, months: int = 12) -> list[SimEvent]:
    """Advance simulation by N months and return events.

    Age increments on birthday (month 0 of each full year passed).
    Uses _simulate_month_tick for smooth sub-year progression.
    """
    all_events: list[SimEvent] = []
    prev_age = char.age

    for _ in range(months):
        char.month += 1
        if char.month >= 12:
            char.month = 0
            char.year += 1
            char.age += 1  # Birthday!

            # Health decay with age (yearly)
            if char.age > 60:
                char.health -= 2
            elif char.age > 45:
                char.health -= 1

        # Random health events (scaled to monthly)
        if rng.random() < 0.05 / 12:
            if rng.random() < 0.5:
                char.health = min(100, char.health + 5)
            else:
                char.health -= 5

        if char.health <= 0:
            char.alive = False
            return all_events

        # Run one month tick
        month_events = _simulate_month_tick(world, state, rng,
                                            char.year, char.month, chaos)
        all_events.extend(month_events)

    # Record notable events in legacy (check last N events)
    for ev in all_events[-10:]:
        if ev.event_type in ("founding", "abandonment", "war", "faction_war",
                             "earthquake", "volcanic_eruption", "great_plague",
                             "tsunami", "meteor_strike", "great_fire", "magical_cataclysm",
                             "faction_collapse", "discovery"):
            if char.settlement in (ev.affected_settlements or []):
                _record_legacy_event(char, f"{ev.event_type.replace('_', ' ')} in {char.settlement}")
            elif char.region in (ev.affected_regions or []):
                _record_legacy_event(char, f"{ev.event_type.replace('_', ' ')} in {char.region}")

    return all_events


def _advance_year(char: PlayerCharacter, world: World,
                  state: SimState, rng: random.Random,
                  chaos: float) -> list[SimEvent]:
    """Legacy wrapper — advances by exactly 12 months (1 year)."""
    return _advance_time(char, world, state, rng, chaos, months=12)


# ── Entry Point ───────────────────────────────────────────────────────


# ── Persistence ────────────────────────────────────────────────────


SAVES_DIR = "saves"


def _save_path(seed: int) -> str:
    """Get the character save file path for a given world seed."""
    return os.path.join(SAVES_DIR, f"wyrd-{seed}-char.json")


def _migrate_save(seed: int) -> str | None:
    """Migrate a character save from the old CWD path to the new saves/ dir.
    Returns the new path if migration happened, None if no save exists.
    """
    old_path = f"wyrd-{seed}-char.json"
    new_path = _save_path(seed)
    if os.path.exists(old_path):
        os.makedirs(SAVES_DIR, exist_ok=True)
        os.rename(old_path, new_path)
        return new_path
    return None


def save_character(char: PlayerCharacter, seed: int) -> None:
    """Save the player character to a JSON file."""
    os.makedirs(SAVES_DIR, exist_ok=True)
    path = _save_path(seed)
    data = {
        "wyrd_version": "0.1.0",
        "seed": seed,
        "character": char.to_dict(),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_character(seed: int) -> PlayerCharacter | None:
    """Load a saved player character from a JSON file.
    Returns None if no save exists.
    """
    # Migrate old save if needed
    _migrate_save(seed)
    path = _save_path(seed)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return PlayerCharacter.from_dict(data.get("character", {}))
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def _save_path_for_world(world: "World") -> str:
    """Get character save path from a world object."""
    return _save_path(world.seed)


def _auto_save(char: PlayerCharacter, world: "World") -> None:
    """Auto-save the character state."""
    save_character(char, world.seed)


def _record_legacy_event(char: PlayerCharacter, event: str) -> None:
    """Record a major life event with the current year."""
    char.legacy_events.append(f"Y{char.year}: {event}")


def _record_deed(char: PlayerCharacter, deed: str) -> None:
    """Record a notable accomplishment."""
    if deed not in char.deeds:
        char.deeds.append(deed)


def _render_epilogue(char: PlayerCharacter) -> str:
    """Render a meaningful death epilogue with Life Ledger."""
    lines = []
    lines.append(f"\n  {ANSI_BOLD}{_color(196)}═══ {char.name} has died ═══{ANSI_RESET}")
    lines.append("")
    lines.append(f"  {ANSI_BOLD}Life Ledger{ANSI_RESET}")
    lines.append(f"  {'─' * 50}")
    lines.append(f"  Age at death:    {char.age}")
    years_active = char.year - max(0, char.age - 18) if char.age > 18 else char.year
    lines.append(f"  Years adventuring: {years_active}")
    lines.append(f"  Gold accumulated: {char.total_gold_earned}")
    lines.append(f"  Gold spent:       {char.total_gold_spent}")
    lines.append(f"  Final wealth:     {char.gold}")
    lines.append(f"  Places lived:     {len(char.settlements_visited) or 1}")
    if char.settlements_visited:
        lines.append(f"  {' '.join(char.settlements_visited[:5])}"
                     f"{'…' if len(char.settlements_visited) > 5 else ''}")

    if char.deeds:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Notable Deeds{ANSI_RESET}")
        for deed in char.deeds:
            lines.append(f"    ⚜ {deed}")

    if char.legacy_events:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}They Witnessed{ANSI_RESET}")
        for ev in char.legacy_events[-5:]:  # Last 5 events
            lines.append(f"    📜 {ev}")

    lines.append("")
    # Last words
    last_words_list = [
        "\"I have seen wonders beyond counting…\"",
        "\"Tell them I died with my boots on.\"",
        "\"The world endures. So shall we all.\"",
        "\"My story ends, but the wyrd spins on.\"",
        "\"I regret nothing.\"",
        "\"Gold… was it worth it?\"",
        "\"Bury me in the highlands, where the wind sings.\"",
        "\"I would have liked to see one more spring.\"",
    ]
    import random as rnd_mod
    rng = rnd_mod.Random(str(char))
    lines.append(f"  {ANSI_DIM}{rng.choice(last_words_list)}{ANSI_RESET}")

    if char.parent_name:
        lines.append("")
        lines.append(f"  {ANSI_DIM}Child of {char.parent_name}{ANSI_RESET}")

    lines.append("")
    lines.append(f"  {ANSI_BOLD}{_color(226)}The wyrd remembers.{ANSI_RESET}")
    lines.append(f"  {'─' * 50}")
    return "\n".join(lines)


def _make_weather() -> str:
    return random.choice([
        "The sky is clear.",
        "A gentle rain falls.",
        "Wind howls through the streets.",
        "Frost glitters on the rooftops.",
        "A warm breeze carries the scent of flowers.",
        "Thunder rumbles in the distance.",
        "Snow falls softly.",
        "Mist clings to the ground.",
        "The sun beats down mercilessly.",
        "A light fog rolls in from the east.",
    ])


def embody_play(world: World,
                name: str | None = None,
                years: int = 100,
                chaos: float = 0.3,
                load_save: bool = True) -> None:
    """Enter the embodied play mode for a world.

    Args:
        world: A generated world
        name: Optional character name (ignored if loading a save)
        years: Max years to simulate
        chaos: Chaos factor for simulation
        load_save: If True, try to load a saved character state
    """
    rng = random.Random(world.seed + 5000000)

    # Try to load saved character state
    char: PlayerCharacter | None = None
    loaded = False
    if load_save:
        char = load_character(world.seed)
        if char is not None:
            loaded = True
            print(f"  {ANSI_DIM}📂 Loaded saved character: {char.name} (Year {char.year}){ANSI_RESET}")

    if char is None:
        # Generate the player character
        char = _generate_character(world, rng, name=name)

    # Initialize sim state
    state = initialize_sim_state(world)

    # If loading from save, fast-forward sim to the character's year
    if loaded and char.year > 0:
        from .sim import simulate_years
        simulate_years(world, state, rng, char.year, chaos)
        # Re-apply sim state to world for accurate rendering
        apply_sim_state_to_world(world, state)
        print(f"  {ANSI_DIM}Catching up the world... Year {char.year} restored.{ANSI_RESET}")

    print(f"\n  {ANSI_BOLD}{_color(45)}wyrd — seed {world.seed}{ANSI_RESET}")
    print(_render_welcome(char, world, char.region))

    # Main loop
    events: list[SimEvent] = []
    running = True
    while running and char.alive and char.year < years:
        cont, months = _prompt(char, world, state, events, rng, chaos, years)
        if not cont:
            running = False
            break

        if months > 0:
            new_events = _advance_time(char, world, state, rng, chaos, months=months)
            events.extend(new_events)
            # Auto-save after time passes
            _auto_save(char, world)

            # Show season change
            seasons = ["Winter", "Spring", "Summer", "Autumn"]
            season = seasons[char.month // 3] if char.month < 12 else "Unknown"
            time_msg = f"{months} month{'s' if months != 1 else ''}"
            print(f"\n  {_color(45)}{time_msg} pass — {season}, Year {char.year}{ANSI_RESET}")

            # Interactive event choices (Phase 17, Item 4)
            _handle_interactive_events(char, world, rng, events)

    # Epilogue — meaningful death with Life Ledger
    if not char.alive:
        print(_render_epilogue(char))
        # Remove save on death
        path = _save_path(world.seed)
        if os.path.exists(path):
            os.remove(path)
            print(f"  {ANSI_DIM}🗑 Character save removed.{ANSI_RESET}")

        # Multi-generational: offer to continue as an heir (Phase 17, Item 6)
        print(f"\n  {_color(226)}The wyrd spins on...{ANSI_RESET}")
        print(f"  {ANSI_DIM}Another thread remains to be woven.{ANSI_RESET}")
        continue_str = input(
            f"  {_color(226)}Continue as an heir?{ANSI_RESET} "
            f"({ANSI_BOLD}y{ANSI_RESET}/n): ").strip().lower()
        if continue_str != "n":
            # Generate heir
            rng_heir = random.Random(world.seed + 6000000 + char.year)
            first_names = ["Aldric", "Beorn", "Cedric", "Elara", "Freya",
                           "Gareth", "Hakon", "Ivar", "Kara", "Leif",
                           "Mira", "Nora", "Orin", "Runa", "Sigurd",
                           "Tova", "Ulf", "Vera", "Astrid", "Brynn"]
            surname = char.name.split()[-1] if " " in char.name else "sson"
            heir_name = f"{rng_heir.choice(first_names)} {surname}"

            # Inherit partial wealth and inventory
            heir_gold = max(20, char.gold // 2)
            heir_inventory = [
                item for item in char.inventory
                if item not in ("a cryptic note", "an old map")  # Personal items lost
            ][:3]  # Max 3 items inherited

            heir = PlayerCharacter(
                name=heir_name,
                settlement=char.settlement,
                region=char.region,
                profession=_OCCUPATIONS[rng_heir.randint(0, len(_OCCUPATIONS) - 1)],
                gold=heir_gold,
                health=100,
                age=rng_heir.randint(16, 25),
                year=char.year,
                inventory=heir_inventory,
                parent_name=char.name,
            )
            # Heir inherits visited settlements knowledge
            heir.settlements_visited = [s for s in char.settlements_visited if s]
            # Heir inherits partial skills (2/3 of parent's XP per skill, min level 1)
            heir.skill_xp = {
                s: max(0, char.skill_xp.get(s, 0) * 2 // 3)
                for s in SKILL_NAMES
            }
            for s in SKILL_NAMES:
                heir.skills[s] = max(1, _skill_level_from_xp(heir.skill_xp.get(s, 0)))
            # Heir inherits some reputation (partial)
            heir.reputation = {
                s: max(-10, min(10, v // 2))
                for s, v in char.reputation.items()
            } if char.reputation else {}
            # Record birth in legacy
            _record_legacy_event(heir, f"Born as heir of {char.name}")
            if char.deeds:
                _record_legacy_event(heir, f"Inherits the legacy of {char.name}")

            print(f"\n  {ANSI_BOLD}{_color(45)}═══ A New Chapter ═══{ANSI_RESET}")
            print(f"  {ANSI_BOLD}{heir_name}{ANSI_RESET}, "
                  f"a {ANSI_DIM}{heir.profession}{ANSI_RESET}, "
                  f"carries on the line.")
            print(f"  Child of {ANSI_BOLD}{char.name}{ANSI_RESET}.")
            if heir_inventory:
                print(f"  Inherited: {', '.join(heir_inventory)}")

            # Save heir and continue
            save_character(heir, world.seed)
            print(f"  {ANSI_DIM}💾 Heir saved. Run 'wyrd embody --seed {world.seed}' to continue.{ANSI_RESET}")

            # Recursive call with heir
            embody_play(world, name=heir_name, years=years,
                       chaos=chaos, load_save=True)
        else:
            print(f"\n  {ANSI_DIM}The line ends here. The world continues without you.{ANSI_RESET}")
    else:
        print(f"\n  {ANSI_DIM}Your journey ends... for now.{ANSI_RESET}")
        print(f"  {char.name} lived to age {char.age} "
              f"and witnessed {char.year} years.")
        print(f"  {ANSI_DIM}💾 Character saved — run 'wyrd embody --seed {world.seed}' to resume.{ANSI_RESET}")

    # Show final summary
    active = state.num_settlements
    pop = state.total_population
    print(f"\n  {ANSI_BOLD}World at Year {char.year}:{ANSI_RESET}")
    print(f"  {active} settlements, {pop:,} souls")
    print(f"  {len(events)} notable events witnessed")
    print()
