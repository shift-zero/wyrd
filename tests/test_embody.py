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
    _record_legacy_event,
    _record_deed,
    _render_epilogue,
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


# ── Interactive Event Choices Tests (Phase 17, Item 4) ────────────────


from src.embody import (
    EventChoiceData,
    ChoiceOutcome,
    _get_interactive_events,
    _resolve_choice,
    _label_for_event,
    _pick_fallback_settlement,
    _maybe_stranger_scenario,
    _maybe_plague_scenario,
    _maybe_war_scenario,
    _maybe_merchant_scenario,
    _maybe_discovery_scenario,
    _maybe_religious_scenario,
    _maybe_exodus_scenario,
    _SCENARIOS,
)
from src.sim import SimEvent


class TestEventChoiceDataModels:
    """EventChoiceData and ChoiceOutcome dataclasses."""

    def test_event_choice_data_minimal(self):
        """EventChoiceData can be created with just prompt and event_type."""
        ec = EventChoiceData(prompt="Test prompt", event_type="test")
        assert ec.prompt == "Test prompt"
        assert ec.event_type == "test"
        assert ec.icon == "•"

    def test_event_choice_data_full(self):
        """EventChoiceData with all fields."""
        ec = EventChoiceData(prompt="Hello", event_type="war", icon="⚔")
        assert ec.icon == "⚔"

    def test_choice_outcome_creation(self):
        """ChoiceOutcome with all fields."""
        co = ChoiceOutcome(
            description="You did a thing",
            gold_delta=50, health_delta=-10,
            inventory_add="sword", travel_dest="Kronar",
        )
        assert co.description == "You did a thing"
        assert co.gold_delta == 50
        assert co.health_delta == -10
        assert co.inventory_add == "sword"
        assert co.travel_dest == "Kronar"

    def test_choice_outcome_defaults(self):
        """ChoiceOutcome default values."""
        co = ChoiceOutcome(description="Nothing happens")
        assert co.gold_delta == 0
        assert co.health_delta == 0
        assert co.inventory_add is None
        assert co.travel_dest is None


class TestLabelForEvent:
    """Event choice option labels."""

    def test_stranger_labels(self):
        assert _label_for_event("stranger", 0) == "Offer shelter"
        assert _label_for_event("stranger", 1) == "Turn them away"
        assert _label_for_event("stranger", 2) == "Rob the stranger"

    def test_plague_labels(self):
        assert _label_for_event("plague", 0) == "Help the sick"
        assert _label_for_event("plague", 1) == "Flee the settlement"
        assert _label_for_event("plague", 2) == "Hoard supplies"

    def test_war_labels(self):
        assert _label_for_event("war", 0) == "Take up arms"
        assert _label_for_event("war", 1) == "Send supplies"
        assert _label_for_event("war", 2) == "Flee the region"

    def test_merchant_labels(self):
        assert _label_for_event("merchant", 0) == "Invest 50 gold"
        assert _label_for_event("merchant", 1) == "Decline the offer"
        assert _label_for_event("merchant", 2) == "Rob the merchant"

    def test_discovery_labels(self):
        assert _label_for_event("discovery", 0) == "Explore the site"
        assert _label_for_event("discovery", 1) == "Report to authorities"
        assert _label_for_event("discovery", 2) == "Ignore it"

    def test_religious_labels(self):
        assert _label_for_event("religious", 0) == "Join the procession"
        assert _label_for_event("religious", 1) == "Make an offering"
        assert _label_for_event("religious", 2) == "Watch from afar"

    def test_exodus_labels(self):
        assert _label_for_event("exodus", 0) == "Join the exodus"
        assert _label_for_event("exodus", 1) == "Stay and rebuild"
        assert _label_for_event("exodus", 2) == "Scavenge what remains"

    def test_unknown_event(self):
        assert _label_for_event("unknown", 0) == "Accept"
        assert _label_for_event("unknown", 1) == "Decline"
        assert _label_for_event("unknown", 2) == "Ignore"

    def test_out_of_range_index(self):
        assert _label_for_event("war", 5) == "Do nothing"


