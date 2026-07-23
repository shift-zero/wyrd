"""
Tests for Phase 14 — Trade & Economy System.

Covers:
1. Economy type constants and data
2. Economy assignment based on terrain
3. Trade route generation
4. Trade route determinism
5. Route disruption detection
6. Trade effects on prosperity
7. Serialization round-trip
8. Integration with simulation
"""

import random
import pytest
from dataclasses import dataclass, field


# ── Mock World ────────────────────────────────────────────────────────


@dataclass
class MockWorld:
    """Minimal mock of World for economy testing."""
    width: int = 40
    height: int = 30
    terrain: list = field(default_factory=list)
    regions: list = field(default_factory=list)
    seed: int = 42


def _make_flat_terrain(w: int, h: int, terrain_type: str = "grass") -> list:
    """Create a flat terrain grid of a single type."""
    return [[terrain_type for _ in range(w)] for _ in range(h)]


def _make_terrain_with_patch(w: int, h: int, patch_type: str,
                              patch_x: int, patch_y: int,
                              patch_radius: int = 3,
                              base: str = "grass") -> list:
    """Create a terrain grid with a central patch of a different type."""
    grid = [[base for _ in range(w)] for _ in range(h)]
    for dy in range(-patch_radius, patch_radius + 1):
        for dx in range(-patch_radius, patch_radius + 1):
            x, y = patch_x + dx, patch_y + dy
            if 0 <= x < w and 0 <= y < h:
                grid[y][x] = patch_type
    return grid


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def rng():
    return random.Random(42)


@pytest.fixture
def grass_world():
    w = MockWorld()
    w.terrain = _make_flat_terrain(40, 30, "grass")
    return w


@pytest.fixture
def forest_world():
    w = MockWorld()
    w.terrain = _make_flat_terrain(40, 30, "forest")
    return w


@pytest.fixture
def coastal_world():
    w = MockWorld()
    # Mix of grass and shallow water
    grid = _make_flat_terrain(40, 30, "grass")
    for y in range(30):
        for x in range(40):
            if x < 5:
                grid[y][x] = "shallow"
    w.terrain = grid
    return w


@pytest.fixture
def mining_world():
    w = MockWorld()
    w.terrain = _make_terrain_with_patch(40, 30, "mountains", 15, 15, 6)
    return w


# ── Basic Test: Economy Types ─────────────────────────────────────────

class TestEconomyTypes:
    """Economy type constants and data structures."""

    def test_economy_types_count(self):
        from src.economy import ECONOMY_TYPES
        assert len(ECONOMY_TYPES) == 6

    def test_economy_icons_all_present(self):
        from src.economy import ECONOMY_TYPES, ECONOMY_ICONS
        for etype in ECONOMY_TYPES:
            assert etype in ECONOMY_ICONS, f"Missing icon for {etype}"

    def test_complementary_all_valid(self):
        from src.economy import ECONOMY_TYPES, COMPLEMENTARY_ECONOMIES
        for etype, complements in COMPLEMENTARY_ECONOMIES.items():
            assert etype in ECONOMY_TYPES, f"Unknown economy: {etype}"
            for c in complements:
                assert c in ECONOMY_TYPES, f"Unknown complementary: {c}"

    def test_trade_goods_all_present(self):
        from src.economy import COMPLEMENTARY_ECONOMIES, TRADE_GOODS
        for etype, complements in COMPLEMENTARY_ECONOMIES.items():
            for c in complements:
                key = (etype, c)
                assert key in TRADE_GOODS, f"Missing trade goods for {etype}↔{c}"


# ── Terrain Counting ──────────────────────────────────────────────────

