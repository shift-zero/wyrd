#!/usr/bin/env python3
"""Tests for mud_parser.py gameplay loop enhancements — combat, trading, skills, time passage."""

import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.mud_parser import (
    parse_command,
    handle_command,
    _handle_combat,
    _handle_buy,
    _handle_sell,
    _handle_hunt,
    _handle_bargain,
    _handle_explore,
    _handle_talk,
    _advance_time,
    _has_weapon,
    _is_market_room,
    _season_from_month,
    _time_of_day,
)
from src.room import Room, Zone, CommandResult
from src.embody import PlayerCharacter, _gain_skill_xp, _make_skills, _make_skill_xp
from src.world import World


# ── Fixtures ─────────────────────────────────────────────────────────

def make_char(**overrides) -> PlayerCharacter:
    """Create a PlayerCharacter with sensible defaults."""
    defaults = {
        "name": "Test Hero",
        "settlement": "Testville",
        "region": "Test Region",
        "profession": "adventurer",
        "gold": 100,
        "health": 100,
        "age": 18,
        "year": 0,
        "month": 0,
        "inventory": ["sword", "bandage", "rations"],
        "skills": _make_skills(),
        "skill_xp": _make_skill_xp(),
    }
    defaults.update(overrides)
    return PlayerCharacter(**defaults)


def make_room(room_id: str = "test_room", tags: list[str] | None = None,
              npcs: list[dict] | None = None, contents: list[dict] | None = None) -> Room:
    return Room(
        name="Test Room",
        description="A room for testing.",
        exits={"n": "next_room"},
        room_id=room_id,
        tags=tags or [],
        npcs=npcs or [],
        contents=contents or [],
    )


def make_zone(name: str = "Test Zone", rooms: dict | None = None,
              entry_room: str = "test_room", zone_type: str = "settlement") -> Zone:
    z = Zone(name=name, entry_room=entry_room, zone_type=zone_type)
    if rooms:
        z.rooms = rooms
    return z


def make_world(seed: int = 42) -> World:
    return World(seed=seed, width=10, height=10)


# ── Tests: _advance_time ─────────────────────────────────────────────

def test_advance_time_basic():
    char = make_char(month=0, year=0, age=18)
    msg = _advance_time(char, 1)
    assert char.month == 1
    assert char.year == 0
    assert char.age == 18
    assert "[1 hours pass" in msg


def test_advance_time_noop():
    char = make_char()
    msg = _advance_time(char, 0)
    assert msg == ""
    assert char.month == 0


def test_advance_time_wrap_year():
    char = make_char(month=10, year=5, age=30)
    _advance_time(char, 5)  # 10+5=15, wraps to month=3, year+1, age+1
    assert char.month == 3
    assert char.year == 6
    assert char.age == 31


def test_advance_time_multi_year():
    char = make_char(month=10, year=5, age=30)
    _advance_time(char, 26)  # 10+26=36, wraps 3 times
    assert char.month == 0
    assert char.year == 8
    assert char.age == 33


# ── Tests: _season_from_month ────────────────────────────────────────

def test_seasons():
    assert _season_from_month(0) == "Spring"
    assert _season_from_month(2) == "Spring"
    assert _season_from_month(3) == "Summer"
    assert _season_from_month(5) == "Summer"
    assert _season_from_month(6) == "Autumn"
    assert _season_from_month(8) == "Autumn"
    assert _season_from_month(9) == "Winter"
    assert _season_from_month(11) == "Winter"


# ── Tests: _time_of_day ──────────────────────────────────────────────

def test_time_of_day():
    assert _time_of_day(2) == "night"
    assert _time_of_day(7) == "morning"
    assert _time_of_day(14) == "afternoon"
    assert _time_of_day(20) == "evening"


# ── Tests: _has_weapon ───────────────────────────────────────────────

def test_has_weapon_with_sword():
    char = make_char(inventory=["sword", "bandage"])
    assert _has_weapon(char)


def test_has_weapon_without():
    char = make_char(inventory=["bandage", "rations", "map"])
    assert not _has_weapon(char)


def test_has_weapon_with_dagger():
    char = make_char(inventory=["dagger"])
    assert _has_weapon(char)


def test_has_weapon_with_axe():
    char = make_char(inventory=["axe"])
    assert _has_weapon(char)


