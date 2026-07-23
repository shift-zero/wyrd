"""
Tests for wyrd Phase 6 — TTRPG Campaign Export.

Covers export structure, content correctness, snapshot-year integration,
and edge cases (no narrative, no chronicles, etc.).
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.export_ttrpg import (
    export_world_ttrpg,
    _terrain_percentages,
    _build_encounter_tables,
    _build_random_tables,
    _build_settlement_statblocks,
    _build_npc_roster,
    _build_factions_section,
    _build_quest_hooks,
    _build_geography,
)


class TestExportStructure:
    """The JSON structure must contain all required sections."""

    def _export(self, world, **kwargs):
        return json.loads(export_world_ttrpg(world, **kwargs))

    def test_top_level_keys_present(self):
        """Should have all required top-level sections."""
        world = generate_world(42)
        doc = self._export(world)
        expected_keys = {
            "meta", "campaign_settings", "geography", "chronicles",
            "settlements", "npcs", "factions", "quests",
            "history", "encounters", "random_tables",
        }
        assert expected_keys.issubset(doc.keys()), f"Missing keys: {expected_keys - doc.keys()}"

    def test_meta_contains_seed_and_format(self):
        """Meta should identify format, version, and seed."""
        world = generate_world(42)
        doc = self._export(world)
        assert doc["meta"]["format"] == "wyrd-ttrpg"
        assert doc["meta"]["seed"] == 42
        assert doc["meta"]["snapshot_year"] is None

    def test_meta_with_snapshot_year(self):
        """When snapshot_year is provided, meta should include it."""
        world = generate_world(42)
        doc = self._export(world, snapshot_year=150)
        assert doc["meta"]["snapshot_year"] == 150

    def test_campaign_settings(self):
        """Campaign settings should have seed, population, settlement count."""
        world = generate_world(42)
        doc = self._export(world)
        cs = doc["campaign_settings"]
        assert cs["seed"] == 42
        assert cs["total_population"] > 0
        assert cs["total_settlements"] > 0
        assert cs["region_count"] > 0


class TestExportContent:
    """Content within each section must be correct."""

    def test_geography_contains_regions(self):
        """Geography should list all regions with biomes and settlements."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        geo = doc["geography"]
        assert len(geo["regions"]) > 0
        for r in geo["regions"]:
            assert "name" in r
            assert "biome" in r
            assert "settlements" in r

    def test_geography_has_terrain_distribution(self):
        """Should include terrain and biome percentage distributions."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        geo = doc["geography"]
        assert "terrain_distribution" in geo
        total = sum(geo["terrain_distribution"].values())
        assert abs(total - 100.0) < 1.0, f"Terrain percentages should sum to ~100, got {total}"

    def test_settlements_have_statblocks(self):
        """Each settlement should have name, kind, population, governance, features."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        for s in doc["settlements"]:
            assert "name" in s
            assert "kind" in s
            assert "population" in s
            assert "governance" in s
            assert "notable_features" in s
            assert "economy" in s

    def test_encounter_tables_derived_from_terrain(self):
        """Encounters should be organized by terrain type present in the world."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        tables = doc["encounters"]
        assert len(tables) > 0
        for terrain, table in tables.items():
            assert "theme" in table
            assert "d10_encounters" in table
            assert len(table["d10_encounters"]) == 10

    def test_random_tables_include_useful_sections(self):
        """Random tables should have settlement names, NPC names, weather, rumours."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        rt = doc["random_tables"]
        assert "settlement_names" in rt
        assert "character_names" in rt
        assert "weather" in rt
        assert "tavern_names" in rt


class TestExportWithNarrative:
    """When narrative data exists, NPCs and quests must be populated."""

    def test_npcs_from_narrative(self):
        """NPC roster should draw from narrative characters."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        if world.narrative and world.narrative.characters:
            assert len(doc["npcs"]) == len(world.narrative.characters)
            for npc in doc["npcs"]:
                assert "name" in npc
                assert "occupation" in npc
                assert "ttrpg_stats" in npc

    def test_quests_from_narrative(self):
        """Quests section should draw from narrative quests."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        if world.narrative and world.narrative.quests:
            assert len(doc["quests"]) == len(world.narrative.quests)

    def test_npc_stats_are_reasonable(self):
        """Generated TTRPG stats should be within 1-20 range."""
        world = generate_world(42)
        doc = json.loads(export_world_ttrpg(world))
        for npc in doc["npcs"]:
            stats = npc["ttrpg_stats"]
            for stat_name in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
                assert stat_name in stats
                assert 1 <= stats[stat_name] <= 20


