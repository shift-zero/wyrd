"""
wyrd — MUD Command Parser (Phase 26.4).

Parses natural MUD commands and processes them against the world state.
Designed for the Textual-based single-user MUD interface.

Supported verbs:
  look/l, get, take, drop, use, talk, say, yell,
  kill, attack, fight, north/n, south/s, east/e, west/w,
  inventory/i, help, quit, score, status,
  buy, sell, hunt, bargain, explore/search

Everything is seed-deterministic: same seed → same room descriptions.
"""

import random
from collections import namedtuple
from typing import Optional

from .room import Room, Zone, describe_terrain, CommandResult
from .embody import PlayerCharacter, _gain_skill_xp
from .world import World

# Direction aliases
DIRECTIONS = {
    "n": "north", "north": "north",
    "s": "south", "south": "south",
    "e": "east", "east": "east",
    "w": "west", "west": "west",
    "ne": "northeast", "northeast": "northeast",
    "nw": "northwest", "northwest": "northwest",
    "se": "southeast", "southeast": "southeast",
    "sw": "southwest", "southwest": "southwest",
    "u": "up", "up": "up",
    "d": "down", "down": "down",
}

# Verb aliases — maps user input to canonical verbs
VERB_ALIASES = {
    # Look
    "l": "look",
    "look": "look",
    "examine": "look",
    "check": "look",
    "read": "look",
    # Get / Take
    "get": "get",
    "take": "get",
    "pick": "get",
    "grab": "get",
    # Drop
    "drop": "drop",
    "put": "drop",
    "discard": "drop",
    # Use
    "use": "use",
    "apply": "use",
    "consume": "use",
    "drink": "use",
    "eat": "use",
    # Talk
    "talk": "talk",
    "speak": "talk",
    "ask": "talk",
    "greet": "talk",
    "say": "say",
    "tell": "say",
    "yell": "yell",
    "shout": "yell",
    # Combat
    "kill": "kill",
    "attack": "kill",
    "fight": "kill",
    "hit": "kill",
    "strike": "kill",
    # Movement
    "n": "north",
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
    "ne": "northeast",
    "northeast": "northeast",
    "se": "southeast",
    "southeast": "southeast",
    "sw": "southwest",
    "southwest": "southwest",
    "u": "up",
    "up": "up",
    "d": "down",
    "down": "down",
    "go": "north",  # "go north" will be handled differently by parser
    "walk": "north",
    # Inventory
    "i": "inventory",
    "inv": "inventory",
    "inventory": "inventory",
    # Meta
    "help": "help",
    "h": "help",
    "quit": "quit",
    "q": "quit",
    "exit": "quit",
    "score": "score",
    "stats": "score",
    "status": "status",
    "st": "status",
    # Buying / Selling
    "buy": "buy",
    "purchase": "buy",
    "sell": "sell",
    "trade": "sell",
    # Active skills
    "hunt": "hunt",
    "hunting": "hunt",
    "bargain": "bargain",
    "haggle": "bargain",
    "explore": "explore",
    "search": "explore",
    "forage": "explore",
}

# Multi-word phrasal verbs
PHRASAL_VERBS = {
    "talk to": "talk",
    "speak to": "talk",
    "look at": "look",
    "look on": "look",
    "pick up": "get",
    "use on": "use",
}

# Items that can exist in rooms / player inventory
COMMON_ITEMS = [
    "bandage", "sword", "shield", "torch", "rope",
    "rations", "water flask", "herbs", "coin pouch",
    "key", "map", "compass", "lantern", "dagger",
    "potion", "scroll", "lockpick", "fishing rod",
]

# Weapons that increase combat damage
WEAPON_ITEMS = {"sword", "axe", "dagger", "spear", "battle axe", "warhammer", "mace", "longsword", "shortsword"}


def parse_command(input_str: str) -> dict:
    """
    Parse a MUD command string.

    Returns {"verb": str, "noun": str | None, "direct": str | None, "target": str | None}

    Examples:
    "look" -> {"verb": "look", "noun": None, "direct": None, "target": None}
    "get sword" -> {"verb": "get", "noun": "sword", "direct": None, "target": None}
    "use bandage" -> {"verb": "use", "noun": "bandage", "direct": None, "target": None}
    "talk to merchant" -> {"verb": "talk", "noun": "merchant", "direct": None, "target": None}
    "n" -> {"verb": "north", "noun": None, "direct": None, "target": None}
    """
    if not input_str or not input_str.strip():
        return {"verb": "look", "noun": None, "direct": None, "target": None}

    raw = input_str.strip()
    lower = raw.lower()

    # Single-character direction aliases
    if lower in DIRECTIONS:
        return {"verb": DIRECTIONS[lower], "noun": None, "direct": None, "target": None}

    # Check for phrasal verbs first (e.g., "talk to merchant")
    for phrase, canonical in sorted(PHRASAL_VERBS.items(), key=lambda x: -len(x[0])):
        if lower.startswith(phrase):
            remainder = lower[len(phrase):].strip()
            if remainder:
                parts = remainder.split(None, 1)
                noun = parts[0]
                target = parts[1] if len(parts) > 1 else None
                if canonical == "use" and target:
                    return {"verb": "use", "noun": noun, "direct": noun, "target": target}
                return {"verb": canonical, "noun": noun, "direct": noun, "target": target}
            return {"verb": canonical, "noun": None, "direct": None, "target": None}

    # "talk merchant" (without 'to') or other two-word patterns
    parts = lower.split()
    verb_part = parts[0]
    noun_part = " ".join(parts[1:]) if len(parts) > 1 else None

    # Resolve verb alias
    verb = VERB_ALIASES.get(verb_part)

    if verb is None:
        # Try as a direction
        if verb_part in DIRECTIONS:
            verb = DIRECTIONS[verb_part]
            return {"verb": verb, "noun": noun_part, "direct": None, "target": None}
        # Unknown verb, treat as look with noun
        return {"verb": "look", "noun": verb_part, "direct": None, "target": None}

    # Handle "go north" pattern
    if verb == "north" and noun_part:
        dir_resolved = DIRECTIONS.get(noun_part)
        if dir_resolved:
            return {"verb": dir_resolved, "noun": None, "direct": None, "target": None}

    return {
        "verb": verb,
        "noun": noun_part,
        "direct": noun_part,
        "target": None,
    }


