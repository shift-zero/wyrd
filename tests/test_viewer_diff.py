"""
Tests for Phase 17 — Year-diff overlay in the interactive viewer.

Tests _snapshot_populations, _compute_diff, and _draw_diff layout.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.sim import SimState, SettlementSnapshot, SimEvent
from src.viewer import _snapshot_populations, _compute_diff


class TestSnapshotPopulations:
    """_snapshot_populations correctly captures settlement state."""

    def test_empty_state(self):
        state = SimState()
        snap = _snapshot_populations(state)
        assert snap == {}

    def test_single_settlement(self):
        state = SimState()
        state.settlements["Rivendell"] = SettlementSnapshot(
            name="Rivendell", region="Vale", x=5, y=10,
            population=1200, kind="town", founded_year=0,
            prosperity=0.7, is_active=True,
        )
        snap = _snapshot_populations(state)
        assert "Rivendell" in snap
        assert snap["Rivendell"]["pop"] == 1200
        assert snap["Rivendell"]["pros"] == 0.7
        assert snap["Rivendell"]["active"] is True

    def test_abandoned_settlement(self):
        state = SimState()
        state.settlements["Ghost"] = SettlementSnapshot(
            name="Ghost", region="Marsh", x=3, y=7,
            population=0, kind="hamlet", founded_year=0,
            prosperity=0.0, is_active=False,
        )
        snap = _snapshot_populations(state)
        assert snap["Ghost"]["active"] is False


class TestComputeDiff:
    """_compute_diff correctly identifies changes between snapshots."""

    def make_state(self, data: dict) -> SimState:
        """Build SimState from dict of {name: {pop, pros, active}}."""
        state = SimState()
        for name, props in data.items():
            state.settlements[name] = SettlementSnapshot(
                name=name, region="Test", x=0, y=0,
                population=props.get("pop", 100),
                kind="village", founded_year=0,
                prosperity=props.get("pros", 0.5),
                is_active=props.get("active", True),
            )
        state.year = 100
        return state

    def test_no_changes(self):
        prev = {"Alpha": {"pop": 100, "pros": 0.5, "active": True}}
        state = self.make_state({"Alpha": {"pop": 100, "pros": 0.5}})
        diff = _compute_diff(prev, state)
        assert len(diff["grew"]) == 0
        assert len(diff["shrank"]) == 0
        assert len(diff["new"]) == 0
        assert len(diff["abandoned"]) == 0

    def test_population_growth(self):
        prev = {"Alpha": {"pop": 100, "pros": 0.5, "active": True}}
        state = self.make_state({"Alpha": {"pop": 150, "pros": 0.5}})
        diff = _compute_diff(prev, state)
        assert len(diff["grew"]) == 1
        name, old, new_, delta = diff["grew"][0]
        assert name == "Alpha"
        assert old == 100
        assert new_ == 150
        assert delta == 50

    def test_population_decline(self):
        prev = {"Alpha": {"pop": 200, "pros": 0.5, "active": True}}
        state = self.make_state({"Alpha": {"pop": 120, "pros": 0.5}})
        diff = _compute_diff(prev, state)
        assert len(diff["shrank"]) == 1
        name, old, new_, delta = diff["shrank"][0]
        assert name == "Alpha"
        assert delta == -80

    def test_new_settlement(self):
        prev = {"Alpha": {"pop": 100, "pros": 0.5, "active": True}}
        state = self.make_state({
            "Alpha": {"pop": 100, "pros": 0.5},
            "Beta": {"pop": 50, "pros": 0.3},
        })
        diff = _compute_diff(prev, state)
        assert len(diff["new"]) == 1
        name, pop, pros = diff["new"][0]
        assert name == "Beta"
        assert pop == 50

    def test_abandonment(self):
        prev = {"Alpha": {"pop": 100, "pros": 0.5, "active": True}}
        state = self.make_state({"Alpha": {"pop": 0, "pros": 0.0}})
        state.settlements["Alpha"].is_active = False
        diff = _compute_diff(prev, state)
        assert len(diff["abandoned"]) == 1
        assert diff["abandoned"][0] == "Alpha"

    def test_rebuilt_settlement(self):
        prev = {"Alpha": {"pop": 0, "pros": 0.0, "active": False}}
        state = self.make_state({"Alpha": {"pop": 80, "pros": 0.4}})
        diff = _compute_diff(prev, state)
        assert len(diff["rebuilt"]) == 1
        assert diff["rebuilt"][0] == "Alpha"

    def test_mixed_changes(self):
        prev = {
            "A": {"pop": 100, "pros": 0.5, "active": True},
            "B": {"pop": 200, "pros": 0.5, "active": True},
            "C": {"pop": 50, "pros": 0.3, "active": True},
        }
        state = self.make_state({
            "A": {"pop": 150, "pros": 0.6},  # grew
            "B": {"pop": 50, "pros": 0.2},   # shrank
            "C": {"pop": 50, "pros": 0.3},   # unchanged
            "D": {"pop": 30, "pros": 0.4},   # new
        })
        diff = _compute_diff(prev, state)
        assert len(diff["grew"]) == 1
        assert diff["grew"][0][0] == "A"
        assert len(diff["shrank"]) == 1
        assert diff["shrank"][0][0] == "B"
        assert len(diff["new"]) == 1
        assert diff["new"][0][0] == "D"

    def test_prosperity_change_threshold(self):
        """Small prosperity changes (<5%) should not appear."""
        prev = {"A": {"pop": 100, "pros": 0.50, "active": True}}
        state = self.make_state({"A": {"pop": 100, "pros": 0.52}})
        diff = _compute_diff(prev, state)
        assert len(diff["pros_up"]) == 0  # +2% below threshold

        state2 = self.make_state({"A": {"pop": 100, "pros": 0.60}})
        diff2 = _compute_diff(prev, state2)
        assert len(diff2["pros_up"]) == 1  # +10% above threshold

    def test_seed_deterministic_diff(self):
        """Same inputs always produce same diff output."""
        prev = {"A": {"pop": 100, "pros": 0.5, "active": True}}
        state1 = self.make_state({"A": {"pop": 150, "pros": 0.5}})
        state2 = self.make_state({"A": {"pop": 150, "pros": 0.5}})
        d1 = _compute_diff(prev, state1)
        d2 = _compute_diff(prev, state2)
        assert d1["grew"] == d2["grew"]

    def test_year_in_diff(self):
        prev = {"A": {"pop": 100, "pros": 0.5, "active": True}}
        state = self.make_state({"A": {"pop": 100, "pros": 0.5}})
        state.year = 42
        diff = _compute_diff(prev, state)
        assert diff["year"] == 42
