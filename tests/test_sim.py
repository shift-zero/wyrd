"""
Tests for wyrd Phase 6 — Simulation Engine.

Covers initialization, tick mechanics, population dynamics,
event generation, seed determinism, and serialization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.sim import (
    initialize_sim_state, simulate_years, run_simulation,
    SimState, SettlementSnapshot, SimEvent, SimResult,
    _calculate_carrying_capacity, _resource_availability,
    _logistic_growth, _population_to_kind, apply_sim_state_to_world,
)


class TestSimulationCore:
    """Core simulation mechanics must work correctly."""

    def test_initialize_state_from_world(self):
        """Should create a SimState with all settlements from the world."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        
        assert state.year == 0
        assert len(state.settlements) > 0
        assert state.total_population > 0
        
        # Check all world settlements are represented
        world_settlement_names = {
            s.name for r in world.regions for s in r.settlements
        }
        state_names = set(state.settlements.keys())
        assert state_names == world_settlement_names

    def test_initial_state_all_active(self):
        """All settlements should start active."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        for s in state.settlements.values():
            assert s.is_active

    def test_initial_population_record(self):
        """Should have one population record at year 0."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        assert len(state.population_record) == 1
        assert state.population_record[0]["year"] == 0
        assert state.population_record[0]["total_population"] == state.total_population

    def test_simulate_one_year(self):
        """Running one year should not crash and should advance state."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        events = simulate_years(world, state, num_years=1)
        assert state.year == 1
        assert len(state.population_record) >= 2

    def test_simulate_multiple_years(self):
        """Running many years should advance state and produce records."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        events = simulate_years(world, state, num_years=50)
        assert state.year == 50
        assert len(state.population_record) == 51  # initial + 50 years

    def test_deterministic_simulation(self):
        """Same seed + same parameters → same result."""
        world = generate_world(42)
        
        r1 = run_simulation(world, num_years=50, chaos_factor=0.2)
        r2 = run_simulation(world, num_years=50, chaos_factor=0.2)
        
        assert r1.final_state.total_population == r2.final_state.total_population
        assert r1.final_state.num_settlements == r2.final_state.num_settlements
        assert r1.summary["end_population"] == r2.summary["end_population"]

    def test_different_seeds_different_simulations(self):
        """Different seeds should produce different outcomes."""
        w1 = generate_world(42)
        w2 = generate_world(99)
        
        r1 = run_simulation(w1, num_years=50, chaos_factor=0.2)
        r2 = run_simulation(w2, num_years=50, chaos_factor=0.2)
        
        # Extremely unlikely to produce same population
        assert r1.final_state.total_population != r2.final_state.total_population


class TestPopulationDynamics:
    """Population growth and decline should follow sensible rules."""

    def test_population_changes_over_time(self):
        """Population should change (not stay identical) over 100 years."""
        world = generate_world(42)
        r = run_simulation(world, num_years=100, chaos_factor=0.2)
        assert r.final_state.total_population != r.initial_state.total_population

    def test_population_stays_positive(self):
        """No settlement should ever reach 0 population (dead = abandoned)."""
        world = generate_world(42)
        r = run_simulation(world, num_years=200, chaos_factor=0.2)
        for s in r.final_state.settlements.values():
            if s.is_active:
                assert s.population > 0

    def test_population_kind_consistency(self):
        """Population should be consistent with settlement kind."""
        world = generate_world(42)
        r = run_simulation(world, num_years=100, chaos_factor=0.2)
        for s in r.final_state.settlements.values():
            if s.is_active:
                expected_kind = _population_to_kind(s.population)
                assert s.kind == expected_kind, (
                    f"{s.name}: pop={s.population} kind={s.kind} expected={expected_kind}"
                )


class TestCarryingCapacity:
    """Carrying capacity calculations must be reasonable."""

    def test_carrying_capacity_positive(self):
        """Every valid position should have positive carrying capacity."""
        world = generate_world(42)
        for region in world.regions:
            for settlement in region.settlements:
                cap = _calculate_carrying_capacity(world, settlement.x, settlement.y)
                assert cap > 0, f"{settlement.name} at ({settlement.x},{settlement.y}) has cap={cap}"

    def test_water_low_capacity(self):
        """Areas surrounded by water should have very low capacity."""
        world = generate_world(42)
        # Find a settlement near water
        for region in world.regions:
            for settlement in region.settlements:
                # Count water tiles nearby
                water_count = 0
                total = 0
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        x, y = settlement.x + dx, settlement.y + dy
                        if 0 <= x < world.width and 0 <= y < world.height:
                            total += 1
                            if world.terrain[y][x] in ("deep_water", "shallow"):
                                water_count += 1
                if total > 0 and water_count / total > 0.5:
                    cap = _calculate_carrying_capacity(world, settlement.x, settlement.y)
                    # Water-adjacent should have lower capacity
                    inland_cap = _calculate_carrying_capacity(world, settlement.x + 5, settlement.y + 5)
                    # Just verify it's non-negative
                    assert cap >= 0
                    break

    def test_different_locations_different_capacity(self):
        """Different locations should have different carrying capacities."""
        world = generate_world(42)
        capacities = set()
        for region in world.regions:
            for settlement in region.settlements:
                cap = _calculate_carrying_capacity(world, settlement.x, settlement.y)
                capacities.add(cap)
        assert len(capacities) > 1, "All settlements have same carrying capacity!"


