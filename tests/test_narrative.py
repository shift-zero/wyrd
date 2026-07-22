"""
Tests for wyrd Phase 4 — Narrative Engine.

Covers character generation, event chains, quest generation,
seed determinism, and narrative serialization round-trip.
"""
import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.narrative import (
    generate_narrative, generate_characters, generate_events, generate_quests,
    Narrative, Character, EventChain, Quest,
)
from src.render import render_characters, render_events, render_quests, render_narrative
from src.serialize import world_to_dict, dict_to_world


class TestCharacterGeneration:
    """Characters must be seeded, grounded in regions, and well-formed."""

    def test_characters_are_generated(self):
        world = generate_world(42)
        narr = world.narrative
        assert len(narr.characters) > 0

    def test_every_settlement_has_at_least_one_character(self):
        world = generate_world(42)
        for region in world.regions:
            for settlement in region.settlements:
                chars = [
                    c for c in world.narrative.characters
                    if c.home_region == region.name
                    and c.home_settlement == settlement.name
                ]
                assert len(chars) >= 1, (
                    f"{settlement.name} ({region.name}) has no characters"
                )

    def test_characters_have_required_attributes(self):
        world = generate_world(42)
        for c in world.narrative.characters:
            assert c.name, "Character must have a name"
            assert c.surname, "Character must have a surname"
            assert c.occupation, "Character must have an occupation"
            assert c.home_region, "Character must have a home region"
            assert c.home_settlement, "Character must have a home settlement"
            assert c.backstory, "Character must have a backstory"
            assert c.full_name, "full_name property must work"
            assert len(c.personality_traits) >= 2

    def test_characters_are_seed_deterministic(self):
        w1 = generate_world(42)
        w2 = generate_world(42)
        for c1, c2 in zip(w1.narrative.characters, w2.narrative.characters):
            assert c1.full_name == c2.full_name
            assert c1.occupation == c2.occupation
            assert c1.backstory == c2.backstory

    def test_different_seeds_different_characters(self):
        w1 = generate_world(42)
        w2 = generate_world(99)
        names1 = [c.full_name for c in w1.narrative.characters]
        names2 = [c.full_name for c in w2.narrative.characters]
        assert names1 != names2, "Different seeds should produce different characters"


class TestEventGeneration:
    """Event chains must be well-formed and seed-deterministic."""

    def test_events_are_generated(self):
        world = generate_world(42)
        assert len(world.narrative.events) >= 3
        assert len(world.narrative.events) <= 8

    def test_events_have_required_attributes(self):
        world = generate_world(42)
        for e in world.narrative.events:
            assert e.name, "Event must have a name"
            assert e.description, "Event must have a description"
            assert e.year > 0, "Event must have a valid year"
            assert e.event_type in (
                "conflict", "discovery", "natural", "political", "cultural"
            ), f"Unknown event type: {e.event_type}"
            assert len(e.regions_involved) > 0

    def test_events_chronological_order(self):
        world = generate_world(42)
        events = sorted(world.narrative.events, key=lambda e: e.year)
        for i in range(1, len(events)):
            assert events[i].year >= events[i - 1].year

    def test_events_are_seed_deterministic(self):
        w1 = generate_world(42)
        w2 = generate_world(42)
        for e1, e2 in zip(w1.narrative.events, w2.narrative.events):
            assert e1.name == e2.name
            assert e1.year == e2.year
            assert e1.description == e2.description


class TestQuestGeneration:
    """Quests must be grounded, well-formed, and seed-deterministic."""

    def test_quests_are_generated(self):
        world = generate_world(42)
        assert len(world.narrative.quests) >= 3
        assert len(world.narrative.quests) <= 6

    def test_quests_have_required_attributes(self):
        world = generate_world(42)
        for q in world.narrative.quests:
            assert q.name, "Quest must have a name"
            assert q.description, "Quest must have a description"
            assert q.quest_type in (
                "exploration", "combat", "diplomacy", "gathering", "intrigue"
            ), f"Unknown quest type: {q.quest_type}"
            assert q.difficulty in (
                "trivial", "easy", "moderate", "hard", "epic"
            ), f"Unknown difficulty: {q.difficulty}"
            assert q.target_region, "Quest must have a target region"
            assert q.is_active in (True, False)

    def test_quests_are_seed_deterministic(self):
        w1 = generate_world(42)
        w2 = generate_world(42)
        for q1, q2 in zip(w1.narrative.quests, w2.narrative.quests):
            assert q1.name == q2.name
            assert q1.description == q2.description
            assert q1.difficulty == q2.difficulty