def test_has_weapon_empty():
    char = make_char(inventory=[])
    assert not _has_weapon(char)


# ── Tests: _is_market_room ───────────────────────────────────────────

def test_market_room():
    room = make_room(tags=["market"])
    assert _is_market_room(room)


def test_shop_room():
    room = make_room(tags=["shop", "indoors"])
    assert _is_market_room(room)


def test_bazaar_room():
    room = make_room(tags=["bazaar"])
    assert _is_market_room(room)


def test_non_market_room():
    room = make_room(tags=["tavern", "indoors"])
    assert not _is_market_room(room)


def test_no_tags_room():
    room = make_room(tags=[])
    assert not _is_market_room(room)


# ── Tests: Combat System ─────────────────────────────────────────────

def test_combat_no_target():
    char = make_char()
    zone = make_zone(rooms={"test_room": make_room()})
    rng = random.Random(42)
    result = _handle_combat(None, char, zone, "test_room", rng)
    assert "Attack what?" in result


def test_combat_no_npc():
    char = make_char()
    zone = make_zone(rooms={"test_room": make_room()})
    rng = random.Random(42)
    result = _handle_combat("goblin", char, zone, "test_room", rng)
    assert "no goblin to fight" in result


def test_combat_victory():
    """Test that combat can succeed and rewards gold + XP."""
    # Give the player very high combat skill so they win
    char = make_char(inventory=["sword"], skills={"combat": 10, "trade": 1, "persuasion": 1, "survival": 1, "crafting": 1})
    char.skill_xp["combat"] = 1000  # enough for level 10
    npcs = [{"name": "Goblin", "title": "nasty goblin", "dialog": "Grr!"}]
    room = make_room(npcs=npcs)
    zone = make_zone(rooms={"test_room": room})
    rng = random.Random(42)

    old_gold = char.gold
    result = _handle_combat("goblin", char, zone, "test_room", rng)
    assert "You slay" in result or "defeated" in result
    assert char.gold >= old_gold  # should have gained gold
    assert room.npcs == []  # NPC removed
    # Loot should be in room
    assert len(room.contents) > 0


def test_combat_near_death():
    """When health hits 0, set to 5."""
    char = make_char(inventory=[], health=5, skills={"combat": 1, "trade": 1, "persuasion": 1, "survival": 1, "crafting": 1})
    npcs = [{"name": "Dragon", "title": "ancient dragon", "dialog": "ROAR!"}]
    room = make_room(npcs=npcs)
    zone = make_zone(rooms={"test_room": room})
    rng = random.Random(999)

    result = _handle_combat("dragon", char, zone, "test_room", rng)
    # Note: with seed 999 and low combat+no weapon, the player might still win
    # But if they'd reach 0, check health is set to 5
    if "nearly dead" in result:
        assert char.health == 5
    else:
        assert char.health > 0


def test_combat_damage_formula():
    """With sword + combat skill 10, damage should be high."""
    char = make_char(
        inventory=["sword"],
        skills={"combat": 10, "trade": 1, "persuasion": 1, "survival": 1, "crafting": 1},
    )
    # base_damage = 5 + (1*5) + (10*2) = 5+5+20 = 30
    # NPC HP is 15-40, so with 30 damage we're likely to one-shot
    npcs = [{"name": "Rat", "title": "giant rat", "dialog": "Squeak!"}]
    room = make_room(npcs=npcs)
    zone = make_zone(rooms={"test_room": room})
    rng = random.Random(42)

    result = _handle_combat("rat", char, zone, "test_room", rng)
    assert "You slay" in result or "defeated" in result


# ── Tests: Trading System ────────────────────────────────────────────

def test_buy_success():
    char = make_char(gold=100)
    room = make_room(
        tags=["market"],
        contents=[{"name": "bandage", "type": "item"}],
        npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Buy something!"}],
    )
    zone = make_zone(rooms={"market_room": room})
    rng = random.Random(42)

    old_gold = char.gold
    result = _handle_buy("bandage", char, zone, "market_room", rng)
    assert "buy" in result.lower()
    assert char.gold < old_gold  # spent gold
    assert "bandage" in [i.lower() for i in char.inventory]


def test_buy_no_money():
    char = make_char(gold=1)  # too poor
    room = make_room(
        tags=["market"],
        contents=[{"name": "sword", "type": "item"}],
        npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Buy something!"}],
    )
    zone = make_zone(rooms={"market_room": room})
    rng = random.Random(42)
    result = _handle_buy("sword", char, zone, "market_room", rng)
    assert "need" in result.lower() or "only" in result.lower()