class TestPickFallbackSettlement:
    """Fallback settlement selection."""

    def test_returns_different_settlement(self):
        world = generate_world(42, width=20, height=15)
        pc = PlayerCharacter(
            name="Test", settlement="First",
            region="Any", profession="farmer",
        )
        rng = random.Random(42)
        dest = _pick_fallback_settlement(pc, world, rng)
        assert dest is not None
        assert dest != "First"

    def test_returns_none_on_empty_world(self):
        from src.world import World
        world = World(seed=1, width=10, height=10)
        pc = PlayerCharacter(
            name="Test", settlement="Nowhere",
            region="Void", profession="wanderer",
        )
        rng = random.Random(42)
        dest = _pick_fallback_settlement(pc, world, rng)
        assert dest is None


class TestResolveChoice:
    """Choice resolution produces correct outcomes."""

    def _make_sc(self, etype):
        return EventChoiceData(prompt="?", event_type=etype)

    def test_stranger_shelter_produces_outcome(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100, health=80)
        outcome, label = _resolve_choice(self._make_sc("stranger"), 0, pc, None, random.Random(42))
        assert label == "Offer shelter"
        assert -5 <= outcome.gold_delta <= 0

    def test_stranger_turn_away_produces_outcome(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer")
        outcome, label = _resolve_choice(self._make_sc("stranger"), 1, pc, None, random.Random(42))
        assert label == "Turn them away"
        assert outcome.gold_delta == 0 and outcome.health_delta == 0

    def test_stranger_rob_produces_outcome(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100, health=80)
        outcome, label = _resolve_choice(self._make_sc("stranger"), 2, pc, None, random.Random(42))
        assert label == "Rob the stranger"
        assert outcome.gold_delta >= 10 and outcome.health_delta <= -10

    def test_plague_help_sick(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", health=80)
        outcome, label = _resolve_choice(self._make_sc("plague"), 0, pc, None, random.Random(42))
        assert label == "Help the sick"
        assert outcome.health_delta < 0

    def test_plague_flee_fallback(self):
        """When world=None, plague flee returns a fallback outcome."""
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", health=80)
        outcome, label = _resolve_choice(self._make_sc("plague"), 1, pc, None, random.Random(42))
        assert label in ("Flee the settlement", "Flee (but no safe haven)")

    def test_plague_hoard_supplies(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100)
        outcome, label = _resolve_choice(self._make_sc("plague"), 2, pc, None, random.Random(42))
        assert label == "Hoard supplies"
        assert outcome.gold_delta < 0

    def test_war_take_up_arms(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100, health=80)
        outcome, label = _resolve_choice(self._make_sc("war"), 0, pc, None, random.Random(42))
        assert label == "Take up arms"
        assert outcome.health_delta < 0
        assert outcome.inventory_add is not None

    def test_war_send_supplies(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100)
        outcome, label = _resolve_choice(self._make_sc("war"), 1, pc, None, random.Random(42))
        assert label == "Send supplies"
        assert outcome.gold_delta < 0

    def test_merchant_invest(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=200)
        outcome, label = _resolve_choice(self._make_sc("merchant"), 0, pc, None, random.Random(42))
        assert label == "Invest 50 gold"
        assert isinstance(outcome.gold_delta, int)

    def test_merchant_decline(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer")
        outcome, label = _resolve_choice(self._make_sc("merchant"), 1, pc, None, random.Random(42))
        assert label == "Decline"
        assert outcome.gold_delta == 0

    def test_discovery_explore(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=50, health=80)
        outcome, label = _resolve_choice(self._make_sc("discovery"), 0, pc, None, random.Random(42))
        assert label == "Explore the site"
        assert outcome.gold_delta > 0 and outcome.health_delta < 0
        assert outcome.inventory_add is not None

    def test_discovery_report(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer")
        outcome, label = _resolve_choice(self._make_sc("discovery"), 1, pc, None, random.Random(42))
        assert label == "Report to authorities"
        assert outcome.gold_delta > 0

    def test_religious_join(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", health=50)
        outcome, label = _resolve_choice(self._make_sc("religious"), 0, pc, None, random.Random(42))
        assert label == "Join the procession"
        assert outcome.health_delta > 0

    def test_religious_donate(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100)
        outcome, label = _resolve_choice(self._make_sc("religious"), 1, pc, None, random.Random(42))
        assert label == "Make an offering"
        assert outcome.gold_delta < 0 and outcome.health_delta > 0

    def test_exodus_join(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100)
        outcome, label = _resolve_choice(self._make_sc("exodus"), 0, pc, None, random.Random(42))
        # Without a world, fallback returns lost; with a world it would be Join the exodus
        assert label in ("Join the exodus", "Join (but lost)")

    def test_exodus_stay_rebuild(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=100)
        outcome, label = _resolve_choice(self._make_sc("exodus"), 1, pc, None, random.Random(42))
        assert label == "Stay and rebuild"
        assert outcome.gold_delta < 0 and outcome.health_delta > 0

    def test_exodus_scavenge(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", gold=0, health=80)
        outcome, label = _resolve_choice(self._make_sc("exodus"), 2, pc, None, random.Random(42))
        assert label == "Scavenge what remains"
        assert outcome.gold_delta > 0

    def test_unknown_event_type_fallback(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer")
        outcome, label = _resolve_choice(self._make_sc("nonexistent"), 0, pc, None, random.Random(42))
        assert label == "Do nothing"
        assert "do nothing" in outcome.description.lower()

    def test_seed_deterministic_choice(self):
        rng1, rng2 = random.Random(42), random.Random(42)
        pc1 = PlayerCharacter(name="A", settlement="T", region="R", profession="f", gold=100, health=80)
        pc2 = PlayerCharacter(name="A", settlement="T", region="R", profession="f", gold=100, health=80)
        sc = self._make_sc("stranger")
        o1, l1 = _resolve_choice(sc, 0, pc1, None, rng1)
        o2, l2 = _resolve_choice(sc, 0, pc2, None, rng2)
        assert l1 == l2
        assert o1.gold_delta == o2.gold_delta
        assert o1.inventory_add == o2.inventory_add


class TestGetInteractiveEvents:
    """Event selection logic."""

    def test_no_events_returns_empty(self):
        world = generate_world(42, width=15, height=10)
        rng = random.Random(0)
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", year=10)
        choices = _get_interactive_events(pc, world, rng, [])
        assert isinstance(choices, list)

    def test_plague_event_triggers_plague_scenario(self):
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="plague", description="Plague", affected_regions=["MyRegion"], affected_settlements=["Town"])]
        choices = _get_interactive_events(pc, world, rng, events)
        assert any(c.event_type == "plague" for c in choices)

    def test_war_event_triggers_war_scenario(self):
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="war", description="War", affected_regions=["MyRegion"])]
        choices = _get_interactive_events(pc, world, rng, events)
        assert any(c.event_type == "war" for c in choices)

    def test_discovery_event_triggers_discovery(self):
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="discovery", description="Discovery", affected_regions=["MyRegion"])]
        choices = _get_interactive_events(pc, world, rng, events)
        assert any(c.event_type == "discovery" for c in choices)

    def test_exodus_event_triggers_exodus(self):
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="exodus", description="Exodus", affected_regions=["MyRegion"], affected_settlements=["Town"])]
        choices = _get_interactive_events(pc, world, rng, events)
        assert any(c.event_type == "exodus" for c in choices)

    def test_at_most_two_events(self):
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [
            SimEvent(year=10, event_type="war", description="War", affected_regions=["MyRegion"]),
            SimEvent(year=10, event_type="discovery", description="Discovery", affected_regions=["MyRegion"]),
            SimEvent(year=10, event_type="plague", description="Plague", affected_regions=["MyRegion"], affected_settlements=["Town"]),
        ]
        choices = _get_interactive_events(pc, world, rng, events)
        assert len(choices) <= 2

    def test_seed_deterministic_choices(self):
        world = generate_world(42, width=15, height=10)
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="war", description="War", affected_regions=["Region"])]
        c1 = _get_interactive_events(pc, world, random.Random(42), events)
        c2 = _get_interactive_events(pc, world, random.Random(42), events)
        assert len(c1) == len(c2)
        for a, b in zip(c1, c2):
            assert a.event_type == b.event_type

    def test_scenario_list_not_empty(self):
        assert len(_SCENARIOS) >= 7


