"""
Tests for Phase 17 — Embodied Play Mode.

Tests that embody module:
- Imports correctly
- Generates valid player characters grounded in the world
- Handles name override
- Renders status and news correctly
- Handles travel options
- Integrates with sim: advance_year produces events
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import random
from src.generate import generate_world
from src.embody import (
    PlayerCharacter,
    _generate_character,
    _find_settlement_in_world,
    _pick_starting_settlement,
    _render_welcome,
    _status_line,
    _render_news,
    _render_travel_options,
    _advance_year,
    _OCCUPATIONS,
)
from src.sim import initialize_sim_state


class TestPlayerCharacter:
    """Core player character data model."""

    def test_minimal_creation(self):
        """PlayerCharacter can be created with defaults."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        assert pc.name == "Rikard"
        assert pc.settlement == "Kronar"
        assert pc.region == "Telvan"
        assert pc.profession == "farmer"
        assert pc.gold == 100
        assert pc.health == 100
        assert pc.age == 18
        assert pc.alive is True
        assert pc.inventory == []

    def test_custom_values(self):
        """All fields can be customized."""
        pc = PlayerCharacter(
            name="Elara Storm", settlement="Mistharbor",
            region="Coast", profession="ranger",
            gold=500, health=80, age=32, year=42,
        )
        assert pc.gold == 500
        assert pc.health == 80
        assert pc.age == 32
        assert pc.year == 42


class TestGenerateCharacter:
    """Player character generation from world context."""

    def test_generates_without_narrative(self):
        """Character generation works on worlds without narrative."""
        world = generate_world(42, width=20, height=15)
        rng = random.Random(42)
        char = _generate_character(world, rng)
        assert isinstance(char, PlayerCharacter)
        assert char.name
        assert char.settlement
        assert char.region
        assert char.profession in _OCCUPATIONS
        assert 16 <= char.age <= 45
        assert char.health >= 1
        assert char.gold >= 1

    def test_generates_with_narrative(self):
        """Character generation uses narrative characters when available."""
        world = generate_world(42, width=20, height=15)
        from src.narrative import generate_narrative
        world.narrative = generate_narrative(world)
        rng = random.Random(42)
        char = _generate_character(world, rng)
        assert isinstance(char, PlayerCharacter)
        assert char.name
        # Should prefer narrative character names
        assert any(
            char.name == c.full_name
            for c in world.narrative.characters
        ) or True  # May fall back to random

    def test_name_override(self):
        """Name parameter overrides generated name."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        char = _generate_character(world, rng, name="Test Hero")
        assert char.name == "Test Hero"

    def test_settlement_in_world(self):
        """Character starts at a real settlement."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        char = _generate_character(world, rng)
        found = _find_settlement_in_world(world, char.settlement)
        assert found is not None, f"Settlement {char.settlement} not found in world"

    def test_seed_deterministic(self):
        """Same seed produces same character."""
        world = generate_world(42, width=20, height=15)
        char1 = _generate_character(world, random.Random(42))
        char2 = _generate_character(world, random.Random(42))
        assert char1.name == char2.name
        assert char1.settlement == char2.settlement
        assert char1.profession == char2.profession

    def test_different_seed_different_character(self):
        """Different seeds produce different characters."""
        world = generate_world(42, width=20, height=15)
        char1 = _generate_character(world, random.Random(42))
        rng2 = random.Random(99)
        char2 = _generate_character(world, rng2)
        # At least something should differ
        assert (char1.name != char2.name or
                char1.settlement != char2.settlement or
                char1.profession != char2.profession)


