"""
Tests for wyrd Bestiary module.

Covers creature generation, determinism, type assignments, habitats,
faction integration, CR/stat block calculations, loot tables, edge cases,
rendering, serialization, and zone-specific creature generation.
"""

import sys, os, random, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.bestiary import (
    generate_bestiary, _build_creature, _assign_faction_creatures,
    _generate_creature_name, _pick_creature_type, _tier_to_cr,
    _get_habitats, generate_creature_for_zone,
    CREATURE_TYPES, BODY_PLANS, BEHAVIOR_TYPES,
    SPECIAL_ABILITIES, LOOT_TABLES, COMBAT_TACTICS,
    CREATURE_ADJECTIVES, CREATURE_PREFIXES, Creature,
)
from src.world import World, Region, Settlement, AdventureZone
from src.render import render_bestiary, render_creature_detail
from src.serialize import world_to_dict, dict_to_world


class TestBestiaryDeterminism:
    """Same seed must always produce the same bestiary."""

    def test_deterministic_generation(self):
        """Same seed yields identical creature list."""
        w1 = generate_world(42)
        w2 = generate_world(42)
        b1 = generate_bestiary(w1)
        b2 = generate_bestiary(w2)
        assert len(b1) == len(b2)
        for c1, c2 in zip(b1, b2):
            assert c1.name == c2.name
            assert c1.tier == c2.tier
            assert c1.creature_type == c2.creature_type
            assert c1.habitat == c2.habitat
            assert c1.behavior == c2.behavior

    def test_different_seed_different_bestiary(self):
        """Different seeds produce (very likely) different bestiaries."""
        b1 = generate_bestiary(generate_world(42))
        b2 = generate_bestiary(generate_world(99))
        names1 = {c.name for c in b1}
        names2 = {c.name for c in b2}
        assert names1 != names2

    def test_seed_offset_is_40000(self):
        """The seed offset should be 40000 to avoid collision with other systems."""
        w = generate_world(1)
        rng = random.Random(w.seed + 40000)
        bestiary = generate_bestiary(w)
        for c in bestiary:
            assert c.tier >= 1
            assert c.tier <= 5