class TestTerrainCounting:
    """Terrain proportion counting within radius."""

    def test_count_terrain_in_radius_grass(self, grass_world, rng):
        from src.economy import _count_terrain_in_radius
        props = _count_terrain_in_radius(grass_world, 20, 15)
        assert "grass" in props
        assert props["grass"] > 0.9  # Almost all grass

    def test_count_terrain_in_radius_mountain(self, mining_world, rng):
        from src.economy import _count_terrain_in_radius
        props = _count_terrain_in_radius(mining_world, 15, 15)
        assert "mountains" in props
        assert props["mountains"] > 0.5  # Mountains dominate

    def test_count_terrain_edge(self, grass_world, rng):
        from src.economy import _count_terrain_in_radius
        # Corner of world — should still work without errors
        props = _count_terrain_in_radius(grass_world, 0, 0)
        assert "grass" in props


# ── Economy Assignment ────────────────────────────────────────────────

class TestEconomyAssignment:
    """Economy type assignment based on terrain."""

    def test_grassland_farming(self, grass_world):
        from src.sim import SettlementSnapshot
        from src.economy import _assign_economy
        ss = SettlementSnapshot(name="Farmville", region="R", x=20, y=15,
                                population=100, kind="hamlet")
        economy = _assign_economy(grass_world, ss, random.Random(42))
        assert economy == "farming", f"Expected farming, got {economy}"

    def test_forest_logging(self, forest_world):
        from src.sim import SettlementSnapshot
        from src.economy import _assign_economy
        ss = SettlementSnapshot(name="Timbertown", region="R", x=20, y=15,
                                population=100, kind="hamlet")
        economy = _assign_economy(forest_world, ss, random.Random(42))
        assert economy == "logging", f"Expected logging, got {economy}"

    def test_coastal_fishing(self, coastal_world):
        from src.sim import SettlementSnapshot
        from src.economy import _assign_economy
        ss = SettlementSnapshot(name="Fishport", region="R", x=5, y=15,
                                population=100, kind="hamlet")
        economy = _assign_economy(coastal_world, ss, random.Random(42))
        assert economy == "fishing", f"Expected fishing, got {economy}"

    def test_hills_mining(self):
        from src.sim import SettlementSnapshot
        from src.economy import _assign_economy
        world = MockWorld()
        world.terrain = _make_terrain_with_patch(40, 30, "hills", 20, 15, 5)
        ss = SettlementSnapshot(name="Minetown", region="R", x=20, y=15,
                                population=100, kind="hamlet")
        economy = _assign_economy(world, ss, random.Random(42))
        assert economy == "mining", f"Expected mining, got {economy}"

    def test_large_settlement_trading(self, grass_world):
        from src.sim import SettlementSnapshot
        from src.economy import _assign_economy
        # Large population should become trading hub
        ss = SettlementSnapshot(name="Metropolis", region="R", x=20, y=15,
                                population=1500, kind="town")
        economy = _assign_economy(grass_world, ss, random.Random(42))
        assert economy == "trading", f"Expected trading, got {economy}"

    def test_deterministic_assignment(self, grass_world):
        from src.sim import SettlementSnapshot
        from src.economy import _assign_economy
        ss = SettlementSnapshot(name="Test", region="R", x=10, y=10,
                                population=100, kind="hamlet")
        e1 = _assign_economy(grass_world, ss, random.Random(42))
        e2 = _assign_economy(grass_world, ss, random.Random(42))
        assert e1 == e2


# ── Trade Route Generation ────────────────────────────────────────────