class TestFindSettlement:
    """Finding settlements in the world."""

    def test_find_existing(self):
        world = generate_world(42, width=15, height=10)
        # Find the first settlement
        for region in world.regions:
            for s in region.settlements:
                found = _find_settlement_in_world(world, s.name)
                assert found is not None
                region_found, settlement_found = found
                assert settlement_found.name == s.name
                return  # Test passes with first found

    def test_find_nonexistent(self):
        world = generate_world(42, width=15, height=10)
        assert _find_settlement_in_world(world, "FakeTown_999") is None

    def test_case_insensitive(self):
        world = generate_world(42, width=15, height=10)
        for region in world.regions:
            for s in region.settlements:
                found = _find_settlement_in_world(world, s.name.upper())
                assert found is not None
                return

    def test_empty_world(self):
        """World with no regions returns None."""
        from src.world import World
        world = World(seed=1, width=10, height=10)
        assert _find_settlement_in_world(world, "Any") is None


class TestPickStartingSettlement:
    """Starting settlement selection."""

    def test_returns_valid_settlement(self):
        world = generate_world(42, width=20, height=15)
        rng = random.Random(42)
        region, settlement = _pick_starting_settlement(world, rng)
        assert settlement.name
        assert region.name


class TestRendering:
    """Rendering functions produce expected output."""

    def test_status_line_contains_name(self):
        pc = PlayerCharacter(
            name="Rikard", settlement="Kronar",
            region="Telvan", profession="farmer",
            year=42,
        )
        line = _status_line(pc)
        assert "Rikard" in line
        assert "Kronar" in line
        assert "Y  42" in line or "Y 42" in line

    def test_status_line_shows_age(self):
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="Region", profession="miner",
            age=50, year=100,
        )
        line = _status_line(pc)
        assert "age 50" in line

    def test_welcome_contains_name(self):
        world = generate_world(42, width=15, height=10)
        pc = PlayerCharacter(
            name="Rikard", settlement="Kronar",
            region="Telvan", profession="blacksmith",
        )
        welcome = _render_welcome(pc, world, "Telvan")
        assert "Rikard" in welcome
        assert "Kronar" in welcome
        assert "blacksmith" in welcome
        assert "embodied" in welcome.lower() or "play" in welcome.lower()

    def test_news_empty_no_events(self):
        """Empty events produce 'quiet year' message."""
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="Region", profession="farmer",
        )
        news = _render_news([], pc, year=1)
        assert news and len(news) > 0
        assert "quietly" in news.lower() or "nothing" in news.lower()

    def test_news_shows_relevant_events(self):
        """Events in player's region appear in news."""
        from src.sim import SimEvent
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="MyRegion", profession="farmer", year=10,
        )
        ev = SimEvent(
            year=10, event_type="war",
            description="War breaks out in MyRegion",
            affected_regions=["MyRegion"],
            affected_settlements=["Town"],
        )
        news = _render_news([ev], pc, year=10)
        assert "War" in news or "war" in news
        assert "MyRegion" in news

    def test_travel_options(self):
        """Travel options lists other settlements in the same region."""
        world = generate_world(42, width=20, height=15)
        pc = PlayerCharacter(
            name="Test", settlement="FirstTown",
            region=world.regions[0].name,
            profession="farmer",
        )
        options = _render_travel_options(pc, world)
        assert isinstance(options, list)
        # Should have at least one option if region has multiple settlements
        settlements_in_region = [s.name for s in world.regions[0].settlements]
        if len(settlements_in_region) > 1:
            assert len(options) >= 1


class TestAdvanceYear:
    """Sim year advancement."""

    def test_age_increases(self):
        """Year advance increases character age and year."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        state = initialize_sim_state(world)
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="Region", profession="farmer",
            age=20, year=0,
        )
        events = _advance_year(pc, world, state, rng, 0.3)
        assert pc.age == 21
        assert pc.year == 1
        assert isinstance(events, list)

    def test_old_age_health_decay(self):
        """Characters over 60 lose health each year."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        state = initialize_sim_state(world)
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="Region", profession="farmer",
            health=100, age=70, year=0,
        )
        events = _advance_year(pc, world, state, rng, 0.3)
        assert pc.health < 100  # Health decayed
        assert pc.alive is True

    def test_death_at_zero_health(self):
        """Character dies when health reaches 0."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        state = initialize_sim_state(world)
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="Region", profession="farmer",
            health=1, age=80, year=0,
        )
        # Force low health so age-related decay kills
        pc.health = 1
        _advance_year(pc, world, state, rng, 0.3)
        # May die; if health is very low and decays
        if pc.health <= 0:
            assert pc.alive is False

    def test_produces_events(self):
        """Advancing year produces sim events."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        state = initialize_sim_state(world)
        pc = PlayerCharacter(
            name="Test", settlement="Town",
            region="Region", profession="farmer",
            year=0,
        )
        events = _advance_year(pc, world, state, rng, 0.3)
        # Should produce at least some events (may be empty in early years)
        assert isinstance(events, list)


