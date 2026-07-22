"""
Tests for wyrd Phase 3 Milestone 4 — Interactive Explorer.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.explore import _find_tile_info


class TestTileInfo:
    """_find_tile_info must return correct data for any coordinate."""

    def test_tile_info_basic(self):
        world = generate_world(42, width=30, height=20)
        info = _find_tile_info(world, 10, 10)
        assert "terrain" in info
        assert info["terrain_key"] in (
            "deep_water", "shallow", "sand", "grass",
            "forest", "hills", "mountains", "snow", "river",
        )
        assert 0 <= info["elevation"] <= 1.0
        assert 0 <= info["moisture"] <= 1.0

    def test_tile_info_settlement(self):
        world = generate_world(42, width=30, height=20)
        for region in world.regions:
            for s in region.settlements:
                info = _find_tile_info(world, s.x, s.y)
                assert info["settlement"] is not None
                assert info["settlement"].name == s.name
                return  # one test is enough

    def test_tile_info_region(self):
        world = generate_world(42, width=30, height=20)
        for region in world.regions:
            for s in region.settlements:
                info = _find_tile_info(world, s.x, s.y)
                assert info["region"] is not None
                return

    def test_out_of_bounds(self):
        world = generate_world(42, width=30, height=20)
        info = _find_tile_info(world, -1, -1)
        assert info["terrain"] == "unknown"

        info2 = _find_tile_info(world, 999, 999)
        assert info2["terrain"] == "unknown"

    def test_no_settlement_on_water(self):
        """If a tile has no settlement, settlement should be None."""
        world = generate_world(42, width=30, height=20)
        # Find a water tile
        for y in range(world.height):
            for x in range(world.width):
                if world.terrain[y][x] in ("deep_water", "shallow"):
                    info = _find_tile_info(world, x, y)
                    # Might still have region via proximity, but no settlement
                    assert info["settlement"] is None
                    return
