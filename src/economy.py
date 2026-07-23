"""
wyrd — Trade & Economy System (Phase 14).

Settlements don't exist in isolation — they trade. Each settlement gets an
economy type based on local terrain. Trade routes form between complementary
economies, boosting prosperity. Routes can be disrupted by war, cataclysm,
or abandonment, generating unique economic events.

Seed-deterministic: same seed + same parameters → same outcome.
"""

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sim import SettlementSnapshot, SimState

# ── Economy Types ─────────────────────────────────────────────────────

ECONOMY_TYPES = [
    "farming",
    "logging",
    "mining",
    "fishing",
    "trading",
    "pastoral",
]

ECONOMY_ICONS = {
    "farming": "\U0001f33e",  # 🌾
    "logging": "\U0001f332",  # 🌲
    "mining": "\u26cf",       # ⛏
    "fishing": "\U0001f41f",  # 🐟
    "trading": "\U0001f4b0",  # 💰
    "pastoral": "\U0001f404", # 🐄
}

ECONOMY_COLORS = {
    "farming": 220,   # golden wheat
    "logging": 28,    # forest green
    "mining": 130,    # earthen brown
    "fishing": 33,    # ocean blue
    "trading": 226,   # bright gold
    "pastoral": 40,   # fresh green
}

# Complementary economy pairs: which economies trade with which
# (source → list of complementary targets)
COMPLEMENTARY_ECONOMIES = {
    "farming": ["mining", "logging", "trading"],
    "logging": ["farming", "mining", "trading"],
    "mining": ["farming", "logging", "fishing", "trading"],
    "fishing": ["farming", "mining", "trading"],
    "trading": ["farming", "logging", "mining", "fishing", "pastoral"],
    "pastoral": ["farming", "trading", "mining"],
}

TRADE_GOODS = {
    ("farming", "mining"): "grain for ore",
    ("mining", "farming"): "ore for grain",
    ("farming", "logging"): "grain for timber",
    ("logging", "farming"): "timber for grain",
    ("farming", "trading"): "grain for finished goods",
    ("trading", "farming"): "finished goods for grain",
    ("farming", "fishing"): "grain for fish",
    ("fishing", "farming"): "fish for grain",
    ("logging", "mining"): "timber for ore",
    ("mining", "logging"): "ore for timber",
    ("logging", "trading"): "timber for finished goods",
    ("trading", "logging"): "finished goods for timber",
    ("mining", "fishing"): "ore for fish",
    ("fishing", "mining"): "fish for ore",
    ("mining", "trading"): "ore for finished goods",
    ("trading", "mining"): "finished goods for ore",
    ("fishing", "trading"): "fish for finished goods",
    ("trading", "fishing"): "finished goods for fish",
    ("trading", "pastoral"): "finished goods for wool",
    ("pastoral", "trading"): "wool for finished goods",
    ("pastoral", "farming"): "wool for grain",
    ("farming", "pastoral"): "grain for wool",
    ("pastoral", "mining"): "wool for tools",
    ("mining", "pastoral"): "tools for wool",
}


# ── Data Models ───────────────────────────────────────────────────────


@dataclass
class TradeRoute:
    """A trade route connecting two settlements."""
    source: str
    destination: str
    goods: str  # what's being traded
    volume: float  # goods volume (0.0-1.0)
    distance: float  # Euclidean distance between settlements
    is_active: bool = True
    established_year: int = 0

    @property
    def key(self) -> str:
        """Unique key for this route (sorted for dedup)."""
        return "|".join(sorted([self.source, self.destination]))


# ── Economy Assignment ────────────────────────────────────────────────


def _count_terrain_in_radius(
    world,
    cx: int, cy: int,
    radius: int = 5,
) -> dict[str, float]:
    """Count terrain type proportions within a radius around (cx, cy).

    Returns dict mapping terrain type → fraction (0.0-1.0) of cells.
    """
    counts: dict[str, int] = {}
    total = 0

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if not (0 <= x < world.width and 0 <= y < world.height):
                continue
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > radius:
                continue
            t = world.terrain[y][x]
            counts[t] = counts.get(t, 0) + 1
            total += 1

    if total == 0:
        return {}

    return {t: c / total for t, c in counts.items()}


def _is_coastal(world, cx: int, cy: int, radius: int = 5) -> bool:
    """Check if the location is near deep_water or shallow."""
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < world.width and 0 <= y < world.height:
                if world.terrain[y][x] in ("deep_water", "shallow"):
                    return True
    return False


