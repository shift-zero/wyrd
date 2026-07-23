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
    initialize_sim_state, _simulate_tick, SimState, SimEvent,
    apply_sim_state_to_world,
)

from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color


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
    lines.append(f"  {_color(226)}►{ANSI_RESET} Type {ANSI_BOLD}n{ANSI_RESET} "
                 f"to advance a year")
    lines.append(f"  {_color(226)}►{ANSI_RESET} Type {ANSI_BOLD}s{ANSI_RESET} "
                 f"to show your status")
    lines.append(f"  {_color(226)}►{ANSI_RESET} Type {ANSI_BOLD}t{ANSI_RESET} "
                 f"to travel to another settlement")
    lines.append(f"  {_color(226)}►{ANSI_RESET} Type {ANSI_BOLD}q{ANSI_RESET} "
                 f"to quit")
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


_SCENARIOS = [
    _maybe_stranger_scenario,
    _maybe_plague_scenario,
    _maybe_war_scenario,
    _maybe_merchant_scenario,
    _maybe_discovery_scenario,
    _maybe_religious_scenario,
    _maybe_exodus_scenario,
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
            if rng.random() < 0.4:
                item = rng.choice(["an old map", "a cryptic note", "a healing salve",
                                   "a pouch of herbs", "a carved talisman"])
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
            survive = rng.random() < 0.6
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
            return (ChoiceOutcome(
                description="You contribute supplies to the war effort. "
                            "The quartermaster thanks you.",
                gold_delta=-30,
            ), "Send supplies")
        else:  # Flee
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
            profit = rng.choice([-30, -10, 20, 50, 100, 150])
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
            item = rng.choice(["an ancient relic", "a golden amulet",
                               "a sealed scroll", "a gemstone",
                               "a mysterious orb", "a silver ring"])
            find_gold = rng.randint(10, 40)
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
            healing = rng.randint(5, 20)
            return (ChoiceOutcome(
                description=f"You join the procession and pray. "
                            f"You feel restored (+{healing} health).",
                health_delta=healing,
            ), "Join the procession")
        elif opt == 1:  # Donate
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
            return (ChoiceOutcome(
                description="You stay and help rebuild. "
                            "Those who remain band together.",
                gold_delta=-10,
                health_delta=5,
            ), "Stay and rebuild")
        else:  # Loot abandoned homes
            loot = rng.randint(10, 25)
            return (ChoiceOutcome(
                description=f"You find abandoned goods worth {loot} gold.",
                gold_delta=loot,
                health_delta=-5,
            ), "Scavenge what remains")

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


def _prompt(char: PlayerCharacter, world: World,
            events: list[SimEvent]) -> bool:
    """One turn of the game loop. Returns False to quit."""
    print(_status_line(char))

    # Show recent news
    news = _render_news(events, char, char.year)
    if news:
        print(news)
        print()

    # Prompt
    print(f"  {ANSI_DIM}[n]ext year  [s]tatus  [t]ravel  [q]uit{ANSI_RESET}")
    try:
        cmd = input(f"  {_color(226)}►{ANSI_RESET} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if cmd == "q":
        return False
    elif cmd == "s":
        # Just re-display; the status is already shown
        print(f"  You are {ANSI_BOLD}{char.name}{ANSI_RESET}, "
              f"a {ANSI_DIM}{char.profession}{ANSI_RESET}.")
        print(f"  Current wealth: {_color(220)}{char.gold} gold{ANSI_RESET}")
        print(f"  Health: {char.health}/100")
        print(f"  Age: {char.age}")
        print(f"  Inventory: {', '.join(char.inventory) if char.inventory else 'nothing yet'}")
        if char.deeds:
            print(f"  Deeds: {', '.join(char.deeds[:3])}"
                  f"{'…' if len(char.deeds) > 3 else ''}")
        if char.settlements_visited:
            print(f"  Places: {', '.join(char.settlements_visited[:5])}"
                  f"{'…' if len(char.settlements_visited) > 5 else ''}")
    elif cmd == "t":
        _handle_travel(char, world)
    elif cmd == "n":
        return True  # Advance a year
    else:
        print(f"  {ANSI_DIM}Unknown: '{cmd}'. Try n, s, t, or q.{ANSI_RESET}")

    return True  # Continue playing


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
            item = None
            if rng.random() < 0.3:
                item = rng.choice([
                    "a claw talisman", "creature hide", "a fang necklace",
                    "a bone charm", "a vial of venom", "a rare pelt",
                ])
            char.gold += gold_reward
            char.total_gold_earned += gold_reward
            char.health = max(0, min(100, char.health + health_cost))
            if item:
                char.inventory.append(item)
            _record_deed(char, f"Defeated a {creature.name} in combat")
            _record_legacy_event(char, f"Survived an encounter with {creature.name}")
            parts = [f"You draw your weapon and face the {creature.name}!"]
            parts.append(f"After a fierce struggle, you emerge victorious!")
            parts.append(f"You find {gold_reward} gold on the beast's remains.")
            if health_cost:
                parts.append(f"You are wounded ({health_cost} HP).")
            if item:
                parts.append(f"You recover {item} as a trophy.")
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

    # Travel takes a year regardless
    char.year += 1
    return True


def _handle_travel(char: PlayerCharacter, world: World) -> None:
    """Handle travel to another settlement."""
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

    # ── Creature encounter during travel ──────────────────────────────
    encounter_happened = _maybe_travel_encounter(char, world)

    char.settlement = dest_name
    # Track visited settlement
    if dest_name not in char.settlements_visited:
        char.settlements_visited.append(dest_name)
        if len(char.settlements_visited) >= 3:
            _record_deed(char, f"Visited {len(char.settlements_visited)} settlements")
    if not encounter_happened:
        char.year += 1  # Travel takes a year
        print(f"  You arrive safely.")
    else:
        # Encounter already consumed the year
        print(f"  {ANSI_DIM}You eventually reach {ANSI_BOLD}{dest_name}{ANSI_RESET}{ANSI_DIM}.{ANSI_RESET}")


def _advance_year(char: PlayerCharacter, world: World,
                  state: SimState, rng: random.Random,
                  chaos: float) -> list[SimEvent]:
    """Advance the simulation one year and return events."""
    char.year += 1
    char.age += 1

    # Health decay with age
    if char.age > 60:
        char.health -= 2
    elif char.age > 45:
        char.health -= 1
    # Random health event
    if rng.random() < 0.05:
        if rng.random() < 0.5:
            char.health = min(100, char.health + 5)
            print(f"  {_color(46)}You feel rejuvenated! +5 health{ANSI_RESET}")
        else:
            char.health -= 5
            print(f"  {_color(196)}You fall ill. -5 health{ANSI_RESET}")

    if char.health <= 0:
        char.alive = False
        return []

    # Run one sim tick
    events = _simulate_tick(world, state, rng, char.year, chaos)

    # Record notable events in legacy
    for ev in events[-5:]:  # Check recent events
        if ev.event_type in ("founding", "abandonment", "war", "faction_war",
                             "earthquake", "volcanic_eruption", "great_plague",
                             "tsunami", "meteor_strike", "great_fire", "magical_cataclysm",
                             "faction_collapse", "discovery"):
            if char.settlement in (ev.affected_settlements or []):
                _record_legacy_event(char, f"{ev.event_type.replace('_', ' ')} in {char.settlement}")
            elif char.region in (ev.affected_regions or []):
                _record_legacy_event(char, f"{ev.event_type.replace('_', ' ')} in {char.region}")

    return events


# ── Entry Point ───────────────────────────────────────────────────────


# ── Persistence ────────────────────────────────────────────────────


def _save_path(seed: int) -> str:
    """Get the character save file path for a given world seed."""
    return f"wyrd-{seed}-char.json"


def save_character(char: PlayerCharacter, seed: int) -> None:
    """Save the player character to a JSON file."""
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
        if not _prompt(char, world, events):
            running = False
            break

        # Check if player chose to advance a year (handled in _prompt)
        if running and char.alive:
            new_events = _advance_year(char, world, state, rng, chaos)
            events.extend(new_events)
            # Auto-save after each year
            _auto_save(char, world)
            print(f"\n  {_color(45)}Year {char.year}{ANSI_RESET} — "
                  f"{_make_weather()}")

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