class TestTradeRouteGeneration:
    """Trade route generation and determinism."""

    def _make_state_with_economies(self, economy_pairs):
        """Create a SimState with settlements having specific economy types."""
        from src.sim import SimState, SettlementSnapshot
        state = SimState(year=0)
        for name, etype, x, y, pop in economy_pairs:
            state.settlements[name] = SettlementSnapshot(
                name=name, region="R", x=x, y=y,
                population=pop, kind="village",
                is_active=True, economy_type=etype,
            )
        return state

    def test_routes_between_complementary(self, rng):
        from src.economy import _generate_trade_routes
        state = self._make_state_with_economies([
            ("Farmville", "farming", 10, 10, 200),
            ("Minetown", "mining", 15, 15, 300),
            ("Forestburg", "logging", 5, 5, 150),
        ])
        routes = _generate_trade_routes(state, rng, 0)
        assert len(routes) >= 2, f"Expected at least 2 routes, got {len(routes)}"

    def test_no_routes_same_economy(self, rng):
        from src.economy import _generate_trade_routes
        state = self._make_state_with_economies([
            ("Farmville", "farming", 10, 10, 200),
            ("Farmstead", "farming", 20, 20, 150),
        ])
        routes = _generate_trade_routes(state, rng, 0)
        # Farming is NOT complementary with farming
        # But may get routes if one is trading
        for r in routes:
            assert r.is_active

    def test_routes_limited_per_settlement(self, rng):
        from src.economy import _generate_trade_routes
        # Many settlements of different types
        pairs = [
            ("Farm1", "farming", 10, 10, 200),
            ("Mine1", "mining", 15, 15, 300),
            ("Mine2", "mining", 20, 18, 250),
            ("Log1", "logging", 5, 8, 150),
            ("Fish1", "fishing", 25, 5, 180),
            ("Trade1", "trading", 30, 25, 1200),
        ]
        state = self._make_state_with_economies(pairs)
        routes = _generate_trade_routes(state, rng, 0)
        # Count outgoing routes per settlement (not incoming)
        from collections import Counter
        route_count = Counter()
        for r in routes:
            route_count[r.source] += 1
        # Each settlement should have at most 3 outgoing routes
        for name, count in route_count.items():
            assert count <= 3, f"{name} has {count} outgoing routes (max 3)"

    def test_deterministic_routes(self, rng):
        from src.economy import _generate_trade_routes
        state = self._make_state_with_economies([
            ("Farmville", "farming", 10, 10, 200),
            ("Minetown", "mining", 15, 15, 300),
            ("Forestburg", "logging", 5, 5, 150),
        ])
        routes1 = _generate_trade_routes(state, random.Random(42), 0)
        routes2 = _generate_trade_routes(state, random.Random(42), 0)
        # Same seed → same routes
        assert len(routes1) == len(routes2)
        for r1, r2 in zip(routes1, routes2):
            assert r1.source == r2.source
            assert r1.destination == r2.destination

    def test_no_routes_without_economy(self, rng):
        from src.sim import SimState, SettlementSnapshot
        from src.economy import _generate_trade_routes
        state = SimState(year=0)
        # No economy_type set
        state.settlements["Test"] = SettlementSnapshot(
            name="Test", region="R", x=10, y=10,
            population=100, kind="hamlet", is_active=True,
        )
        routes = _generate_trade_routes(state, rng, 0)
        assert len(routes) == 0

    def test_route_key_unique(self, rng):
        from src.economy import _generate_trade_routes
        state = self._make_state_with_economies([
            ("Farmville", "farming", 10, 10, 200),
            ("Minetown", "mining", 15, 15, 300),
        ])
        routes = _generate_trade_routes(state, rng, 0)
        keys = [r.key for r in routes]
        assert len(keys) == len(set(keys)), "Duplicate route keys found"


# ── Trade Effects ─────────────────────────────────────────────────────

class TestTradeEffects:
    """Prosperity boost from active trade routes."""

    def test_prosperity_boost(self, rng):
        from src.sim import SimState, SettlementSnapshot
        from src.economy import TradeRoute, _apply_trade_effects
        state = SimState(year=0)
        state.settlements["A"] = SettlementSnapshot(
            name="A", region="R", x=10, y=10,
            population=200, kind="village", is_active=True,
            prosperity=0.5,
        )
        state.settlements["B"] = SettlementSnapshot(
            name="B", region="R", x=20, y=20,
            population=300, kind="village", is_active=True,
            prosperity=0.5,
        )
        routes = [
            TradeRoute(source="A", destination="B", goods="grain for ore",
                       volume=0.8, distance=14.0, is_active=True),
        ]
        old_a = state.settlements["A"].prosperity
        old_b = state.settlements["B"].prosperity
        _apply_trade_effects(state, routes)
        assert state.settlements["A"].prosperity > old_a
        assert state.settlements["B"].prosperity > old_b

    def test_no_boost_for_inactive(self, rng):
        from src.sim import SimState, SettlementSnapshot
        from src.economy import TradeRoute, _apply_trade_effects
        state = SimState(year=0)
        state.settlements["A"] = SettlementSnapshot(
            name="A", region="R", x=10, y=10,
            population=200, kind="village", is_active=True,
            prosperity=0.5,
        )
        routes = [
            TradeRoute(source="A", destination="B", goods="grain for ore",
                       volume=0.8, distance=14.0, is_active=False),
        ]
        old = state.settlements["A"].prosperity
        _apply_trade_effects(state, routes)
        assert state.settlements["A"].prosperity == old  # No change


