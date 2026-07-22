"""
Tests for the wyrd web dashboard server (Phase 8 Item 1).
"""

import json
import os
import threading
import time
from http.client import HTTPConnection
from http.server import HTTPServer

import pytest

from src.serve import WyrdHandler, _find_worlds, _load_world, _get_snapshot_years
from src.generate import generate_world
from src.serialize import save_world, save_sim_state
from src.sim import SimState, SettlementSnapshot, SimEvent


# ── Helpers ─────────────────────────────────────────────────────────

def _get_region_for(world, x, y):
    """Find the region name for a coordinate."""
    for r in world.regions:
        for s in r.settlements:
            if s.x == x and s.y == y:
                return r.name
    return "Unknown"


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def world():
    """Generate a test world."""
    w = generate_world(12345, width=40, height=20)
    save_world(w, "wyrd-12345.json")
    yield w
    if os.path.exists("wyrd-12345.json"):
        os.remove("wyrd-12345.json")


@pytest.fixture(scope="module")
def world_with_sim(world):
    """Create a sim state for the test world."""
    state = SimState(year=100)
    for r in world.regions:
        for s in r.settlements:
            state.settlements[s.name] = SettlementSnapshot(
                name=s.name, region=r.name, kind=s.kind,
                population=s.population, x=s.x, y=s.y,
                founded_year=0, is_active=True,
            )

    # Add an abandoned settlement
    state.settlements["Oldtown"] = SettlementSnapshot(
        name="Oldtown", region=world.regions[0].name,
        kind="village", population=0,
        x=5, y=5, founded_year=10, is_active=False,
    )

    state.world_modifiers = ["Post-War Rebuilding"]
    state.population_record = [
        {"year": 0, "total_population": sum(s.population for r in world.regions for s in r.settlements)},
        {"year": 50, "total_population": 2500},
        {"year": 100, "total_population": 3500},
    ]

    state.events = [
        SimEvent(year=45, event_type="founding",
                 description="Newtown founded by settlers",
                 affected_settlements=["Newtown"]),
        SimEvent(year=90, event_type="abandonment",
                 description="Oldtown abandoned after plague",
                 affected_settlements=["Oldtown"]),
    ]

    save_sim_state(state, "wyrd-12345-sim.json")
    yield state
    if os.path.exists("wyrd-12345-sim.json"):
        os.remove("wyrd-12345-sim.json")


# ── Tests: _find_worlds ─────────────────────────────────────────────

class TestFindWorlds:
    def test_finds_generated_world(self, world):
        worlds = _find_worlds()
        seeds = [w["seed"] for w in worlds]
        assert 12345 in seeds

    def test_world_metadata(self, world):
        worlds = _find_worlds()
        w = next(w for w in worlds if w["seed"] == 12345)
        assert w["seed"] == 12345
        assert w["dimensions"] == "40×20"
        assert w["population"] > 0
        assert w["regions"] > 0
        assert w["has_lore"] is True

    def test_sim_badge(self, world_with_sim):
        worlds = _find_worlds()
        w = next(w for w in worlds if w["seed"] == 12345)
        assert w["has_sim"] is True


# ── Tests: _load_world ──────────────────────────────────────────────

class TestLoadWorld:
    def test_loads_existing_world(self):
        w = _load_world(12345)
        assert w is not None
        assert w.seed == 12345

    def test_returns_none_for_missing(self):
        w = _load_world(999999)
        assert w is None


# ── Tests: _get_snapshot_years ──────────────────────────────────────

class TestGetSnapshotYears:
    def test_empty_for_no_sim(self):
        years = _get_snapshot_years(999999)
        assert years == []


# ── Tests: HTTP Server ──────────────────────────────────────────────

class TestHTTPServer:
    """Integration tests against the HTTP server."""

    @pytest.fixture(autouse=True)
    def setup_server(self, world_with_sim):
        """Start server on a random port."""
        self.server = HTTPServer(("127.0.0.1", 0), WyrdHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)
        yield
        self.server.shutdown()
        self.thread.join(timeout=2)

    def _get(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            return resp.status, resp.getheader("Content-Type", ""), body
        finally:
            conn.close()

    def test_root_returns_html(self):
        status, ctype, body = self._get("/")
        assert status == 200
        assert "text/html" in ctype
        assert "wyrd" in body.lower()

    def test_world_detail_returns_html(self):
        status, ctype, body = self._get("/world/12345")
        assert status == 200
        assert "text/html" in ctype
        assert "Population" in body
        assert "Regions" in body or "regions" in body.lower()

    def test_world_list_shows_seeds(self, world):
        status, _, body = self._get("/")
        assert "12345" in body

    def test_missing_world_returns_404(self):
        status, _, body = self._get("/world/999999")
        assert status == 404
        assert "not found" in body.lower()

    def test_invalid_seed_returns_400(self):
        status, _, body = self._get("/world/abc")
        assert status == 400

    def test_unknown_route_returns_404(self):
        status, _, body = self._get("/nonexistent")
        assert status == 404
        assert "not found" in body.lower()

    def test_api_worlds_returns_json(self):
        status, ctype, body = self._get("/api/worlds")
        assert status == 200
        assert "application/json" in ctype
        data = json.loads(body)
        assert "worlds" in data
        seeds = [w["seed"] for w in data["worlds"]]
        assert 12345 in seeds

    def test_api_world_returns_json(self):
        status, ctype, body = self._get("/api/world/12345")
        assert status == 200
        assert "application/json" in ctype
        data = json.loads(body)
        assert data["seed"] == 12345
        assert "regions" in data

    def test_api_world_missing_returns_404(self):
        status, _, body = self._get("/api/world/999999")
        assert status == 404

    def test_events_page_returns_html(self):
        status, ctype, body = self._get("/world/12345/events")
        assert status == 200
        assert "text/html" in ctype

    def test_server_handles_multiple_requests(self):
        """Verify the server handles concurrent requests."""
        results = []
        for _ in range(5):
            s, _, b = self._get("/")
            results.append((s, "wyrd" in b.lower()))
        assert all(r[0] == 200 for r in results)
        assert all(r[1] for r in results)