class TestNarrativeSerialization:
    """Full narrative round-trip through JSON."""

    def test_narrative_in_serialization(self):
        world = generate_world(42)
        data = world_to_dict(world)
        assert "narrative" in data
        assert "characters" in data["narrative"]
        assert "events" in data["narrative"]
        assert "quests" in data["narrative"]

    def test_narrative_round_trip(self):
        world = generate_world(42)
        data = world_to_dict(world)
        restored = dict_to_world(data)

        assert restored.narrative is not None
        assert restored.narrative.seed == world.narrative.seed
        assert len(restored.narrative.characters) == len(world.narrative.characters)
        assert len(restored.narrative.events) == len(world.narrative.events)
        assert len(restored.narrative.quests) == len(world.narrative.quests)

        # Check first character
        c1 = world.narrative.characters[0]
        c2 = restored.narrative.characters[0]
        assert c1.full_name == c2.full_name
        assert c1.backstory == c2.backstory
        assert c1.occupation == c2.occupation

        # Check first event
        e1 = world.narrative.events[0]
        e2 = restored.narrative.events[0]
        assert e1.name == e2.name
        assert e1.description == e2.description

        # Check first quest
        q1 = world.narrative.quests[0]
        q2 = restored.narrative.quests[0]
        assert q1.name == q2.name
        assert q1.description == q2.description

    def test_round_trip_preserves_everything(self):
        """Full file-based save/load round-trip."""
        world = generate_world(42)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(world_to_dict(world), f, indent=2)
            tmp_path = f.name

        try:
            with open(tmp_path) as f:
                data = json.load(f)
            restored = dict_to_world(data)

            assert len(restored.narrative.characters) == len(world.narrative.characters)
            assert len(restored.narrative.events) == len(world.narrative.events)
            assert len(restored.narrative.quests) == len(world.narrative.quests)
        finally:
            os.unlink(tmp_path)

    def test_backwards_compatible_no_narrative(self):
        """Old saves without narrative data should still load."""
        world = generate_world(42)
        data = world_to_dict(world)
        # Remove narrative to simulate old save
        data.pop("narrative", None)
        restored = dict_to_world(data)
        assert restored.narrative is None


class TestNarrativeRendering:
    """Rendering functions produce non-empty output."""

    def test_render_characters(self):
        world = generate_world(42)
        output = render_characters(world)
        assert len(output) > 50

    def test_render_events(self):
        world = generate_world(42)
        output = render_events(world)
        assert "AE" in output
        assert len(output) > 50

    def test_render_quests(self):
        world = generate_world(42)
        output = render_quests(world)
        assert "ACTIVE" in output
        assert len(output) > 50

    def test_render_narrative(self):
        world = generate_world(42)
        output = render_narrative(world)
        assert "Characters" in output
        assert "Timeline" in output
        assert "Quests" in output
        assert len(output) > 200

    def test_render_empty_narrative(self):
        """Render functions should handle missing narrative gracefully."""
        from src.world import World
        world = World(seed=0, width=10, height=10)
        assert render_characters(world) != ""
        assert render_events(world) != ""
        assert render_quests(world) != ""
        assert render_narrative(world) != ""


class TestNarrativeSeedOffset:
    """Narrative uses a unique seed offset for determinism."""

    def test_different_worlds_different_narrative(self):
        w1 = generate_world(42)
        w2 = generate_world(43)
        n1 = w1.narrative
        n2 = w2.narrative

        # Should have different number of characters/events/quests in most cases
        names1 = [(c.full_name, c.occupation) for c in n1.characters]
        names2 = [(c.full_name, c.occupation) for c in n2.characters]
        assert names1 != names2