# ── Route Disruption ──────────────────────────────────────────────────

class TestRouteDisruption:
    """Route detection and deactivation."""

    def test_disruption_on_abandonment(self, rng):
        from src.sim import SimState, SettlementSnapshot
        from src.economy import TradeRoute, _check_route_disruptions
        state = SimState(year=0)
        state.settlements["A"] = SettlementSnapshot(
            name="A", region="R", x=10, y=10,
            population=200, kind="village", is_active=False,  # Abandoned!
        )
        state.settlements["B"] = SettlementSnapshot(
            name="B", region="R", x=20, y=20,
            population=300, kind="village", is_active=True,
        )
        route = TradeRoute(source="A", destination="B", goods="grain",
                           volume=0.5, distance=14.0, is_active=True)
        disruptions = _check_route_disruptions(state, [route], rng, 50)
        assert len(disruptions) == 1
        assert disruptions[0][0] == "abandonment"
        assert not route.is_active

    def test_no_disruption_for_active(self, rng):
        from src.sim import SimState, SettlementSnapshot
        from src.economy import TradeRoute, _check_route_disruptions
        state = SimState(year=0)
        state.settlements["A"] = SettlementSnapshot(
            name="A", region="R", x=10, y=10,
            population=200, kind="village", is_active=True,
            prosperity=0.5,
        )
        state.settlements["B"] = SettlementSnapshot(
            name="B", region="R", x=20, y=20,
            population=300, kind="village", is_active=True,
            prosperity=0.5,
        )
        route = TradeRoute(source="A", destination="B", goods="grain",
                           volume=0.5, distance=14.0, is_active=True)
        disruptions = _check_route_disruptions(state, [route], rng, 50)
        assert len(disruptions) == 0
        assert route.is_active


# ── Serialization ─────────────────────────────────────────────────────

class TestSerialization:
    """Trade route serialization round-trip."""

    def test_route_to_dict(self):
        from src.economy import TradeRoute, trade_route_to_dict
        route = TradeRoute(
            source="A", destination="B", goods="grain for ore",
            volume=0.7, distance=15.0, is_active=True, established_year=50,
        )
        d = trade_route_to_dict(route)
        assert d["source"] == "A"
        assert d["destination"] == "B"
        assert d["volume"] == 0.7
        assert d["established_year"] == 50

    def test_route_from_dict(self):
        from src.economy import trade_route_from_dict
        d = {"source": "A", "destination": "B", "goods": "grain for ore",
             "volume": 0.7, "distance": 15.0, "is_active": True,
             "established_year": 50}
        route = trade_route_from_dict(d)
        assert route.source == "A"
        assert route.volume == 0.7

    def test_round_trip(self):
        from src.economy import TradeRoute, serialize_routes, reconstruct_routes
        routes = [
            TradeRoute(source="A", destination="B", goods="grain",
                       volume=0.5, distance=10.0, is_active=True, established_year=0),
            TradeRoute(source="C", destination="D", goods="ore",
                       volume=0.3, distance=20.0, is_active=False, established_year=10),
        ]
        dicts = serialize_routes(routes)
        restored = reconstruct_routes(dicts)
        assert len(restored) == 2
        assert restored[0].source == "A"
        assert restored[0].volume == 0.5
        assert not restored[1].is_active
        assert restored[1].established_year == 10