def test_buy_non_market():
    char = make_char()
    room = make_room(tags=["tavern"])
    zone = make_zone(rooms={"tavern": room})
    rng = random.Random(42)
    result = _handle_buy("bandage", char, zone, "tavern", rng)
    assert "no merchant" in result.lower()


def test_sell_success():
    char = make_char(inventory=["sword"])
    room = make_room(
        tags=["market"],
        npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Buy something!"}],
    )
    zone = make_zone(rooms={"market_room": room})
    rng = random.Random(42)

    old_gold = char.gold
    old_inv_len = len(char.inventory)
    result = _handle_sell("sword", char, zone, "market_room", rng)
    assert "sell" in result.lower()
    assert char.gold > old_gold  # gained gold
    assert len(char.inventory) == old_inv_len - 1  # removed from inventory


def test_sell_non_market():
    char = make_char(inventory=["sword"])
    room = make_room(tags=["tavern"])
    zone = make_zone(rooms={"tavern": room})
    rng = random.Random(42)
    result = _handle_sell("sword", char, zone, "tavern", rng)
    assert "no merchant" in result.lower()


# ── Tests: Market Talk ───────────────────────────────────────────────

def test_talk_in_market_shows_trade_menu():
    room = make_room(
        tags=["market"],
        npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Buy something!"}],
        contents=[{"name": "bandage", "type": "item"}],
    )
    zone = make_zone(rooms={"market_room": room})
    rng = random.Random(42)
    result = _handle_talk(None, zone, "market_room", rng)
    assert "buy" in result.lower()
    assert "sell" in result.lower()
    assert "bargain" in result.lower()
    assert "bandage" in result


def test_talk_in_non_market():
    room = make_room(
        tags=["tavern"],
        npcs=[{"name": "Bard", "title": "bard", "dialog": "Sing a song?"}],
    )
    zone = make_zone(rooms={"tavern": room})
    rng = random.Random(42)
    result = _handle_talk(None, zone, "tavern", rng)
    assert "buy" not in result.lower()
    assert "Sing a song" in result


# ── Tests: Active Skills ─────────────────────────────────────────────

def test_hunt_success():
    char = make_char(
        skills={"combat": 1, "trade": 1, "persuasion": 1, "survival": 10, "crafting": 1},
    )
    room = make_room(tags=[])
    zone = make_zone(rooms={"wild_room": room})
    rng = random.Random(42)
    old_inv_len = len(char.inventory)
    result = _handle_hunt(char, zone, "wild_room", rng)

    # With survival 10, chances are good for success
    if "successfully" in result or "hunt" in result.lower():
        assert "survival skill" in result


def test_hunt_indoors_fails():
    char = make_char()
    room = make_room(tags=["indoors"])
    zone = make_zone(rooms={"indoor_room": room})
    rng = random.Random(42)
    result = _handle_hunt(char, zone, "indoor_room", rng)
    assert "can't hunt indoors" in result.lower()


def test_bargain():
    char = make_char()
    rng = random.Random(42)
    result = _handle_bargain(char, rng)
    assert "haggle" in result.lower() or "bargain" in result.lower()
    assert "trade skill" in result


def test_explore_wilderness():
    char = make_char(
        skills={"combat": 1, "trade": 1, "persuasion": 1, "survival": 5, "crafting": 1},
    )
    zone = make_zone(name="Wilderness", zone_type="wilderness", rooms={})
    rng = random.Random(42)
    old_inv_len = len(char.inventory)
    result = _handle_explore(char, zone, "wilderness", rng)
    assert "search" in result.lower() or "find" in result.lower() or "nothing" in result
    assert "survival skill" in result


def test_explore_indoors_fails():
    char = make_char()
    room = make_room(tags=["indoors"])
    zone = make_zone(rooms={"indoor_room": room})
    rng = random.Random(42)
    result = _handle_explore(char, zone, "indoor_room", rng)
    assert "nothing to discover" in result.lower()


# ── Tests: Seed Determinism ──────────────────────────────────────────

