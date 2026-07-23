"""
Tests for wyrd REST API v1 (Phase 18: Depth & Quality).

Covers all /api/v1/ endpoints with pagination, error states,
and response shape validation.
"""

import json
import os
import threading
import time
from http.client import HTTPConnection
from http.server import HTTPServer

import pytest

from src.serve import WyrdHandler, _load_world
from src.generate import generate_world
from src.serialize import save_world, save_sim_state
from src.sim import SimState, SettlementSnapshot, SimEvent


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def world():
    """Generate a test world with full narrative, lore, etc."""
    w = generate_world(54321, width=30, height=20)
    save_world(w, "wyrd-54321.json")
    yield w
    if os.path.exists("wyrd-54321.json"):
        os.remove("wyrd-54321.json")


@pytest.fixture(scope="module")
def world_with_sim(world):
    """Create sim state for the test world."""
    state = SimState(year=200)
    for r in world.regions:
        for s in r.settlements:
            state.settlements[s.name] = SettlementSnapshot(
                name=s.name, region=r.name, kind=s.kind,
                population=s.population, x=s.x, y=s.y,
                founded_year=0, is_active=True,
            )
    state.settlements["Lostburg"] = SettlementSnapshot(
        name="Lostburg", region=world.regions[0].name,
        kind="village", population=0,
        x=3, y=3, founded_year=10, is_active=False,
    )
    state.world_modifiers = ["Post-War Rebuilding"]
    state.population_record = [
        {"year": 0, "total_population": 500},
        {"year": 100, "total_population": 2500},
        {"year": 200, "total_population": 4500},
    ]
    state.events = [
        SimEvent(year=45, event_type="founding",
                 description="Riverside founded by settlers",
                 affected_settlements=["Riverside"]),
        SimEvent(year=120, event_type="war",
                 description="War breaks out between factions",
                 affected_settlements=["Hillfort", "Oakvale"]),
    ]
    save_sim_state(state, "wyrd-54321-sim.json")
    yield state
    if os.path.exists("wyrd-54321-sim.json"):
        os.remove("wyrd-54321-sim.json")


@pytest.fixture(scope="module")
def server_port(world_with_sim):
    """Start server on random port for the whole test module."""
    server = HTTPServer(("127.0.0.1", 0), WyrdHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)
    yield port
    server.shutdown()
    thread.join(timeout=2)


# ── Helpers ─────────────────────────────────────────────────────────

def _get(port, path):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        return resp.status, resp.getheader("Content-Type", ""), body
    finally:
        conn.close()


# ── API Root ────────────────────────────────────────────────────────

