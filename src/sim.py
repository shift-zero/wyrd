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
}


# ── Data Models ────────────────────────────────────────────────────────


@dataclass
class SimEvent:
    """An event that occurred during simulation."""
    year: int
    event_type: str
    description: str
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


@dataclass
class SimState:
    """
    Complete simulation state at a point in time.
    
    Stores snapshots of all settlements plus metadata
    about the simulation run.
    """
    year: int = 0
    settlements: dict[str, SettlementSnapshot] = field(default_factory=dict)
    events: list[SimEvent] = field(default_factory=list)
    world_modifiers: list[str] = field(default_factory=list)
    population_record: list[dict] = field(default_factory=list)
    
    @property
    def total_population(self) -> int:
        return sum(s.population for s in self.settlements.values() if s.is_active)
    
    @property
    def num_settlements(self) -> int:
        return sum(1 for s in self.settlements.values() if s.is_active)
    
    @property
    def num_abandoned(self) -> int:
        return sum(1 for s in self.settlements.values() if not s.is_active)


# ── Simulation Helpers ────────────────────────────────────────────────


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
    The settlement draws resources from a radius around it.
    """
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
    """
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
                   year: int, chaos_factor: float = 0.1) -> list[SimEvent]:
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
                events.append(SimEvent(
                    year=year,
                    event_type="plague",
                    description=f"Plague ravages {s.name} in {region_name}, killing {death_toll}.",
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
                events.append(SimEvent(
                    year=year,
                    event_type="famine",
                    description=f"Famine grips {s.name}. {death_toll} perish from hunger.",
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
                events.append(SimEvent(
                    year=year,
                    event_type="war",
                    description=(
                        f"War erupts between {s1.name} ({s1.region}) and "
                        f"{s2.name} ({s2.region}). "
                        f"{actual_s1_loss + actual_s2_loss} total casualties."
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
            
            events.append(SimEvent(
                year=year,
                event_type="founding",
                description=(
                    f"A new settlement, {new_name}, is founded by emigrants "
                    f"from {s.name}. Initial population: {emigrants}."
                ),
                affected_settlements=[s.name, new_name],
                affected_regions=[s.region],
            ))
    
    # Settlement abandonment (when population drops to near zero)
    for s_name in list(state.settlements.keys()):
        s = state.settlements[s_name]
        if not s.is_active:
            continue
        if s.population <= 3 and len(state.settlements) > sum(1 for ss in state.settlements.values() if ss.is_active):
            s.is_active = False
            events.append(SimEvent(
                year=year,
                event_type="abandonment",
                description=f"{s_name} is abandoned. Its few remaining residents scatter.",
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
            events.append(SimEvent(
                year=year,
                event_type="prosperity",
                description=(
                    f"{s.name} experiences a trade boom. "
                    f"Population grows by {boom_pop} as wealth flows in."
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
            )
    
    # Initial population record
    state.population_record.append({
        "year": 0,
        "total_population": state.total_population,
        "num_settlements": state.num_settlements,
        "num_abandoned": 0,
    })
    
    return state


def simulate_years(world: World, state: SimState, num_years: int,
                   seed_offset: int = 0, chaos_factor: float = 0.1,
                   snapshot_interval: int = 0,
                   snapshots_out: list[SimState] | None = None) -> list[SimEvent]:
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
    
    for y in range(1, num_years + 1):
        current_year = start_year + y
        state.year = current_year
        
        year_events = _simulate_tick(world, state, rng, current_year, chaos_factor)
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
                   snapshot_interval: int = 50) -> SimResult:
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
    
    snapshots: list[SimState] = []
    
    # Take initial snapshot
    if snapshot_interval > 0:
        snapshots.append(copy.deepcopy(state))
    
    events = simulate_years(
        world, state, num_years, seed_offset, chaos_factor,
        snapshot_interval=snapshot_interval,
        snapshots_out=snapshots,
    )
    
    # Take final snapshot (only if not already captured by interval)
    if snapshot_interval > 0 and (num_years == 0 or num_years % snapshot_interval != 0):
        snapshots.append(copy.deepcopy(state))
    
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
        }
        event_colors = {
            "plague": _color(196), "famine": _color(130), "war": _color(160),
            "discovery": _color(33), "prosperity": _color(28), "disaster": _color(202),
            "exodus": _color(240), "founding": _color(226), "abandonment": _color(240),
            "trade_boom": _color(220),
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
        )
    
    if len(active) > 10:
        lines.append(f"    {ANSI_DIM}... and {len(active) - 10} more{ANSI_RESET}")
    
    if abandoned:
        lines.append(f"")
        lines.append(f"  {_color(240)}Abandoned Settlements:{ANSI_RESET}")
        for s in abandoned:
            lines.append(f"    {_color(240)}✗ {s.name} (abandoned){ANSI_RESET}")
    
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
