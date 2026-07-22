"""
Tests for wyrd — Simulation Serialization (compact/gzip).

Covers gzip save/load, CLI fallback loading (.json → .json.gz),
and data integrity through compact round-trips.
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.sim import run_simulation, SimState, SettlementSnapshot, SimEvent
from src.serialize import (
    save_sim_state, load_sim_state,
    sim_state_to_dict, save_world, load_world,
)

TEST_SIM_FILE = "_test_wyrd_sim"


def _cleanup():
    for f in [f"{TEST_SIM_FILE}.json", f"{TEST_SIM_FILE}.json.gz",
              f"{TEST_SIM_FILE}-42-sim.json", f"{TEST_SIM_FILE}-42-sim.json.gz",
              f"wyrd-42-sim.json", f"wyrd-42-sim.json.gz"]:
        if os.path.exists(f):
            os.remove(f)


class TestCompactSerialization:
    """Compact (gzip) save and load must work correctly."""

    def setup_method(self):
        _cleanup()

    def teardown_method(self):
        _cleanup()

    def test_save_compact_creates_gz(self):
        """Compact save should create a .json.gz file."""
        world = generate_world(42)
        result = run_simulation(world, num_years=20, chaos_factor=0.3)
        path = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=True)
        assert path.endswith(".gz"), f"Expected .gz path, got {path}"
        assert os.path.exists(path)

    def test_save_noncompact_creates_json(self):
        """Non-compact save should create a .json file."""
        world = generate_world(42)
        result = run_simulation(world, num_years=20, chaos_factor=0.3)
        path = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=False)
        assert not path.endswith(".gz")
        assert os.path.exists(path)

    def test_compact_is_smaller(self):
        """Compact gzip should be smaller than uncompressed."""
        world = generate_world(42)
        result = run_simulation(world, num_years=100, chaos_factor=0.3, snapshot_interval=25)
        path_full = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=False)
        path_compact = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=True)
        size_full = os.path.getsize(path_full.replace(".gz", ""))
        size_compact = os.path.getsize(path_compact)
        assert size_compact < size_full, (
            f"Compact ({size_compact}) should be smaller than full ({size_full})"
        )
        # Typically 5-20% of original size
        assert size_compact < size_full * 0.5, (
            f"Compact should be less than 50% of original ({size_compact}/{size_full})"
        )

    def test_load_compact(self):
        """Compact gzip should load back correctly."""
        world = generate_world(42)
        result = run_simulation(world, num_years=20, chaos_factor=0.3)
        path = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=True)
        loaded = load_sim_state(path)
        assert loaded is not None
        assert loaded["seed"] == result.seed
        assert loaded["num_years"] == 20

    def test_compact_preserves_snapshots(self):
        """Snapshots should survive compact round-trip."""
        world = generate_world(42)
        result = run_simulation(world, num_years=50, chaos_factor=0.3, snapshot_interval=10)
        path = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=True)
        loaded = load_sim_state(path)
        snap_keys = sorted(loaded.get("snapshots", {}).keys())
        assert len(snap_keys) > 0
        # Should have snapshots at multiples of 10 + final
        assert "0" in snap_keys

    def test_compact_preserves_events(self):
        """All sim events should survive compact round-trip."""
        world = generate_world(42)
        result = run_simulation(world, num_years=100, chaos_factor=0.3)
        path = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=True)
        loaded = load_sim_state(path)
        assert len(loaded["events"]) == len(result.events)
        for e1, e2 in zip(result.events, loaded["events"]):
            assert e1.year == e2["year"]
            assert e1.event_type == e2["event_type"]

    def test_compact_preserves_population_record(self):
        """Population record should survive compact round-trip."""
        world = generate_world(42)
        result = run_simulation(world, num_years=50, chaos_factor=0.3)
        path = save_sim_state(result, f"{TEST_SIM_FILE}.json", compact=True)
        loaded = load_sim_state(path)
        assert len(loaded["population_record"]) == len(result.final_state.population_record)

    def test_compact_non_existent(self):
        """Loading a non-existent file should return None."""
        result = load_sim_state("nonexistent_file.json")
        assert result is None
        result = load_sim_state("nonexistent_file.json.gz")
        assert result is None


class TestCLILoadingStrategy:
    """The CLI's fallback loading (.json → .json.gz) must work."""

    def setup_method(self):
        _cleanup()

    def teardown_method(self):
        _cleanup()

    def test_load_json_then_gz_fallback(self):
        """When .json doesn't exist but .json.gz does, loading should work via fallback."""
        world = generate_world(42)
        result = run_simulation(world, num_years=20, chaos_factor=0.3)
        save_sim_state(result, f"wyrd-42-sim.json", compact=True)

        # Try loading .json first (should fail), then .json.gz (should succeed)
        sim_data = load_sim_state("wyrd-42-sim.json")
        assert sim_data is None, "Non-existent .json should return None"

        sim_data = load_sim_state("wyrd-42-sim.json.gz")
        assert sim_data is not None, ".json.gz should load"
        assert sim_data["seed"] == result.seed

    def test_snapshot_year_from_gz(self):
        """Specific snapshot years must be loadable from gzip file."""
        world = generate_world(42)
        result = run_simulation(world, num_years=100, chaos_factor=0.3, snapshot_interval=25)
        save_sim_state(result, f"wyrd-42-sim.json", compact=True)

        loaded = load_sim_state("wyrd-42-sim.json.gz")
        snapshots = loaded["snapshots"]

        # Check specific years exist
        years = sorted(int(k) for k in snapshots.keys())
        assert 25 in years
        assert 50 in years
        assert 75 in years

        # Extract a snapshot and verify data
        snap = snapshots["50"]
        assert snap["year"] == 50
        assert len(snap["settlements"]) > 0
        assert snap["population_record"][-1]["year"] == 50


class TestSaveSimStateDirect:
    """Save a bare SimState (not SimResult) directly."""

    def setup_method(self):
        _cleanup()

    def teardown_method(self):
        _cleanup()

    def test_save_simstate_direct(self):
        """A bare SimState should also be savable as compact."""
        state = SimState(year=42)
        state.settlements["Testburg"] = SettlementSnapshot(
            name="Testburg", region="Test", x=10, y=10,
            population=500, kind="village", is_active=True,
        )
        path = save_sim_state(state, f"{TEST_SIM_FILE}.json", compact=True)
        loaded = load_sim_state(path)
        assert loaded["year"] == 42
        assert "Testburg" in loaded["settlements"]
        assert loaded["settlements"]["Testburg"]["population"] == 500

    def test_compact_deterministic(self):
        """Compact save should be deterministic for same content."""
        state = SimState(year=100)
        state.settlements["Testburg"] = SettlementSnapshot(
            name="Testburg", region="Test", x=5, y=5,
            population=1000, kind="town", is_active=True,
        )
        path1 = save_sim_state(state, f"{TEST_SIM_FILE}-1.json", compact=True)
        path2 = save_sim_state(state, f"{TEST_SIM_FILE}-2.json", compact=True)

        # Read gzip content (not the parsed dict, which normalizes keys)
        import gzip
        with gzip.open(path1, "rt") as f:
            data1 = f.read()
        with gzip.open(path2, "rt") as f:
            data2 = f.read()
        assert data1 == data2