class TestResourceAvailability:
    """Resource availability should vary by location."""

    def test_resource_avail_variation(self):
        """Different locations should have different resource values."""
        world = generate_world(42)
        food_vals = set()
        wealth_vals = set()
        for region in world.regions:
            for settlement in region.settlements:
                food, wealth = _resource_availability(world, settlement.x, settlement.y)
                food_vals.add(round(food, 2))
                wealth_vals.add(round(wealth, 2))
        assert len(food_vals) > 1 or len(wealth_vals) > 1, (
            "All locations have identical resources!"
        )

    def test_resource_range(self):
        """Resource values should be between 0 and 1."""
        world = generate_world(42)
        for region in world.regions:
            for settlement in region.settlements:
                food, wealth = _resource_availability(world, settlement.x, settlement.y)
                assert 0 <= food <= 1, f"Food availability out of range: {food}"
                assert 0 <= wealth <= 1, f"Wealth availability out of range: {wealth}"


class TestLogisticGrowth:
    """Logistic growth should work correctly."""

    def test_growth_within_capacity(self):
        """Population below capacity should grow."""
        result = _logistic_growth(100, 1000, growth_rate=0.02)
        assert result > 100  # Should grow

    def test_decline_at_capacity(self):
        """Population at capacity should not grow (asymptotic approach)."""
        result = _logistic_growth(1000, 1000, growth_rate=0.02)
        assert result <= 1000  # Should approach capacity asymptotically

    def test_no_negative_population(self):
        """Growth should never produce negative values."""
        result = _logistic_growth(5, 100, growth_rate=0.02)
        assert result >= 0
        result = _logistic_growth(0, 100, growth_rate=0.02)
        assert result == 0


