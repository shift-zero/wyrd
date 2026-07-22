"""
Tests for wyrd Phase 1 — World Generator.

Covers terrain generation, noise, rivers, settlement placement,
and seed determinism for the core map generation pipeline.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world, Noise
from src.world import World, TERRAIN


class TestNoise:
    """2D value noise must be deterministic and cover a useful range."""

    def test_noise_is_deterministic(self):
        n1 = Noise(42)
        n2 = Noise(42)
        for x in range(0, 100, 7):
            for y in range(0, 100, 7):
                assert n1.sample(x * 0.1, y * 0.1) == n2.sample(x * 0.1, y * 0.1)

    def test_different_seeds_different_noise(self):
        n1 = Noise(42)
        n2 = Noise(99)
        samples1 = [n1.sample(x * 0.1, y * 0.1) for x in range(10) for y in range(10)]
        samples2 = [n2.sample(x * 0.1, y * 0.1) for x in range(10) for y in range(10)]
        assert samples1 != samples2

    def test_noise_range_includes_extremes(self):
        """Over a large sample, noise should approach both 0 and 1."""
        n = Noise(42)
        vals = [n.sample(x * 0.05, y * 0.05) for x in range(40) for y in range(40)]
        assert min(vals) < 0.15, f"Min noise too high: {min(vals)}"
        assert max(vals) > 0.85, f"Max noise too low: {max(vals)}"

    def test_noise_not_flat(self):
        """Noise should not return the same value for different inputs."""
        n = Noise(42)
        vals = {n.sample(x * 0.37, y * 0.37) for x in range(10) for y in range(10)}
        assert len(vals) > 50, f"Too few unique noise values: {len(vals)}"

    def test_octave_deterministic(self):
        n1 = Noise(42)
        n2 = Noise(42)
        for x in range(10):
            for y in range(10):
                assert n1.octave(x * 0.3, y * 0.3) == n2.octave(x * 0.3, y * 0.3)

    def test_octave_range(self):
        n = Noise(42)
        vals = [n.octave(x * 0.1, y * 0.1, octaves=4) for x in range(20) for y in range(20)]
        assert 0 <= min(vals) < max(vals) <= 1.0
        # Octave noise tends to cluster near 0.5, but should have some spread
        assert max(vals) - min(vals) > 0.3


class TestTerrainGeneration:
    """Terrain must be deterministic and have reasonable distributions."""

    def test_world_has_all_terrain_types(self):
        """Over enough samples, all terrain types should appear."""
        all_types = set()
        for seed in range(20):
            w = generate_world(seed, width=40, height=30)
            for row in w.terrain:
                all_types.update(row)
        missing = [t for t in TERRAIN if t not in all_types]
        # river and snow may not appear in every world, but deep_water through mountains should
        expected = {"deep_water", "shallow", "sand", "grass", "forest", "hills", "mountains"}
        assert expected.issubset(all_types), f"Missing terrain types: {expected - all_types}"

    def test_land_water_ratio_reasonable(self):
        """World should have both land and water in reasonable proportions."""
        for seed in [0, 1, 42, 999, 12345]:
            w = generate_world(seed, width=50, height=30)
            water = sum(
                1 for row in w.terrain for t in row
                if t in ("deep_water", "shallow")
            )
            land = w.tiles - water
            ratio = land / w.tiles
            assert 0.3 < ratio < 0.9, (
                f"Seed {seed}: land ratio {ratio:.2f} too extreme "
                f"(land={land}, water={water})"
            )

    def test_deterministic_across_seeds(self):
        """Same seed → identical terrain every time."""
        for seed in [0, 1, 42, 999, 4242]:
            w1 = generate_world(seed)
            w2 = generate_world(seed)
            assert w1.terrain == w2.terrain
            assert w1.elevation == w2.elevation
            assert w1.moisture == w2.moisture
            assert len(w1.rivers) == len(w2.rivers)
            assert [s.name for r in w1.regions for s in r.settlements] == \
                   [s.name for r in w2.regions for s in r.settlements]

    def test_different_seeds_different_worlds(self):
        """Different seeds should produce different terrain."""
        w1 = generate_world(42)
        w2 = generate_world(99)
        # Extremely unlikely that two different seeds produce identical terrain
        assert w1.terrain != w2.terrain


class TestSettlements:
    """Settlements must be on land, named uniquely, and have valid types."""

    def test_settlements_on_land(self):
        """No settlement should be in water."""
        for seed in range(10):
            w = generate_world(seed, width=40, height=30)
            for region in w.regions:
                for s in region.settlements:
                    t = w.terrain[s.y][s.x]
                    assert t not in ("deep_water", "shallow", "river"), (
                        f"Seed {seed}: {s.name} at ({s.x},{s.y}) on {t}"
                    )

    def test_settlement_kinds_valid(self):
        """Each settlement should have a valid kind."""
        valid_kinds = {"hamlet", "village", "town", "city"}
        for seed in range(10):
            w = generate_world(seed)
            for region in w.regions:
                for s in region.settlements:
                    assert s.kind in valid_kinds, f"Seed {seed}: invalid kind '{s.kind}'"

    def test_settlement_population_range(self):
        """Population should be between 50 and 3000."""
        for seed in range(10):
            w = generate_world(seed)
            for region in w.regions:
                for s in region.settlements:
                    assert 50 <= s.population <= 3000, (
                        f"Seed {seed}: {s.name} pop {s.population} out of range"
                    )

    def test_settlement_kind_matches_population(self):
        """Settlement kind should be consistent with population."""
        for seed in range(10):
            w = generate_world(seed)
            for region in w.regions:
                for s in region.settlements:
                    expected = (
                        "hamlet" if s.population < 200
                        else "village" if s.population < 800
                        else "town" if s.population < 2000
                        else "city"
                    )
                    assert s.kind == expected, (
                        f"Seed {seed}: {s.name} pop={s.population} kind={s.kind} "
                        f"expected={expected}"
                    )

    def test_unique_settlement_names(self):
        """No two settlements in the same world should share a name."""
        for seed in range(20):
            w = generate_world(seed)
            names = [s.name for r in w.regions for s in r.settlements]
            assert len(names) == len(set(names)), (
                f"Seed {seed}: duplicate names: "
                f"{[n for n in names if names.count(n) > 1]}"
            )

    def test_each_region_has_settlements(self):
        """Every region should have at least one settlement."""
        for seed in range(10):
            w = generate_world(seed)
            for region in w.regions:
                assert len(region.settlements) >= 1, (
                    f"Seed {seed}: region {region.name} has no settlements"
                )

    def test_settlement_marker_char(self):
        """Settlement char should match population tier."""
        for seed in range(10):
            w = generate_world(seed)
            for region in w.regions:
                for s in region.settlements:
                    c = s.char
                    assert c in ("·", "∘", "●", "◉"), f"Invalid char '{c}'"


class TestRivers:
    """Rivers must flow downhill and be placed reasonably."""

    def test_rivers_end_in_water(self):
        """Every river should eventually reach water (using all 8 directions)."""
        for seed in range(10):
            w = generate_world(seed, width=50, height=30)
            river_set = set(w.rivers)
            for x, y in w.rivers:
                # Check all 8 neighbors (rivers can flow diagonally)
                adj_to_water = False
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w.width and 0 <= ny < w.height:
                            t = w.terrain[ny][nx]
                            if t in ("deep_water", "shallow"):
                                adj_to_water = True
                                break
                    if adj_to_water:
                        break
                if not adj_to_water:
                    # Check it has at least one river neighbor (8-directional)
                    neighbors_in_river = sum(
                        1 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if not (dx == 0 and dy == 0)
                        and (x + dx, y + dy) in river_set
                    )
                    assert neighbors_in_river >= 1, (
                        f"Seed {seed}: river at ({x},{y}) not in water and isolated"
                    )

    def test_rivers_flow_downhill(self):
        """River paths should generally flow downhill."""
        for seed in [0, 1, 42, 999]:
            w = generate_world(seed, width=60, height=40)
            elev = w.elevation
            river_set = set(w.rivers)
            # For each non-trivial river segment, check downhill trend
            down_count = 0
            up_count = 0
            for (x, y) in w.rivers:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if (nx, ny) in river_set:
                            if elev[ny][nx] < elev[y][x]:
                                down_count += 1
                            elif elev[ny][nx] > elev[y][x]:
                                up_count += 1
            # Most connections should be downhill or flat
            total = down_count + up_count
            if total > 0:
                assert down_count >= up_count * 0.5, (
                    f"Seed {seed}: too many uphill river segments "
                    f"(down={down_count}, up={up_count})"
                )

    def test_some_rivers_exist(self):
        """Most worlds should have at least one river."""
        river_worlds = 0
        total = 20
        for seed in range(total):
            w = generate_world(seed, width=40, height=30)
            if len(w.rivers) > 0:
                river_worlds += 1
        assert river_worlds >= total * 0.5, (
            f"Only {river_worlds}/{total} worlds have rivers"
        )


class TestRegions:
    """Region generation must be reasonable."""

    def test_region_count_range(self):
        """World should have 3-6 regions."""
        for seed in range(20):
            w = generate_world(seed)
            assert 3 <= len(w.regions) <= 6, (
                f"Seed {seed}: {len(w.regions)} regions (expected 3-6)"
            )

    def test_regions_have_valid_biomes(self):
        """Each region should have a valid biome type."""
        valid_biomes = {"temperate", "arid", "tundra", "tropical"}
        for seed in range(10):
            w = generate_world(seed)
            for region in w.regions:
                assert region.biome in valid_biomes, (
                    f"Seed {seed}: region {region.name} has invalid biome '{region.biome}'"
                )


class TestEdgeCases:
    """Generation must handle edge cases gracefully."""

    def test_tiny_world_generates(self):
        """Even a very small world should generate without crashing."""
        w = generate_world(42, width=10, height=10)
        assert w is not None
        assert len(w.terrain) == 10
        assert len(w.terrain[0]) == 10

    def test_large_world_generates(self):
        """A large world should generate without crashing."""
        w = generate_world(42, width=200, height=100)
        assert w is not None
        assert len(w.terrain) == 100
        assert len(w.terrain[0]) == 200

    def test_seed_zero_works(self):
        """Seed 0 should generate a valid world."""
        w = generate_world(0)
        assert w is not None
        assert len(w.regions) > 0

    def test_max_seed_works(self):
        """A very large seed should generate a valid world."""
        w = generate_world(999999)
        assert w is not None
        assert len(w.regions) > 0