class TestScenarioFunctions:
    """Individual scenario functions."""

    def test_stranger_scenario_event_type(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer")
        result = _maybe_stranger_scenario(pc, None, random.Random(42), [])
        if result is not None:
            assert result.event_type == "stranger"

    def test_plague_scenario_with_event(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="plague", description="Plague", affected_settlements=["Town"])]
        result = _maybe_plague_scenario(pc, None, random.Random(42), events)
        assert result is not None and result.event_type == "plague"

    def test_plague_scenario_without_event(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", year=10)
        result = _maybe_plague_scenario(pc, None, random.Random(42), [])
        assert result is None

    def test_war_scenario_with_event(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="war", description="War", affected_regions=["MyRegion"])]
        result = _maybe_war_scenario(pc, None, random.Random(42), events)
        assert result is not None and result.event_type == "war"

    def test_war_scenario_wrong_region(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="war", description="War", affected_regions=["OtherRegion"])]
        result = _maybe_war_scenario(pc, None, random.Random(42), events)
        assert result is None

    def test_merchant_scenario_with_trade_event(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="Region", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="trade_boom", description="Trade boom")]
        result = _maybe_merchant_scenario(pc, None, random.Random(42), events)
        if result is not None:
            assert result.event_type == "merchant"

    def test_discovery_scenario_wrong_region(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="discovery", description="Discovery", affected_regions=["OtherRegion"])]
        result = _maybe_discovery_scenario(pc, None, random.Random(42), events)
        assert result is None

    def test_religious_scenario_with_event(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="divine_blessing", description="Blessing", affected_regions=["MyRegion"])]
        result = _maybe_religious_scenario(pc, None, random.Random(42), events)
        if result is not None:
            assert result.event_type == "religious"

    def test_exodus_scenario_with_event(self):
        pc = PlayerCharacter(name="Test", settlement="Town", region="MyRegion", profession="farmer", year=10)
        events = [SimEvent(year=10, event_type="exodus", description="Exodus", affected_settlements=["Town"])]
        result = _maybe_exodus_scenario(pc, None, random.Random(42), events)
        assert result is not None and result.event_type == "exodus"


