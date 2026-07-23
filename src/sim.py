"""
wyrd — Simulation Engine (Phase 6: The Turning of the World).

Year-by-year world simulation in the Dwarf Fortress tradition.
The world is no longer a static artifact — it lives and changes.

Seed-deterministic: same seed + same parameters → same outcome.
All simulation data is stored in a SimState that can be snapshot at any year.
"""

import random
import math
import copy
from dataclasses import dataclass, field
from typing import Optional

from .world import World, Region, Settlement, TERRAIN
from .faction_sim import initialize_faction_state, _simulate_political_tick
from .cataclysm import _simulate_cataclysm_tick, cataclysm_to_sim_event
from .economy import assign_economies, _simulate_economy_tick, _generate_trade_routes, _get_specialization_title


# ── Terrain Resource Values ───────────────────────────────────────────

# Carrying capacity: max population a cell of this terrain can support
TERRAIN_CAPACITY = {
    "deep_water": 0,
    "shallow": 0,
    "sand": 20,
    "grass": 100,
    "forest": 80,
    "hills": 60,
    "mountains": 30,
    "snow": 5,
    "river": 50,
}

# Resource extraction rates
TERRAIN_FOOD = {
    "deep_water": 0,
    "shallow": 5,
    "sand": 10,
    "grass": 100,
    "forest": 60,
    "hills": 40,
    "mountains": 15,
    "snow": 3,
    "river": 40,
}

TERRAIN_WEALTH = {
    "deep_water": 0,
    "shallow": 30,
    "sand": 10,
    "grass": 50,
    "forest": 60,
    "hills": 80,
    "mountains": 100,
    "snow": 20,
    "river": 40,
}


# ── Event Templates (Simulation Events) ───────────────────────────────

SIM_EVENT_TEMPLATES = {
    "plague": (
        "A plague sweeps through {settlement} in {region}. "
        "{effect}"
    ),
    "famine": (
        "Crops fail across {region} as {cause}. "
        "Settlements struggle as food stores dwindle. "
        "{effect}"
    ),
    "war": (
        "{aggressor} launches an attack on {target}. "
        "The battle at {battle_site} ends with {outcome}. "
        "{effect}"
    ),
    "discovery": (
        "{discoverer} discovers {discovery} near {location}. "
        "{reaction}"
    ),
    "prosperity": (
        "{settlement} enters a time of prosperity as {cause}. "
        "Trade flourishes and {effect}."
    ),
    "disaster": (
        "A {disaster_type} strikes {settlement}, "
        "{disaster_effect}. {aftermath}"
    ),
    "exodus": (
        "Dwindling resources in {region} drive {emigrants} "
        "to seek new lands. {destination}."
    ),
    "founding": (
        "A new settlement, {new_settlement}, is founded near "
        "{parent_settlement} by {founders} seeking {reason}."
    ),
    "abandonment": (
        "{settlement} is abandoned as {cause} "
        "makes life untenable. {fate}."
    ),
    "trade_boom": (
        "Trade routes through {region} bring unprecedented wealth. "
        "{settlement} becomes {transformation}."
    ),
    "religious_tension": (
        "Religious tension flares between {settlement_a} and {settlement_b}. "
        "Followers of {faith_a} and {faith_b} clash over {cause}. "
        "{effect}"
    ),
    "divine_blessing": (
        "A blessing from {deity} descends upon {settlement}. "
        "Crops flourish, herds multiply, and the people prosper. "
        "{effect}"
    ),
    "holy_pilgrimage": (
        "A great pilgrimage to {holy_site} draws devotees "
        "from across the land. {effect}"
    ),
    "heresy": (
        "A heretical movement spreads through {settlement}, "
        "challenging the authority of the {religion_name} clergy. "
        "{effect}"
    ),
    # Political Events (Phase 12)
    "faction_war": (
        "{description}"
    ),
    "faction_alliance": (
        "{description}"
    ),
    "faction_power_shift": (
        "{description}"
    ),
    "faction_collapse": (
        "{description}"
    ),
    "faction_peace_treaty": (
        "{description}"
    ),
}


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class SimEvent:
    """An event that occurred during simulation."""
    year: int
    event_type: str
    description: str
    month: int = 0  # 0 = year-level (no specific month), 1-12 for sub-year ticks
    affected_settlements: list[str] = field(default_factory=list)
    affected_regions: list[str] = field(default_factory=list)


@dataclass
class SettlementSnapshot:
    """Simulation state for a single settlement."""
    name: str
    region: str
    x: int
    y: int
    population: int
    kind: str
    is_active: bool = True  # False = abandoned
    founded_year: int = 0
    prosperity: float = 0.5  # 0.0 = destitute, 1.0 = thriving
    food_stores: float = 100.0
    health: float = 1.0  # 0.0 = plague-ridden, 1.0 = healthy
    religion: str | None = None  # Religion name from PantheonSystem
    economy_type: str | None = None  # Economy type from economy module (Phase 14)
    economy_since_year: int = 0  # Year this settlement got its current economy type (for specialization titles, Phase 16)


@dataclass
class SimState:
    """
    Complete simulation state at a point in time.
    
    Stores snapshots of all settlements plus metadata
    about the simulation run.
    """
    year: int = 0
    sub_year_month: int = 0  # 0-11, month within current year. Only used in sub-year tick mode.
    settlements: dict[str, SettlementSnapshot] = field(default_factory=dict)
    events: list[SimEvent] = field(default_factory=list)
    world_modifiers: list[str] = field(default_factory=list)
    population_record: list[dict] = field(default_factory=list)
    character_status: dict[str, str] = field(default_factory=dict)
    # Maps "Character Fullname" -> "alive" | "dead" | "missing"
    # Tracks named characters from the narrative engine through sim years.
    # Populated by _init_character_status and mutated by sim events.
    current_era: str = "The Founding Age"
    # Name of the current chronicle era. Updated by era transition checks.
    era_history: list[dict] = field(default_factory=list)
    # Records of era transitions that occurred during sim.
    faction_state: dict = field(default_factory=dict)
    # Maps faction name -> FactionSnapshot from faction_sim module.
    # Tracks faction power, wars, alliances through simulation.
    trade_routes: list = field(default_factory=list)
    # TradeRoute dicts for Phase 14 economy system.
    # Persisted as list of dicts for serialization.
    
    @property
    def total_population(self) -> int:
        return sum(s.population for s in self.settlements.values() if s.is_active)
    
    @property
    def num_settlements(self) -> int:
        return sum(1 for s in self.settlements.values() if s.is_active)
    
    @property
    def num_abandoned(self) -> int:
        return sum(1 for s in self.settlements.values() if not s.is_active)


# ── Trade Route State (Phase 14) ─────────────────────────────────────

# Global trade routes tracked across sim ticks.
# Persisted as list of dicts in SimState for serialization.


# ── Simulation Helpers ────────────────────────────────────────────────


def _precompute_resource_maps(world: World, radius: int = 5) -> None:
    """Precompute carrying capacity, food, and wealth maps for the entire world.

    Stores the results on world.capacity_map, world.food_map, and world.wealth_map
    so that _calculate_carrying_capacity and _resource_availability can do O(1) lookups
    instead of looping over radius² cells per call.

    Must be called again after any terrain mutation (e.g. cataclysm).
    """
    w, h = world.width, world.height
    cap_map = [[0] * w for _ in range(h)]
    food_map = [[0.0] * w for _ in range(h)]
    wealth_map = [[0.0] * w for _ in range(h)]

    for y in range(h):
        for x in range(w):
            total_cap = 0
            total_food = 0.0
            total_wealth = 0.0
            cells = 0
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        t = world.terrain[ny][nx]
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist <= radius:
                            falloff = 1 - (dist / (radius + 1))
                            total_cap += TERRAIN_CAPACITY.get(t, 50) * falloff
                            total_food += TERRAIN_FOOD.get(t, 20) * falloff
                            total_wealth += TERRAIN_WEALTH.get(t, 20) * falloff
                            cells += 1
            cap_map[y][x] = int(total_cap)
            food_map[y][x] = min(1.0, total_food / (cells * 40)) if cells else 0.1
            wealth_map[y][x] = min(1.0, total_wealth / (cells * 40)) if cells else 0.1

    world.capacity_map = cap_map
    world.food_map = food_map
    world.wealth_map = wealth_map


def _logistic_growth(current: float, carrying_capacity: float, growth_rate: float = 0.02) -> float:
    """Logistic growth model with carrying capacity."""
    if carrying_capacity <= 0:
        return current * 0.95  # Decline without capacity
    if current <= 0:
        return 0
    return current + growth_rate * current * (1 - current / carrying_capacity)


def _calculate_carrying_capacity(world: World, sx: int, sy: int, radius: int = 5) -> int:
    """
    Calculate carrying capacity for a settlement based on surrounding terrain.
    Uses precomputed map if available, otherwise computes from scratch.
    """
    if world.capacity_map is not None and 0 <= sy < len(world.capacity_map) and 0 <= sx < len(world.capacity_map[0]):
        return world.capacity_map[sy][sx]
    total_capacity = 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = sx + dx, sy + dy
            if 0 <= x < world.width and 0 <= y < world.height:
                t = world.terrain[y][x]
                # Distance falloff
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius:
                    falloff = 1 - (dist / (radius + 1))
                    capacity = TERRAIN_CAPACITY.get(t, 50)
                    total_capacity += capacity * falloff
    return int(total_capacity)