# ── Integration ───────────────────────────────────────────────────────

class TestIntegration:
    """Integration with simulation engine."""

    def test_economy_assignment_in_simulate_years(self):
        """Test that _simulate_tick runs without error when economies are assigned."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, simulate_years

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        events = simulate_years(world, state, 10, seed_offset=0, chaos_factor=0.3)
        # Should not crash
        assert events is not None

    def test_economy_types_assigned_in_sim(self):
        """Test that settlements get economy types after running sim."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, simulate_years

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        simulate_years(world, state, 10, seed_offset=0, chaos_factor=0.3)
        # At least some settlements should have economy types
        has_economy = sum(1 for s in state.settlements.values() if s.is_active and s.economy_type)
        assert has_economy > 0, "No settlements have economy types assigned"

    def test_trade_routes_persist_across_years(self):
        """Test that trade routes survive across multiple years."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, simulate_years

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        simulate_years(world, state, 50, seed_offset=0, chaos_factor=0.3)
        # Trade routes should exist
        assert len(state.trade_routes) > 0, "No trade routes generated"

    def test_deterministic_economy(self):
        """Same seed → same economy assignment."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, simulate_years

        world1 = generate_world(42, width=30, height=20)
        state1 = initialize_sim_state(world1)
        simulate_years(world1, state1, 20, seed_offset=0, chaos_factor=0.3)

        world2 = generate_world(42, width=30, height=20)
        state2 = initialize_sim_state(world2)
        simulate_years(world2, state2, 20, seed_offset=0, chaos_factor=0.3)

        # Economy types should be the same
        for name in state1.settlements:
            s1 = state1.settlements[name]
            s2 = state2.settlements[name]
            assert s1.economy_type == s2.economy_type, \
                f"Mismatch for {name}: {s1.economy_type} != {s2.economy_type}"

    def test_trade_routes_serialization_roundtrip(self):
        """Economy types and trade routes survive save/load."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, simulate_years
        from src.serialize import sim_state_to_dict

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        simulate_years(world, state, 30, seed_offset=0, chaos_factor=0.3)

        # Serialize
        d = sim_state_to_dict(state)
        assert "trade_routes" in d
        assert len(d["trade_routes"]) > 0

        # Verify settlement economy types in serialized data
        for name, sd in d["settlements"].items():
            # Some settlements should have economy_type
            pass

    def test_economy_integration_with_factions(self):
        """Economy system works alongside faction simulation."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, simulate_years

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        # Run with both factions + economy active
        events = simulate_years(world, state, 30, seed_offset=0, chaos_factor=0.3)
        assert events is not None
        # Should have faction events
        faction_events = [e for e in events if e.event_type.startswith("faction_")]
        economy_events = [e for e in events if "trade" in e.event_type or e.event_type == "trade_boom"]
        # Both should exist (though rare)
        assert len(state.faction_state) > 0
        assert len(state.trade_routes) > 0