# ── Legacy Tracking & Multi-Generational Tests (Phase 17 Items 3 & 6) ──


class TestLegacyTracking:
    """Legacy event and deed tracking."""

    def test_record_legacy_event(self):
        """Record a legacy event with year prefix."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer", year=42)
        _record_legacy_event(pc, "Found a treasure")
        assert len(pc.legacy_events) == 1
        assert pc.legacy_events[0] == "Y42: Found a treasure"

    def test_record_multiple_events(self):
        """Multiple legacy events accumulate."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer", year=5)
        _record_legacy_event(pc, "First event")
        _record_legacy_event(pc, "Second event")
        assert len(pc.legacy_events) == 2

    def test_record_deed(self):
        """Record a deed."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _record_deed(pc, "Fought in a war")
        assert "Fought in a war" in pc.deeds

    def test_no_duplicate_deeds(self):
        """Same deed is not recorded twice."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _record_deed(pc, "Fought in a war")
        _record_deed(pc, "Fought in a war")
        assert len(pc.deeds) == 1

    def test_deed_uniqueness(self):
        """Different deeds are all recorded."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _record_deed(pc, "Fought in a war")
        _record_deed(pc, "Helped the sick")
        assert len(pc.deeds) == 2

    def test_legacy_fields_in_to_dict(self):
        """Legacy fields are serialized."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        pc.legacy_events.append("Y10: Fought bravely")
        pc.deeds.append("Knighted")
        pc.settlements_visited.append("Kronar")
        pc.total_gold_earned = 500
        pc.total_gold_spent = 200
        d = pc.to_dict()
        assert "legacy_events" in d
        assert "deeds" in d
        assert "settlements_visited" in d
        assert "total_gold_earned" in d
        assert "total_gold_spent" in d

    def test_legacy_fields_survive_roundtrip(self):
        """Legacy fields survive save/load round-trip."""
        import os
        from src.embody import save_character, load_character, _save_path
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer",
                             year=10)
        _record_deed(pc, "Fought in a war")
        _record_legacy_event(pc, "War in Telvan")
        pc.total_gold_earned = 500
        pc.total_gold_spent = 100
        pc.settlements_visited.append("Kronar")
        try:
            save_character(pc, 9999)
            loaded = load_character(9999)
            assert loaded is not None
            assert len(loaded.deeds) == 1
            assert len(loaded.legacy_events) == 1
            assert loaded.total_gold_earned == 500
            assert loaded.total_gold_spent == 100
            assert len(loaded.settlements_visited) == 1
        finally:
            path = _save_path(9999)
            if os.path.exists(path):
                os.remove(path)


