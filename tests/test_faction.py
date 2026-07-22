"""Tests for wyrd Phase 11 — Faction System.

Covers faction generation, content correctness, seed determinism,
serialization round-trip, rendering, and edge cases.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.faction import (
    generate_factions,
    Faction,
    FactionRelationship,
    FACTION_TYPES,
    RELATIONSHIP_TYPES,
)
from src.render import render_factions, render_faction_detail
from src.serialize import world_to_dict, dict_to_world
import random


class TestFactionGeneration:
    """Factions must be generated with valid properties."""

    def test_factions_generated_from_world(self):
        """Generate should include factions."""
        world = generate_world(42)
        assert len(world.factions) > 0
        assert len(world.factions) <= 10  # sanity bound

    def test_faction_has_all_fields(self):
        """Every faction must have name, type, territory, leader, etc."""
        world = generate_world(42)
        for f in world.factions:
            assert f.name and len(f.name) > 2
            assert f.faction_type in FACTION_TYPES
            assert f.leader_name
            assert f.leader_title
            assert 0 <= f.influence <= 100
            assert 0 <= f.wealth <= 100
            assert 0 <= f.military <= 100
            assert 0 <= f.stability <= 100
            assert f.reputation in ["benevolent", "respected", "neutral", "feared", "hated"]
            assert f.description
            assert len(f.goals) >= 1

    def test_faction_power_score(self):
        """Power score should be the sum of influence, wealth, military."""
        world = generate_world(42)
        for f in world.factions:
            assert f.power_score == f.influence + f.wealth + f.military

    def test_faction_type_info(self):
        """Faction.type_info should return correct data."""
        world = generate_world(42)
        for f in world.factions:
            info = f.type_info
            assert "desc" in info
            assert "icon" in info
            assert "color" in info


class TestFactionRelationships:
    """Factions should have inter-faction relationships."""

    def test_relationships_generated(self):
        """Faction relationships should be generated."""
        world = generate_world(42)
        assert len(world.faction_relationships) > 0

    def test_relationship_has_valid_type(self):
        """Each relationship should have a valid type."""
        world = generate_world(42)
        for rel in world.faction_relationships:
            assert rel.rel_type in RELATIONSHIP_TYPES, \
                f"Unknown relationship type: {rel.rel_type}"
            assert rel.faction_a and rel.faction_b
            assert rel.description

    def test_relationship_bidirectional(self):
        """Relationships should reference actual factions."""
        world = generate_world(42)
        faction_names = {f.name for f in world.factions}
        for rel in world.faction_relationships:
            assert rel.faction_a in faction_names
            assert rel.faction_b in faction_names


class TestFactionDeterminism:
    """Same seed must produce identical factions."""

    def test_deterministic_factions(self):
        """Two worlds with the same seed should have identical factions."""
        w1 = generate_world(42)
        w2 = generate_world(42)
        assert len(w1.factions) == len(w2.factions)
        for f1, f2 in zip(w1.factions, w2.factions):
            assert f1.name == f2.name
            assert f1.faction_type == f2.faction_type
            assert f1.leader_name == f2.leader_name
            assert f1.power_score == f2.power_score

    def test_different_seeds_different_factions(self):
        """Different seeds should produce different faction layouts."""
        w1 = generate_world(42)
        w2 = generate_world(99)
        names1 = {f.name for f in w1.factions}
        names2 = {f.name for f in w2.factions}
        # Very unlikely to produce the same set
        assert names1 != names2, "Different seeds produced identical factions!"


class TestFactionRendering:
    """Rendering functions should produce sensible output."""

    def test_render_factions_returns_string(self):
        """render_factions should return a non-empty string."""
        world = generate_world(42)
        output = render_factions(world)
        assert output and len(output) > 50
        assert "Factions" in output

    def test_render_single_faction(self):
        """Rendering a single faction should include its fields."""
        world = generate_world(42)
        faction = world.factions[0]
        output = render_faction_detail(faction)
        assert faction.name in output
        assert faction.leader_name in output
        assert faction.description in output
        for goal in faction.goals:
            assert goal in output


class TestFactionSerialization:
    """Factions should survive save/load round-trip."""

    def test_faction_round_trip(self):
        """Factions should survive to_dict/from_dict serialization."""
        world = generate_world(42)
        data = world_to_dict(world)
        assert "factions" in data
        restored = dict_to_world(data)

        assert len(restored.factions) == len(world.factions)
        for orig, rest in zip(world.factions, restored.factions):
            assert orig.name == rest.name
            assert orig.faction_type == rest.faction_type
            assert orig.leader_name == rest.leader_name
            assert orig.power_score == rest.power_score
            assert orig.goals == rest.goals
            assert orig.reputation == rest.reputation

    def test_relationship_round_trip(self):
        """Faction relationships should survive serialization."""
        world = generate_world(42)
        data = world_to_dict(world)
        restored = dict_to_world(data)

        assert len(restored.faction_relationships) == len(world.faction_relationships)
        for orig, rest in zip(world.faction_relationships, restored.faction_relationships):
            assert orig.faction_a == rest.faction_a
            assert orig.faction_b == rest.faction_b
            assert orig.rel_type == rest.rel_type


class TestFactionEdgeCases:
    """Edge cases and error handling."""

    def test_empty_world_factions(self):
        """Generating factions with no regions should still work."""
        world = generate_world(42)
        world.regions = []
        factions = generate_factions(world)
        assert isinstance(factions, list)
        assert len(factions) >= 1  # should still produce at least one faction

    def test_faction_no_goals_fallback(self):
        """Factions should be usable even without goals."""
        f = Faction(
            name="Test Faction",
            faction_type="kingdom",
            territory=["Testland"],
            leader_name="King Test",
            leader_title="King",
        )
        assert f.name == "Test Faction"
        assert f.power_score == 150  # default: 50+50+50
        assert f.goals == []  # no goals set