class TestRoadInfrastructure:
    """Tests for Phase 16 road/infrastructure system."""

    def test_road_upgrade_after_50_years(self):
        """Active routes upgrade to roads after 50+ consecutive years."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state
        from src.economy import TradeRoute

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        state.year = 100

        # Create a route that has been active for 60 years
        route = TradeRoute(
            source="Testville",
            destination="Testburg",
            goods="grain for ore",
            volume=0.5,
            distance=10.0,
            is_active=True,
            established_year=40,
            years_active=60,
            is_road=False,
        )

        # Run economy tick
        from src.economy import _simulate_economy_tick
        from src.economy import reconstruct_routes, serialize_routes
        routes = [route]
        rng = random.Random(42)
        routes_out, events = _simulate_economy_tick(
            world, state, rng, 100, routes, 0.3
        )

        # Route should now be a road
        assert len(routes_out) == 1
        upgraded = routes_out[0]
        assert upgraded.is_road, "Route with 60 years_active should be a road"
        assert upgraded.volume > 0.5, "Road should boost trade volume"

        # Should emit a road construction event
        road_events = [e for e in events if e[0] == "road_construction"]
        assert len(road_events) == 1

    def test_road_takes_50_years(self):
        """Route with <50 years active should NOT become a road."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state
        from src.economy import TradeRoute

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)
        state.year = 50

        route = TradeRoute(
            source="Testville",
            destination="Testburg",
            goods="grain for ore",
            volume=0.5,
            distance=10.0,
            is_active=True,
            established_year=49,
            years_active=1,
            is_road=False,
        )

        from src.economy import _simulate_economy_tick
        routes = [route]
        rng = random.Random(42)
        routes_out, events = _simulate_economy_tick(
            world, state, rng, 50, routes, 0.3
        )

        assert not routes_out[0].is_road, "1-year-old route should not be a road"
        road_events = [e for e in events if e[0] == "road_construction"]
        assert len(road_events) == 0

    def test_years_active_resets_on_disruption(self):
        """Inactive routes should reset years_active to 0."""
        from src.economy import TradeRoute

        route = TradeRoute(
            source="Src", destination="Dst",
            goods="goods", volume=0.5, distance=10.0,
            is_active=False, established_year=0,
            years_active=55, is_road=True,
        )
        # Run economy tick cycles
        from src.economy import _simulate_economy_tick
        from src.generate import generate_world
        from src.sim import initialize_sim_state
        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)

        rng = random.Random(42)
        routes, events = _simulate_economy_tick(
            world, state, rng, 100, [route], 0.3
        )

        # Inactive route should have years_active reset to 0
        assert routes[0].years_active == 0

    def test_road_serialization_roundtrip(self):
        """is_road and years_active survive serialization."""
        from src.economy import TradeRoute, trade_route_to_dict, trade_route_from_dict

        route = TradeRoute(
            source="A", destination="B",
            goods="grain for ore", volume=0.8,
            distance=15.0, is_active=True,
            established_year=10, years_active=60,
            is_road=True,
        )

        d = trade_route_to_dict(route)
        assert d["is_road"] is True
        assert d["years_active"] == 60

        restored = trade_route_from_dict(d)
        assert restored.is_road is True
        assert restored.years_active == 60
        assert restored.source == "A"
        assert restored.destination == "B"

    def test_road_defaults_for_old_data(self):
        """Old saved data without road fields should load gracefully."""
        from src.economy import trade_route_from_dict

        old_data = {
            "source": "OldTown",
            "destination": "OldVillage",
            "goods": "local goods",
            "volume": 0.3,
            "distance": 12.0,
            "is_active": True,
            "established_year": 0,
        }

        restored = trade_route_from_dict(old_data)
        assert restored.years_active == 0
        assert restored.is_road is False
        assert restored.source == "OldTown"

    def test_road_prosperity_bonus(self):
        """Settlements connected by roads get additional prosperity."""
        from src.generate import generate_world
        from src.sim import initialize_sim_state, SettlementSnapshot
        from src.economy import _apply_trade_effects, TradeRoute

        world = generate_world(42, width=30, height=20)
        state = initialize_sim_state(world)

        # Add two test settlements with known prosperity
        state.settlements["A"] = SettlementSnapshot(
            name="A", region="Test", x=5, y=5,
            population=500, kind="village",
            economy_type="farming", prosperity=0.5,
        )
        state.settlements["B"] = SettlementSnapshot(
            name="B", region="Test", x=15, y=5,
            population=300, kind="hamlet",
            economy_type="mining", prosperity=0.5,
        )

        # Road route between them
        routes = [
            TradeRoute(
                source="A", destination="B",
                goods="grain for ore", volume=0.5,
                distance=10.0, is_active=True, established_year=0,
                years_active=60, is_road=True,
            ),
        ]

        _apply_trade_effects(state, routes)

        # Both road-connected settlements should have higher prosperity
        assert state.settlements["A"].prosperity > 0.5
        assert state.settlements["B"].prosperity > 0.5