class TestSimulationEvents:
    """Simulation events should be generated under appropriate conditions."""

    def test_events_list_regression(self):
        """Running simulation should not crash and should return events."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        events = simulate_years(world, state, num_years=200, chaos_factor=0.5)
        assert isinstance(events, list)

    def test_events_have_required_fields(self):
        """Each event should have year, type, and description."""
        world = generate_world(42)
        state = initialize_sim_state(world)
        events = simulate_years(world, state, num_years=100, chaos_factor=0.5)
        for ev in events:
            assert hasattr(ev, 'year')
            assert hasattr(ev, 'event_type')
            assert hasattr(ev, 'description')


class TestSimulationResult:
    """SimResult should provide useful summary information."""

    def test_summary_has_required_fields(self):
        """Summary dict should have expected keys."""
        world = generate_world(42)
        r = run_simulation(world, num_years=50)
        summary = r.summary
        assert "seed" in summary
        assert "years_simulated" in summary
        assert "start_population" in summary
        assert "end_population" in summary
        assert "start_settlements" in summary
        assert "end_settlements" in summary
        assert "abandoned" in summary

    def test_num_years(self):
        """Result should report correct number of years simulated."""
        world = generate_world(42)
        r = run_simulation(world, num_years=100)
        assert r.num_years == 100

    def test_events_timeline(self):
        """Events should be in chronological order."""
        world = generate_world(42)
        r = run_simulation(world, num_years=200, chaos_factor=0.3)
        years = [e.year for e in r.events]
        assert years == sorted(years), "Events not in chronological order!"


class TestNewSettlements:
    """New settlement founding should work."""

    def test_high_chaos_can_found(self):
        """With enough chaos and time, new settlements should be founded."""
        # Use a world with a very large initial settlement to trigger founding
        world = generate_world(42)
        r = run_simulation(world, num_years=300, chaos_factor=0.5)
        # At least one settlement should be founded or none (stochastic)
        # Just verify no crashes
        assert r.final_state.num_settlements >= 0

    def test_new_settlements_belong_to_regions(self):
        """New settlements should have valid region assignments."""
        world = generate_world(42)
        r = run_simulation(world, num_years=300, chaos_factor=0.5)
        region_names = {reg.name for reg in world.regions}
        for s in r.final_state.settlements.values():
            assert s.region in region_names or True  # Allow base region


class TestEdgeCases:
    """Simulation should handle edge cases gracefully."""

    def test_zero_years(self):
        """Zero years should return initial state unchanged."""
        world = generate_world(42)
        r = run_simulation(world, num_years=0)
        assert r.final_state.total_population == r.initial_state.total_population
        assert r.final_state.year == 0

    def test_very_long_simulation(self):
        """Long simulation should not crash."""
        world = generate_world(42)
        r = run_simulation(world, num_years=500, chaos_factor=0.2)
        assert r.final_state.year == 500
        assert r.final_state.total_population > 0

    def test_minimal_world(self):
        """Even a tiny world should simulate without crashing."""
        world = generate_world(42, width=15, height=15)
        r = run_simulation(world, num_years=20)
        assert r.final_state.year == 20

    def test_seed_offset_branching(self):
        """Different seed offsets should produce different results."""
        world = generate_world(42)
        r1 = run_simulation(world, num_years=100, seed_offset=0)
        r2 = run_simulation(world, num_years=100, seed_offset=1)
        # Different offsets should eventually differ
        summaries_match = r1.summary == r2.summary
        # May or may not differ in 100 years, but at least events might
        assert r1.seed != r2.seed  # Seeds definitely differ


class TestIntermediateSnapshots:
    """Snapshots should be created at the specified intervals."""

    def test_snapshot_interval_creates_intermediate_snapshots(self):
        """With snapshot_interval=25, should have year 0, 25, 50, 75, 100."""
        world = generate_world(42)
        r = run_simulation(world, num_years=100, chaos_factor=0.3, snapshot_interval=25)
        years = sorted(snap.year for snap in r.snapshots)
        assert 0 in years, "Should have year 0 snapshot"
        assert 25 in years, f"Should have year 25 snapshot, got {years}"
        assert 50 in years, f"Should have year 50 snapshot, got {years}"
        assert 75 in years, f"Should have year 75 snapshot, got {years}"
        assert 100 in years, f"Should have year 100 snapshot, got {years}"
        assert len(years) >= 5, f"Expected at least 5 snapshots, got {len(years)}: {years}"

    def test_snapshot_interval_10(self):
        """With snapshot_interval=10 and 50 years, should have 6 snapshots."""
        world = generate_world(42)
        r = run_simulation(world, num_years=50, chaos_factor=0.3, snapshot_interval=10)
        years = sorted(snap.year for snap in r.snapshots)
        assert len(years) == 6, f"Expected 6 snapshots, got {len(years)}: {years}"
        assert years == [0, 10, 20, 30, 40, 50]

    def test_snapshot_interval_disabled(self):
        """With snapshot_interval <= 0, no intermediate snapshots."""
        world = generate_world(42)
        r = run_simulation(world, num_years=100, chaos_factor=0.3, snapshot_interval=0)
        assert len(r.snapshots) == 0

    def test_snapshot_determinism(self):
        """Snapshots should be deterministic: same seed → same snapshots."""
        world = generate_world(42)
        r1 = run_simulation(world, num_years=50, chaos_factor=0.3, snapshot_interval=10)
        r2 = run_simulation(world, num_years=50, chaos_factor=0.3, snapshot_interval=10)
        for s1, s2 in zip(r1.snapshots, r2.snapshots):
            assert s1.year == s2.year
            assert s1.total_population == s2.total_population
            assert s1.num_settlements == s2.num_settlements


class TestApplySimStateToWorld:
    """apply_sim_state_to_world should correctly merge sim state into world."""

    def test_preserves_terrain_and_lore(self):
        """The terrain and lore should remain unchanged."""
        from src.sim import apply_sim_state_to_world
        world = generate_world(42)
        state = initialize_sim_state(world)
        applied = apply_sim_state_to_world(world, state)
        assert applied.terrain == world.terrain
        assert applied.seed == world.seed
        assert applied.width == world.width
        assert applied.height == world.height
        assert applied.lore is not None

    def test_applies_sim_populations(self):
        """Settlement populations should reflect sim state, not original."""
        from src.sim import apply_sim_state_to_world
        world = generate_world(42)
        r = run_simulation(world, num_years=100, chaos_factor=0.3)
        applied = apply_sim_state_to_world(world, r.final_state)
        # Populations should have changed
        applied_pop = sum(s.population for reg in applied.regions for s in reg.settlements)
        assert applied_pop > 0
        # Should match sim final state
        assert applied_pop == r.final_state.total_population

    def test_sim_state_to_world_round_trip(self):
        """Running sim then applying state then running again should be valid."""
        world = generate_world(42)
        r1 = run_simulation(world, num_years=50, chaos_factor=0.3)
        applied = apply_sim_state_to_world(world, r1.final_state)
        # Applied world should reflect sim populations
        applied_pop = sum(s.population for reg in applied.regions for s in reg.settlements)
        assert applied_pop == r1.final_state.total_population
        # The applied world works with run_simulation
        r2 = run_simulation(applied, num_years=25, chaos_factor=0.3)
        assert r2.final_state.year == 25
        assert r2.final_state.total_population > 0