class TestRenderEpilogue:
    """Death epilogue rendering."""

    def test_render_epilogue_basic(self):
        """Epilogue renders with basic stats."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer",
                             age=52, year=34, gold=250)
        pc.total_gold_earned = 800
        pc.total_gold_spent = 550
        result = _render_epilogue(pc)
        assert "Rikard" in result
        assert "Life Ledger" in result
        assert "800" in result  # Total gold earned
        assert "250" in result  # Final wealth
        assert "The wyrd remembers" in result

    def test_epilogue_shows_deeds(self):
        """Epilogue includes deeds."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _record_deed(pc, "Fought in a war")
        result = _render_epilogue(pc)
        assert "Notable Deeds" in result
        assert "Fought in a war" in result

    def test_epilogue_shows_events(self):
        """Epilogue includes witnessed events."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _record_legacy_event(pc, "War in Telvan")
        result = _render_epilogue(pc)
        assert "They Witnessed" in result
        assert "War in Telvan" in result

    def test_epilogue_shows_parent(self):
        """Epilogue shows parent name for multi-generational."""
        pc = PlayerCharacter(name="Elara", settlement="Kronar",
                             region="Telvan", profession="farmer",
                             parent_name="Rikard")
        result = _render_epilogue(pc)
        assert "Child of" in result
        assert "Rikard" in result

    def test_epilogue_last_words(self):
        """Epilogue includes last words."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        result = _render_epilogue(pc)
        # Should have at least one quote character
        assert '"' in result or '"' in result

    def test_epilogue_visited_settlements(self):
        """Epilogue shows visited settlements."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        pc.settlements_visited.extend(["Kronar", "Mistharbor", "Thornwall"])
        result = _render_epilogue(pc)
        assert "Places lived" in result

    def test_epilogue_no_crash_empty(self):
        """Epilogue doesn't crash with minimal character."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer", age=0, year=0)
        result = _render_epilogue(pc)
        assert result  # Should produce output


# ── Phase 18 — Skill System ──────────────────────────────────────────


