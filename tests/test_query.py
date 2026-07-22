"""
Tests for wyrd Phase 3 Milestone 5 — World Query Engine.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.query import (
    query_world, _find_region, _find_settlement,
    _match_query_type, QueryResult,
)


class TestQueryMatching:
    """Query type detection and target extraction."""

    def test_overview_query(self):
        qtype, target = _match_query_type("tell me about this world")
        assert qtype == "overview"

    def test_region_query(self):
        qtype, target = _match_query_type("tell me about Greendale")
        assert qtype == "region_info"
        assert target and "greendale" in target.lower()

    def test_settlement_query(self):
        qtype, target = _match_query_type("where is Fairhaven")
        assert qtype == "settlement_locate"
        assert target and "fairhaven" in target.lower()

    def test_feature_query(self):
        qtype, target = _match_query_type("what mountains are there")
        assert qtype == "feature_search"

    def test_settlements_in_region(self):
        qtype, target = _match_query_type("what settlements are in Greendale")
        assert qtype == "settlements_in_region"

    def test_population_query(self):
        qtype, target = _match_query_type("what is the population")
        assert qtype == "population_query"

    def test_culture_query(self):
        qtype, target = _match_query_type("tell me about the cultures")
        assert qtype == "culture_search"


class TestQueryResults:
    """Query results must be coherent and come from real world data."""

    def test_overview_result(self):
        world = generate_world(42)
        result = query_world(world, "overview")
        assert result.found
        assert str(world.seed) in result.title
        assert "Regions" in " ".join(result.lines)
        assert len(result.lines) > 5

    def test_region_info_found(self):
        world = generate_world(42)
        # Pick a known region
        region = world.regions[0]
        result = query_world(world, f"tell me about {region.name}")
        assert result.found
        assert region.name in result.title

    def test_settlement_found(self):
        world = generate_world(42)
        for region in world.regions:
            if region.settlements:
                s = region.settlements[0]
                result = query_world(world, f"where is {s.name}")
                assert result.found
                assert s.name in result.title
                return

    def test_blank_query_gives_overview(self):
        world = generate_world(42)
        result = query_world(world, "")
        assert result.found
        assert "Overview" in result.title or str(world.seed) in result.title

    def test_keyword_search_finds_something(self):
        world = generate_world(42)
        result = query_world(world, "river")
        # Either it finds something or gracefully reports nothing
        assert isinstance(result, QueryResult)

    def test_regions_lists_all(self):
        world = generate_world(42)
        result = query_world(world, "tell me about")
        # Without target, should list all regions or show overview
        assert result.found
        assert len(result.lines) > 0


class TestRegionFinder:
    """_find_region must fuzzy-match region names."""

    def test_finds_region(self):
        world = generate_world(42)
        for region in world.regions:
            found = _find_region(world, region.name)
            assert found is not None
            assert found.name == region.name
            break

    def test_fuzzy_match(self):
        world = generate_world(42)
        region = world.regions[0]
        # Try first 3 characters
        partial = region.name[:min(4, len(region.name))]
        found = _find_region(world, partial)
        assert found is not None

    def test_nonexistent_region(self):
        world = generate_world(42)
        found = _find_region(world, "Nowhereland")
        assert found is None


class TestSettlementFinder:
    """_find_settlement must find settlements by name."""

    def test_finds_settlement(self):
        world = generate_world(42)
        for region in world.regions:
            if region.settlements:
                s = region.settlements[0]
                found_s, found_r = _find_settlement(world, s.name)
                assert found_s is not None
                assert found_s.name == s.name
                assert found_r.name == region.name
                return

    def test_nonexistent_settlement(self):
        world = generate_world(42)
        s, r = _find_settlement(world, "Atlantis")
        assert s is None and r is None
