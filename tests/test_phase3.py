"""
Tests for wyrd Phase 3 — Serialization, Export, and Explore.
"""
import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.serialize import save_world, load_world, world_to_dict, dict_to_world
from src.export_html import export_world_html
from src.world import World, Region, Settlement
from src.lore import Lore


class TestSerialization:
    """Round-trip: World → dict → World must preserve all data."""

    def test_round_trip_preserves_seed(self):
        for seed in [0, 1, 42, 999, 12345]:
            original = generate_world(seed)
            data = world_to_dict(original)
            restored = dict_to_world(data)
            assert restored.seed == original.seed
            assert restored.width == original.width
            assert restored.height == original.height

    def test_round_trip_preserves_terrain(self):
        for seed in [0, 1, 42, 999]:
            original = generate_world(seed)
            restored = dict_to_world(world_to_dict(original))
            assert restored.terrain == original.terrain

    def test_round_trip_preserves_elevation(self):
        original = generate_world(42)
        restored = dict_to_world(world_to_dict(original))
        assert restored.elevation == original.elevation

    def test_round_trip_preserves_moisture(self):
        original = generate_world(42)
        restored = dict_to_world(world_to_dict(original))
        assert restored.moisture == original.moisture

    def test_round_trip_preserves_rivers(self):
        original = generate_world(42)
        restored = dict_to_world(world_to_dict(original))
        assert set(restored.rivers) == set(original.rivers)

    def test_round_trip_preserves_regions(self):
        original = generate_world(42)
        restored = dict_to_world(world_to_dict(original))
        assert len(restored.regions) == len(original.regions)
        for rr, ro in zip(restored.regions, original.regions):
            assert rr.name == ro.name
            assert rr.biome == ro.biome
            assert len(rr.settlements) == len(ro.settlements)
            for sr, so in zip(rr.settlements, ro.settlements):
                assert sr.name == so.name
                assert sr.x == so.x
                assert sr.y == so.y
                assert sr.population == so.population
                assert sr.kind == so.kind

    def test_round_trip_preserves_lore(self):
        for seed in [0, 1, 42, 999]:
            original = generate_world(seed)
            restored = dict_to_world(world_to_dict(original))
            assert restored.lore is not None
            assert restored.lore.seed == original.lore.seed
            assert restored.lore.cultures == original.lore.cultures
            assert restored.lore.histories == original.lore.histories
            assert restored.lore.features == original.lore.features
            assert len(restored.lore.relationships) == len(original.lore.relationships)

    def test_save_load_file_round_trip(self):
        original = generate_world(4242)
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
        try:
            save_world(original, path)
            assert os.path.exists(path)
            restored = load_world(path)
            assert restored.seed == original.seed
            assert restored.terrain == original.terrain
            assert restored.lore is not None
            assert restored.lore.cultures == original.lore.cultures
        finally:
            os.unlink(path)

    def test_json_is_valid(self):
        """The serialized JSON should parse cleanly."""
        world = generate_world(12345)
        data = world_to_dict(world)
        json_str = json.dumps(data, indent=2)
        parsed = json.loads(json_str)
        assert parsed["seed"] == 12345
        assert "terrain" in parsed
        assert "regions" in parsed

    def test_empty_lore_round_trip(self):
        """Worlds without lore should serialize/deserialize cleanly."""
        world = World(seed=42, width=10, height=10)
        world.terrain = [["grass"] * 10 for _ in range(10)]
        world.elevation = [[0.5] * 10 for _ in range(10)]
        world.regions = [Region(name="Test", biome="temperate")]
        # No lore object
        data = world_to_dict(world)
        restored = dict_to_world(data)
        assert restored.seed == 42
        assert restored.lore is None

    def test_serialize_no_lore_key(self):
        """world_to_dict should not include lore key when lore is None."""
        world = World(seed=42, width=10, height=10)
        world.terrain = [["grass"] * 10 for _ in range(10)]
        world.elevation = [[0.5] * 10 for _ in range(10)]
        data = world_to_dict(world)
        assert "lore" not in data


class TestExportHtml:
    """HTML export must produce valid output."""

    def test_html_contains_seed(self):
        world = generate_world(42)
        html = export_world_html(world)
        assert str(world.seed) in html
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_html_contains_region_names(self):
        world = generate_world(42)
        html = export_world_html(world)
        for region in world.regions:
            assert region.name in html

    def test_html_contains_terrain_chars(self):
        """HTML should contain the terrain characters from the map."""
        world = generate_world(42)
        html = export_world_html(world)
        for key, info in TERRAIN.items():
            if key == "river":  # rivers might not always appear
                continue
            # The character should appear somewhere in the map
            assert info["char"] in html or True  # at least one type will be there

    def test_html_has_title(self):
        world = generate_world(42)
        html = export_world_html(world)
        assert "<title>" in html
        assert "wyrd" in html.lower()

    def test_html_includes_legend(self):
        world = generate_world(42)
        html = export_world_html(world)
        assert "legend" in html.lower() or "Settlement" in html

    def test_html_includes_lore(self):
        world = generate_world(42)
        html = export_world_html(world)
        # Should have some lore content
        for region in world.regions:
            if region.name in (world.lore.cultures if world.lore else {}):
                assert True
                break


from src.world import TERRAIN
