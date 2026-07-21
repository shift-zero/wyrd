"""
Tests for wyrd Phase 2 — Lore Engine.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.lore import generate_lore, Lore
from src.world import World, Region, Settlement


class TestLoreDeterminism:
    """Same seed → same lore, always."""

    def test_lore_is_deterministic(self):
        a = generate_world(42)
        b = generate_world(42)
        assert a.lore is not None
        assert b.lore is not None
        assert a.lore.cultures == b.lore.cultures
        assert a.lore.histories == b.lore.histories
        assert a.lore.region_descriptions == b.lore.region_descriptions
        assert len(a.lore.features) == len(b.lore.features)
        assert len(a.lore.relationships) == len(b.lore.relationships)

    def test_different_seeds_different_lore(self):
        a = generate_world(42)
        b = generate_world(99)
        # Very unlikely to generate identical cultures for different seeds
        assert a.lore is not None
        assert b.lore is not None
        assert a.lore.cultures != b.lore.cultures or \
               a.lore.histories != b.lore.histories


class TestCultureGeneration:
    """Culture names and descriptions must be biome-appropriate."""

    def test_every_region_has_culture(self):
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            assert region.name in world.lore.cultures
            assert world.lore.cultures[region.name] != ""

    def test_every_region_has_culture_description(self):
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            assert region.name in world.lore.culture_descriptions
            descs = world.lore.culture_descriptions[region.name]
            assert len(descs) >= 1


class TestRegionDescriptions:
    """Each region gets a description of its settlements."""

    def test_region_descriptions_exist(self):
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            assert region.name in world.lore.region_descriptions
            desc = world.lore.region_descriptions[region.name]
            assert "settlement" in desc.lower()
            assert "dot" in desc.lower() or "dots" in desc.lower()

    def test_singular_settlement_grammar(self):
        """A region with exactly 1 settlement uses 'dots' not 'dot'."""
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            if len(region.settlements) == 1:
                desc = world.lore.region_descriptions[region.name]
                assert "dots" in desc, f"Expected 'dots' for single settlement: {desc}"


class TestHistory:
    """History snippets are generated for each region."""

    def test_every_region_has_history(self):
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            assert region.name in world.lore.histories
            assert len(world.lore.histories[region.name]) > 20

    def test_no_double_period(self):
        """History text should never have '..'."""
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            history = world.lore.histories[region.name]
            assert ".." not in history, f"Double period in history: {history}"

    def test_history_ends_with_period(self):
        world = generate_world(4242)
        assert world.lore is not None
        for region in world.regions:
            history = world.lore.histories[region.name]
            assert history.endswith("."), f"History doesn't end with period: {history}"


class TestFeatures:
    """Geographical features are named and region-linked."""

    def test_features_exist(self):
        world = generate_world(4242)
        assert world.lore is not None
        assert len(world.lore.features) > 0

    def test_features_have_required_fields(self):
        world = generate_world(4242)
        assert world.lore is not None
        for feat in world.lore.features:
            assert "type" in feat
            assert "name" in feat
            assert "region" in feat
            assert feat["type"] in ("mountain_range", "river", "bay", "forest")
            assert len(feat["name"]) > 0

    def test_feature_types_varied(self):
        """Features should include multiple types across different seeds."""
        types_seen = set()
        for seed in range(10):
            world = generate_world(seed)
            assert world.lore is not None
            for feat in world.lore.features:
                types_seen.add(feat["type"])
        # Should see at least 3 different feature types
        assert len(types_seen) >= 3, f"Only saw: {types_seen}"


class TestRelationships:
    """Settlement-to-settlement relationships."""

    def test_relationships_exist(self):
        world = generate_world(4242)
        assert world.lore is not None
        assert len(world.lore.relationships) > 0

    def test_no_self_relationships(self):
        """A settlement should never be in a relationship with itself."""
        world = generate_world(4242)
        assert world.lore is not None
        for rel in world.lore.relationships:
            assert rel["source"] != rel["target"] or \
                   rel["source_region"] != rel["target_region"], \
                   f"Self-relationship: {rel}"

    def test_no_duplicate_pairs(self):
        """No two relationships should reference the same pair of settlements."""
        world = generate_world(4242)
        assert world.lore is not None
        seen = set()
        for rel in world.lore.relationships:
            pair = frozenset([
                (rel["source_region"], rel["source"]),
                (rel["target_region"], rel["target"]),
            ])
            assert pair not in seen, f"Duplicate pair: {rel}"
            seen.add(pair)

    def test_relationships_have_descriptions(self):
        world = generate_world(4242)
        assert world.lore is not None
        for rel in world.lore.relationships:
            assert "description" in rel
            assert len(rel["description"]) > 10
            assert rel["type"] in ("trade", "rivalry", "alliance", "feud",
                                   "vassalage", "marriage_tie", "religious",
                                   "cultural")


class TestWorldIntegration:
    """Lore is fully wired into world generation."""

    def test_world_has_lore_after_generation(self):
        world = generate_world(42)
        assert world.lore is not None
        assert isinstance(world.lore, Lore)

    def test_lore_seed_offset(self):
        """Lore seed is terrain seed + 1,000,000."""
        world = generate_world(42)
        assert world.lore is not None
        assert world.lore.seed == 42 + 1000000

    def test_generate_and_describe_no_errors(self):
        """Smoke test: the full pipeline runs without exceptions."""
        for seed in [0, 1, 999, 12345, 77777]:
            world = generate_world(seed, width=30, height=20)
            assert world.lore is not None
            from src.render import render_lore, render_map
            _ = render_map(world)
            _ = render_lore(world)


class TestNoopLoreForSmallWorlds:
    """Even tiny worlds get some lore."""

    def test_tiny_world_has_lore(self):
        world = generate_world(42, width=20, height=15)
        assert world.lore is not None
        # Should have at least some content
        assert len(world.lore.cultures) > 0
        assert len(world.lore.features) > 0
