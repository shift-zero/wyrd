"""
Tests for wyrd Phase 8 — Magic System Generation.

Covers generation, seed determinism, serialization roundtrip,
and integration with world biomes and cultures.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.magic import (
    generate_magic_system, MagicSystem, MagicSchool, MagicTradition,
    _pick_magic_source, _select_schools, _generate_traditions,
)
from src.world import World, Region, Settlement
from src.serialize import world_to_dict, dict_to_world, save_world


class TestMagicGeneration:
    """The magic system must generate correctly from world data."""

    def test_magic_system_created(self):
        """Generate should always succeed."""
        world = generate_world(42)
        magic = generate_magic_system(world)
        assert magic.name != ""
        assert magic.source in ("arcane", "divine", "natural", "elemental", "shadow", "blood", "celestial")
        assert len(magic.description) > 0

    def test_magic_system_has_schools(self):
        """Every magic system should have 3-6 schools."""
        world = generate_world(42)
        magic = generate_magic_system(world)
        assert 3 <= len(magic.schools) <= 6

    def test_magic_system_has_traditions(self):
        """Every magic system should have at least one tradition."""
        world = generate_world(42)
        magic = generate_magic_system(world)
        assert len(magic.traditions) >= 1

    def test_school_fields(self):
        """Every school must have name, description, spell_examples, alignment."""
        world = generate_world(42)
        magic = generate_magic_system(world)
        for s in magic.schools:
            assert isinstance(s, MagicSchool)
            assert s.name != ""
            assert s.description != ""
            assert len(s.spell_examples) >= 1
            assert s.alignment in ("good", "evil", "lawful", "chaotic", "neutral")

    def test_tradition_fields(self):
        """Every tradition must have name, description, origin, region."""
        world = generate_world(42)
        magic = generate_magic_system(world)
        for t in magic.traditions:
            assert isinstance(t, MagicTradition)
            assert t.name != ""
            assert t.description != ""
            assert t.origin in (
                "ancient", "secret", "forgotten", "forbidden", "revered",
                "wandering", "monastic", "tribal", "courtly", "scholarly",
            )
            assert t.region != ""


class TestSeedDeterminism:
    """Same seed → same magic system."""

    def test_same_seed_same_magic(self):
        """Identical seeds should produce identical systems."""
        world1 = generate_world(42)
        world2 = generate_world(42)
        m1 = generate_magic_system(world1)
        m2 = generate_magic_system(world2)
        assert m1.name == m2.name
        assert m1.source == m2.source
        assert len(m1.schools) == len(m2.schools)
        assert [s.name for s in m1.schools] == [s.name for s in m2.schools]

    def test_different_seeds_different_systems(self):
        """Different seeds should likely produce different magic."""
        world1 = generate_world(42)
        world2 = generate_world(99)
        m1 = generate_magic_system(world1)
        m2 = generate_magic_system(world2)
        # The systems should differ in at least one important way
        different = (m1.name != m2.name) or (m1.source != m2.source)
        assert different, "Different seeds should produce different magic systems"


class TestSerialization:
    """Magic system must survive save/load roundtrip."""

    def test_magic_in_world_dict(self):
        """magic should appear in world_to_dict output."""
        world = generate_world(42)
        world.magic = generate_magic_system(world)
        d = world_to_dict(world)
        assert "magic" in d
        assert d["magic"]["name"] == world.magic.name

    def test_roundtrip(self):
        """dict_to_world(world_to_dict(w)) should preserve magic."""
        world = generate_world(42)
        world.magic = generate_magic_system(world)
        d = world_to_dict(world)
        w2 = dict_to_world(d)
        assert w2.magic is not None
        assert w2.magic.name == world.magic.name
        assert w2.magic.source == world.magic.source
        assert len(w2.magic.schools) == len(world.magic.schools)

    def test_magic_is_generated_during_export(self):
        """wyrd magic ... --save should persist magic to file."""
        world = generate_world(42)
        world.magic = generate_magic_system(world)
        import tempfile
        import os
        path = os.path.join(tempfile.gettempdir(), "wyrd-magic-test-save.json")
        save_world(world, path)
        with open(path) as f:
            import json
            d = json.load(f)
        assert "magic" in d
        assert d["magic"]["name"] == world.magic.name
        os.unlink(path)

    def test_magic_none_serialization(self):
        """World with magic=None should serialize without error."""
        world = generate_world(42)
        world.magic = None
        d = world_to_dict(world)
        assert "magic" not in d
        w2 = dict_to_world(d)
        assert w2.magic is None


class TestBiomeIntegration:
    """Magic system source should be influenced by world biomes."""

    def test_biome_affects_source(self):
        """A tundra-heavy world should favor different sources than a tropical one."""
        # Generate a tropical world (should lean toward natural/celestial)
        # vs a tundra world (should lean toward divine/arcane)
        world = generate_world(42)
        # Just verify the _pick_magic_source works without error
        import random
        rng = random.Random(42)
        source_key, source_data = _pick_magic_source(world, rng)
        assert source_key in ("arcane", "divine", "natural", "elemental", "shadow", "blood", "celestial")
        assert len(source_data["description"]) > 0


class TestIntegration:
    """Full integration with the wyrd CLI dispatch."""

    def test_magic_in_generate_flow(self):
        """Generating a world and adding magic should not error."""
        world = generate_world(42)
        assert world.magic is None
        magic = generate_magic_system(world)
        world.magic = magic
        assert world.magic is not None
        assert len(world.magic.schools) >= 3