def _resource_availability(world: World, sx: int, sy: int, radius: int = 5) -> tuple[float, float]:
    """
    Calculate food and wealth availability for a settlement location.
    Returns (food_availability, wealth_availability) as 0.0-1.0 values.
    Uses precomputed maps if available, otherwise computes from scratch.
    """
    if world.food_map is not None and world.wealth_map is not None and 0 <= sy < len(world.food_map) and 0 <= sx < len(world.food_map[0]):
        return (world.food_map[sy][sx], world.wealth_map[sy][sx])
    total_food = 0
    total_wealth = 0
    cells = 0
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = sx + dx, sy + dy
            if 0 <= x < world.width and 0 <= y < world.height:
                t = world.terrain[y][x]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist <= radius:
                    falloff = 1 - (dist / (radius + 1))
                    total_food += TERRAIN_FOOD.get(t, 20) * falloff
                    total_wealth += TERRAIN_WEALTH.get(t, 20) * falloff
                    cells += 1
    if cells == 0:
        return (0.1, 0.1)
    return (min(1.0, total_food / (cells * 40)), min(1.0, total_wealth / (cells * 40)))


def _simulate_tick(world: World, state: SimState, rng: random.Random,
                   year: int, chaos_factor: float = 0.1,
                   characters: list | None = None) -> list[SimEvent]:
    """
    Simulate one year for the world.
    
    Args:
        world: The base world data (terrain, regions, etc.)
        state: Current simulation state
        rng: Seeded RNG for determinism
        year: Current simulation year
        chaos_factor: How much random fluctuation to apply (0.0-1.0)
    
    Returns:
        List of events generated this year
    """
    events: list[SimEvent] = []
    
    # Process each active settlement
    for s_name in list(state.settlements.keys()):
        s = state.settlements[s_name]
        if not s.is_active:
            continue
        
        # Find the region for more context
        region_name = s.region
        
        # Calculate carrying capacity based on terrain
        carrying_cap = _calculate_carrying_capacity(world, s.x, s.y)
        food_avail, wealth_avail = _resource_availability(world, s.x, s.y)
        
        # Update food stores
        # Each person produces food based on local land quality
        # and consumes a baseline amount. Surplus drives growth.
        food_production = s.population * food_avail * 2.0
        food_consumption = s.population * 0.5 * (1 + _random_variation(rng, 0.1))
        s.food_stores += food_production - food_consumption
        s.food_stores = max(0, min(s.food_stores, s.population * 5))
        
        # Health dynamics
        # Overcrowding reduces health significantly
        crowding_ratio = s.population / max(carrying_cap, 1)
        s.health = max(0.05, 1.0 - crowding_ratio * 0.5 + _random_variation(rng, 0.08))
        
        # Prosperity dynamics
        target_prosperity = wealth_avail * 0.7 + food_avail * 0.3
        s.prosperity += (target_prosperity - s.prosperity) * 0.1 + _random_variation(rng, 0.02)
        s.prosperity = max(0.0, min(1.0, s.prosperity))
        
        # Population dynamics
        if s.food_stores <= 0 or s.health < 0.2:
            # Famine or plague — population declines
            decline_rate = 0.05 + (1 - s.health) * 0.2 + max(0, -s.food_stores / s.population) * 0.1
            s.population = max(1, int(s.population * (1 - decline_rate)))
        else:
            # Normal logistic growth
            effective_capacity = carrying_cap * max(food_avail, 0.2)
            growth_rate = 0.02 + s.prosperity * 0.02
            new_pop = _logistic_growth(s.population, effective_capacity, growth_rate)
            # Add random fluctuation
            new_pop *= (1 + _random_variation(rng, 0.03))
            s.population = max(1, int(new_pop))
        
        # Update kind based on population
        s.kind = _population_to_kind(s.population)
        
        # Check for events
        # Plague (triggered by low health + random chance)
        if s.health < 0.4 and rng.random() < 0.03 * chaos_factor and s.population > 5:
            death_toll = max(1, int(s.population * rng.uniform(0.1, 0.4)))
            s.population -= death_toll
            if s.population < 1:
                s.population = 1
                death_toll = 0  # no one actually died — too small to matter
            s.health = rng.uniform(0.3, 0.6)
            if death_toll > 0:
                char_name = _select_named_character(rng, characters, s.name, region_name, "plague")
                # Character might die in the plague
                if char_name and rng.random() < 0.4:
                    state.character_status[char_name.full_name] = "dead"
                    desc = _describe_with_character(
                        f"Plague ravages {s.name} in {region_name}, killing {death_toll}.",
                        char_name, "{char} succumbs to the outbreak and dies."
                    )
                else:
                    desc = _describe_with_character(
                        f"Plague ravages {s.name} in {region_name}, killing {death_toll}.",
                        char_name, "{char} struggles to contain the outbreak."
                    )
                events.append(SimEvent(
                    year=year,
                    event_type="plague",
                    description=desc,
                    affected_settlements=[s.name],
                    affected_regions=[region_name],
                ))
        
        # Famine (triggered by low food stores)
        if s.food_stores < s.population * 0.5 and rng.random() < 0.03 * chaos_factor and s.population > 3:
            death_toll = max(1, int(s.population * rng.uniform(0.05, 0.2)))
            s.population -= death_toll
            if s.population < 1:
                s.population = 1
                death_toll = 0
            s.food_stores = max(0, s.food_stores - s.population * 0.5)
            if death_toll > 0:
                char_name = _select_named_character(rng, characters, s.name, region_name, "famine")
                desc = _describe_with_character(
                    f"Famine grips {s.name}. {death_toll} perish from hunger.",
                    char_name, "{char} leads desperate prayers for rain."
                )
                events.append(SimEvent(
                    year=year,
                    event_type="famine",
                    description=desc,
                    affected_settlements=[s.name],
                    affected_regions=[region_name],
                ))
    
    # Rivalry/war between settlements (based on crowding and scarcity)
    active_settlements = [s for s in state.settlements.values() if s.is_active]
    if len(active_settlements) >= 2 and rng.random() < 0.03 * chaos_factor * (1 + len(active_settlements) * 0.03):
        # Pick two settlements that might conflict
        s1 = rng.choice(active_settlements)
        others = [s for s in active_settlements if s.name != s1.name]
        if others:
            s2 = rng.choice(others)
            distance = math.sqrt((s1.x - s2.x) ** 2 + (s1.y - s2.y) ** 2)
            # Closer settlements are more likely to conflict
            crowding_bonus = max(0, 1 - distance / 30)
            poverty_factor = max(0, 0.6 - s1.prosperity) + max(0, 0.6 - s2.prosperity)
            war_chance = crowding_bonus * (0.15 + poverty_factor * 0.5) * chaos_factor
            if rng.random() < war_chance:
                # War!
                casualties = max(1, int(min(s1.population, s2.population) * rng.uniform(0.05, 0.2)))
                actual_s1_loss = min(casualties // 2, s1.population - 1)
                actual_s2_loss = min(casualties - actual_s1_loss, s2.population - 1)
                s1.population -= actual_s1_loss
                s2.population -= actual_s2_loss
                if s1.population < 1:
                    s1.population = 1
                if s2.population < 1:
                    s2.population = 1
                
                # Characters involved in war may die
                c1 = _select_named_character(rng, characters, s1.name, s1.region, "war")
                c2 = _select_named_character(rng, characters, s2.name, s2.region, "war")
                if c1 and rng.random() < 0.25:
                    state.character_status[c1.full_name] = "dead"
                if c2 and rng.random() < 0.25:
                    state.character_status[c2.full_name] = "dead"
                
                def _war_status(character) -> str:
                    if character and hasattr(character, "full_name"):
                        status = state.character_status.get(character.full_name)
                        return "dead" if status == "dead" else "alive"
                    return "unknown"
                
                events.append(SimEvent(
                    year=year,
                    event_type="war",
                    description=_describe_with_character(
                        _describe_with_character(
                            (
                                f"War erupts between {s1.name} ({s1.region}) and "
                                f"{s2.name} ({s2.region}). "
                                f"{actual_s1_loss + actual_s2_loss} total casualties."
                            ),
                            c1,
                            "{char} leads the assault." if _war_status(c1) != "dead" else "{char} falls in battle.",
                        ),
                        c2,
                        "{char} marshals the defenders." if _war_status(c2) != "dead" else "{char} dies defending.",
                    ),
                    affected_settlements=[s1.name, s2.name],
                    affected_regions=list(set([s1.region, s2.region])),
                ))
    
    # New settlement founding (when a settlement gets very large)
    for s in list(state.settlements.values()):
        if not s.is_active:
            continue
        carrying_cap = _calculate_carrying_capacity(world, s.x, s.y)
        if s.population > carrying_cap * 0.7 and rng.random() < 0.02 * chaos_factor:
            # Spawn a new settlement nearby
            new_x = s.x + rng.randint(-8, 8)
            new_y = s.y + rng.randint(-8, 8)
            # Clamp to world bounds
            new_x = max(1, min(world.width - 2, new_x))
            new_y = max(1, min(world.height - 2, new_y))
            # Check it's on land
            if world.terrain[new_y][new_x] in ("deep_water", "shallow"):
                continue
            
            # Generate a name
            new_name = _generate_settlement_name(rng, state)
            if new_name in state.settlements:
                continue
            
            emigrants = int(s.population * rng.uniform(0.05, 0.15))
            s.population -= emigrants
            
            new_s = SettlementSnapshot(
                name=new_name,
                region=s.region,
                x=new_x,
                y=new_y,
                population=max(1, emigrants),
                kind="hamlet",
                founded_year=year,
                prosperity=0.3,
                food_stores=emigrants * 2,
                health=0.8,
            )
            state.settlements[new_name] = new_s
            
            char_name = _select_named_character(rng, characters, s.name, s.region, "founding")
            # Build a rich founding description using the character's story
            if char_name and hasattr(char_name, "occupation") and hasattr(char_name, "backstory"):
                # Use the character's backstory to inform the founding narrative
                backstory_snippet = char_name.backstory.split(".")[0] if char_name.backstory else ""
                founding_desc = (
                    f"A new settlement, {new_name}, is founded by emigrants "
                    f"from {s.name}. {char_name.full_name}, a {char_name.occupation} "
                    f"from {s.name}, leads the expedition. {backstory_snippet}."
                    f" Initial population: {emigrants}."
                )
            else:
                founding_desc = (
                    f"A new settlement, {new_name}, is founded by emigrants "
                    f"from {s.name}. Initial population: {emigrants}."
                )
            events.append(SimEvent(
                year=year,
                event_type="founding",
                description=founding_desc,
                affected_settlements=[s.name, new_name],
                affected_regions=[s.region],
            ))
        
        # Migration event: mild overpopulation leads to character-driven migration
        # (separate from full founding — this is a smaller movement event)
        elif s.population > carrying_cap * 0.5 and rng.random() < 0.008 * chaos_factor:
            char_name = _select_named_character(rng, characters, s.name, s.region, "exodus")
            emigrants = max(1, int(s.population * rng.uniform(0.02, 0.06)))
            s.population -= emigrants
            if char_name and hasattr(char_name, "full_name"):
                migration_desc = (
                    f"{char_name.full_name}, a {char_name.occupation} from {s.name}, "
                    f"leads {emigrants} settlers {'beyond ' + s.region + ' ' if s.region else ''}"
                    f"in search of new opportunities as {s.name} grows crowded."
                )
            else:
                migration_desc = (
                    f"A group of {emigrants} settlers departs {s.name} "
                    f"seeking new opportunities in the surrounding region."
                )
            events.append(SimEvent(
                year=year,
                event_type="exodus",
                description=migration_desc,
                affected_settlements=[s.name],
                affected_regions=[s.region],
            ))
    
    # Settlement abandonment (when population drops to near zero)
    for s_name in list(state.settlements.keys()):
        s = state.settlements[s_name]
        if not s.is_active:
            continue
        if s.population <= 3 and len(state.settlements) > sum(1 for ss in state.settlements.values() if ss.is_active):
            s.is_active = False
            char_name = _select_named_character(rng, characters, s_name, None, "abandonment")
            events.append(SimEvent(
                year=year,
                event_type="abandonment",
                description=_describe_with_character(
                    f"{s_name} is abandoned. Its few remaining residents scatter.",
                    char_name, "{char} is the last to leave."
                ),
                affected_settlements=[s_name],
                affected_regions=[s.region],
            ))
    
    # Prosperity events (random positive events)
    for s in list(state.settlements.values()):
        if not s.is_active:
            continue
        if s.prosperity > 0.7 and rng.random() < 0.01 * chaos_factor:
            boom_pop = int(s.population * rng.uniform(0.03, 0.08))
            s.population += boom_pop
            s.prosperity = min(1.0, s.prosperity + 0.05)
            char_name = _select_named_character(rng, characters, s.name, s.region, "prosperity")
            events.append(SimEvent(
                year=year,
                event_type="prosperity",
                description=_describe_with_character(
                    f"{s.name} experiences a trade boom. "
                    f"Population grows by {boom_pop} as wealth flows in.",
                    char_name, "{char} brokers lucrative trade agreements."
                ),
                affected_settlements=[s.name],
                affected_regions=[s.region],
            ))

    # ── Religious events ──────────────────────────────────────────
    # Only fire when the world has a pantheon
    has_religion = (
        world.pantheon is not None
        and len(world.pantheon.religions) > 0
    )

    # Religious tension: settlements with different religions nearby
    if has_religion and len(active_settlements) >= 2:
        # Find settlement pairs with different religions
        for s1 in active_settlements:
            if not s1.is_active or not s1.religion:
                continue
            for s2 in active_settlements:
                if not s2.is_active or not s2.religion:
                    continue
                if s1.name >= s2.name or s1.religion == s2.religion:
                    continue
                distance = math.sqrt((s1.x - s2.x) ** 2 + (s1.y - s2.y) ** 2)
                if distance < 25 and rng.random() < 0.02 * chaos_factor:
                    # Religious tension event!
                    cause = rng.choice([
                        "a disputed holy site",
                        "proselytizing in forbidden territory",
                        "an insult to a visiting priest",
                        "competing harvest festivals",
                        "a marriage across faiths",
                    ])
                    effect = rng.choice([
                        "The clergy call for calm, but tensions remain high.",
                        "Trade between the settlements suffers as a result.",
                        "A council of elders is convened to mediate the dispute.",
                        "The conflict simmers beneath the surface, waiting for a spark.",
                        "Zealots on both sides call for action.",
                    ])
                    events.append(SimEvent(
                        year=year,
                        event_type="religious_tension",
                        description=(
                            f"Religious tension flares between {s1.name} and {s2.name}. "
                            f"Followers of {s1.religion} and {s2.religion} clash over "
                            f"{cause}. {effect}"
                        ),
                        affected_settlements=[s1.name, s2.name],
                        affected_regions=list(set([s1.region, s2.region])),
                    ))
                    break  # One tension event per settlement per tick
            else:
                continue
            break

    # Divine blessing: settlement with religion, high prosperity
    if has_religion:
        for s in active_settlements:
            if not s.is_active or not s.religion:
                continue
            if s.prosperity > 0.6 and s.health > 0.7 and rng.random() < 0.008 * chaos_factor:
                # Pick a deity from the settlement's religion
                deity_name = _pick_deity_for_religion(world, s.religion, rng)
                boom_pop = max(1, int(s.population * rng.uniform(0.02, 0.06)))
                s.population += boom_pop
                s.prosperity = min(1.0, s.prosperity + 0.08)
                effect = rng.choice([
                    "The temple reports miraculous signs.",
                    "Pilgrims arrive bearing gifts and offerings.",
                    "The harvest is the richest in living memory.",
                    "Sicknesses are healed at the holy shrine.",
                ])
                events.append(SimEvent(
                    year=year,
                    event_type="divine_blessing",
                    description=(
                        f"A blessing from {deity_name} descends upon {s.name}. "
                        f"{effect} Population grows by {boom_pop}."
                    ),
                    affected_settlements=[s.name],
                    affected_regions=[s.region],
                ))

        # Pilgrimage events: trigger when a settlement has a holy site from its religion
        if has_religion and rng.random() < 0.01 * chaos_factor:
            _maybe_pilgrimage_event(world, state, events, rng, year)

        # Heresy events: religious settlements with low health/prosperity
        for s in active_settlements:
            if not s.is_active or not s.religion:
                continue
            if s.health < 0.4 and rng.random() < 0.015 * chaos_factor and s.population > 5:
                effect = rng.choice([
                    "The clergy denounce the heretics and call for their repentance.",
                    "A splinter sect breaks away, causing a schism in the faith.",
                    "The movement gains followers among the disaffected poor.",
                    "The authorities move to suppress the uprising.",
                ])
                events.append(SimEvent(
                    year=year,
                    event_type="heresy",
                    description=(
                        f"A heretical movement spreads through {s.name}, "
                        f"challenging the authority of the {s.religion} clergy. "
                        f"{effect}"
                    ),
                    affected_settlements=[s.name],
                    affected_regions=[s.region],
                ))

    # Record population data
    pop_record = {
        "year": year,
        "total_population": state.total_population,
        "num_settlements": state.num_settlements,
        "num_abandoned": state.num_abandoned,
    }
    state.population_record.append(pop_record)
    
    # Update world modifiers based on total trends
    _update_modifiers(state)
    
    # Check for era transitions (every 50+ years and on major population shifts)
    _check_era_transition(state, year, rng, chaos_factor)
    
    # Political tick — faction power drift, wars, alliances
    try:
        political_events = _simulate_political_tick(
            world, state, rng, year, chaos_factor
        )
        events.extend(political_events)
    except Exception:
        pass  # Political events are non-critical; don't crash sim

    # Cataclysm tick — rare catastrophic events that reshape terrain
    try:
        cataclysms = _simulate_cataclysm_tick(world, state, rng, year, chaos_factor)
        for cataclysm in cataclysms:
            events.append(cataclysm_to_sim_event(cataclysm))
            # Create refugee/exodus events for settlements that survived but lost population
            for s_name in cataclysm.affected_settlements:
                if s_name not in cataclysm.settlements_destroyed:
                    s = state.settlements.get(s_name)
                    if s and s.is_active:
                        # Survivors flee the devastation
                        emigrants = max(1, int(s.population * rng.uniform(0.1, 0.3)))
                        s.population -= emigrants
                        if emigrants > 0:
                            char_name = _select_named_character(rng, characters, s_name, s.region, "exodus")
                            events.append(SimEvent(
                                year=year,
                                event_type="exodus",
                                description=_describe_with_character(
                                    f"Survivors of the {cataclysm.cataclysm_type} flee {s_name}, "
                                    f"seeking refuge beyond {s.region or 'the devastated lands'}. "
                                    f"{emigrants} souls wander as refugees.",
                                    char_name, "{char} leads the desperate column."
                                ),
                                affected_settlements=[s_name],
                                affected_regions=[s.region] if s.region else [],
                            ))
            # Create settlement destruction events
            for s_destroyed in cataclysm.settlements_destroyed:
                events.append(SimEvent(
                    year=year,
                    event_type="abandonment",
                    description=f"{s_destroyed} is utterly destroyed by the {cataclysm.cataclysm_type}. Nothing remains but rubble and ash.",
                    affected_settlements=[s_destroyed],
                    affected_regions=cataclysm.affected_regions,
                ))
    except Exception:
        pass  # Cataclysm events are non-critical; don't crash sim

    # Economy tick — trade prosperity, route disruption, new routes
    try:
        from .economy import reconstruct_routes, serialize_routes
        route_objects = reconstruct_routes(state.trade_routes)
        route_objects, economy_events_raw = _simulate_economy_tick(
            world, state, rng, year, route_objects, chaos_factor,
        )
        state.trade_routes = serialize_routes(route_objects)
        for etype, desc, icon in economy_events_raw:
            events.append(SimEvent(
                year=year,
                event_type=etype,
                description=desc,
            ))
    except Exception:
        pass  # Economy events are non-critical; don't crash sim

    # Re-evaluate kind for all settlements after any population modifications
    # (plague, famine, war casualties, emigration — all can change pop without
    #  updating kind at the modification site)
    for s in state.settlements.values():
        if s.is_active:
            s.kind = _population_to_kind(s.population)

    return events


# ── Sub-year Month Tick ─────────────────────────────────────────────


def _simulate_month_tick(world: World, state: SimState, rng: random.Random,
                         year: int, month: int, chaos_factor: float = 0.1,
                         characters: list | None = None) -> list[SimEvent]:
    """Simulate one month (1/12 of a year) for the world.

    This is a lightweight tick that distributes ~1/12 of yearly effects
    across each month. Year-end subsystems (economy, faction_sim, cataclysm,
    era transitions, political) only fire when month == 11 (the 12th month).

    Args:
        world: The base world data
        state: Current simulation state (mutated in-place)
        rng: Seeded RNG for determinism
        year: Current simulation year
        month: Current month (0-11)
        chaos_factor: Overall chaos scaling
        characters: Named characters for event integration

    Returns:
        List of events generated this month
    """
    events: list[SimEvent] = []
    state.sub_year_month = month

    # Scale factor: how much of yearly activity happens this month
    # Months 0-10: lightweight tick (1/24 of yearly for smoothness)
    # Month 11: year-end wrap-up + remaining effects
    if month < 11:
        sf = 1.0 / 24.0  # Half-weight for intra-year months (smooth)
    else:
        sf = 1.0 - (11.0 / 24.0)  # Remainder in the 12th month (about 0.54)

    # Process each active settlement
    for s_name in list(state.settlements.keys()):
        s = state.settlements[s_name]
        if not s.is_active:
            continue

        # Calculate carrying capacity
        if world.capacity_map is not None and 0 <= s.y < len(world.capacity_map) and 0 <= s.x < len(world.capacity_map[0]):
            carrying_cap = world.capacity_map[s.y][s.x]
        else:
            carrying_cap = _calculate_carrying_capacity(world, s.x, s.y)

        if world.food_map is not None and world.wealth_map is not None and 0 <= s.y < len(world.food_map) and 0 <= s.x < len(world.food_map[0]):
            food_avail = world.food_map[s.y][s.x]
            wealth_avail = world.wealth_map[s.y][s.x]
        else:
            food_avail, wealth_avail = _resource_availability(world, s.x, s.y)

        # Food: scaled monthly production and consumption
        food_production = s.population * food_avail * 2.0 * sf
        food_consumption = s.population * 0.5 * (1 + _random_variation(rng, 0.1 / 12)) * sf
        s.food_stores += food_production - food_consumption
        s.food_stores = max(0, min(s.food_stores, s.population * 5))

        # Health: very subtle monthly drift
        crowding_ratio = s.population / max(carrying_cap, 1)
        s.health += (max(0.05, 1.0 - crowding_ratio * 0.5) - s.health) * sf * 0.5
        s.health = max(0.05, min(1.0, s.health))

        # Prosperity: scaled monthly drift
        target_prosperity = wealth_avail * 0.7 + food_avail * 0.3
        s.prosperity += (target_prosperity - s.prosperity) * 0.1 * sf + _random_variation(rng, 0.02 * sf)
        s.prosperity = max(0.0, min(1.0, s.prosperity))

        # Population: scaled monthly logistic growth
        if s.food_stores <= 0 or s.health < 0.2:
            decline_rate = (0.05 + (1 - s.health) * 0.2 + max(0, -s.food_stores / s.population) * 0.1) * sf
            s.population = max(1, int(s.population * (1 - decline_rate)))
        else:
            effective_capacity = carrying_cap * max(food_avail, 0.2)
            growth_rate = (0.02 + s.prosperity * 0.02) * sf
            new_pop = _logistic_growth(s.population, effective_capacity, growth_rate)
            new_pop *= (1 + _random_variation(rng, 0.03 * sf))
            s.population = max(1, int(new_pop))

        # Update kind based on scaled population
        s.kind = _population_to_kind(s.population)

        # Event checks (scaled probability per month)
        # Plague
        if s.health < 0.4 and rng.random() < 0.03 * chaos_factor * sf and s.population > 5:
            death_toll = max(1, int(s.population * rng.uniform(0.1, 0.4) * sf))
            if death_toll < 2:
                death_toll = 0  # Too small to matter
            if death_toll > 0:
                s.population -= death_toll
                if s.population < 1:
                    s.population = 1
                s.health = rng.uniform(0.3, 0.6)
                events.append(SimEvent(
                    year=year, month=month + 1,
                    event_type="plague",
                    description=f"Plague lingers in {s.name} ({s.region}), claiming {death_toll} this month.",
                    affected_settlements=[s.name],
                    affected_regions=[s.region],
                ))

        # Famine
        if (s.food_stores < s.population * 0.5
                and rng.random() < 0.03 * chaos_factor * sf
                and s.population > 3 and month == 11):
            death_toll = max(1, int(s.population * rng.uniform(0.05, 0.2)))
            s.population -= death_toll
            if s.population < 1:
                s.population = 1
            s.food_stores = max(0, s.food_stores - s.population * 0.5)
            if death_toll > 0:
                events.append(SimEvent(
                    year=year, month=month + 1,
                    event_type="famine",
                    description=f"Famine deepens in {s.name}. {death_toll} perish from hunger.",
                    affected_settlements=[s.name],
                    affected_regions=[s.region],
                ))

        # Prosperity events (month 11 only)
        if s.prosperity > 0.7 and rng.random() < 0.01 * chaos_factor * (sf * 12) and month == 11:
            boom_pop = int(s.population * rng.uniform(0.03, 0.08))
            s.population += boom_pop
            s.prosperity = min(1.0, s.prosperity + 0.05)
            events.append(SimEvent(
                year=year, month=month + 1,
                event_type="prosperity",
                description=f"{s.name} experiences a trade boom. Population grows by {boom_pop}.",
                affected_settlements=[s.name],
                affected_regions=[s.region],
            ))

    # ── Year-end subsystems (fire only in month 11) ─────────────────
    if month == 11:
        # New settlement founding
        for s in list(state.settlements.values()):
            if not s.is_active:
                continue
            carrying_cap = _calculate_carrying_capacity(world, s.x, s.y)
            if s.population > carrying_cap * 0.7 and rng.random() < 0.02 * chaos_factor:
                new_x = s.x + rng.randint(-8, 8)
                new_y = s.y + rng.randint(-8, 8)
                new_x = max(1, min(world.width - 2, new_x))
                new_y = max(1, min(world.height - 2, new_y))
                if world.terrain[new_y][new_x] in ("deep_water", "shallow"):
                    continue
                new_name = _generate_settlement_name(rng, state)
                if new_name in state.settlements:
                    continue
                emigrants = int(s.population * rng.uniform(0.05, 0.15))
                s.population -= emigrants
                new_s = SettlementSnapshot(
                    name=new_name, region=s.region,
                    x=new_x, y=new_y,
                    population=max(1, emigrants), kind="hamlet",
                    founded_year=year, prosperity=0.3,
                    food_stores=emigrants * 2, health=0.8,
                )
                state.settlements[new_name] = new_s
                events.append(SimEvent(
                    year=year, month=month + 1,
                    event_type="founding",
                    description=f"A new settlement, {new_name}, is founded by emigrants from {s.name}.",
                    affected_settlements=[s.name, new_name],
                    affected_regions=[s.region],
                ))

            # Migration
            elif s.population > carrying_cap * 0.5 and rng.random() < 0.008 * chaos_factor:
                emigrants = max(1, int(s.population * rng.uniform(0.02, 0.06)))
                s.population -= emigrants
                events.append(SimEvent(
                    year=year, month=month + 1,
                    event_type="exodus",
                    description=f"A group of {emigrants} departs {s.name} seeking new opportunities.",
                    affected_settlements=[s.name],
                    affected_regions=[s.region],
                ))

        # Settlement abandonment (year-end check)
        for s_name in list(state.settlements.keys()):
            s_state = state.settlements[s_name]
            if not s_state.is_active:
                continue
            if s_state.population <= 3:
                s_state.is_active = False
                events.append(SimEvent(
                    year=year, month=month + 1,
                    event_type="abandonment",
                    description=f"{s_name} falls silent. Its last residents scatter.",
                    affected_settlements=[s_name],
                    affected_regions=[s_state.region],
                ))

        # War between settlements
        active_settlements = [s for s in state.settlements.values() if s.is_active]
        if len(active_settlements) >= 2 and rng.random() < 0.03 * chaos_factor * (1 + len(active_settlements) * 0.03):
            s1 = rng.choice(active_settlements)
            others = [s for s in active_settlements if s.name != s1.name]
            if others:
                s2 = rng.choice(others)
                distance = math.sqrt((s1.x - s2.x) ** 2 + (s1.y - s2.y) ** 2)
                crowding_bonus = max(0, 1 - distance / 30)
                poverty_factor = max(0, 0.6 - s1.prosperity) + max(0, 0.6 - s2.prosperity)
                war_chance = crowding_bonus * (0.15 + poverty_factor * 0.5) * chaos_factor
                if rng.random() < war_chance:
                    casualties = max(1, int(min(s1.population, s2.population) * rng.uniform(0.05, 0.2)))
                    actual_s1_loss = min(casualties // 2, s1.population - 1)
                    actual_s2_loss = min(casualties - actual_s1_loss, s2.population - 1)
                    s1.population -= actual_s1_loss
                    s2.population -= actual_s2_loss
                    if s1.population < 1: s1.population = 1
                    if s2.population < 1: s2.population = 1
                    events.append(SimEvent(
                        year=year, month=month + 1,
                        event_type="war",
                        description=f"War erupts between {s1.name} and {s2.name}. "
                                    f"{actual_s1_loss + actual_s2_loss} total casualties.",
                        affected_settlements=[s1.name, s2.name],
                        affected_regions=list(set([s1.region, s2.region])),
                    ))

        # Political tick
        try:
            from .faction_sim import _simulate_political_tick
            political_events = _simulate_political_tick(world, state, rng, year, chaos_factor)
            for pe in political_events:
                pe.month = month + 1
            events.extend(political_events)
        except Exception:
            pass

        # Cataclysm tick
        try:
            from .cataclysm import _simulate_cataclysm_tick, cataclysm_to_sim_event
            cataclysms = _simulate_cataclysm_tick(world, state, rng, year, chaos_factor)
            for cataclysm in cataclysms:
                ce = cataclysm_to_sim_event(cataclysm)
                ce.month = month + 1
                events.append(ce)
        except Exception:
            pass

        # Economy tick
        try:
            from .economy import reconstruct_routes, serialize_routes, _simulate_economy_tick
            route_objects = reconstruct_routes(state.trade_routes)
            route_objects, economy_events_raw = _simulate_economy_tick(
                world, state, rng, year, route_objects, chaos_factor,
            )
            state.trade_routes = serialize_routes(route_objects)
            for etype, desc, icon in economy_events_raw:
                events.append(SimEvent(
                    year=year, month=month + 1,
                    event_type=etype,
                    description=desc,
                ))
        except Exception:
            pass

        # Record population data for this year
        state.population_record.append({
            "year": year,
            "total_population": state.total_population,
            "num_settlements": state.num_settlements,
            "num_abandoned": state.num_abandoned,
        })

        # Update world modifiers and era transitions
        _update_modifiers(state)
        _check_era_transition(state, year, rng, chaos_factor)

    # Re-evaluate kind for all active settlements
    for s in state.settlements.values():
        if s.is_active:
            s.kind = _population_to_kind(s.population)

    return events


def _random_variation(rng: random.Random, magnitude: float) -> float:
    """Generate a small random variation around 0, in range [-magnitude, magnitude]."""
    return rng.uniform(-magnitude, magnitude)


def _population_to_kind(population: int) -> str:
    """Convert population number to settlement kind."""
    if population < 200:
        return "hamlet"
    elif population < 800:
        return "village"
    elif population < 2000:
        return "town"
    else:
        return "city"


def _generate_settlement_name(rng: random.Random, state: SimState) -> str:
    """Generate a new settlement name that doesn't conflict with existing ones."""
    PREFIXES = ["Oak", "Ash", "Fern", "Mist", "Sun", "Star", "Moon", "Raven",
                "Fox", "Wolf", "Bear", "Deer", "Hawk", "Eagle", "Stone",
                "Iron", "Copper", "Gold", "Silver", "Crystal", "Briar",
                "Thorn", "Rush", "Brook", "Dun", "Red", "White", "Grey",
                "Black", "Green", "Fern", "Moss", "Pine"]
    
    SUFFIXES = ["dale", "ford", "gate", "grove", "haven", "holt", "keep",
                "mere", "moor", "reach", "ridge", "run", "shire", "stead",
                "vale", "wall", "watch", "wood", "field", "brook",
                "burgh", "bury", "ham", "wick", "worth", "stead"]
    
    for _ in range(50):
        prefix = rng.choice(PREFIXES)
        suffix = rng.choice(SUFFIXES)
        name = f"{prefix}{suffix}"
        if name not in state.settlements:
            return name
    
    # Fallback: numbered name
    return f"Newstead-{rng.randint(100, 999)}"


def _update_modifiers(state: SimState) -> None:
    """Update world-level modifiers based on simulation trends."""
    state.world_modifiers.clear()
    total_pop = state.total_population

    if total_pop > 5000:
        state.world_modifiers.append("Growing population strains resources")
    if state.num_abandoned > 2:
        state.world_modifiers.append(f"Ruins dot the landscape ({state.num_abandoned} abandoned settlements)")
    if total_pop < 200 and state.year > 50:
        state.world_modifiers.append("Population in decline — the world grows quiet")

    # Religion-aware modifiers
    active_religions = set()
    for s in state.settlements.values():
        if s.is_active and s.religion:
            active_religions.add(s.religion)
    if len(active_religions) >= 2:
        state.world_modifiers.append(
            f"Religious diversity: {len(active_religions)} faiths coexist"
        )


def _check_era_transition(state: SimState, year: int, rng: random.Random,
                          chaos_factor: float = 0.1) -> None:
    """
    Check if conditions warrant an era transition and apply it.

    Triggers at milestone years or when world conditions shift significantly.
    Records the transition in state.era_history for audit.
    """
    # No transitions before year 50 — let the world settle
    if year < 50:
        return
    
    # Eras are named after 50-year milestones
    era_interval = 50
    
    # Check for new era at milestone years
    if year % era_interval != 0:
        return
    
    # Check we haven't already recorded this milestone
    milestone_key = f"Year {year}"
    for record in state.era_history:
        if record.get("milestone") == milestone_key:
            return  # Already recorded this one
    
    total_pop = state.total_population
    num_active = state.num_settlements
    num_abandoned = state.num_abandoned

    # Check for religious diversity among active settlements
    active_religions = set()
    for s in state.settlements.values():
        if s.is_active and s.religion:
            active_religions.add(s.religion)
    num_religions = len(active_religions)

    # Determine era name based on world conditions
    era_adjs = ["Rising", "Golden", "Iron", "Crimson", "Ashen", "Silent",
                "Burning", "Fading", "Dawning", "Shattered", "Weeping",
                "Kindled", "Hollow"]
    era_nouns = ["Tide", "Age", "Century", "Turning", "Cycle", "Season",
                 "Reign", "Crown", "Bloom", "Frost", "Flame", "Eclipse"]

    # Religion-themed era naming
    faith_adjs = ["Pious", "Zealous", "Devout", "Sacred", "Heretic", "Schismatic"]
    faith_nouns = ["Faith", "Schism", "Crusade", "Conviction", "Doubt", "Grace"]

    # Conditions-based era naming
    if total_pop > state.population_record[0]["total_population"] * 3 and num_abandoned <= 2:
        adj = rng.choice(["Golden", "Rising", "Dawning", "Kindled", "Prosperous"])
        noun = rng.choice(["Age", "Century", "Reign", "Bloom"])
        era_type = "prosperity"
    elif num_abandoned > max(3, num_active // 4):
        adj = rng.choice(["Ashen", "Fading", "Hollow", "Shattered", "Weeping"])
        noun = rng.choice(["Decline", "Frost", "Eclipse", "Silence"])
        era_type = "decline"
    elif num_active > state.population_record[0].get("num_settlements", len(state.settlements)) * 2:
        adj = rng.choice(["Rising", "Burning", "Iron", "Expanding"])
        noun = rng.choice(["Age", "Century", "Flame", "Tide"])
        era_type = "expansion"
    elif total_pop < state.population_record[0]["total_population"] * 0.5 and num_abandoned > 1:
        adj = rng.choice(["Crimson", "Shattered", "Weeping", "Fallen"])
        noun = rng.choice(["War", "Blood", "Ash", "Bones"])
        era_type = "conflict"
    elif num_religions >= 2 and rng.random() < 0.5:
        # Religious diversity shapes the era
        adj = rng.choice(faith_adjs)
        noun = rng.choice(faith_nouns)
        era_type = "religious_age"
    else:
        # Random flavor pick
        adj = rng.choice(era_adjs)
        noun = rng.choice(era_nouns)
        era_type = "transition"

    era_name = f"The {adj} {noun}"

    # Build era description — include religious flavor if available
    era_desc = f"The world enters the {adj} {noun}. "
    if num_religions >= 2:
        rel_list = ", ".join(sorted(active_religions)[:3])
        era_desc += f"{num_religions} faiths — {rel_list} — vie for influence. "
    era_desc += (
        f"Population: {total_pop:,} across {num_active} settlements"
        + (f" with {num_abandoned} lying in ruins." if num_abandoned > 0 else ".")
    )
    
    # Record the transition
    state.current_era = era_name
    state.era_history.append({
        "milestone": milestone_key,
        "year": year,
        "era_name": era_name,
        "era_type": era_type,
        "description": era_desc,
    })


# ── Religion Helpers ────────────────────────────────────────────────


def _pick_deity_for_religion(world, religion_name: str, rng: random.Random) -> str:
    """Pick a deity name from the specified religion's pantheon."""
    if not world.pantheon or not world.pantheon.religions:
        return "the gods"
    for rel in world.pantheon.religions:
        if rel.name == religion_name and rel.pantheon:
            deity = rng.choice(rel.pantheon)
            return f"{deity.name} {deity.surname}"
    # Fallback: pick any deity from any religion
    for rel in world.pantheon.religions:
        if rel.pantheon:
            deity = rng.choice(rel.pantheon)
            return f"{deity.name} {deity.surname}"
    return "the gods"


def _maybe_pilgrimage_event(world, state, events, rng, year):
    """Generate a pilgrimage event to a holy site, if one exists."""
    if not world.pantheon:
        return
    # Collect all holy sites
    all_holy_sites = []
    for rel in world.pantheon.religions:
        for site in rel.holy_sites:
            all_holy_sites.append((rel.name, site))
    if not all_holy_sites:
        return
    rel_name, chosen_site = rng.choice(all_holy_sites)
    # Find the settlement where the holy site is located
    source_settlements = [
        s for s in state.settlements.values()
        if s.is_active and s.religion == rel_name and s.name != chosen_site.settlement
    ]
    if not source_settlements:
        return
    source = rng.choice(source_settlements)
    effect = rng.choice([
        f"Devotees travel for weeks to reach the sacred site.",
        f"The pilgrimage strengthens the faith of {rel_name} followers.",
        f"Merchants follow the pilgrims, setting up temporary markets along the route.",
        f"The temple reports a surge in donations and offerings.",
    ])
    events.append(SimEvent(
        year=year,
        event_type="holy_pilgrimage",
        description=(
            f"A great pilgrimage to {chosen_site.name} draws devotees "
            f"from {source.name} across the land. {effect}"
        ),
        affected_settlements=[source.name, chosen_site.settlement],
        affected_regions=[chosen_site.region],
    ))


# ── Character Integration ───────────────────────────────────────────


def _init_character_status(characters: list | None) -> dict[str, str]:
    """Build character_status dict from narrative characters, all marked 'alive'."""
    if not characters:
        return {}
    return {c.full_name: "alive" for c in characters}


def _apply_narrative_consequences(world, state: SimState, events: list[SimEvent]) -> None:
    """
    Apply sim event consequences back to the world's narrative data.

    - Marks characters as dead based on sim character_status
    - Deactivates quests whose giver died
    - Generates new quests from major sim events

    Args:
        world: The World object (mutated in-place for narrative changes)
        state: Final simulation state
        events: All sim events that occurred
    """
    if not world.narrative:
        return

    # 1. Update character statuses in the narrative
    dead_names = {
        name for name, status in state.character_status.items()
        if status == "dead"
    }
    for c in world.narrative.characters:
        if c.full_name in dead_names and c.status == "alive":
            c.status = "dead"

    # 2. Deactivate quests whose giver is dead
    for q in world.narrative.quests:
        if q.giver_character and q.giver_character in dead_names:
            q.is_active = False

    # 3. Generate new quests from major sim events
    # Pick the most impactful events (wars, plagues, foundings) to spawn quests
    import random as _random
    rng = _random.Random(world.seed + 9000000 + state.year)

    quest_templates = [
        ("exploration", "Scout {target} after the {event_type}. Locals report {detail}."),
        ("combat", "{event_type} aftermath: {detail}. {giver} seeks aid."),
        ("diplomacy", "The aftermath of {event_type} requires {detail}."),
        ("gathering", "{event_type} has left {detail}. Collect supplies."),
    ]

    spawnable_types = {"war", "plague", "famine", "disaster", "founding", "abandonment",
                       "religious_tension", "divine_blessing", "holy_pilgrimage", "heresy",
                       "earthquake", "volcanic_eruption", "great_plague", "tsunami",
                       "meteor_strike", "great_fire", "magical_cataclysm"}
    new_quests = []
    for ev in events[-20:]:  # Only from recent events
        if ev.event_type in spawnable_types and rng.random() < 0.15:
            qtype, qtext_tpl = rng.choice(quest_templates)
            # Find a giver from an unaffected settlement
            giver = None
            for c in world.narrative.characters:
                if c.status == "alive" and c.home_settlement not in ev.affected_settlements:
                    giver = c
                    break
            giver_name = giver.full_name if giver else "The Council"

            affected = ", ".join(ev.affected_settlements[:2]) or "the region"
            detail_options = {
                "war": "wandering mercenaries and displaced refugees",
                "plague": "a need for rare medicinal herbs",
                "famine": "crop blight spreading to neighbouring farms",
                "founding": "a need to establish trade routes to the new settlement",
                "abandonment": "rumours of valuable goods left behind in the ruins",
                "disaster": "urgent repair supplies needed from afar",
                "religious_tension": "a fragile peace that could shatter at any moment",
                "divine_blessing": "a pilgrimage route that needs protection",
                "holy_pilgrimage": "sacred relics that require safe passage",
                "heresy": "schismatic teachings threatening the established order",
                "earthquake": "landslides and unstable ground near the broken landscape",
                "volcanic_eruption": "ash-choked skies and lava-blocked passes",
                "great_plague": "quarantine zones and the search for a cure",
                "tsunami": "drowned coasts and refugees stranded on high ground",
                "meteor_strike": "strange celestial fragments scattered across the impact site",
                "great_fire": "scorched earth and the need for rebuilding supplies",
                "magical_cataclysm": "reality-bending anomalies that must be contained or studied",
            }
            detail = detail_options.get(ev.event_type, "unusual activity")

            quest_desc = qtext_tpl.format(
                event_type=ev.event_type,
                target=affected,
                detail=detail,
                giver=giver_name.capitalize(),
            )

            new_quest = type('Quest', (), {
                'name': f"The {ev.event_type.capitalize()} Aftermath",
                'quest_type': qtype,
                'difficulty': "moderate",
                'description': quest_desc,
                'giver_character': giver_name,
                'giver_settlement': giver.home_settlement if giver else affected,
                'target_region': ev.affected_regions[0] if ev.affected_regions else "",
                'rewards': ["coin", "gratitude of the settlement"],
                'is_active': True,
            })
            new_quests.append(new_quest)

    world.narrative.quests.extend(new_quests)


_CHARACTER_ROLE_MAP: dict[str, list[str]] = {
    "plague": [  # who'd be involved in a plague event
        "healer", "herbalist", "priest", "sage", "alchemist",
    ],
    "famine": [  # who'd be involved in a famine
        "farmer", "miller", "baker", "brewer", "innkeeper", "trader",
    ],
    "war": [  # who'd be involved in war
        "soldier", "guard", "ranger", "scout", "warlord", "chieftain",
        "lord", "seneschal", "hunter",
    ],
    "discovery": [  # who'd make or witness a discovery
        "sage", "scholar", "alchemist", "cartographer", "ranger", "miner",
    ],
    "prosperity": [  # who'd drive a prosperity event
        "merchant", "trader", "lord", "governor", "innkeeper", "shipwright",
    ],
    "disaster": [  # who'd be affected by disaster
        "mason", "carpenter", "miner", "shipwright", "sailor",
    ],
    "exodus": [  # who'd lead an exodus
        "ranger", "scout", "hunter", "chieftain", "lord", "explorer",
    ],
    "founding": [  # who'd found a new settlement
        "ranger", "scout", "hunter", "explorer", "trader", "warlord",
        "chieftain", "lord", "governor", "shipwright",
    ],
    "abandonment": [  # who'd be the last to leave
        "priest", "hermit", "judge", "eldest", "seneschal",
    ],
    "trade_boom": [  # who'd drive a trade boom
        "merchant", "trader", "lord", "governor", "shipwright", "innkeeper",
    ],
    "religious_tension": [  # who'd be involved in religious conflict
        "priest", "sage", "alchemist", "lord", "governor", "chieftain",
    ],
    "divine_blessing": [  # who'd witness a divine blessing
        "priest", "healer", "herbalist", "sage", "farmer",
    ],
    "holy_pilgrimage": [  # who'd lead or join a pilgrimage
        "priest", "sage", "healer", "bard", "trader",
    ],
    "heresy": [  # who'd be involved in a heresy
        "priest", "sage", "scholar", "alchemist", "herbalist", "lord",
    ],
}


def _select_named_character(
    rng: random.Random,
    characters: list | None,
    settlement_name: str,
    region_name: str | None,
    event_type: str,
):
    """
    Pick a named (alive) character connected to the affected settlement or region.

    Returns the Character object, or None if no suitable character found.
    """
    if not characters:
        return None

    # Preferred occupations for this event type
    preferred = _CHARACTER_ROLE_MAP.get(event_type, [])

    # First: characters who live in the affected settlement AND have a preferred occupation
    candidates = [
        c for c in characters
        if c.status == "alive" and c.home_settlement == settlement_name
        and c.occupation.lower() in preferred
    ]

    # Second: characters from the affected region
    if not candidates and region_name:
        candidates = [
            c for c in characters
            if c.status == "alive" and c.home_region == region_name
            and c.occupation.lower() in preferred
        ]

    # Third: any alive character from the settlement
    if not candidates:
        candidates = [
            c for c in characters
            if c.status == "alive" and c.home_settlement == settlement_name
        ]

    # Fourth: any alive character from the region
    if not candidates and region_name:
        candidates = [
            c for c in characters
            if c.status == "alive" and c.home_region == region_name
        ]

    if not candidates:
        return None

    return rng.choice(candidates)


def _describe_with_character(
    base: str,
    character,
    occupation_prompt: str | None = None,
) -> str:
    """
    Append a character reference to an event description.

    If character is provided, appends a brief occupation-flavoured note.
    If not, returns the base description unchanged.
    """
    if not character:
        return base
    char_name = character.full_name if hasattr(character, "full_name") else str(character)
    if occupation_prompt:
        return f"{base} — {occupation_prompt.format(char=char_name)}"
    return f"{base} — {char_name}"


# ── Initialization ──────────────────────────────────────────────────


def initialize_sim_state(world: World) -> SimState:
    """
    Initialize a SimState from the static world data.
    
    Converts the World's settlement data into SettlementSnapshot objects
    that can be evolved year by year.
    """
    state = SimState(year=0)
    
    for region in world.regions:
        for settlement in region.settlements:
            # Determine religion from PantheonSystem if available
            religion_name = None
            if world.pantheon and hasattr(world.pantheon, 'region_religion'):
                religion_name = world.pantheon.region_religion.get(region.name)
            state.settlements[settlement.name] = SettlementSnapshot(
                name=settlement.name,
                region=region.name,
                x=settlement.x,
                y=settlement.y,
                population=settlement.population,
                kind=settlement.kind,
                is_active=True,
                founded_year=0,
                prosperity=0.5,
                food_stores=settlement.population * 2,
                health=1.0,
                religion=religion_name,
            )
    
    # Initial population record
    state.population_record.append({
        "year": 0,
        "total_population": state.total_population,
        "num_settlements": state.num_settlements,
        "num_abandoned": 0,
    })
    
    # Initialize faction simulation state
    state.faction_state = initialize_faction_state(world)

    # Precompute resource maps for O(1) lookups in sim tick
    _precompute_resource_maps(world)

    return state


def simulate_years(world: World, state: SimState, num_years: int,
                   seed_offset: int = 0, chaos_factor: float = 0.1,
                   snapshot_interval: int = 0,
                   snapshots_out: list[SimState] | None = None,
                   characters: list | None = None) -> list[SimEvent]:
    """
    Run the simulation for a number of years.
    
    Args:
        world: The base world
        state: Simulation state (will be mutated)
        num_years: How many years to simulate
        seed_offset: Offset for the RNG seed (used for branching)
        chaos_factor: How much random chaos to apply (0.0-1.0)
        snapshot_interval: Take snapshots every N years (0 = no intermediate snapshots)
        snapshots_out: List to append snapshots to (if None, no snapshots taken)
    
    Returns:
        Complete list of events generated during the simulation
    """
    all_events: list[SimEvent] = []
    
    # Create a seeded RNG for determinism
    sim_seed = world.seed + 4000000 + seed_offset
    rng = random.Random(sim_seed)
    
    start_year = state.year

    # Initialize economy (seed-deterministic)
    try:
        from .economy import serialize_routes
        rng_for_economy = random.Random(sim_seed + 999)  # Dedicated RNG stream for economy
        assign_economies(world, state, rng_for_economy)
        routes = _generate_trade_routes(state, rng_for_economy, 0)
        state.trade_routes = serialize_routes(routes)
    except Exception:
        pass  # Economy initialization is non-critical

    for y in range(1, num_years + 1):
        current_year = start_year + y
        state.year = current_year
        
        year_events = _simulate_tick(world, state, rng, current_year, chaos_factor, characters)
        all_events.extend(year_events)
        
        # Take intermediate snapshots at the specified interval
        if snapshots_out is not None and snapshot_interval > 0 and current_year % snapshot_interval == 0:
            snapshots_out.append(copy.deepcopy(state))
    
    return all_events


# ── High-Level API ──────────────────────────────────────────────────


@dataclass
class SimResult:
    """
    Complete result of a simulation run.
    
    Contains the final state plus all events and metadata.
    """
    seed: int
    num_years: int
    initial_state: SimState
    final_state: SimState
    events: list[SimEvent]
    snapshots: list[SimState] = field(default_factory=list)
    
    @property
    def total_events(self) -> int:
        return len(self.events)
    
    @property
    def summary(self) -> dict:
        return {
            "seed": self.seed,
            "years_simulated": self.num_years,
            "events": self.total_events,
            "start_population": self.initial_state.total_population,
            "end_population": self.final_state.total_population,
            "start_settlements": self.initial_state.num_settlements,
            "end_settlements": self.final_state.num_settlements,
            "abandoned": self.final_state.num_abandoned,
        }


def run_simulation(world: World, num_years: int = 100,
                   seed_offset: int = 0, chaos_factor: float = 0.3,
                   snapshot_interval: int = 50,
                   characters: list | None = None) -> SimResult:
    """
    Run a complete simulation and return the result.
    
    Args:
        world: The world to simulate
        num_years: How many years to run
        seed_offset: Branching offset for the RNG seed
        chaos_factor: Random chaos amount (0.0-1.0)
        snapshot_interval: Years between snapshots (0 = no snapshots)
    
    Returns:
        SimResult with final state and all events
    """
    initial_state = initialize_sim_state(world)
    state = copy.deepcopy(initial_state)

    # Initialize character tracking
    state.character_status = _init_character_status(characters)

    snapshots: list[SimState] = []

    # Take initial snapshot
    if snapshot_interval > 0:
        snapshots.append(copy.deepcopy(state))

    events = simulate_years(
        world, state, num_years, seed_offset, chaos_factor,
        snapshot_interval=snapshot_interval,
        snapshots_out=snapshots,
        characters=characters,
    )
    
    # Take final snapshot (only if not already captured by interval)
    if snapshot_interval > 0 and (num_years == 0 or num_years % snapshot_interval != 0):
        snapshots.append(copy.deepcopy(state))
    
    # Apply narrative consequences: character deaths, quest updates, new quests
    _apply_narrative_consequences(world, state, events)
    
    return SimResult(
        seed=world.seed + 4000000 + seed_offset,
        num_years=num_years,
        initial_state=initial_state,
        final_state=state,
        events=events,
        snapshots=snapshots,
    )


def simulate_years_monthly(world: World, state: SimState, num_years: int,
                           seed_offset: int = 0, chaos_factor: float = 0.1,
                           snapshot_interval: int = 0,
                           snapshots_out: list[SimState] | None = None,
                           characters: list | None = None) -> list[SimEvent]:
    """Run simulation using month-level ticks for smoother granularity.

    Unlike simulate_years (which ticks one year at a time), this function
    ticks 12 months per year using _simulate_month_tick, distributing
    population/food/health changes smoothly across the year.

    The total effects over 12 months are equivalent to one year tick,
    but intermediate state snapshots show gradual change rather than
    sudden jumps.

    Args:
        world: The base world
        state: Simulation state (will be mutated)
        num_years: How many years to simulate
        seed_offset: Offset for the RNG seed
        chaos_factor: Random chaos amount (0.0-1.0)
        snapshot_interval: Snapshots every N years (0 = no snapshots)
        snapshots_out: List to append snapshots to
        characters: Named characters for event integration

    Returns:
        List of all events generated during the simulation
    """
    all_events: list[SimEvent] = []

    sim_seed = world.seed + 4000000 + seed_offset
    rng = random.Random(sim_seed)

    start_year = state.year

    # Initialize economy (seed-deterministic)
    try:
        from .economy import serialize_routes, assign_economies, _generate_trade_routes
        rng_for_economy = random.Random(sim_seed + 999)
        assign_economies(world, state, rng_for_economy)
        routes = _generate_trade_routes(state, rng_for_economy, 0)
        state.trade_routes = serialize_routes(routes)
    except Exception:
        pass

    for y in range(1, num_years + 1):
        current_year = start_year + y
        state.year = current_year
        state.sub_year_month = 0

        for m in range(12):
            month_events = _simulate_month_tick(
                world, state, rng, current_year, m,
                chaos_factor, characters,
            )
            all_events.extend(month_events)

        # Take snapshots at year boundaries
        if snapshots_out is not None and snapshot_interval > 0 and current_year % snapshot_interval == 0:
            snapshots_out.append(copy.deepcopy(state))

    return all_events


def run_monthly_simulation(world: World, num_years: int = 100,
                           seed_offset: int = 0, chaos_factor: float = 0.3,
                           snapshot_interval: int = 50,
                           characters: list | None = None) -> SimResult:
    """Run a monthly-granularity simulation and return the result.

    Same interface as run_simulation, but uses month-level ticks for
    smoother population/food changes. Useful for the viewer and embody
    modes where sub-year granularity matters.

    Args:
        world: The world to simulate
        num_years: How many years to run
        seed_offset: Branching offset for the RNG seed
        chaos_factor: Random chaos amount (0.0-1.0)
        snapshot_interval: Years between snapshots (0 = no snapshots)

    Returns:
        SimResult with final state and all events
    """
    initial_state = initialize_sim_state(world)
    state = copy.deepcopy(initial_state)

    state.character_status = _init_character_status(characters)

    snapshots: list[SimState] = []

    if snapshot_interval > 0:
        snapshots.append(copy.deepcopy(state))

    events = simulate_years_monthly(
        world, state, num_years, seed_offset, chaos_factor,
        snapshot_interval=snapshot_interval,
        snapshots_out=snapshots,
        characters=characters,
    )

    if snapshot_interval > 0 and (num_years == 0 or num_years % snapshot_interval != 0):
        snapshots.append(copy.deepcopy(state))

    _apply_narrative_consequences(world, state, events)

    return SimResult(
        seed=world.seed + 4000000 + seed_offset,
        num_years=num_years,
        initial_state=initial_state,
        final_state=state,
        events=events,
        snapshots=snapshots,
    )


def apply_sim_state_to_world(world: World, sim_state: SimState) -> World:
    """
    Create a copy of a World with simulation-state settlements applied.
    
    This allows the explore, query, and export commands to see the world
    as it exists at a specific simulation year — with evolved populations,
    new founded settlements, and abandoned settlements removed.
    
    Args:
        world: The base world (terrain, lore, etc.)
        sim_state: The simulation state to apply
    
    Returns:
        A new World with settlements reflecting the sim state
    """
    import copy
    new_world = copy.deepcopy(world)
    
    # Build region name → region map
    region_map: dict[str, Region] = {r.name: r for r in new_world.regions}
    
    # Clear existing settlements from all regions
    for r in new_world.regions:
        r.settlements.clear()
    
    # Add active settlements from the sim state
    for s in sim_state.settlements.values():
        if not s.is_active:
            continue
        settlement = Settlement(
            name=s.name,
            x=s.x,
            y=s.y,
            population=s.population,
            kind=s.kind,
        )
        if s.region in region_map:
            region_map[s.region].settlements.append(settlement)
        else:
            # New settlement in a sim-only region — add to first region as fallback
            if new_world.regions:
                new_world.regions[0].settlements.append(settlement)
    
    return new_world


def render_sim_summary(result: SimResult) -> str:
    """Render a compact summary of the simulation results."""
    lines = []
    s = result.summary
    
    pop_change = s["end_population"] - s["start_population"]
    pop_sign = "+" if pop_change >= 0 else ""
    pop_pct = ((s["end_population"] - s["start_population"]) / max(s["start_population"], 1)) * 100
    
    lines.append("╔══════════════════════════════════════════╗")
    lines.append(f"║  wyrd — Simulation Complete              ║")
    lines.append(f"║  Seed: {s['seed']:<37}║")
    lines.append(f"║  Years: {s['years_simulated']:<6}  Events: {s['events']:<6}       ║")
    lines.append("╠══════════════════════════════════════════╣")
    lines.append(f"║  Population: {s['start_population']:>5} → {s['end_population']:<5}  ({pop_sign}{pop_change:+,} | {pop_pct:+.0f}%)║")
    lines.append(f"║  Settlements: {s['start_settlements']:>3} → {s['end_settlements']:<3}  Abandoned: {s['abandoned']:<3}     ║")
    lines.append("╚══════════════════════════════════════════╝")
    
    return "\n".join(lines)


def render_sim_detailed(result: SimResult, world) -> str:
    """Render a detailed view of the simulation, including events."""
    from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color
    
    lines = []
    s = result.summary
    
    lines.append(f"{ANSI_BOLD}═══ wyrd Simulation: Seed {result.seed} ═══{ANSI_RESET}")
    lines.append(f"{ANSI_DIM}{result.num_years} years simulated{ANSI_RESET}")
    lines.append("")
    
    # Population timeline
    lines.append(f"{ANSI_BOLD}Population Over Time:{ANSI_RESET}")
    for record in result.final_state.population_record:
        if record["year"] == 0 or record["year"] == result.num_years or record["year"] % 20 == 0:
            year_str = f"{record['year']:>4}"
            pop_str = f"{record['total_population']:>5}"
            settle_str = f"{record['num_settlements']:>2}/{record['num_abandoned']:>2}"
            lines.append(f"  {ANSI_DIM}Year {year_str}{ANSI_RESET}  {_color(226)}{pop_str}{ANSI_RESET} souls  {ANSI_DIM}({settle_str} active/abandoned){ANSI_RESET}")
    lines.append("")
    
    # Events by decade
    if result.events:
        lines.append(f"{ANSI_BOLD}Significant Events:{ANSI_RESET}")
        
        event_icons = {
            "plague": "☠", "famine": "🌾", "war": "⚔",
            "discovery": "✦", "prosperity": "↑", "disaster": "🌋",
            "exodus": "→", "founding": "▲", "abandonment": "✗",
            "trade_boom": "💰",
            "religious_tension": "✝", "divine_blessing": "✨",
            "holy_pilgrimage": "🕊", "heresy": "⚠",
            "faction_war": "⚔", "faction_alliance": "⚝",
            "faction_power_shift": "⇈", "faction_collapse": "💀",
            "faction_peace_treaty": "☮",
            # Cataclysm events (Phase 13)
            "earthquake": "💢", "volcanic_eruption": "🌋",
            "great_plague": "☠", "tsunami": "🌊",
            "meteor_strike": "☄", "great_fire": "🔥",
            "magical_cataclysm": "⚡",
            # Economy events (Phase 14)
            "trade_disruption": "💰", "new_trade_route": "💰",
        }
        event_colors = {
            "plague": _color(196), "famine": _color(130), "war": _color(160),
            "discovery": _color(33), "prosperity": _color(28), "disaster": _color(202),
            "exodus": _color(240), "founding": _color(226), "abandonment": _color(240),
            "trade_boom": _color(220),
            "religious_tension": _color(99), "divine_blessing": _color(226),
            "holy_pilgrimage": _color(45), "heresy": _color(196),
            "faction_war": _color(160), "faction_alliance": _color(33),
            "faction_power_shift": _color(99), "faction_collapse": _color(196),
            "faction_peace_treaty": _color(45),
            # Cataclysm events (Phase 13)
            "earthquake": _color(130), "volcanic_eruption": _color(202),
            "great_plague": _color(90), "tsunami": _color(33),
            "meteor_strike": _color(160), "great_fire": _color(196),
            "magical_cataclysm": _color(99),
            # Economy events (Phase 14)
            "trade_disruption": _color(196), "new_trade_route": _color(28),
        }
        
        for ev in result.events[-50:]:  # Show last 50 events max
            icon = event_icons.get(ev.event_type, "·")
            color = event_colors.get(ev.event_type, _color(255))
            lines.append(
                f"  {ANSI_DIM}[{ev.year:>3}]{ANSI_RESET} "
                f"{color}{icon}{ANSI_RESET} "
                f"{ev.description}"
            )
        if len(result.events) > 50:
            lines.append(f"  {ANSI_DIM}... and {len(result.events) - 50} more events{ANSI_RESET}")
        lines.append("")
    
    # World state at end
    lines.append(f"{ANSI_BOLD}World State at Year {result.num_years}:{ANSI_RESET}")
    active = [s for s in result.final_state.settlements.values() if s.is_active]
    abandoned = [s for s in result.final_state.settlements.values() if not s.is_active]
    
    lines.append(f"  {_color(28)}Active Settlements:{ANSI_RESET}")
    for s in sorted(active, key=lambda x: -x.population)[:10]:
        kind_colors = {"hamlet": _color(240), "village": _color(28),
                       "town": _color(33), "city": _color(226)}
        kc = kind_colors.get(s.kind, _color(255))
        health_str = "●" if s.health > 0.7 else "◔" if s.health > 0.4 else "○"
        lines.append(
            f"    {_color(226)}•{ANSI_RESET} {ANSI_BOLD}{s.name}{ANSI_RESET} "
            f"{kc}[{s.kind}]{ANSI_RESET} "
            f"pop {s.population}  "
            f"☕ {s.food_stores:.0f}   "
            f"{health_str} health"
            + (f" {_color(220)}[{s.economy_type or '?'}]{ANSI_RESET}" if s.economy_type else "")
            + (f" {_color(28)}‹{_get_specialization_title(s.economy_type, max(0, state.year - s.economy_since_year))}›{ANSI_RESET}"
               if s.economy_type and s.economy_since_year and _get_specialization_title(s.economy_type, max(0, state.year - s.economy_since_year))
               else "")
        )
    
    if len(active) > 10:
        lines.append(f"    {ANSI_DIM}... and {len(active) - 10} more{ANSI_RESET}")
    
    if abandoned:
        lines.append(f"")
        lines.append(f"  {_color(240)}Abandoned Settlements:{ANSI_RESET}")
        for s in abandoned:
            lines.append(f"    {_color(240)}✗ {s.name} (abandoned){ANSI_RESET}")
    
    # ── Faction Power at End of Simulation ──────────────────────
    if result.final_state.faction_state and len(result.final_state.faction_state) > 0:
        lines.append("")
        lines.append(f"{ANSI_BOLD}Faction Power at Year {result.num_years}:{ANSI_RESET}")
        sorted_factions = sorted(
            result.final_state.faction_state.values(),
            key=lambda fs: fs.power_score,
            reverse=True,
        )
        for fs in sorted_factions:
            status = ""
            if not fs.is_active:
                status = f" {_color(196)}[COLLAPSED]{ANSI_RESET}"
            elif fs.at_war_with:
                status = f" {_color(160)}[WAR]{ANSI_RESET}"
            
            # Power bar
            ps = fs.power_score
            bar_full = min(40, ps // 8)
            bar_empty = 40 - bar_full
            bar = f"{_color(226)}{'█' * bar_full}{ANSI_RESET}{ANSI_DIM}{'░' * bar_empty}{ANSI_RESET}"
            
            lines.append(
                f"  {_color(226)}•{ANSI_RESET} {ANSI_BOLD}{fs.name}{ANSI_RESET}"
                f"{status}  {bar}  {_color(240)}{ps}{ANSI_RESET}"
            )
            if fs.at_war_with:
                enemies = ", ".join(fs.at_war_with[:3])
                lines.append(f"        {_color(160)}⚔ at war with:{ANSI_RESET} {enemies}")
            lines.append(
                f"        {_color(240)}I:{fs.influence} W:{fs.wealth} "
                f"M:{fs.military} S:{fs.stability}{ANSI_RESET}"
            )
    

    # ── Trade Routes at End of Simulation ──────────────────
    if result.final_state.trade_routes and len(result.final_state.trade_routes) > 0:
        lines.append("")
        lines.append(f"{ANSI_BOLD}Trade Routes:{ANSI_RESET}")
        active_routes = [r for r in result.final_state.trade_routes if r.get("is_active", True)]
        if active_routes:
            # Group by settlement for compact display
            route_by_source: dict[str, list] = {}
            for r in active_routes:
                src = r.get("source", "?")
                if src not in route_by_source:
                    route_by_source[src] = []
                route_by_source[src].append(r)
            
            # Show top 5 most connected settlements
            sorted_sources = sorted(route_by_source.keys(),
                                     key=lambda s: -len(route_by_source[s]))[:5]
            for src_name in sorted_sources:
                routes = route_by_source[src_name]
                route_strs = []
                for r in routes:
                    dest = r.get("destination", "?")
                    goods = r.get("goods", "goods")
                    vol = r.get("volume", 0.5)
                    route_strs.append(f"{dest} ({goods}, {vol:.0%})")
                lines.append(
                f"    {_color(226)}•{ANSI_RESET} {ANSI_BOLD}{src_name}{ANSI_RESET} → {', '.join(route_strs)}"
                )
            if sum(len(r) for r in route_by_source.values()) > len(sorted_sources) * 1:
                lines.append(f"    {ANSI_DIM}... and {len(active_routes) - len(sorted_sources)} more route legs{ANSI_RESET}")
        else:
            lines.append(f"    {ANSI_DIM}No active trade routes{ANSI_RESET}")
    
    # Summary footer
    summary = result.summary
    lines.append("")
    lines.append(f"{ANSI_DIM}═══ {summary['end_population']} souls across {summary['end_settlements']} settlements ═══{ANSI_RESET}")
    
    return "\n".join(lines)


def render_sim_summary_from_state(sim_state, world, seed: int) -> str:
    """Render a summary from a loaded SimState."""
    from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color
    
    lines = []
    lines.append(f"{ANSI_BOLD}═══ wyrd #{seed} — Year {sim_state.year} ═══{ANSI_RESET}")
    lines.append("")
    
    active = [s for s in sim_state.settlements.values() if s.is_active]
    abandoned = [s for s in sim_state.settlements.values() if not s.is_active]
    total_pop = sum(s.population for s in active)
    
    lines.append(f"{ANSI_BOLD}Population:{ANSI_RESET} {total_pop}")
    lines.append(f"{ANSI_BOLD}Settlements:{ANSI_RESET} {len(active)} active, {len(abandoned)} abandoned")
    lines.append("")
    
    lines.append(f"{ANSI_BOLD}Settlements:{ANSI_RESET}")
    for s in sorted(active, key=lambda x: -x.population):
        lines.append(f"  {s.name} ({s.region}) — pop {s.population} [{s.kind}]")
    
    return "\n".join(lines)