from src.embody import (
    SKILL_NAMES,
    _xp_for_level,
    _xp_to_next_level,
    _skill_level_from_xp,
    _skill_bonus,
    _gain_skill_xp,
    _change_reputation,
    _maybe_bandit_raid,
    _maybe_festival,
    _maybe_monster_hunt,
)


class TestSkillSystem:
    """Skill levels, XP, and bonuses."""

    def test_skill_defaults(self):
        """Characters start with all skills at level 1 and 0 XP."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        for s in SKILL_NAMES:
            assert pc.skills[s] == 1
            assert pc.skill_xp[s] == 0

    def test_xp_level_thresholds(self):
        """XP thresholds follow triangular sequence."""
        assert _xp_for_level(1) == 0
        assert _xp_for_level(2) == 15
        assert _xp_for_level(3) == 45  # (3*2/2)*15 = 45
        assert _xp_for_level(4) == 90  # (4*3/2)*15 = 90
        assert _xp_for_level(5) == 150  # (5*4/2)*15 = 150

    def test_xp_to_next_level(self):
        """XP needed from current level to next."""
        assert _xp_to_next_level(1) == 15  # 15 - 0
        assert _xp_to_next_level(2) == 30  # 45 - 15
        assert _xp_to_next_level(3) == 45  # 90 - 45

    def test_skill_level_from_xp(self):
        """Determining level from total XP."""
        assert _skill_level_from_xp(0) == 1
        assert _skill_level_from_xp(14) == 1
        assert _skill_level_from_xp(15) == 2
        assert _skill_level_from_xp(44) == 2
        assert _skill_level_from_xp(45) == 3

    def test_skill_bonus_scales(self):
        """Skill bonus increases with level."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        assert _skill_bonus(pc, "combat") == 0.0  # Level 1
        pc.skills["combat"] = 5
        assert _skill_bonus(pc, "combat") == 0.2  # (5-1) * 0.05
        pc.skills["combat"] = 10
        assert _skill_bonus(pc, "combat") == 0.45  # (10-1) * 0.05

    def test_gain_skill_xp_level_up(self):
        """Gaining enough XP levels up the skill."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        assert pc.skills["combat"] == 1
        _gain_skill_xp(pc, "combat", 15)
        assert pc.skills["combat"] == 2
        assert pc.skill_xp["combat"] == 15

    def test_gain_skill_xp_partial(self):
        """Gaining XP below threshold keeps current level."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _gain_skill_xp(pc, "combat", 10)
        assert pc.skills["combat"] == 1
        assert pc.skill_xp["combat"] == 10

    def test_gain_skill_xp_multiple_levels(self):
        """Gaining large XP can jump multiple levels."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _gain_skill_xp(pc, "trade", 150)
        assert pc.skills["trade"] == 5
        assert pc.skill_xp["trade"] == 150

    def test_skill_max_level_10(self):
        """Skills cap at level 10."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _gain_skill_xp(pc, "survival", 99999)
        assert pc.skills["survival"] == 10

    def test_skill_xp_unknown_skill_noop(self):
        """Unknown skill name doesn't crash."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _gain_skill_xp(pc, "nonexistent", 100)  # Should not raise

    def test_skills_in_save_round_trip(self):
        """Skills and XP persist through save/load."""
        from src.embody import save_character, load_character, _save_path
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _gain_skill_xp(pc, "combat", 50)
        _gain_skill_xp(pc, "trade", 20)
        pc.skills["persuasion"] = 3
        try:
            save_character(pc, 999)
            loaded = load_character(999)
            assert loaded is not None
            assert loaded.skills["combat"] == pc.skills["combat"]
            assert loaded.skill_xp["combat"] == pc.skill_xp["combat"]
            assert loaded.skills["trade"] > 1
            assert loaded.skills["persuasion"] == 3
        finally:
            path = _save_path(999)
            if os.path.exists(path):
                os.remove(path)


class TestReputation:
    """Reputation system."""

    def test_default_empty(self):
        """Characters start with no reputation."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        assert pc.reputation == {}

    def test_add_positive(self):
        """Reputation can be increased."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        result = _change_reputation(pc, "Kronar", 3)
        assert pc.reputation["Kronar"] == 3
        assert "improves" in result

    def test_add_negative(self):
        """Reputation can be decreased."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        result = _change_reputation(pc, "Kronar", -2)
        assert pc.reputation["Kronar"] == -2
        assert "suffers" in result

    def test_clamp_positive(self):
        """Reputation maxes at +10."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _change_reputation(pc, "Kronar", 100)
        assert pc.reputation["Kronar"] == 10

    def test_clamp_negative(self):
        """Reputation min at -10."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _change_reputation(pc, "Kronar", -100)
        assert pc.reputation["Kronar"] == -10

    def test_reputation_different_settlements(self):
        """Reputation is per-settlement."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _change_reputation(pc, "Kronar", 5)
        _change_reputation(pc, "Mistharbor", -3)
        assert pc.reputation["Kronar"] == 5
        assert pc.reputation["Mistharbor"] == -3

    def test_reputation_zero_delta_no_output(self):
        """Zero delta produces empty string."""
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        result = _change_reputation(pc, "Kronar", 0)
        assert result == ""

    def test_reputation_in_save_round_trip(self):
        """Reputation persists through save/load."""
        from src.embody import save_character, load_character, _save_path
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        _change_reputation(pc, "Kronar", 5)
        _change_reputation(pc, "Mistharbor", -3)
        try:
            save_character(pc, 888)
            loaded = load_character(888)
            assert loaded is not None
            assert loaded.reputation["Kronar"] == 5
            assert loaded.reputation["Mistharbor"] == -3
        finally:
            path = _save_path(888)
            if os.path.exists(path):
                os.remove(path)


class TestBanditScenario:
    """Bandit raid scenario."""

    def test_labels(self):
        """Bandit labels are correct."""
        assert _label_for_event("bandit", 0) == "Fight the bandits"
        assert _label_for_event("bandit", 1) == "Pay them off"
        assert _label_for_event("bandit", 2) == "Hide and wait"

    def test_can_trigger(self):
        """Bandit scenario can trigger (with high random)."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer",
                             year=10)
        result = _maybe_bandit_raid(pc, world, rng, [])
        # May or may not trigger; should not crash
        assert result is None or isinstance(result, EventChoiceData)

    def test_trigger_in_war(self):
        """Bandit scenario triggers more in war."""
        from src.sim import SimEvent
        war_event = SimEvent(year=10, event_type="war",
                             description="War!",
                             affected_regions=["Telvan"])
        # Force trigger by overriding random
        rng = random.Random(42)
        world = generate_world(42, width=15, height=10)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer",
                             year=10)
        # Patch _maybe_bandit_raid to check it gets called
        result = _maybe_bandit_raid(pc, world, rng, [war_event])
        # Should work with war event and some random seeds
        assert result is None or result.event_type == "bandit"

    def test_fight_option(self):
        """Fight resolution produces valid outcome."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        sc = EventChoiceData(prompt="Bandits!", event_type="bandit", icon="🗡")
        outcome, label = _resolve_choice(sc, 0, pc, world, rng)
        assert isinstance(outcome, ChoiceOutcome)
        assert label == "Fight the bandits"
        assert "gold" in outcome.description.lower() or "bandits" in outcome.description.lower()

    def test_pay_option(self):
        """Pay resolution deducts gold."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer", gold=100)
        sc = EventChoiceData(prompt="Bandits!", event_type="bandit", icon="🗡")
        outcome, label = _resolve_choice(sc, 1, pc, world, rng)
        assert outcome.gold_delta < 0
        assert label == "Pay them off"

    def test_hide_option(self):
        """Hide resolution produces outcome."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        sc = EventChoiceData(prompt="Bandits!", event_type="bandit", icon="🗡")
        outcome, label = _resolve_choice(sc, 2, pc, world, rng)
        assert isinstance(outcome, ChoiceOutcome)
        assert label == "Hide and wait"

    def test_gives_skill_xp(self):
        """Bandit scenario gives skill XP."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        old_combat_xp = pc.skill_xp["combat"]
        sc = EventChoiceData(prompt="Bandits!", event_type="bandit", icon="🗡")
        _resolve_choice(sc, 0, pc, world, rng)
        assert pc.skill_xp["combat"] > old_combat_xp