def _assign_economy(
    world,
    settlement: "SettlementSnapshot",  # noqa: F821
    rng: random.Random,
) -> str:
    """Assign an economy type based on local terrain and settlement characteristics.

    Precedence (first match wins):
    1. trading — size-based (town or city, 800+ pop)
    2. fishing — coastal settlements
    3. mining — hills/mountains terrain
    4. logging — heavy forest terrain
    5. farming — grassland dominant
    6. pastoral — default for non-matching
    """
    proportions = _count_terrain_in_radius(world, settlement.x, settlement.y)

    # 1. Trading hub — large settlements become trading posts
    if settlement.population >= 800:
        return "trading"

    # 2. Fishing — coastal settlements
    if _is_coastal(world, settlement.x, settlement.y):
        if proportions.get("shallow", 0) + proportions.get("deep_water", 0) > 0.25:
            return "fishing"

    # 3. Mining — hills/mountains dominant
    mining_terrain = proportions.get("mountains", 0) + proportions.get("hills", 0)
    if mining_terrain > 0.25:
        return "mining"

    # 4. Logging — forest dominant
    if proportions.get("forest", 0) > 0.30:
        return "logging"

    # 5. Farming — grassland dominant
    if proportions.get("grass", 0) > 0.25:
        return "farming"

    # 6. Pastoral — default for hills/grass mixes
    if proportions.get("hills", 0) + proportions.get("grass", 0) > 0.20:
        return "pastoral"

    # Fallback: random from remaining types
    return rng.choice(["farming", "pastoral", "fishing"])


def assign_economies(
    world,
    state: "SimState",  # noqa: F821
    rng: random.Random,
) -> None:
    """Assign economy types to all active settlements."""
    for s in state.settlements.values():
        if s.is_active:
            s.economy_type = _assign_economy(world, s, rng)


# ── Trade Route Generation ────────────────────────────────────────────


def _distance_between(
    state: "SimState",  # noqa: F821
    name_a: str,
    name_b: str,
) -> float:
    """Euclidean distance between two settlements."""
    s_a = state.settlements.get(name_a)
    s_b = state.settlements.get(name_b)
    if not s_a or not s_b:
        return float("inf")
    return math.sqrt((s_a.x - s_b.x) ** 2 + (s_a.y - s_b.y) ** 2)


def _generate_trade_routes(
    state: "SimState",  # noqa: F821
    rng: random.Random,
    year: int,
    max_routes_per_settlement: int = 3,
    max_distance: float = 30.0,
) -> list[TradeRoute]:
    """Generate trade routes between settlements with complementary economies.

    For each active settlement, looks for complementary-economy partners within
    max_distance and creates trade routes.
    """
    routes: list[TradeRoute] = []
    route_keys: set[str] = set()

    active = {name: s for name, s in state.settlements.items() if s.is_active}
    # Sort by population (larger first) so bigger settlements attract more routes
    sorted_names = sorted(active.keys(), key=lambda n: -active[n].population)

    for name in sorted_names:
        s = active[name]
        if not s.economy_type:
            continue

        complementary = COMPLEMENTARY_ECONOMIES.get(s.economy_type, [])
        routes_from_here = 0

        # Find partners among other active settlements
        candidates = []
        for other_name, other_s in active.items():
            if other_name == name:
                continue
            if other_s.economy_type in complementary:
                dist = _distance_between(state, name, other_name)
                if dist <= max_distance:
                    # Filter out really isolated settlements
                    candidates.append((other_name, dist))

        # Sort by distance (closer = more likely to trade)
        candidates.sort(key=lambda c: c[1])

        for other_name, dist in candidates:
            if routes_from_here >= max_routes_per_settlement:
                break

            other_s = active[other_name]
            key = "|".join(sorted([name, other_name]))
            if key in route_keys:
                continue

            # Determine trade goods
            goods = TRADE_GOODS.get(
                (s.economy_type, other_s.economy_type),
                f"local goods"
            )

            # Volume decreases with distance
            volume = max(0.1, min(1.0, 1.0 - (dist / max_distance) * 0.5))
            # Add random variation
            volume = max(0.05, min(1.0, volume * rng.uniform(0.8, 1.2)))

            route = TradeRoute(
                source=name,
                destination=other_name,
                goods=goods,
                volume=volume,
                distance=dist,
                is_active=True,
                established_year=year,
            )
            routes.append(route)
            route_keys.add(key)
            routes_from_here += 1

    return routes


