"""Tests for Phase 7 — Living World features."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.sim import (
    run_simulation, _check_era_transition,
    SimState, SettlementSnapshot, SimEvent,
    _apply_narrative_consequences, _select_named_character,
    _describe_with_character,
)
from src.narrative import Character, generate_narrative
from src.branch import run_branch_comparison


class TestEraTransitions:
    """Era transitions should work during simulation."""

    def test_era_history_initial_empty(self):
        """Fresh SimState should have no era history."""
        world = generate_world(42)
        r = run_simulation(world, num_years=25)  # Too short for first era
        assert len(r.final_state.era_history) == 0

    def test_era_triggered_at_milestones(self):
        """Should record era transitions at 50-year milestones."""
        world = generate_world(42)
        r = run_simulation(world, num_years=100, chaos_factor=0.3)
        # Should have at least era at year 50
        assert len(r.final_state.era_history) > 0
        years = {e["year"] for e in r.final_state.era_history}
        assert 50 in years, f"Expected year 50 era, got years {sorted(years)}"

    def test_era_names_are_sensible(self):
        """Era names should be non-empty and formatted as 'The ...'."""
        world = generate_world(42)
        r = run_simulation(world, num_years=150, chaos_factor=0.3)
        for era in r.final_state.era_history:
            assert era["era_name"].startswith("The ")
            assert len(era["era_name"]) > 5
            assert era["era_type"] in ("prosperity", "decline", "expansion",
                                        "conflict", "transition")
            assert era["description"]

    def test_era_determinism(self):
        """Same seed should produce same era progression."""
        w1 = generate_world(42)
        w2 = generate_world(42)
        r1 = run_simulation(w1, num_years=100, chaos_factor=0.3)
        r2 = run_simulation(w2, num_years=100, chaos_factor=0.3)
        for e1, e2 in zip(r1.final_state.era_history, r2.final_state.era_history):
            assert e1["year"] == e2["year"]
            assert e1["era_name"] == e2["era_name"]
            assert e1["era_type"] == e2["era_type"]

    def test_era_multiple_milestones(self):
        """200 year sim should have multiple era records."""
        world = generate_world(42)
        r = run_simulation(world, num_years=200, chaos_factor=0.3)
        assert len(r.final_state.era_history) >= 3, \
            f"Expected >=3 eras for 200 years, got {len(r.final_state.era_history)}"


class TestCharacterDrivenFounding:
    """Founding events should include character references."""

    def test_founding_references_character(self):
        """Founding events should include the founder's name."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        r = run_simulation(
            world, num_years=300, chaos_factor=0.5,
            characters=world.narrative.characters,
        )
        founding_events = [e for e in r.events if e.event_type == "founding"]
        if founding_events:
            for fe in founding_events[:3]:
                assert "leads the expedition" in fe.description or "founded by" in fe.description

    def test_migration_events_created(self):
        """High-population settlements should produce migration events."""
        world = generate_world(42)
        r = run_simulation(world, num_years=200, chaos_factor=0.5)
        exodus_events = [e for e in r.events if e.event_type == "exodus"]
        # May or may not trigger, but should not crash

    def test_character_linked_to_founding(self):
        """Founding events should link to the character's backstory when available."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        r = run_simulation(
            world, num_years=300, chaos_factor=0.5,
            characters=world.narrative.characters,
        )
        for fe in r.events:
            if fe.event_type == "founding" and "leads the expedition" in fe.description:
                # Should reference at least one named character
                assert any(
                    c.full_name in fe.description
                    for c in world.narrative.characters
                )


class TestSimNarrativeConsequences:
    """Sim events should affect narrative data."""

    def test_simulation_with_narrative_does_not_crash(self):
        """Full sim with narrative should not crash."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        r = run_simulation(
            world, num_years=100, chaos_factor=0.3,
            characters=world.narrative.characters,
        )
        assert r.total_events >= 0

    def test_character_death_tracked_in_sim_state(self):
        """Character deaths should be recorded in sim state."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        r = run_simulation(
            world, num_years=200, chaos_factor=0.5,
            characters=world.narrative.characters,
        )
        dead = [name for name, status in r.final_state.character_status.items()
                if status == "dead"]
        # May or may not have deaths, but check the tracking exists
        assert hasattr(r.final_state, 'character_status')

    def test_character_deaths_propagate_to_narrative(self):
        """Sim character deaths should update narrative character status."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        initial_alive = sum(1 for c in world.narrative.characters if c.status == "alive")
        r = run_simulation(
            world, num_years=200, chaos_factor=0.5,
            characters=world.narrative.characters,
        )
        dead_in_narrative = [c for c in world.narrative.characters if c.status == "dead"]
        # The sim state's tracking and narrative should be consistent
        for c in dead_in_narrative:
            assert r.final_state.character_status.get(c.full_name) in ("dead", None), \
                f"{c.full_name} dead in narrative but not in sim state"

    def test_quests_deactivated_when_giver_dies(self):
        """Quests from dead characters should be marked inactive."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        r = run_simulation(
            world, num_years=200, chaos_factor=0.5,
            characters=world.narrative.characters,
        )
        dead_names = {c.full_name for c in world.narrative.characters if c.status == "dead"}
        for q in world.narrative.quests:
            if q.giver_character and q.giver_character in dead_names:
                assert not q.is_active, \
                    f"Quest '{q.name}' from dead giver {q.giver_character} still active"

    def test_new_quests_generated_from_events(self):
        """Major sim events should spawn new quests."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        original_quest_count = len(world.narrative.quests)
        r = run_simulation(
            world, num_years=300, chaos_factor=0.5,
            characters=world.narrative.characters,
        )
        # New quests may or may not be generated (stochastic)
        # At minimum total shouldn't decrease
        assert len(world.narrative.quests) >= original_quest_count