def test_combat_seed_deterministic():
    """Same seed should produce same combat result."""
    def run_combat(seed_num):
        char = make_char(
            inventory=["sword"],
            skills={"combat": 3, "trade": 1, "persuasion": 1, "survival": 1, "crafting": 1},
        )
        npcs = [{"name": "Goblin", "title": "nasty goblin", "dialog": "Grr!"}]
        room = make_room(npcs=npcs)
        zone = make_zone(rooms={"test_room": room})
        rng = random.Random(seed_num)
        return _handle_combat("goblin", char, zone, "test_room", rng)

    result1 = run_combat(42)
    result2 = run_combat(42)
    assert result1 == result2


def test_buy_seed_deterministic():
    """Same seed should produce same buy price."""
    def run_buy(seed_num):
        char = make_char(gold=999)
        room = make_room(
            tags=["market"],
            contents=[{"name": "bandage", "type": "item"}],
            npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Buy!"}],
        )
        zone = make_zone(rooms={"mr": room})
        rng = random.Random(seed_num)
        return _handle_buy("bandage", char, zone, "mr", rng)

    r1 = run_buy(42)
    r2 = run_buy(42)
    assert r1 == r2


# ── Tests: handle_command integration ────────────────────────────────

def test_handle_command_combat():
    char = make_char()
    room = make_room(npcs=[{"name": "Bandit", "title": "bandit", "dialog": "Your gold!"}])
    zone = make_zone(rooms={"test_room": room})
    world = make_world(42)
    parsed = {"verb": "kill", "noun": "bandit"}
    result = handle_command(parsed, char, zone, "test_room", world, 42)
    assert isinstance(result, CommandResult)
    assert result.char_changed


def test_handle_command_buy():
    char = make_char(gold=100)
    room = make_room(
        tags=["market"],
        contents=[{"name": "bandage", "type": "item"}],
        npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Buy!"}],
    )
    zone = make_zone(rooms={"mr": room})
    world = make_world(42)
    parsed = {"verb": "buy", "noun": "bandage"}
    result = handle_command(parsed, char, zone, "mr", world, 42)
    assert isinstance(result, CommandResult)
    assert result.char_changed


def test_handle_command_sell():
    char = make_char(inventory=["bandage"])
    room = make_room(
        tags=["market"],
        npcs=[{"name": "Merchant", "title": "merchant", "dialog": "Sell!"}],
    )
    zone = make_zone(rooms={"mr": room})
    world = make_world(42)
    parsed = {"verb": "sell", "noun": "bandage"}
    result = handle_command(parsed, char, zone, "mr", world, 42)
    assert isinstance(result, CommandResult)
    assert result.char_changed


def test_handle_command_hunt():
    char = make_char()
    room = make_room()
    zone = make_zone(rooms={"test_room": room})
    world = make_world(42)
    parsed = {"verb": "hunt", "noun": None}
    result = handle_command(parsed, char, zone, "test_room", world, 42)
    assert isinstance(result, CommandResult)
    assert result.char_changed


def test_handle_command_explore():
    char = make_char()
    room = make_room()
    zone = make_zone(rooms={"test_room": room})
    world = make_world(42)
    parsed = {"verb": "explore", "noun": None}
    result = handle_command(parsed, char, zone, "test_room", world, 42)
    assert isinstance(result, CommandResult)
    assert result.char_changed


def test_handle_command_bargain():
    char = make_char()
    room = make_room()
    zone = make_zone(rooms={"test_room": room})
    world = make_world(42)
    parsed = {"verb": "bargain", "noun": None}
    result = handle_command(parsed, char, zone, "test_room", world, 42)
    assert isinstance(result, CommandResult)
    assert result.char_changed


def test_handle_command_parse_buy():
    parsed = parse_command("buy bandage")
    assert parsed["verb"] == "buy"
    assert parsed["noun"] == "bandage"


def test_handle_command_parse_sell():
    parsed = parse_command("sell sword")
    assert parsed["verb"] == "sell"
    assert parsed["noun"] == "sword"


def test_handle_command_parse_hunt():
    parsed = parse_command("hunt")
    assert parsed["verb"] == "hunt"


def test_handle_command_parse_bargain():
    parsed = parse_command("bargain")
    assert parsed["verb"] == "bargain"


def test_handle_command_parse_explore():
    parsed = parse_command("explore")
    assert parsed["verb"] == "explore"
    parsed2 = parse_command("search")
    assert parsed2["verb"] == "explore"


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick smoke test
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