# ── Command Handler ──────────────────────────────────────────────────


def handle_command(
    parsed: dict,
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    world: World,
    seed: int,
) -> CommandResult:
    """Process a parsed command and return the result.

    Args:
        parsed: Output from parse_command().
        char: The PlayerCharacter.
        zone: Current Zone (settlement rooms).
        current_room_id: ID of the room the character is in.
        world: The World object.
        seed: World seed for determinism.

    Returns:
        CommandResult: (output, new_room, char_changed, events)
            output: str — text to display to the player.
            new_room: str | None — new room_id if player moved.
            char_changed: bool — True if character state was modified.
            events: list[str] — world events triggered by this action.
    """
    verb = parsed["verb"]
    noun = parsed.get("noun")

    rng = random.Random(seed + hash(str(char.year) + str(char.age) + verb + (noun or "")) % (2**31))

    events: list[str] = []
    char_changed = False

    # ── Movement Commands ──────────────────────────────────────────

    if verb in ("north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "up", "down"):
        result = _handle_move(verb, char, zone, current_room_id, world, seed, rng)
        # Movement costs 1 hour
        time_msg = _advance_time(char, 1)
        output = result.output + time_msg
        return CommandResult(output, result.new_room, True, result.events)

    # ── Look ───────────────────────────────────────────────────────

    if verb == "look":
        output = _handle_look(zone, current_room_id, char, noun, rng)
        return CommandResult(output, None, False, [])

    # ── Get / Take ─────────────────────────────────────────────────

    if verb == "get":
        output = _handle_get(noun, char, current_room_id, zone, rng)
        char_changed = "picked up" in output or "You take" in output
        return CommandResult(output, None, char_changed, [])

    # ── Drop ───────────────────────────────────────────────────────

    if verb == "drop":
        output = _handle_drop(noun, char, current_room_id, zone, rng)
        char_changed = "dropped" in output
        return CommandResult(output, None, char_changed, [])

    # ── Use ────────────────────────────────────────────────────────

    if verb == "use":
        output = _handle_use(noun, char, rng)
        char_changed = "used" in output
        return CommandResult(output, None, char_changed, [])

    # ── Talk ───────────────────────────────────────────────────────

    if verb == "talk":
        output = _handle_talk(noun, zone, current_room_id, rng)
        time_msg = _advance_time(char, 1)
        return CommandResult(output + time_msg, None, True, [])

    # ── Say ────────────────────────────────────────────────────────

    if verb == "say":
        output = _handle_say(noun, char)
        return CommandResult(output, None, False, [])

    # ── Yell ───────────────────────────────────────────────────────

    if verb == "yell":
        output = _handle_yell(noun, char)
        return CommandResult(output, None, False, [])

    # ── Kill / Attack ─────────────────────────────────────────────

    if verb == "kill":
        output = _handle_combat(noun, char, zone, current_room_id, rng)
        char_changed = True
        time_msg = _advance_time(char, 2)
        if "You slay" in output or "defeated" in output:
            events.append(f"Combat: {char.name} fought in {zone.name}")
        return CommandResult(output + time_msg, None, True, events)

    # ── Buy ────────────────────────────────────────────────────────

    if verb == "buy":
        output = _handle_buy(noun, char, zone, current_room_id, rng)
        time_msg = _advance_time(char, 1)
        return CommandResult(output + time_msg, None, True, [])

    # ── Sell ───────────────────────────────────────────────────────

    if verb == "sell":
        output = _handle_sell(noun, char, zone, current_room_id, rng)
        time_msg = _advance_time(char, 1)
        return CommandResult(output + time_msg, None, True, [])

    # ── Hunt ───────────────────────────────────────────────────────

    if verb == "hunt":
        output = _handle_hunt(char, zone, current_room_id, rng)
        time_msg = _advance_time(char, 3)
        return CommandResult(output + time_msg, None, True, [])

    # ── Bargain ────────────────────────────────────────────────────

    if verb == "bargain":
        output = _handle_bargain(char, rng)
        time_msg = _advance_time(char, 1)
        return CommandResult(output + time_msg, None, True, [])

    # ── Explore / Search ───────────────────────────────────────────

    if verb == "explore":
        output = _handle_explore(char, zone, current_room_id, rng)
        time_msg = _advance_time(char, 3)
        return CommandResult(output + time_msg, None, True, [])

    # ── Inventory ──────────────────────────────────────────────────

    if verb == "inventory":
        output = _handle_inventory(char)
        return CommandResult(output, None, False, [])

    # ── Help ───────────────────────────────────────────────────────

    if verb == "help":
        output = _handle_help()
        return CommandResult(output, None, False, [])

    # ── Quit ───────────────────────────────────────────────────────

    if verb == "quit":
        return CommandResult("Your journey ends here. Farewell!", None, False, [])

    # ── Score ──────────────────────────────────────────────────────

    if verb == "score":
        output = _handle_score(char)
        return CommandResult(output, None, False, [])

    # ── Status ─────────────────────────────────────────────────────

    if verb == "status":
        output = _handle_status(char, zone, current_room_id)
        return CommandResult(output, None, False, [])

    # ── Fallback ───────────────────────────────────────────────────

    return CommandResult(f"You try to {verb}, but nothing happens.", None, False, [])


# ── Time Passage ─────────────────────────────────────────────────────


def _advance_time(char: PlayerCharacter, hours: int) -> str:
    """Advance the game clock by `hours`. Returns a time-passage message.

    - char.month increments by hours mod 12.
    - When month wraps past 12, increment year and age the character by 1.
    """
    if hours <= 0:
        return ""

    old_year = char.year
    old_month = char.month

    char.month += hours
    while char.month >= 12:
        char.month -= 12
        char.year += 1
        char.age += 1

    # Build a compact time-passage message
    if char.year > old_year:
        years_passed = char.year - old_year
        msg = f"\n[{hours} hours pass... You are now {char.age} years old (year {char.year}).]"
    else:
        msg = f"\n[{hours} hours pass...]"

    return msg


def _season_from_month(month: int) -> str:
    """Return the season name for a given month (0-11)."""
    if month < 3:
        return "Spring"
    elif month < 6:
        return "Summer"
    elif month < 9:
        return "Autumn"
    else:
        return "Winter"


def _time_of_day(hours_accumulated: int) -> str:
    """Return a time-of-day string based on accumulated hours."""
    hour_of_day = hours_accumulated % 24
    if hour_of_day < 6:
        return "night"
    elif hour_of_day < 12:
        return "morning"
    elif hour_of_day < 18:
        return "afternoon"
    else:
        return "evening"


# ── Command Implementations ─────────────────────────────────────────


def _handle_move(
    direction: str,
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    world: World,
    seed: int,
    rng: random.Random,
) -> CommandResult:
    """Handle movement commands."""
    current_room = zone.rooms.get(current_room_id)
    if current_room is None:
        return CommandResult("You are lost in the void.", None, False, [])

    # Check exit
    direction_short = direction[0]  # n, s, e, w, etc.
    target = current_room.exits.get(direction_short)

    # Try full direction name
    if target is None:
        compass = {"north": "n", "south": "s", "east": "e", "west": "w",
                    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
                    "up": "u", "down": "d"}
        target = current_room.exits.get(compass.get(direction, direction))

    if target is None:
        return CommandResult(f"You cannot go {direction} from here.", None, False, [])

    # Handle wilderness exit
    if target.endswith("_to_wilderness"):
        # Leaving settlement — would transition to world map
        return CommandResult(
            f"You leave {char.settlement} behind and venture into the wild lands beyond.",
            "wilderness", False, [],
        )

    # Handle wilderness back to settlement
    if target == "wilderness":
        if zone.name == "Wilderness":
            return CommandResult(
                f"You try to find your way, but the wilderness stretches endlessly.",
                None, False, [],
            )
        return CommandResult(
            f"You venture deeper into the wilderness.",
            target, False, [],
        )

    # Normal room-to-room movement
    if target in zone.rooms:
        target_room = zone.rooms[target]
        output = f"You go {direction}.\n{target_room.name}\n{target_room.description}"
        # Show visible exits
        if target_room.exits:
            exit_dirs = sorted(target_room.exits.keys())
            output += f"\n\nExits: {', '.join(exit_dirs)}"
        # Show NPCs in the new room
        if target_room.npcs:
            npc_names = [npc["name"] for npc in target_room.npcs]
            output += f"\n\nHere: {', '.join(npc_names)}"
        return CommandResult(output, target, False, [])

    return CommandResult(f"You cannot go that way.", None, False, [])


def _handle_look(
    zone: Zone,
    current_room_id: str,
    char: PlayerCharacter,
    noun: str | None,
    rng: random.Random,
) -> str:
    """Handle the 'look' command."""
    if current_room_id == "wilderness":
        # Wilderness description depends on terrain
        return _describe_wilderness(char, rng)

    room = zone.rooms.get(current_room_id)
    if room is None:
        return "You see nothing but darkness."

    if noun:
        # Looking at something specific in the room
        return _look_at_specific(room, noun, rng)

    # Full room description
    lines = []
    lines.append(f"[ {room.name} ]")
    lines.append("")
    lines.append(room.description)

    # Show items on the ground
    if room.contents:
        item_names = [item.get("name", "something") for item in room.contents]
        lines.append("")
        lines.append(f"You see: {', '.join(item_names)}.")

    # Show NPCs
    if room.npcs:
        for npc in room.npcs:
            title = npc.get("title", "")
            name = npc.get("name", "Someone")
            lines.append("")
            lines.append(f"{name} stands here, {title}.")

    # Show exits
    if room.exits:
        exit_dirs = sorted(room.exits.keys())
        # Map short dirs to full names
        full_names = {
            "n": "north", "s": "south", "e": "east", "w": "west",
            "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest",
            "u": "up", "d": "down",
        }
        display_dirs = [full_names.get(d, d) for d in exit_dirs]
        lines.append("")
        lines.append(f"Exits: {', '.join(display_dirs)}.")

    # Show room tags (for markets, shops, etc.)
    if room.tags:
        tags_str = ", ".join(room.tags)
        lines.append("")
        lines.append(f"[{tags_str}]")

    return "\n".join(lines)


def _describe_wilderness(char: PlayerCharacter, rng: random.Random) -> str:
    """Describe the wilderness based on the player's approximate location."""
    lines = []
    lines.append("[ Wilderness ]")
    lines.append("")

    # Get some terrain-based descriptions
    terrain_descs = [
        "The wild lands stretch before you, untamed and vast.",
        "Nature reigns supreme here — no path, no sign of civilization.",
        "The wind whispers through the untamed landscape.",
    ]
    lines.append(rng.choice(terrain_descs))
    lines.append("")
    lines.append("You could return to the settlement, or press deeper into the unknown.")
    lines.append("")
    lines.append("Exits: back (return to settlement).")

    return "\n".join(lines)


def _look_at_specific(room: Room, noun: str, rng: random.Random) -> str:
    """Describe a specific thing in the room."""
    noun_lower = noun.lower()

    # Check NPCs
    for npc in room.npcs:
        if noun_lower in npc.get("name", "").lower() or noun_lower in npc.get("title", "").lower():
            name = npc["name"]
            title = npc.get("title", "person")
            dialog = npc.get("dialog", "They nod in greeting.")
            return f"You look at {name}, the {title}.\n{dialog}"

    # Check contents
    for item in room.contents:
        name = item.get("name", "").lower()
        if noun_lower in name:
            return f"You examine the {name} closely. It looks like an ordinary {item.get('type', 'object')}, but it might be useful."

    # Check exits
    full_names = {"n": "north", "s": "south", "e": "east", "w": "west"}
    for short_dir, full_dir in full_names.items():
        if noun_lower in (short_dir, full_dir):
            target = room.exits.get(short_dir)
            if target:
                target_name = target.replace("_", " ").title()
                return f"To the {full_dir}, you see {target_name}."
            return f"There is nothing in that direction."

    return f"You don't see a {noun} here."


def _handle_get(
    noun: str | None,
    char: PlayerCharacter,
    current_room_id: str,
    zone: Zone,
    rng: random.Random,
) -> str:
    """Handle picking up an item."""
    if not noun:
        return "What do you want to get?"

    room = zone.rooms.get(current_room_id)
    if room is None:
        return "There's nothing here to get."

    noun_lower = noun.lower()

    # Check room contents
    for i, item in enumerate(room.contents):
        if noun_lower in item.get("name", "").lower():
            char.inventory.append(item["name"])
            room.contents.pop(i)
            return f"You pick up the {item['name']}."

    return f"You don't see a {noun} here."


def _handle_drop(
    noun: str | None,
    char: PlayerCharacter,
    current_room_id: str,
    zone: Zone,
    rng: random.Random,
) -> str:
    """Handle dropping an item."""
    if not noun:
        return "What do you want to drop?"

    noun_lower = noun.lower()

    # Check inventory
    for i, item_name in enumerate(char.inventory):
        if noun_lower in item_name.lower():
            room = zone.rooms.get(current_room_id)
            if room is not None:
                room.contents.append({"type": "dropped", "name": item_name})
            char.inventory.pop(i)
            return f"You drop the {item_name}."

    return f"You don't have a {noun}."


def _handle_use(noun: str | None, char: PlayerCharacter, rng: random.Random) -> str:
    """Handle using an item."""
    if not noun:
        return "What do you want to use?"

    noun_lower = noun.lower()

    if noun_lower not in [item.lower() for item in char.inventory]:
        return f"You don't have a {noun} to use."

    # Item-specific effects
    if "bandage" in noun_lower:
        if char.health >= 100:
            return "You're already fully healed."
        heal = rng.randint(10, 25)
        char.health = min(100, char.health + heal)
        char.inventory = [i for i in char.inventory if "bandage" not in i.lower()]
        return f"You use the bandage. You feel better (+{heal} health)."

    if "potion" in noun_lower:
        heal = rng.randint(20, 50)
        char.health = min(100, char.health + heal)
        char.inventory = [i for i in char.inventory if "potion" not in i.lower()]
        return f"You drink the potion. Warmth spreads through your body (+{heal} health)."

    if "rations" in noun_lower:
        heal = rng.randint(5, 10)
        char.health = min(100, char.health + heal)
        char.inventory = [i for i in char.inventory if "rations" not in i.lower()]
        return f"You eat the rations. Not the best meal, but it helps (+{heal} health)."

    if "torch" in noun_lower:
        return "You light the torch. It burns brightly, illuminating the area."

    if "map" in noun_lower:
        return "You study the map. It shows the surrounding region with markings you don't fully understand."

    return f"You use the {noun}. Nothing obvious happens."


# ── Trading System ───────────────────────────────────────────────────


def _is_market_room(room: Room) -> bool:
    """Check if a room has market/shop tags for trading."""
    if room.tags:
        for tag in room.tags:
            if tag in ("market", "shop", "bazaar"):
                return True
    return False


def _handle_talk(
    noun: str | None,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle talking to an NPC."""
    room = zone.rooms.get(current_room_id)
    if room is None:
        return "There's no one here to talk to."

    if not room.npcs:
        return "There's no one here to talk to."

    # Check if this is a market room — show trade menu
    if _is_market_room(room):
        market_npcs = [n for n in room.npcs if "merchant" in n.get("title", "").lower()
                       or "vendor" in n.get("title", "").lower()
                       or "haggler" in n.get("title", "").lower()
                       or "appraiser" in n.get("title", "").lower()
                       or "shop" in n.get("title", "").lower()
                       or "trader" in n.get("title", "").lower()
                       or "keeper" in n.get("title", "").lower()]
        if market_npcs or noun is None:
            trade_npc = market_npcs[0] if market_npcs else room.npcs[0]

            # Show items available for sale from room contents
            sellable_items = [item for item in room.contents
                              if item.get("type") not in ("fountain", "notice_board", "bench", "statue",
                                                          "barrel", "table", "hearth", "board_game",
                                                          "altar", "candle", "offering", "holy_symbol",
                                                          "throne", "map", "ledger", "seal",
                                                          "anvil", "forge", "tools", "weapon_rack",
                                                          "sack", "scales", "anchor", "net", "rope",
                                                          "armor", "torch", "signal_horn",
                                                          "bookshelf", "desk", "lectern", "scroll",
                                                          "crate", "pottery", "fabric")]

            lines = [f"You approach {trade_npc['name']}, the {trade_npc.get('title', 'merchant')}.",
                     "",
                     "\"Welcome! Feel free to browse my wares.\"",
                     "",
                     "You can use:",
                     "  buy <item>  — purchase an item",
                     "  sell <item> — sell an item from your inventory",
                     "  bargain     — haggle for better prices",
                     ""]

            if sellable_items:
                lines.append("Items for sale:")
                for item in sellable_items:
                    price = _item_price(item["name"], rng)
                    lines.append(f"  {item['name']:20s} {price:3d} gold")
            else:
                lines.append("(The merchant's stall seems sparse today.)")

            return "\n".join(lines)

    if not noun:
        # Talk to first NPC
        npc = room.npcs[0]
        dialog = npc.get("dialog", "They nod in greeting but say nothing.")
        return f"You speak with {npc['name']}, the {npc.get('title', 'person')}.\n\"{dialog}\""

    # Try to find specific NPC
    noun_lower = noun.lower()
    for npc in room.npcs:
        if noun_lower in npc.get("name", "").lower() or noun_lower in npc.get("title", "").lower():
            dialog = npc.get("dialog", "They nod in greeting but say nothing.")

            # If market room and talking to a merchant-type NPC, show trade menu
            if _is_market_room(room):
                return _handle_talk(noun, zone, current_room_id, rng)  # Re-route to show trade menu

            return f"You speak with {npc['name']}, the {npc.get('title', 'person')}.\n\"{dialog}\""

    return f"You don't see {noun} here to talk to."


def _item_price(item_name: str, rng: random.Random, for_sale: bool = False) -> int:
    """Determine the price of an item. Market prices vary by item type."""
    name_lower = item_name.lower()
    # Item price table
    prices = {
        "bandage": 10, "potion": 25, "rations": 8, "torch": 5,
        "sword": 50, "dagger": 30, "shield": 40, "spear": 35,
        "axe": 45, "battle axe": 60, "warhammer": 55, "mace": 40,
        "longsword": 65, "shortsword": 45,
        "herbs": 12, "rope": 8, "lantern": 20, "lockpick": 15,
        "map": 15, "compass": 25, "scroll": 30, "fishing rod": 10,
        "leather": 15, "fur": 10, "raw meat": 5, "pelt": 12,
        "bone": 3, "feather": 2, "old boots": 5, "rusty dagger": 8,
        "few coins": 0, "coin pouch": 20, "key": 10, "water flask": 6,
    }
    base_price = 5  # default
    for key, price in prices.items():
        if key in name_lower:
            base_price = price
            break

    # Add variation
    variation = rng.randint(-2, 2)
    return max(1, base_price + variation)


def _handle_buy(
    noun: str | None,
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle buying an item from a market NPC."""
    if not noun:
        return "What do you want to buy?"

    room = zone.rooms.get(current_room_id)
    if room is None:
        return "There's no one here to trade with."

    if not _is_market_room(room):
        return "There's no merchant here to buy from."

    noun_lower = noun.lower()

    # Find the item in room contents
    for i, item in enumerate(room.contents):
        if noun_lower in item.get("name", "").lower():
            # Skip fixture items (non-purchasable)
            if item.get("type") in ("fountain", "notice_board", "bench", "statue",
                                    "barrel", "table", "hearth", "board_game",
                                    "altar", "candle", "offering", "holy_symbol",
                                    "throne", "map", "ledger", "seal",
                                    "anvil", "forge", "tools",
                                    "sack", "scales", "anchor", "net",
                                    "armor", "torch", "signal_horn",
                                    "bookshelf", "desk", "lectern",
                                    "crate", "pottery", "fabric"):
                return f"You can't buy the {item['name']} — it's not for sale."

            price = _item_price(item["name"], rng, for_sale=True)

            # Apply bargain buff (20% discount)
            bargain_buff = _get_bargain_buff(char)
            final_price = max(1, int(price * (1.0 - bargain_buff)))

            if char.gold < final_price:
                return f"You need {final_price} gold to buy the {item['name']}, but you only have {char.gold}."

            char.gold -= final_price
            char.total_gold_spent += final_price
            item_name = item["name"]
            char.inventory.append(item_name)
            room.contents.pop(i)

            # Gain trade XP
            _gain_skill_xp(char, "trade", 5)

            return f"You buy the {item_name} for {final_price} gold."

    # Check if the item might be in inventory already
    for inv_item in char.inventory:
        if noun_lower in inv_item.lower():
            return f"You already have {inv_item}."

    return f"The merchant doesn't have a {noun} for sale."


def _handle_sell(
    noun: str | None,
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle selling an item to a market NPC."""
    if not noun:
        return "What do you want to sell?"

    room = zone.rooms.get(current_room_id)
    if room is None:
        return "There's no one here to trade with."

    if not _is_market_room(room):
        return "There's no merchant here to sell to."

    noun_lower = noun.lower()

    # Find the item in inventory
    for i, item_name in enumerate(char.inventory):
        if noun_lower in item_name.lower():
            price = _item_price(item_name, rng, for_sale=False)

            # Apply bargain buff (20% bonus on sell price)
            bargain_buff = _get_bargain_buff(char)
            final_price = max(1, int(price * (0.5 + bargain_buff)))  # Base 50% of value + bargain bonus

            char.inventory.pop(i)
            char.gold += final_price
            char.total_gold_earned += final_price

            # Add to room contents
            if room is not None:
                room.contents.append({"type": "dropped", "name": item_name})

            # Gain trade XP
            _gain_skill_xp(char, "trade", 5)

            return f"You sell the {item_name} to the merchant for {final_price} gold."

    return f"You don't have a {noun} to sell."


# ── Active Skills ────────────────────────────────────────────────────


def _get_bargain_buff(char: PlayerCharacter) -> float:
    """Get the current bargain buff value (0.0 to 0.3 based on trade skill, decays)."""
    trade_level = char.skills.get("trade", 1)
    return (trade_level - 1) * 0.03  # +3% per level over 1, max ~0.27 at level 10


def _handle_bargain(char: PlayerCharacter, rng: random.Random) -> str:
    """Handle the bargain command — improve trade prices for the next transaction."""
    trade_level = char.skills.get("trade", 1)
    skill_bonus = _get_bargain_buff(char)
    # Bargain also grants some XP
    xp_amount = rng.randint(3, 8)
    _gain_skill_xp(char, "trade", xp_amount)

    discount_pct = int(skill_bonus * 100)
    return (
        f"You haggle with the merchant, drawing on your trade skill (level {trade_level}).\n"
        f"You secure a {discount_pct}% better price on future transactions here.\n"
        f"Your trade skill improves (+{xp_amount} XP)."
    )


def _handle_hunt(
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle the hunt command — find food/leather in wilderness."""
    room = zone.rooms.get(current_room_id)

    # Hunting works in wilderness or outdoors
    is_outdoors = True
    if room and room.tags:
        if "indoors" in room.tags:
            is_outdoors = False

    if current_room_id == "wilderness":
        is_outdoors = True

    if not is_outdoors:
        return "You can't hunt indoors. Try the wilderness or open areas."

    survival_level = char.skills.get("survival", 1)
    success_chance = 0.3 + (survival_level * 0.05)  # 35% at level 1, 80% at level 10
    xp_amount = rng.randint(5, 12)

    if rng.random() < success_chance:
        # Successful hunt
        loot_options = [
            {"name": "raw meat", "type": "food"},
            {"name": "leather", "type": "material"},
            {"name": "fur", "type": "material"},
            {"name": "pelt", "type": "material"},
            {"name": "feathers", "type": "material"},
            {"name": "bone", "type": "material"},
        ]
        loot = rng.choice(loot_options)
        amount = rng.randint(1, 3)
        for _ in range(amount):
            char.inventory.append(loot["name"])

        _gain_skill_xp(char, "survival", xp_amount)

        return (
            f"You stalk through the wilds, drawing on your survival skill (level {survival_level}).\n"
            f"You successfully hunt and gather {amount}x {loot['name']}!\n"
            f"Your survival skill improves (+{xp_amount} XP)."
        )
    else:
        # Failed hunt, still gain some XP
        _gain_skill_xp(char, "survival", max(1, xp_amount // 2))
        return (
            f"You stalk through the wilds, drawing on your survival skill (level {survival_level}).\n"
            f"The hunt is unsuccessful today. You find no game.\n"
            f"Your survival skill improves slightly (+{max(1, xp_amount // 2)} XP)."
        )


def _handle_explore(
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle the explore/search command — find random items."""
    room = zone.rooms.get(current_room_id)
    is_wilderness = current_room_id == "wilderness" or (zone and zone.zone_type == "wilderness")

    is_outdoors = True
    if room and room.tags and "indoors" in room.tags:
        is_outdoors = False

    if not is_outdoors and not is_wilderness:
        return "There's nothing to discover in here. Try the wilderness or open areas."

    survival_level = char.skills.get("survival", 1)
    xp_amount = rng.randint(3, 10)

    if is_wilderness:
        # Wilderness exploration — find rarer items
        loot_table = [
            {"name": "herbs", "type": "consumable"},
            {"name": "rare herbs", "type": "consumable"},
            {"name": "fishing rod", "type": "tool"},
            {"name": "rope", "type": "tool"},
            {"name": "bandage", "type": "consumable"},
            {"name": "water flask", "type": "consumable"},
            {"name": "ancient coin", "type": "treasure"},
            {"name": "shiny pebble", "type": "curio"},
            {"name": "map fragment", "type": "scroll"},
            {"name": "mushroom", "type": "food"},
        ]
    else:
        # Settlement exploration — find common items
        loot_table = [
            {"name": "herbs", "type": "consumable"},
            {"name": "bandage", "type": "consumable"},
            {"name": "coin pouch", "type": "treasure"},
            {"name": "rusty dagger", "type": "weapon"},
            {"name": "old boots", "type": "junk"},
            {"name": "key", "type": "tool"},
            {"name": "torch", "type": "tool"},
            {"name": "few coins", "type": "treasure"},
        ]

    # Multiple items based on skill
    find_count = 1 + (survival_level >= 5) + (survival_level >= 9)
    loot_found = []
    for _ in range(find_count):
        if rng.random() < 0.6:  # 60% chance per roll
            item = rng.choice(loot_table)
            loot_found.append(item["name"])
            char.inventory.append(item["name"])

    _gain_skill_xp(char, "survival", xp_amount)

    if loot_found:
        items_str = ", ".join(loot_found)
        return (
            f"You search the area carefully, drawing on your survival skill (level {survival_level}).\n"
            f"You find: {items_str}!\n"
            f"Your survival skill improves (+{xp_amount} XP)."
        )
    else:
        return (
            f"You search the area carefully, drawing on your survival skill (level {survival_level}).\n"
            f"You find nothing of interest.\n"
            f"Your survival skill improves slightly (+{xp_amount} XP)."
        )


# ── Combat System ────────────────────────────────────────────────────


def _has_weapon(char: PlayerCharacter) -> bool:
    """Check if the player is carrying a weapon."""
    for item in char.inventory:
        if item.lower() in WEAPON_ITEMS:
            return True
        # Also check if item contains known weapon substrings
        for weapon in WEAPON_ITEMS:
            if weapon in item.lower():
                return True
    return False


def _handle_combat(
    noun: str | None,
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle combat commands with proper damage system."""
    room = zone.rooms.get(current_room_id)
    if room is None:
        return "There's nothing here to fight."

    if not noun:
        return "Attack what?"

    noun_lower = noun.lower()

    # Check for NPCs to fight
    for npc in room.npcs[:]:  # iterate over copy
        if noun_lower in npc.get("name", "").lower() or noun_lower in npc.get("title", "").lower():
            npc_name = npc["name"]
            npc_title = npc.get("title", "creature")

            # Determine NPC HP (15-40, seed-deterministic from rng)
            npc_hp = rng.randint(15, 40)

            # Player combat stats
            combat_skill = char.skills.get("combat", 1)
            has_weapon_val = 1 if _has_weapon(char) else 0
            player_damage = 5 + (has_weapon_val * 5) + (combat_skill * 2)

            # NPC damage (3-10)
            npc_damage = rng.randint(3, 10)

            lines = []
            lines.append(f"You attack {npc_name} the {npc_title}!")
            lines.append("")

            # Combat round
            round_damage = player_damage + rng.randint(-3, 3)  # slight variance
            round_damage = max(1, round_damage)
            npc_hp -= round_damage

            # NPC retaliates
            player_takes = npc_damage + rng.randint(-2, 2)  # slight variance
            player_takes = max(1, player_takes)
            char.health -= player_takes

            lines.append(f"You strike for {round_damage} damage! (NPC has {max(0, npc_hp)} HP remaining)")
            lines.append(f"{npc_name} hits back for {player_takes} damage!")

            if char.health <= 0:
                char.health = 5  # Don't kill, but nearly dead
                lines.append("")
                lines.append("You are nearly dead! You barely manage to retreat.")
                return "\n".join(lines)

            if npc_hp <= 0:
                # Victory!
                room.npcs.remove(npc)

                # Gold reward
                gold_reward = rng.randint(5, 20)
                char.gold += gold_reward
                char.total_gold_earned += gold_reward

                # Combat XP
                combat_xp = rng.randint(10, 25)
                _gain_skill_xp(char, "combat", combat_xp)

                # Loot drops
                loot_items = [["rusty dagger", "few coins", "old boots"],
                              ["few coins", "leather scraps"],
                              ["old boots", "bone charm"],
                              ["rusty dagger", "pelt"],
                              ["few coins", "rations", "torch"]]
                loot = rng.choice(loot_items)
                for loot_name in loot:
                    room.contents.append({"type": "loot", "name": loot_name})

                lines.append("")
                lines.append(f"You slay {npc_name}!")
                lines.append(f"They drop {gold_reward} gold and: {', '.join(loot)}.")
                lines.append(f"Your combat skill improves (+{combat_xp} XP).")
            else:
                lines.append("")
                lines.append(f"{npc_name} still stands, wounded but defiant.")

            return "\n".join(lines)

    return f"There's no {noun} to fight here."


def _handle_say(noun: str | None, char: PlayerCharacter) -> str:
    """Handle saying something."""
    if not noun:
        return "Say what?"
    return f'You say, "{noun}"\nYour words echo in the air.'


def _handle_yell(noun: str | None, char: PlayerCharacter) -> str:
    """Handle yelling."""
    if not noun:
        noun = "HEY!"
    message = noun.upper()
    return f'You yell, "{message}!"\nYour voice carries through the area.'


def _handle_inventory(char: PlayerCharacter) -> str:
    """Handle inventory command."""
    if not char.inventory:
        output = "You are carrying:\n  (nothing)"
    else:
        items = "\n  ".join(char.inventory)
        output = f"You are carrying:\n  {items}"
    output += f"\n\nGold: {char.gold} coins"
    return output


def _handle_help() -> str:
    """Handle the help command."""
    return """\
╔══════════════════════════════════════════╗
║           wyrd — MUD Commands            ║
╠══════════════════════════════════════════╣
║  Movement:                               ║
║    n/s/e/w      — cardinal directions    ║
║    ne/nw/se/sw  — diagonal directions    ║
║    up/down/u/d  — vertical movement      ║
║                                          ║
║  Actions:                                ║
║    look/l       — look around            ║
║    get/take     — pick up an item        ║
║    drop         — drop an item           ║
║    use          — use an item            ║
║    talk         — talk to someone        ║
║    say/tell     — say something          ║
║    yell/shout   — yell loudly            ║
║    kill/attack  — fight an enemy         ║
║    buy          — buy from a merchant    ║
║    sell         — sell to a merchant     ║
║    bargain      — haggle for prices      ║
║    hunt         — hunt in the wilds      ║
║    explore      — search for items       ║
║                                          ║
║  Info:                                   ║
║    inventory/i  — check your items       ║
║    status/st    — your current state     ║
║    score/stats  — character summary      ║
║    help/h       — this help screen       ║
║    quit/q       — end your journey       ║
╚══════════════════════════════════════════╝"""


def _handle_score(char: PlayerCharacter) -> str:
    """Handle the score command — character summary with bars."""
    lines = []

    # Header
    divider = "═" * 38
    lines.append(f"╔{divider}╗")
    lines.append(f"║  {_pad_right(char.name, 34)} ║")
    lines.append(f"║  {_pad_right(char.profession, 34)} ║")
    lines.append(f"╠{divider}╣")

    # Health bar
    health_blocks = char.health // 5
    health_bar = "█" * health_blocks + "░" * (20 - health_blocks)
    lines.append(f"║  Health: {health_bar}  ║")
    lines.append(f"║          {char.health:>3}/100                 ║")

    lines.append(f"║  Gold:   {char.gold:>5} coins              ║")
    lines.append(f"║  Age:    {char.age:>3} years               ║")
    lines.append(f"║  Year:   {char.year:>4}  ({_season_from_month(char.month):>6})        ║")

    lines.append(f"╠{divider}╣")
    lines.append("║  Skills:                          ║")
    for skill_name in ["combat", "trade", "persuasion", "survival", "crafting"]:
        level = char.skills.get(skill_name, 1)
        total_xp = char.skill_xp.get(skill_name, 0)
        # XP bar (20 chars)
        xp_for_current = _xp_for_level(level)
        xp_for_next = _xp_for_level(min(level + 1, 10))
        xp_in_level = total_xp - xp_for_current
        xp_range = xp_for_next - xp_for_current
        if xp_range > 0:
            xp_blocks = min(20, int((xp_in_level / xp_range) * 20))
        else:
            xp_blocks = 20  # max level
        xp_bar = "█" * xp_blocks + "░" * (20 - xp_blocks)

        level_bar = "█" * level + "░" * (10 - level)
        lines.append(f"║  {_pad_right(skill_name, 9)} Lv{level:>2} {level_bar:<12} ║")
        lines.append(f"║  {'':>9} XP {xp_bar} ║")

    lines.append(f"╠{divider}╣")
    lines.append(f"║  Location: {_pad_right(char.settlement, 23)} ║")
    lines.append(f"║  Region:   {_pad_right(char.region, 23)} ║")

    # Time info
    time_of_day_name = _time_of_day(char.month * 2 * 24)  # rough time of day based on month progression
    lines.append(f"║  Time:     {_pad_right(time_of_day_name + ' in ' + _season_from_month(char.month), 23)} ║")

    lines.append(f"╚{divider}╝")
    return "\n".join(lines)


def _handle_status(char: PlayerCharacter, zone: Zone, current_room_id: str) -> str:
    """Handle status command — quick status check with time and season."""
    room = zone.rooms.get(current_room_id, Room(name="Unknown", description="", exits={}, room_id="unknown"))
    health_blocks = char.health // 5
    health_bar = "█" * health_blocks + "░" * (20 - health_blocks)

    season = _season_from_month(char.month)
    time_of_day = _time_of_day(char.month * 2 * 24)

    return (
        f"{char.name} | {char.profession}\n"
        f"Health: {health_bar} ({char.health}/100)\n"
        f"Gold: {char.gold}  |  Age: {char.age}  |  Year: {char.year}\n"
        f"Season: {season}  |  Time: {time_of_day}\n"
        f"Location: {char.settlement} → {room.name}"
    )


def _pad_right(text: str, width: int) -> str:
    """Left-align text in a field of given width."""
    return text.ljust(width)


def _xp_for_level(level: int) -> int:
    """XP needed to reach a given level (level 1 = 0, level 2 = 15, etc.)."""
    if level <= 1:
        return 0
    return int((level * (level - 1) / 2) * 15)