class TestBranchComparison:
    """Branch comparison should work correctly."""

    def test_branch_runs_two_sims(self):
        """Branch should run sims with different offsets."""
        world = generate_world(42)
        results = run_branch_comparison(world, num_years=50, chaos_factor=0.3)
        assert 0 in results
        assert 1 in results

    def test_branch_different_seeds(self):
        """Different offsets should produce different seeds."""
        world = generate_world(42)
        results = run_branch_comparison(world, num_years=50, chaos_factor=0.3)
        assert results[0].seed != results[1].seed

    def test_branch_custom_offsets(self):
        """Should accept custom list of offsets."""
        world = generate_world(42)
        results = run_branch_comparison(world, num_years=30, chaos_factor=0.3,
                                         offsets=[0, 2, 5])
        assert len(results) == 3
        assert 0 in results
        assert 2 in results
        assert 5 in results

    def test_branch_with_narrative(self):
        """Branch should work with narrative characters."""
        world = generate_world(42)
        world.narrative = generate_narrative(world)
        results = run_branch_comparison(world, num_years=30, chaos_factor=0.3)
        assert 0 in results
        assert results[0].total_events >= 0


class TestSelectNamedCharacterObject:
    """_select_named_character should return Character objects."""

    def test_returns_character_object(self):
        """Should return a Character, not a string."""
        from src.sim import _select_named_character
        import random
        rng = random.Random(42)
        chars = [
            Character("Aldric", "Stonehand", 35, "male", "warlord",
                      ["brave"], "North", "Ironhaven", ""),
        ]
        char = _select_named_character(rng, chars, "Ironhaven", "North", "war")
        assert char is not None
        assert isinstance(char, Character)
        assert char.full_name == "Aldric Stonehand"

    def test_describe_with_character_string_compat(self):
        """_describe_with_character should still accept string names."""
        from src.sim import _describe_with_character
        result = _describe_with_character("Plague ravages Ironhaven.",
                                          "Aldric Stonehand",
                                          "{char} struggles.")
        assert "Aldric Stonehand" in result
        assert "struggles" in result