# ── Trade Effects ─────────────────────────────────────────────────────


def _apply_trade_effects(
    state: "SimState",  # noqa: F821
    routes: list[TradeRoute],
) -> None:
    """Apply prosperity modifiers from active trade routes."""
    # Calculate total trade volume for each settlement
    trade_volume: dict[str, float] = {}
    for route in routes:
        if not route.is_active:
            continue
        trade_volume[route.source] = (
            trade_volume.get(route.source, 0) + route.volume
        )
        trade_volume[route.destination] = (
            trade_volume.get(route.destination, 0) + route.volume
        )

    # Apply prosperity boost proportional to trade volume
    for s_name, s in state.settlements.items():
        if not s.is_active:
            continue
        vol = trade_volume.get(s_name, 0.0)
        if vol > 0:
            # Each unit of volume adds up to 0.02 prosperity per year
            boost = max(0.0, min(0.15, vol * 0.015))
            s.prosperity = min(1.0, s.prosperity + boost)


# ── Route Disruption ──────────────────────────────────────────────────


def _check_route_disruptions(
    state: "SimState",  # noqa: F821
    routes: list[TradeRoute],
    rng: random.Random,
    year: int,
) -> list[tuple[str, str, int]]:
    """Check if any trade routes need to be disrupted.

    Returns list of (reason, description, severity) tuples for affected routes.
    - reason: "war", "cataclysm", "abandonment", "economic_collapse"
    """
    disruptions: list[tuple[str, str, int]] = []

    # Check which settlements are still active
    active_names = {
        name for name, s in state.settlements.items()
        if s.is_active
    }

    for route in routes:
        if not route.is_active:
            continue

        # 1. Settlement abandoned or destroyed
        if route.source not in active_names:
            # Boost remaining settlement as goods redirect
            dest = state.settlements.get(route.destination)
            if dest and dest.is_active:
                dest.prosperity = min(1.0, dest.prosperity + 0.02)
            disruptions.append(
                ("abandonment", f"{route.source} is gone — trade route with {route.destination} collapses", 2)
            )
            route.is_active = False
            continue

        if route.destination not in active_names:
            src = state.settlements.get(route.source)
            if src and src.is_active:
                src.prosperity = min(1.0, src.prosperity + 0.02)
            disruptions.append(
                ("abandonment", f"{route.destination} is gone — trade route with {route.source} collapses", 2)
            )
            route.is_active = False
            continue

        # 2. Check for prosperity collapse (settlement devastated)
        src = state.settlements.get(route.source)
        dest = state.settlements.get(route.destination)

        if src and src.prosperity < 0.15 and rng.random() < 0.3:
            disruptions.append(
                ("economic_collapse",
                 f"Economic collapse in {route.source} — trade with {route.destination} stops",
                 1)
            )
            route.is_active = False
            continue

        if dest and dest.prosperity < 0.15 and rng.random() < 0.3:
            disruptions.append(
                ("economic_collapse",
                 f"Economic collapse in {route.destination} — trade with {route.source} stops",
                 1)
            )
            route.is_active = False
            continue

    return disruptions


# ── New Route Discovery ───────────────────────────────────────────────


def _discover_new_routes(
    state: "SimState",  # noqa: F821
    existing_routes: list[TradeRoute],
    rng: random.Random,
    year: int,
    chaos_factor: float = 0.1,
) -> list[TradeRoute]:
    """Discover new trade routes (rare, ~1% per existing route per year).

    Returns list of new routes.
    """
    new_routes: list[TradeRoute] = []

    # Count existing routes per settlement
    existing_count: dict[str, int] = {}
    for route in existing_routes:
        if route.is_active:
            existing_count[route.source] = existing_count.get(route.source, 0) + 1
            existing_count[route.destination] = existing_count.get(route.destination, 0) + 1

    active = {name: s for name, s in state.settlements.items() if s.is_active}

    # For each settlement with room for more routes, try to find a new partner
    for name, s in active.items():
        current = existing_count.get(name, 0)
        if current >= 3:
            continue  # Already at max routes
        if not s.economy_type:
            continue

        complementary = COMPLEMENTARY_ECONOMIES.get(s.economy_type, [])
        for other_name, other_s in active.items():
            if other_name == name:
                continue
            if other_s.economy_type not in complementary:
                continue

            # Check this pair doesn't already have a route
            key = "|".join(sorted([name, other_name]))
            already_exists = any(
                r.is_active and r.key == key for r in existing_routes
            )
            if already_exists:
                continue

            existing_other = existing_count.get(other_name, 0)
            if existing_other >= 3:
                continue

            # Very rare: ~0.5% chance per candidate pair
            if rng.random() < 0.005 * chaos_factor:
                dist = _distance_between(state, name, other_name)
                goods = TRADE_GOODS.get(
                    (s.economy_type, other_s.economy_type),
                    "local goods"
                )
                volume = max(0.1, min(1.0, 1.0 - (dist / 30.0) * 0.5))
                volume *= rng.uniform(0.8, 1.2)

                new_route = TradeRoute(
                    source=name,
                    destination=other_name,
                    goods=goods,
                    volume=volume,
                    distance=dist,
                    is_active=True,
                    established_year=year,
                )
                new_routes.append(new_route)
                break  # One new route per settlement per tick

    return new_routes


