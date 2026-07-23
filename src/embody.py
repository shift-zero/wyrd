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

        # Apply consequences
        char.gold += outcome.gold_delta
        char.health = max(0, min(100, char.health + outcome.health_delta))
        if outcome.inventory_add:
            if outcome.inventory_add not in char.inventory:
                char.inventory.append(outcome.inventory_add)
        if outcome.travel_dest:
            char.settlement = outcome.travel_dest

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
    elif cmd == "t":
        _handle_travel(char, world)
    elif cmd == "n":
        return True  # Advance a year
    else:
        print(f"  {ANSI_DIM}Unknown: '{cmd}'. Try n, s, t, or q.{ANSI_RESET}")

    return True  # Continue playing


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
    char.settlement = dest_name
    char.year += 1  # Travel takes a year
    print(f"  You arrive safely.")


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

    # Epilogue
    if not char.alive:
        print(f"\n  {ANSI_BOLD}{_color(196)}═══ {char.name} has died ═══{ANSI_RESET}")
        print(f"  Aged {char.age}, in {char.settlement}.")
        print(f"  They lived through {char.year} years of the world's history.")
        # Remove save on death
        path = _save_path(world.seed)
        if os.path.exists(path):
            os.remove(path)
            print(f"  {ANSI_DIM}🗑 Character save removed.{ANSI_RESET}")
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