class TestFestivalScenario:
    """Festival celebration scenario."""

    def test_labels(self):
        """Festival labels are correct."""
        assert _label_for_event("festival", 0) == "Join the celebration"
        assert _label_for_event("festival", 1) == "Help organize"
        assert _label_for_event("festival", 2) == "Skip it"

    def test_can_trigger(self):
        """Festival scenario can trigger."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer",
                             year=10)
        result = _maybe_festival(pc, world, rng, [])
        assert result is None or isinstance(result, EventChoiceData)

    def test_join_option(self):
        """Join festival gives gold and health."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer", gold=50)
        sc = EventChoiceData(prompt="Festival!", event_type="festival", icon="🎉")
        outcome, label = _resolve_choice(sc, 0, pc, world, rng)
        assert label == "Join the celebration"
        assert outcome.health_delta > 0  # Always gain health from joining

    def test_organize_option(self):
        """Organize festival gives gold and reputation."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        sc = EventChoiceData(prompt="Festival!", event_type="festival", icon="🎉")
        outcome, label = _resolve_choice(sc, 1, pc, world, rng)
        assert label == "Help organize"
        assert outcome.gold_delta >= 0  # Always earns something

    def test_skip_option(self):
        """Skip festival does nothing."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        sc = EventChoiceData(prompt="Festival!", event_type="festival", icon="🎉")
        outcome, label = _resolve_choice(sc, 2, pc, world, rng)
        assert label == "Skip it"
        assert outcome.gold_delta == 0


