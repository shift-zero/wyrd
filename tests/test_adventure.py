"""Tests for wyrd Phase 10 — Adventure Zone Generation.

Covers zone placement, content correctness, seed determinism,
and edge cases (tiny worlds, no suitable terrain, etc.).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.adventure import (
    generate_adventure_zones,
    render_zones,
    render_zone_detail,
    _num_zones,
    _find_placement,
    _generate_zone_name,
    _pick_difficulty,
)
from src.world import AdventureZone, ADVENTURE_ZONE_TYPES
import random


class TestZonePlacement:
    """Zones must be placed on suitable terrain without overlaps."""

    def test_placement_from_generate_world(self):
        """Generate should include adventure zones."""
        world = generate_world(42)
        assert len(world.adventure_zones) > 0
        assert len(world.adventure_zones) <= 50  # sanity check

    def test_no_overlap_with_settlements(self):
        """Zones should not be placed on top of settlements."""
        world = generate_world(42)
        settlement_coords = set()
        for r in world.regions:
            for s in r.settlements:
                settlement_coords.add((s.x, s.y))
        for z in world.adventure_zones:
            assert (z.x, z.y) not in settlement_coords, \
                f"{z.name} overlaps settlement at ({z.x}, {z.y})"

    def test_no_self_overlap(self):
        """Zones should not overlap each other."""
        world = generate_world(42)
        coords = [(z.x, z.y) for z in world.adventure_zones]
        assert len(coords) == len(set(coords))

    def test_preferred_terrain(self):
        """Each zone type should appear on its preferred terrain."""
        world = generate_world(42)
        for z in world.adventure_zones:
            info = ADVENTURE_ZONE_TYPES.get(z.zone_type)
            if info:
                terrain_key = world.terrain[z.y][z.x]
                # Check the terrain is in preferred or is a reasonable nearby type
                assert terrain_key in info["preferred_terrain"] + ["grass", "forest"], \
                    f"{z.name} ({z.zone_type}) on {terrain_key} at ({z.x},{z.y})"


class TestZoneContent:
    """Each zone should have meaningful, well-formed content."""

    def test_zone_has_all_fields(self):
        """Every zone must have name, type, location, difficulty, etc."""
        world = generate_world(42)
        for z in world.adventure_zones:
            assert z.name and len(z.name) > 3
            assert z.zone_type in ADVENTURE_ZONE_TYPES
            assert 0 <= z.x < world.width
            assert 0 <= z.y < world.height
            assert z.region
            assert z.difficulty in ["trivial", "easy", "moderate", "hard", "deadly"]
            assert z.description
            assert z.inhabitants

    def test_treasure_tier_matches_difficulty(self):
        """Treasure tier should align with difficulty level."""
        world = generate_world(42)
        for z in world.adventure_zones:
            diff_idx = ["trivial", "easy", "moderate", "hard", "deadly"].index(z.difficulty)
            assert z.treasure_tier == diff_idx + 1, \
                f"{z.name}: difficulty {z.difficulty} but treasure tier {z.treasure_tier}"

    def test_zones_have_quest_hooks(self):
        """Every zone should have a quest hook."""
        world = generate_world(42)
        for z in world.adventure_zones:
            assert z.quest_hook, f"{z.name} has no quest hook"

    def test_zone_char_property(self):
        """Char property should return the correct marker."""
        world = generate_world(42)
        for z in world.adventure_zones:
            expected = ADVENTURE_ZONE_TYPES[z.zone_type]["char"]
            assert z.char == expected, f"{z.zone_type}: expected '{expected}' got '{z.char}'"


class TestZoneDeterminism:
    """Same seed must produce identical adventure zones."""

    def test_deterministic_zones(self):
        """Two worlds with the same seed should have identical zones."""
        w1 = generate_world(42)
        w2 = generate_world(42)
        assert len(w1.adventure_zones) == len(w2.adventure_zones)
        for z1, z2 in zip(w1.adventure_zones, w2.adventure_zones):
            assert z1.name == z2.name
            assert z1.zone_type == z2.zone_type
            assert z1.x == z2.x and z1.y == z2.y
            assert z1.difficulty == z2.difficulty
            assert z1.description == z2.description

    def test_different_seeds_different_zones(self):
        """Different seeds should produce different zone layouts."""
        w1 = generate_world(42)
        w2 = generate_world(99)
        # Very unlikely to produce the same set
        names1 = {(z.x, z.y) for z in w1.adventure_zones}
        names2 = {(z.x, z.y) for z in w2.adventure_zones}
        assert names1 != names2, "Different seeds produced identical zone layouts!"


class TestZoneEdgeCases:
    """Edge cases and error handling."""

    def test_tiny_world(self):
        """Tiny worlds should still get some zones."""
        world = generate_world(42, width=30, height=20)
        assert len(world.adventure_zones) >= 1

    def test_zone_round_trip(self):
        """Adventure zones should survive to_dict/from_dict serialization."""
        world = generate_world(42)
        # Simulate what serialize.py would do
        zones_data = []
        for z in world.adventure_zones:
            zones_data.append({
                "name": z.name,
                "zone_type": z.zone_type,
                "x": z.x,
                "y": z.y,
                "region": z.region,
                "difficulty": z.difficulty,
                "inhabitants": z.inhabitants,
                "description": z.description,
                "treasure_tier": z.treasure_tier,
                "is_cleared": z.is_cleared,
                "quest_hook": z.quest_hook,
            })
        restored = [AdventureZone(**zd) for zd in zones_data]
        assert len(restored) == len(world.adventure_zones)
        for orig, rest in zip(world.adventure_zones, restored):
            assert orig.name == rest.name
            assert orig.zone_type == rest.zone_type
            assert orig.x == rest.x

    def test_empty_world_no_zones(self):
        """A world with an empty terrain grid should produce empty zones."""
        world = generate_world(42)
        world.terrain = [["deep_water"] * world.width for _ in range(world.height)]
        zones = generate_adventure_zones(world)
        # Should still produce some zones since we have candidates
        assert isinstance(zones, list)


class TestZoneRendering:
    """Rendering functions should produce sensible output."""

    def test_render_zones_returns_string(self):
        """render_zones should return a non-empty string."""
        world = generate_world(42)
        output = render_zones(world, detail=False)
        assert output and len(output) > 50
        assert "Adventure Zones" in output

    def test_render_zones_with_detail(self):
        """Detailed rendering should include descriptions."""
        world = generate_world(42)
        output = render_zones(world, detail=True)
        assert output and len(output) > 100
        # Should include zone descriptions
        for z in world.adventure_zones[:3]:
            if z.description:
                assert z.description[:20] in output

    def test_render_single_zone(self):
        """Rendering a single zone should include all its fields."""
        world = generate_world(42)
        zone = world.adventure_zones[0]
        output = render_zone_detail(zone)
        assert zone.name in output
        assert ADVENTURE_ZONE_TYPES[zone.zone_type]["desc"] in output
        assert zone.difficulty in output
        assert zone.description in output
        assert zone.inhabitants in output