# ── Main Economy Tick ─────────────────────────────────────────────────


def _simulate_economy_tick(
    world,
    state: "SimState",  # noqa: F821
    rng: random.Random,
    year: int,
    routes: list[TradeRoute],
    chaos_factor: float = 0.1,
) -> tuple[list[TradeRoute], list[tuple[str, str, str]]]:
    """Simulate one year of economic activity.

    Args:
        world: The world object (used for terrain checks)
        state: Current simulation state
        rng: Seeded RNG
        year: Current year
        routes: Current list of trade routes (mutated in-place for disruptions)
        chaos_factor: Randomness multiplier

    Returns:
        (updated_routes, events) where events is list of
        (event_type, description, event_icon) tuples for the sim event log.
    """
    events: list[tuple[str, str, str]] = []

    # 1. Check for route disruptions
    disruptions = _check_route_disruptions(state, routes, rng, year)
    for reason, desc, _ in disruptions:
        events.append(("trade_disruption", desc, "💰"))

    # 2. Apply trade prosperity effects to active routes
    _apply_trade_effects(state, routes)

    # 3. Discover new routes (rare)
    new_routes = _discover_new_routes(state, routes, rng, year, chaos_factor)
    for nr in new_routes:
        routes.append(nr)
        events.append(
            ("new_trade_route",
             f"Trade route established between {nr.source} and {nr.destination} — {nr.goods}",
             "💰")
        )

    # 4. Random trade boom events (rare)
    if rng.random() < 0.005 * chaos_factor:
        active = [s for s in state.settlements.values() if s.is_active and s.economy_type]
        if active:
            boom_settlement = rng.choice(active)
            boom_settlement.prosperity = min(1.0, boom_settlement.prosperity + 0.1)
            # Boost connected settlements too
            for route in routes:
                if not route.is_active:
                    continue
                if route.source == boom_settlement.name:
                    other = state.settlements.get(route.destination)
                    if other and other.is_active:
                        other.prosperity = min(1.0, other.prosperity + 0.05)
                elif route.destination == boom_settlement.name:
                    other = state.settlements.get(route.source)
                    if other and other.is_active:
                        other.prosperity = min(1.0, other.prosperity + 0.05)
            events.append(
                ("trade_boom",
                 f"A trade boom in {boom_settlement.name} brings unprecedented wealth to the region!",
                 "💰")
            )

    return routes, events


# ── Serialization Helpers ─────────────────────────────────────────────


def trade_route_to_dict(route: TradeRoute) -> dict:
    """Convert a TradeRoute to a dict for serialization."""
    return {
        "source": route.source,
        "destination": route.destination,
        "goods": route.goods,
        "volume": route.volume,
        "distance": route.distance,
        "is_active": route.is_active,
        "established_year": route.established_year,
    }


def trade_route_from_dict(d: dict) -> TradeRoute:
    """Convert a dict back to a TradeRoute."""
    return TradeRoute(
        source=d["source"],
        destination=d["destination"],
        goods=d.get("goods", "local goods"),
        volume=d.get("volume", 0.5),
        distance=d.get("distance", 10.0),
        is_active=d.get("is_active", True),
        established_year=d.get("established_year", 0),
    )


def reconstruct_routes(route_dicts: list[dict]) -> list[TradeRoute]:
    """Convert stored dict routes back to TradeRoute objects."""
    return [trade_route_from_dict(r) for r in route_dicts]


def serialize_routes(routes: list[TradeRoute]) -> list[dict]:
    """Convert TradeRoute objects to serializable dicts."""
    return [trade_route_to_dict(r) for r in routes]
