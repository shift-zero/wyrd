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
                chaos: float = 0.3) -> None:
    """Enter the embodied play mode for a world.

    Args:
        world: A generated world
        name: Optional character name
        years: Max years to simulate
        chaos: Chaos factor for simulation
    """
    rng = random.Random(world.seed + 5000000)

    # Generate the player character
    char = _generate_character(world, rng, name=name)

    # Initialize sim state
    state = initialize_sim_state(world)

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
            print(f"\n  {_color(45)}Year {char.year}{ANSI_RESET} — "
                  f"{_make_weather()}")

    # Epilogue
    if not char.alive:
        print(f"\n  {ANSI_BOLD}{_color(196)}═══ {char.name} has died ═══{ANSI_RESET}")
        print(f"  Aged {char.age}, in {char.settlement}.")
        print(f"  They lived through {char.year} years of the world's history.")
    else:
        print(f"\n  {ANSI_DIM}Your journey ends... for now.{ANSI_RESET}")
        print(f"  {char.name} lived to age {char.age} "
              f"and witnessed {char.year} years.")

    # Show final summary
    active = state.num_settlements
    pop = state.total_population
    print(f"\n  {ANSI_BOLD}World at Year {char.year}:{ANSI_RESET}")
    print(f"  {active} settlements, {pop:,} souls")
    print(f"  {len(events)} notable events witnessed")
    print()