class TestAPIRoot:
    def test_api_root_returns_endpoints(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1")
        assert status == 200
        assert "application/json" in ctype
        data = json.loads(body)
        assert data["wyrd"] == "Generative Fantasy Sandbox"
        assert "endpoints" in data
        assert "GET /worlds" in data["endpoints"]


# ── Worlds List ─────────────────────────────────────────────────────

class TestWorldsList:
    def test_list_worlds_returns_paginated(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total"] >= 1
        # Our world should be in the list
        seeds = [w["seed"] for w in data["data"]]
        assert 54321 in seeds

    def test_list_worlds_pagination_limit(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds?limit=1")
        data = json.loads(body)
        assert len(data["data"]) == 1
        assert data["pagination"]["limit"] == 1
        assert data["pagination"]["total"] >= 1

    def test_list_worlds_pagination_offset(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds?limit=1&offset=0")
        data0 = json.loads(body)
        status, _, body = _get(server_port, "/api/v1/worlds?limit=1&offset=1")
        data1 = json.loads(body)
        # Different worlds at different offsets
        if len(data0["data"]) > 0 and len(data1["data"]) > 0:
            assert data0["data"][0]["seed"] != data1["data"][0]["seed"]

    def test_list_worlds_invalid_limit_clamps(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds?limit=9999")
        data = json.loads(body)
        assert data["pagination"]["limit"] == 100  # Max clamped


# ── World Detail ────────────────────────────────────────────────────

class TestWorldDetail:
    def test_world_detail_returns_summary(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321")
        assert status == 200
        data = json.loads(body)
        assert data["seed"] == 54321
        assert data["width"] == 30
        assert data["height"] == 20
        assert data["regions"] > 0
        assert data["settlements"] > 0
        assert data["population"] > 0
        assert "terrain_distribution" in data
        assert data["has_lore"] is True
        assert data["has_narrative"] is True

    def test_world_detail_missing_404(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/999999")
        assert status == 404
        data = json.loads(body)
        assert "error" in data


# ── Regions ─────────────────────────────────────────────────────────

class TestRegions:
    def test_regions_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/regions")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        assert len(data["data"]) > 0
        region = data["data"][0]
        assert "name" in region
        assert "biome" in region
        assert "settlements" in region
        assert "settlement_count" in region
        assert "total_population" in region

    def test_regions_have_settlements(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/regions")
        data = json.loads(body)
        # At least one region should have settlements
        has_settlements = any(r["settlement_count"] > 0 for r in data["data"])
        assert has_settlements


# ── Settlements ─────────────────────────────────────────────────────

class TestSettlements:
    def test_settlements_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/settlements")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        assert len(data["data"]) > 0
        s = data["data"][0]
        assert "name" in s
        assert "x" in s
        assert "y" in s
        assert "population" in s
        assert "kind" in s
        assert "region" in s
        assert "biome" in s

    def test_settlements_flat_structure(self, server_port):
        """Settlements are flattened across regions with region field."""
        status, _, body = _get(server_port, "/api/v1/worlds/54321/settlements")
        data = json.loads(body)
        regions = set(s["region"] for s in data["data"])
        assert len(regions) > 0


# ── Characters ──────────────────────────────────────────────────────

class TestCharacters:
    def test_characters_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/characters")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        if len(data["data"]) > 0:
            c = data["data"][0]
            assert "name" in c
            assert "surname" in c
            assert "full_name" in c
            assert "occupation" in c
            assert "home_region" in c
            assert "home_settlement" in c
            assert "backstory" in c

    def test_characters_empty_world_returns_empty(self, server_port):
        """Non-existent world returns 404.""" 
        status, _, body = _get(server_port, "/api/v1/worlds/999999/characters")
        assert status == 404


# ── Quests ──────────────────────────────────────────────────────────

class TestQuests:
    def test_quests_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/quests")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        if len(data["data"]) > 0:
            q = data["data"][0]
            assert "name" in q
            assert "quest_type" in q
            assert "difficulty" in q
            assert "description" in q
            assert "rewards" in q


# ── Events ──────────────────────────────────────────────────────────

class TestEvents:
    def test_events_merges_narrative_and_sim(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/events")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        # Should have events from both sources
        assert len(data["data"]) > 0
        e = data["data"][0]
        assert "year" in e
        assert "type" in e
        assert "description" in e
        assert "source" in e

    def test_events_sorted_by_year(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/events")
        data = json.loads(body)
        years = [e["year"] for e in data["data"]]
        assert years == sorted(years)


# ── Factions ────────────────────────────────────────────────────────

class TestFactions:
    def test_factions_returns_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/factions")
        assert status == 200
        data = json.loads(body)
        assert "factions" in data
        assert "relationships" in data
        if len(data["factions"]) > 0:
            f = data["factions"][0]
            assert "name" in f
            assert "faction_type" in f
            assert "power_score" in f
            assert "goals" in f

    def test_factions_include_relationships(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/factions")
        data = json.loads(body)
        if len(data["relationships"]) > 0:
            r = data["relationships"][0]
            assert "faction_a" in r
            assert "faction_b" in r
            assert "rel_type" in r


# ── Adventure Zones ─────────────────────────────────────────────────

class TestZones:
    def test_zones_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/zones")
        assert status == 200
        data = json.loads(body)
        assert "data" in data
        if len(data["data"]) > 0:
            z = data["data"][0]
            assert "name" in z
            assert "zone_type" in z
            assert "char" in z
            assert "difficulty" in z
            assert "quest_hook" in z


# ── Pantheon ────────────────────────────────────────────────────────

class TestPantheon:
    def test_pantheon_returns_religions(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/pantheon")
        assert status == 200
        data = json.loads(body)
        assert "religions" in data
        assert "total_deities" in data
        assert "total_holy_sites" in data

    def test_pantheon_has_deities(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/pantheon")
        data = json.loads(body)
        if len(data["religions"]) > 0:
            rel = data["religions"][0]
            assert "name" in rel
            assert "deities" in rel
            assert "holy_sites" in rel
            assert len(rel["deities"]) > 0
            d = rel["deities"][0]
            assert "name" in d
            assert "domains" in d
            assert "description" in d


# ── Economy ─────────────────────────────────────────────────────────

class TestEconomy:
    def test_economy_returns_data(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/economy")
        assert status == 200
        data = json.loads(body)
        assert "has_economy_data" in data
        assert "settlements" in data
        assert len(data["settlements"]) > 0


# ── Magic ───────────────────────────────────────────────────────────

class TestMagic:
    def test_magic_returns_schools(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/magic")
        assert status == 200
        data = json.loads(body)
        assert "schools" in data
        if len(data["schools"]) > 0:
            s = data["schools"][0]
            assert "name" in s
            assert "description" in s


# ── Simulation ──────────────────────────────────────────────────────

class TestSimulation:
    def test_simulation_returns_summary(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/simulation")
        assert status == 200
        data = json.loads(body)
        assert data["total_years"] == 200
        assert data["total_events"] > 0
        assert "world_modifiers" in data

    def test_simulation_no_data_returns_404(self, server_port):
        """Non-existent world returns 404."""
        status, _, body = _get(server_port, "/api/v1/worlds/999999/simulation")
        assert status == 404
        data = json.loads(body)
        assert "error" in data


# ── Snapshots ───────────────────────────────────────────────────────

class TestSnapshots:
    def test_snapshots_list(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/snapshots")
        assert status == 200
        data = json.loads(body)
        assert "snapshots" in data
        if len(data["snapshots"]) > 0:
            s = data["snapshots"][0]
            assert "year" in s
            assert "settlements" in s
            assert "population" in s

    def test_snapshots_no_data_returns_404(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/999999/snapshots")
        assert status == 404
        data = json.loads(body)
        assert "error" in data


# ── Terrain ─────────────────────────────────────────────────────────

class TestTerrain:
    def test_terrain_returns_grid(self, server_port):
        status, ctype, body = _get(server_port, "/api/v1/worlds/54321/terrain")
        assert status == 200
        data = json.loads(body)
        assert data["width"] == 30
        assert data["height"] == 20
        assert "grid" in data
        assert len(data["grid"]) == 20
        assert len(data["grid"][0]) == 30
        cell = data["grid"][0][0]
        assert "x" in cell
        assert "y" in cell
        assert "terrain" in cell
        assert "elevation" in cell

    def test_terrain_cell_has_terrain_type(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/terrain")
        data = json.loads(body)
        # Check all cells have valid terrain
        for row in data["grid"]:
            for cell in row:
                assert cell["terrain"] in (
                    "deep_water", "shallow", "sand", "grass",
                    "forest", "hills", "mountains", "snow", "river",
                    "swamp", "desert",
                )


# ── Pagination Query Parameter Handling ─────────────────────────────

class TestPaginationEdgeCases:
    def test_offset_beyond_total(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/regions?offset=9999")
        data = json.loads(body)
        assert len(data["data"]) == 0
        assert data["pagination"]["offset"] == 9999

    def test_negative_offset_defaults_to_zero(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/regions?offset=-5")
        data = json.loads(body)
        assert data["pagination"]["offset"] == 0
        assert len(data["data"]) > 0

    def test_zero_limit_defaults_to_1(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/regions?limit=0")
        data = json.loads(body)
        assert data["pagination"]["limit"] == 1  # Clamped to min 1


# ── Error Handling ──────────────────────────────────────────────────

class TestErrorHandling:
    def test_invalid_seed_returns_400(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/abc")
        assert status == 400
        data = json.loads(body)
        assert "error" in data

    def test_unknown_resource_returns_404(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/frobnitz")
        assert status == 404

    def test_unknown_endpoint_returns_404(self, server_port):
        status, _, body = _get(server_port, "/api/v1/bananas")
        assert status == 404

    def test_unknown_path_returns_404(self, server_port):
        status, _, body = _get(server_port, "/api/v1/worlds/54321/magic/sub")
        assert status == 404