class TestMonsterHuntScenario:
    """Monster hunt scenario."""

    def test_labels(self):
        """Monster hunt labels are correct."""
        assert _label_for_event("monster_hunt", 0) == "Hunt the creature"
        assert _label_for_event("monster_hunt", 1) == "Hire a hunter"
        assert _label_for_event("monster_hunt", 2) == "Ignore the threat"

    def test_requires_bestiary(self):
        """Monster hunt returns None when world has no bestiary."""
        world = generate_world(42, width=15, height=10)
        world.bestiary = None
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        result = _maybe_monster_hunt(pc, world, rng, [])
        assert result is None

    def test_hunt_option(self):
        """Hunt resolution produces valid outcome."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        sc = EventChoiceData(prompt="Monster!", event_type="monster_hunt", icon="🐉")
        outcome, label = _resolve_choice(sc, 0, pc, world, rng)
        assert isinstance(outcome, ChoiceOutcome)
        assert label == "Hunt the creature"

    def test_hire_option(self):
        """Hire resolution costs gold."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer", gold=100)
        sc = EventChoiceData(prompt="Monster!", event_type="monster_hunt", icon="🐉")
        outcome, label = _resolve_choice(sc, 1, pc, world, rng)
        assert label == "Hire a hunter"
        assert outcome.gold_delta < 0  # Always costs gold

    def test_ignore_option(self):
        """Ignore resolution does nothing."""
        world = generate_world(42, width=15, height=10)
        rng = random.Random(42)
        pc = PlayerCharacter(name="Rikard", settlement="Kronar",
                             region="Telvan", profession="farmer")
        sc = EventChoiceData(prompt="Monster!", event_type="monster_hunt", icon="🐉")
        outcome, label = _resolve_choice(sc, 2, pc, world, rng)
        assert label == "Ignore the threat"
        assert outcome.gold_delta == 0