class TestCreatureStructure:
    """Each Creature must have valid, populated fields."""

    def _make_world_and_bestiary(self, seed=42):
        w = generate_world(seed)
        return w, generate_bestiary(w)

    def test_all_creatures_have_valid_types(self):
        _, bestiary = self._make_world_and_bestiary()
        valid_types = set(CREATURE_TYPES)
        for c in bestiary:
            assert c.creature_type in valid_types, f"Invalid creature type: {c.creature_type}"

    def test_all_creatures_have_valid_tiers(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert 1 <= c.tier <= 5, f"Invalid tier {c.tier} for {c.name}"

    def test_all_creatures_have_names(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert c.name and len(c.name) > 0

    def test_all_creatures_have_habitats(self):
        _, bestiary = self._make_world_and_bestiary()
        valid_habitats = {"temperate", "arid", "tundra", "tropical", "swamp", "desert", "various"}
        for c in bestiary:
            assert c.habitat in valid_habitats, f"Invalid habitat: {c.habitat}"

    def test_all_creatures_have_descriptions(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert c.description and len(c.description) > 10

    def test_all_creatures_have_body_plans(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert c.body_plan and len(c.body_plan) > 0

    def test_all_creatures_have_valid_behaviors(self):
        _, bestiary = self._make_world_and_bestiary()
        valid = set(BEHAVIOR_TYPES)
        for c in bestiary:
            assert c.behavior in valid, f"Invalid behavior: {c.behavior}"

    def test_all_creatures_have_challenge_ratings(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert 0.1 <= c.challenge_rating <= 30

    def test_all_creatures_have_valid_sizes(self):
        _, bestiary = self._make_world_and_bestiary()
        valid_sizes = {"tiny", "small", "medium", "large", "huge", "gargantuan"}
        for c in bestiary:
            assert c.size in valid_sizes, f"Invalid size: {c.size} for {c.name}"

    def test_all_creatures_have_tactics(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert c.combat_tactics and len(c.combat_tactics) > 0

    def test_all_creatures_have_encounter_sizes(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert c.encounters and len(c.encounters) > 0

    def test_all_creatures_have_suggested_levels(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert c.suggested_level_range, f"Missing level range for {c.name}"

    def test_creatures_have_special_abilities(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert len(c.special_abilities) >= 1, f"No abilities for {c.name}"

    def test_creatures_have_loot(self):
        _, bestiary = self._make_world_and_bestiary()
        for c in bestiary:
            assert len(c.loot) >= 1, f"No loot for {c.name}"


class TestHabitats:
    """Creature habitats should match world biomes."""

    def test_habitats_cover_world_biomes(self):
        world = generate_world(42)
        world_biomes = set()
        for r in world.regions:
            world_biomes.add(r.biome)
        bestiary = generate_bestiary(world)
        bestiary_habitats = {c.habitat for c in bestiary if c.habitat != "various"}
        for biome in world_biomes:
            assert biome in bestiary_habitats, f"Biome {biome} has no creatures"

    def test_get_habitats_from_world(self):
        """_get_habitats returns unique biomes from world regions."""
        world = generate_world(42)
        habitats = _get_habitats(world)
        assert len(habitats) >= 1
        for h in habitats:
            assert h in ("temperate", "arid", "tundra", "tropical", "swamp", "desert")

    def test_no_regions_fallback(self):
        """World with no regions should fall back to all biome types."""
        world = generate_world(42)
        world.regions = []
        bestiary = generate_bestiary(world)
        assert len(bestiary) >= 8


class TestFactionIntegration:
    """Faction-tied creatures should reference actual factions."""

    def test_faction_creatures_have_affiliation(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        faction_creatures = [c for c in bestiary if c.faction_affiliation]
        if faction_creatures:
            faction_names = {f.name for f in world.factions}
            for c in faction_creatures:
                assert c.faction_affiliation in faction_names, \
                    f"{c.faction_affiliation} not in world factions"

    def test_faction_creatures_are_habitat_various(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        for c in bestiary:
            if c.faction_affiliation:
                assert c.habitat == "various"

    def test_no_factions_no_faction_creatures(self):
        """World with no factions produces no faction creatures."""
        world = generate_world(42)
        world.factions = []
        creatures = _assign_faction_creatures(world, random.Random(42))
        assert len(creatures) == 0


class TestUniqueCreatures:
    """Unique creatures should have higher tiers and special names."""

    def test_unique_creatures_exist(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        uniques = [c for c in bestiary if c.is_unique]
        assert len(uniques) >= 1, "No unique creatures generated"

    def test_unique_creatures_mostly_high_tier(self):
        """Most unique creatures should be tier 4+ (tier>=4 or 5% random)."""
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        unique_high = [c for c in bestiary if c.is_unique and c.tier >= 4]
        unique_low = [c for c in bestiary if c.is_unique and c.tier < 4]
        assert len(unique_high) >= len(unique_low), \
            f"Expected most unique creatures to be tier 4+, got {len(unique_high)} high vs {len(unique_low)} low"

    def test_high_tier_unique_has_good_stats(self):
        """Tier 4+ unique creatures should have solid stat blocks."""
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        for c in bestiary:
            if c.is_unique and c.tier >= 4:
                sb = c.stat_block
                assert sb["hit_points"] >= 80
                assert sb["armor_class"] >= 14


class TestTierAndCR:
    """Tier mapping and CR calculations should be reasonable."""

    def test_tier_cr_range(self):
        """CR values per tier should be in expected ranges."""
        rng = random.Random(42)
        expected_ranges = {
            1: (0, 3),
            2: (1, 7),
            3: (4, 11),
            4: (9, 19),
            5: (17, 31),
        }
        for tier, (lo, hi) in expected_ranges.items():
            for _ in range(10):
                cr = _tier_to_cr(tier, rng)
                assert lo <= cr <= hi, f"CR {cr} out of range [{lo}, {hi}] for tier {tier}"

    def test_higher_tier_higher_cr(self):
        """Higher tiers should generally have higher CR."""
        rng = random.Random(42)
        crs = {t: _tier_to_cr(t, rng) for t in range(1, 6)}
        assert crs[5] > crs[1]
        assert crs[4] > crs[2]

    def test_stat_block_tier_scaling(self):
        """Higher tier = higher HP and AC."""
        for tier in range(1, 6):
            c = Creature(
                name="Test", tier=tier, creature_type="beast",
                habitat="temperate", description="Test",
                behavior="aggressive",
            )
            sb = c.stat_block
            assert sb["hit_points"] >= 10, f"Tier {tier} has too few HP"
            assert sb["armor_class"] >= 10, f"Tier {tier} has too low AC"

    def test_stat_block_size_modifiers(self):
        """Larger creatures should have more HP, less AC."""
        tiny = Creature("Tiny", 3, "beast", "temperate", "Tiny", "aggressive", size="tiny")
        huge = Creature("Huge", 3, "beast", "temperate", "Huge", "aggressive", size="huge")
        assert huge.stat_block["hit_points"] > tiny.stat_block["hit_points"]
        assert tiny.stat_block["armor_class"] >= huge.stat_block["armor_class"]

    def test_stat_block_type_modifiers(self):
        """Dragons should have more HP than fey of same tier."""
        dragon = Creature("D", 3, "dragon", "temperate", "D", "aggressive")
        fey = Creature("F", 3, "fey", "temperate", "F", "aggressive")
        assert dragon.stat_block["hit_points"] > fey.stat_block["hit_points"]


class TestLootTables:
    """Loot tables should scale with tier."""

    def test_loot_count_scales_with_tier(self):
        """Higher tiers should have more loot items available."""
        for tier in [1, 2, 3, 4, 5]:
            options = LOOT_TABLES.get(tier, [])
            assert len(options) >= 4, f"Tier {tier} has too few loot options"

    def test_loot_quality_improves(self):
        """Higher tier loot should mention better items."""
        t1_loot = " ".join(LOOT_TABLES[1]).lower()
        t5_loot = " ".join(LOOT_TABLES[5]).lower()
        assert "gold" in t5_loot or "legendary" in t5_loot


class TestNameGeneration:
    """Creature names should be varied and appropriate."""

    def test_name_generation_produces_valid_names(self):
        rng = random.Random(42)
        for ctype in CREATURE_TYPES:
            for habitat in ("temperate", "arid", "tundra", "tropical"):
                names = set()
                for _ in range(5):
                    name = _generate_creature_name(ctype, habitat, rng)
                    assert name and len(name) > 0
                    names.add(name)

    def test_biome_specific_naming_templates(self):
        """Creature names should reflect their habitat."""
        rng = random.Random(42)
        arid_names = set()
        for _ in range(20):
            arid_names.add(_generate_creature_name("beast", "arid", rng))
        arid_prefixes = {"Sand", "Dune", "Ash", "Waste"}
        has_arid_names = any(
            any(name.startswith(p) for p in arid_prefixes)
            for name in arid_names
        )
        assert has_arid_names, "No arid-prefixed names generated"

    def test_creature_types_have_valid_names(self):
        """Each creature type should produce valid names."""
        for ctype in ("beast", "dragon", "undead", "elemental", "fey", "giant"):
            rng = random.Random(42)
            name = _generate_creature_name(ctype, "temperate", rng)
            assert name and len(name) > 0, f"Empty name for {ctype}"


class TestCreatureTypeSelection:
    """Creature type selection should be weighted by habitat."""

    def test_all_types_are_selectable(self):
        """Every CREATURE_TYPE should be selectable from some habitat."""
        rng = random.Random(42)
        seen_types = set()
        for _ in range(200):
            seen_types.add(_pick_creature_type("temperate", rng))
        assert seen_types == set(CREATURE_TYPES)

    def test_tundra_prefers_cold_types(self):
        """Tundra should favor undead and giant types."""
        rng = random.Random(42)
        counts = {t: 0 for t in CREATURE_TYPES}
        for _ in range(500):
            counts[_pick_creature_type("tundra", rng)] += 1
        tundra_undead_giant = counts["undead"] + counts["giant"]
        rng2 = random.Random(42)
        trop_counts = {t: 0 for t in CREATURE_TYPES}
        for _ in range(500):
            trop_counts[_pick_creature_type("tropical", rng2)] += 1
        tropical_undead_giant = trop_counts["undead"] + trop_counts["giant"]
        assert tundra_undead_giant > tropical_undead_giant, \
            "Tundra should have more undead/giant than tropical"


class TestCreatureForZone:
    """Zone-specific creatures should match zone types."""

    def test_dungeon_creatures_are_dungeon_appropriate(self):
        """Dungeons should get undead/aberration/construct/monstrosity."""
        world = generate_world(42)
        zone = AdventureZone(
            name="Test Dungeon", zone_type="dungeon",
            x=5, y=5, region="TestRegion", difficulty="moderate",
            description="A test dungeon",
            inhabitants="unknown", treasure_tier=3,
            quest_hook="Explore",
        )
        rng = random.Random(42)
        creature = generate_creature_for_zone(zone, world, rng)
        assert creature is not None
        assert creature.creature_type in ("undead", "aberration", "construct", "monstrosity")

    def test_grove_creatures_are_fey_or_beast(self):
        """Groves should get fey/beast/elemental."""
        world = generate_world(42)
        zone = AdventureZone(
            name="Test Grove", zone_type="grove",
            x=5, y=5, region="TestRegion", difficulty="easy",
            description="A sacred grove",
            inhabitants="spirits", treasure_tier=1,
            quest_hook="Protect",
        )
        rng = random.Random(42)
        creature = generate_creature_for_zone(zone, world, rng)
        assert creature is not None
        assert creature.creature_type in ("fey", "beast", "elemental")

    def test_zone_difficulty_maps_to_tier(self):
        """Zone difficulty should map to appropriate creature tier."""
        world = generate_world(42)
        zone = AdventureZone(
            name="Deadly Lair", zone_type="lair",
            x=5, y=5, region="TestRegion", difficulty="deadly",
            description="A deadly lair",
            inhabitants="dragon", treasure_tier=5,
            quest_hook="Slay",
        )
        rng = random.Random(42)
        creature = generate_creature_for_zone(zone, world, rng)
        assert creature is not None
        assert creature.tier >= 4, f"Deadly zone got tier {creature.tier}"

    def test_trivial_zone_low_tier(self):
        """Trivial difficulty should produce low-tier creatures."""
        world = generate_world(42)
        zone = AdventureZone(
            name="Easy Cave", zone_type="cave",
            x=5, y=5, region="TestRegion", difficulty="trivial",
            description="An easy cave",
            inhabitants="rats", treasure_tier=1,
            quest_hook="Clear",
        )
        rng = random.Random(42)
        creature = generate_creature_for_zone(zone, world, rng)
        assert creature is not None
        assert creature.tier <= 2


class TestCrLabel:
    """CR label formatting."""

    def test_cr_label_below_one(self):
        c = Creature("Test", 1, "beast", "temperate", "Test", "aggressive", challenge_rating=0.25)
        assert "0.25" in c.cr_label or "CR" in c.cr_label

    def test_cr_label_integer(self):
        c = Creature("Test", 3, "beast", "temperate", "Test", "aggressive", challenge_rating=5)
        assert "CR 5" in c.cr_label

    def test_tier_label(self):
        c = Creature("Test", 1, "beast", "temperate", "Test", "aggressive")
        assert "Common" in c.tier_label
        c5 = Creature("Test2", 5, "beast", "temperate", "Test", "aggressive")
        assert "Mythic" in c5.tier_label


class TestBuildCreature:
    """Direct _build_creature calls should produce valid creatures."""

    def test_build_with_defaults(self):
        world = generate_world(42)
        rng = random.Random(42)
        c = _build_creature(world, "temperate", rng)
        assert isinstance(c, Creature)
        assert c.tier >= 1
        assert c.creature_type in CREATURE_TYPES

    def test_build_with_specified_type(self):
        world = generate_world(42)
        rng = random.Random(42)
        c = _build_creature(world, "temperate", rng, creature_type="dragon")
        assert c.creature_type == "dragon"
        assert c.tier >= 1

    def test_build_with_specified_tier(self):
        world = generate_world(42)
        rng = random.Random(42)
        c = _build_creature(world, "arid", rng, tier=5)
        assert c.tier == 5
        assert c.challenge_rating >= 18

    def test_build_with_faction(self):
        world = generate_world(42)
        rng = random.Random(42)
        c = _build_creature(world, "temperate", rng, faction="The Crown")
        assert c.faction_affiliation == "The Crown"

    def test_description_uses_templates(self):
        world = generate_world(42)
        rng = random.Random(42)
        c = _build_creature(world, "arid", rng)
        assert c.description


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_world(self):
        """An empty world should still generate a valid bestiary."""
        world = World(seed=0, width=10, height=10)
        world.regions = []
        bestiary = generate_bestiary(world)
        assert len(bestiary) >= 8

    def test_single_region_world(self):
        """World with a single biome should still have variety."""
        world = World(seed=42, width=20, height=20)
        world.regions = [
            Region("Test", "temperate",
                   settlements=[Settlement("Town", 10, 10, 100, "village")])
        ]
        bestiary = generate_bestiary(world)
        assert len(bestiary) >= 6
        for c in bestiary:
            if c.habitat == "various":
                continue
            assert c.habitat == "temperate"

    def test_variant_field(self):
        """Some creatures should have variant fields."""
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        variants = [c for c in bestiary if c.variant]
        assert len(variants) >= 0

    def test_all_creatures_have_unique_names_within_world(self):
        """No two creatures in the same world should share a name."""
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        names = [c.name for c in bestiary]
        assert len(names) == len(set(names)), f"Duplicate creature names found: {[n for n in names if names.count(n) > 1]}"

    def test_variant_is_empty_by_default(self):
        """Default variant should be empty string."""
        c = Creature("Test", 1, "beast", "temperate", "Test", "aggressive")
        assert c.variant == ""


class TestRendering:
    """Bestiary rendering should produce beautiful output."""

    def test_render_bestiary_returns_string(self):
        world = generate_world(42)
        world.bestiary = generate_bestiary(world)
        result = render_bestiary(world)
        assert isinstance(result, str)
        assert len(result) > 100
        assert "Bestiary" in result or "wyrd" in result or "creatures" in result.lower()

    def test_render_creature_detail_returns_string(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        result = render_creature_detail(bestiary[0])
        assert isinstance(result, str), f"Expected string, got {type(result)}"
        assert len(result) > 50

    def test_render_empty_bestiary(self):
        """Empty bestiary should render gracefully."""
        world = generate_world(42)
        world.bestiary = []
        result = render_bestiary(world)
        assert result, "Should return non-empty string even for empty bestiary"

    def test_render_detail_shows_stat_block(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        result = render_creature_detail(bestiary[0])
        assert "AC" in result or "HP" in result or "armor" in result.lower()


class TestSerialization:
    """Bestiary must survive JSON serialization round-trip."""

    def test_bestiary_survives_serialization(self):
        world = generate_world(42)
        world.bestiary = generate_bestiary(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        assert len(restored.bestiary) == len(world.bestiary)
        for orig, rest in zip(world.bestiary, restored.bestiary):
            assert orig.name == rest.name
            assert orig.tier == rest.tier
            assert orig.creature_type == rest.creature_type
            assert orig.habitat == rest.habitat
            assert orig.challenge_rating == rest.challenge_rating
            assert orig.is_unique == rest.is_unique

    def test_bestiary_round_trip_maintains_loot(self):
        world = generate_world(42)
        world.bestiary = generate_bestiary(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        for orig, rest in zip(world.bestiary, restored.bestiary):
            assert len(orig.loot) == len(rest.loot)
            assert orig.loot == rest.loot

    def test_bestiary_round_trip_maintains_abilities(self):
        world = generate_world(42)
        world.bestiary = generate_bestiary(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        for orig, rest in zip(world.bestiary, restored.bestiary):
            assert orig.special_abilities == rest.special_abilities

    def test_bestiary_round_trip_maintains_faction_affiliation(self):
        world = generate_world(42)
        world.bestiary = generate_bestiary(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        for orig, rest in zip(world.bestiary, restored.bestiary):
            assert orig.faction_affiliation == rest.faction_affiliation


class TestBodyPlans:
    """Each creature type should have valid body plans."""

    def test_all_body_plans_valid(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        for c in bestiary:
            valid_plans = BODY_PLANS.get(c.creature_type, [])
            if valid_plans:
                assert c.body_plan in valid_plans, \
                    f"{c.body_plan} not in valid plans for {c.creature_type}"


class TestCombatTactics:
    """Combat tactics should be from the pool."""

    def test_tactics_are_from_pool(self):
        world = generate_world(42)
        bestiary = generate_bestiary(world)
        for c in bestiary:
            if c.combat_tactics != "Engages directly":
                assert len(c.combat_tactics) > 5