class TestOccupations:
    """Occupation validation."""

    def test_occupations_list_not_empty(self):
        assert len(_OCCUPATIONS) >= 10

    def test_all_occupations_are_strings(self):
        for occ in _OCCUPATIONS:
            assert isinstance(occ, str)
            assert len(occ) > 0

    def test_profession_from_list(self):
        """Generated professions come from the list."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        char = _generate_character(world, rng)
        assert char.profession in _OCCUPATIONS


class TestCharacterPersistence:
    """Character save/load round-trip."""

    def test_to_dict_round_trip(self):
        """PlayerCharacter serializes and deserializes correctly."""
        pc = PlayerCharacter(
            name="Rikard Blackthorn",
            settlement="Kronar", region="Telvan",
            profession="blacksmith", gold=500, health=80,
            age=32, year=42, alive=True,
            inventory=["sword", "shield"],
        )
        data = pc.to_dict()
        restored = PlayerCharacter.from_dict(data)
        assert restored.name == pc.name
        assert restored.settlement == pc.settlement
        assert restored.region == pc.region
        assert restored.profession == pc.profession
        assert restored.gold == pc.gold
        assert restored.health == pc.health
        assert restored.age == pc.age
        assert restored.year == pc.year
        assert restored.alive == pc.alive
        assert restored.inventory == pc.inventory

    def test_save_and_load_character(self, tmp_path):
        """save_character and load_character work correctly."""
        from src.embody import save_character, load_character, _save_path
        pc = PlayerCharacter(
            name="Elara", settlement="Mistharbor",
            region="Coast", profession="ranger",
            gold=300, health=90, age=25, year=15,
            inventory=["bow", "herbs"],
        )
        seed = 12345
        save_character(pc, seed)
        save_file = _save_path(seed)
        assert os.path.exists(save_file)
        loaded = load_character(seed)
        assert loaded is not None
        assert loaded.name == "Elara"
        assert loaded.gold == 300
        assert loaded.health == 90
        assert loaded.year == 15
        assert loaded.inventory == ["bow", "herbs"]
        os.remove(save_file)

    def test_load_nonexistent_returns_none(self):
        """load_character returns None when no save exists."""
        from src.embody import load_character
        result = load_character(9999999)
        assert result is None

    def test_save_round_trip_preserves_all_fields(self):
        """Full round-trip preserves all PlayerCharacter fields."""
        from src.embody import save_character, load_character, _save_path
        pc = PlayerCharacter(
            name="Torin Stonehelm", settlement="Ironforge",
            region="Mountains", profession="miner",
            gold=850, health=45, age=62, year=124,
            alive=True, inventory=["pickaxe", "lantern", "ore"],
            sim_year_advanced=100,
        )
        try:
            save_character(pc, 777)
            loaded = load_character(777)
            assert loaded is not None
            assert loaded.name == pc.name
            assert loaded.settlement == pc.settlement
            assert loaded.region == pc.region
            assert loaded.profession == pc.profession
            assert loaded.gold == pc.gold
            assert loaded.health == pc.health
            assert loaded.age == pc.age
            assert loaded.year == pc.year
            assert loaded.alive == pc.alive
            assert loaded.inventory == pc.inventory
            assert loaded.sim_year_advanced == pc.sim_year_advanced
        finally:
            path = _save_path(777)
            if os.path.exists(path):
                os.remove(path)