class TestExportEdgeCases:
    """Export must handle missing data gracefully."""

    def test_no_narrative(self):
        """Export should work when narrative is None."""
        world = generate_world(42)
        world.narrative = None
        doc = json.loads(export_world_ttrpg(world))
        assert doc["npcs"] == []
        assert doc["quests"] == []

    def test_no_chronicles(self):
        """Export should work when chronicles is None."""
        world = generate_world(42)
        world.chronicles = None
        doc = json.loads(export_world_ttrpg(world))
        assert doc["chronicles"] == []
        # campaign_settings should still function
        assert doc["campaign_settings"]["total_population"] > 0

    def test_no_factions(self):
        """Export should work when factions list is empty."""
        world = generate_world(42)
        world.factions = []
        world.faction_relationships = []
        world.lore.relationships = []
        doc = json.loads(export_world_ttrpg(world))
        assert doc["factions"]["factions"] == []
        assert doc["factions"]["relationships"] == []
        assert doc["factions"]["total_factions"] == 0

    def test_tiny_world(self):
        """Export should work on very small worlds."""
        world = generate_world(42, width=20, height=15)
        doc = json.loads(export_world_ttrpg(world))
        assert doc["meta"]["seed"] == 42

    def test_deterministic_export(self):
        """Same seed should produce identical exports."""
        w1 = generate_world(42)
        w2 = generate_world(42)
        r1 = json.loads(export_world_ttrpg(w1))
        r2 = json.loads(export_world_ttrpg(w2))
        # Compare non-timestamp fields
        del r1["meta"]["generated"]
        del r2["meta"]["generated"]
        assert r1 == r2


class TestExportHelperFunctions:
    """Internal helper functions should work correctly."""

    def test_terrain_percentages_sum(self):
        """Terrain percentages should sum to ~100%."""
        world = generate_world(42)
        pcts = _terrain_percentages(world)
        total = sum(pcts.values())
        assert abs(total - 100.0) < 1.0

    def test_encounter_tables_structure(self):
        """Encounter tables should have correct structure for each terrain type."""
        world = generate_world(42)
        tables = _build_encounter_tables(world)
        for terrain, table in tables.items():
            assert "theme" in table, f"{terrain} missing theme"
            assert len(table["d10_encounters"]) == 10, f"{terrain} should have 10 encounters"

    def test_random_tables_have_all_sections(self):
        """Random tables must include settlement, NPC, weather, and tavern generators."""
        world = generate_world(42)
        tables = _build_random_tables(world)
        assert "settlement_names" in tables
        assert "character_names" in tables
        assert "rumours" in tables
        assert "weather" in tables
        assert "tavern_names" in tables

    def test_settlement_statblocks(self):
        """Statblocks should have tier-appropriate governance and features."""
        world = generate_world(42)
        statblocks = _build_settlement_statblocks(world)
        for s in statblocks:
            assert "defenses" in s
            assert "economy" in s
            assert len(s["economy"]) >= 1
            if s["kind"] == "hamlet":
                assert len(s["defenses"]) >= 1

    def test_geography_includes_map_stats(self):
        """Geography should include map dimensions and land/water ratio."""
        world = generate_world(42)
        geo = _build_geography(world)
        assert "map" in geo
        assert geo["map"]["dimensions"] == "80×40"
        assert 0 < geo["map"]["land_percentage"] < 100

    def test_factions_empty_when_no_factions(self):
        """With no factions, the section should be empty."""
        world = generate_world(42)
        world.factions = []
        world.faction_relationships = []
        world.lore.relationships = []
        factions = _build_factions_section(world)
        assert factions["factions"] == []
        assert factions["relationships"] == []
        assert factions["total_factions"] == 0

    def test_quest_hooks_without_narrative(self):
        """With no narrative, quest hooks should be empty."""
        world = generate_world(42)
        world.narrative = None
        hooks = _build_quest_hooks(world)
        assert hooks == []
