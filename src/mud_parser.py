"""
wyrd — MUD Command Parser (Phase 26.2).

Parses natural MUD commands and processes them against the world state.
Designed for the Textual-based single-user MUD interface.

Supported verbs:
  look/l, get, take, drop, use, talk, say, yell,
  kill, attack, fight, north/n, south/s, east/e, west/w,
  inventory/i, help, quit, score, status

Everything is seed-deterministic: same seed → same room descriptions.
"""

import random
from collections import namedtuple
from typing import Optional

from .room import Room, Zone, describe_terrain, CommandResult
from .embody import PlayerCharacter
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
    "nw": "northwest",
    "northwest": "northwest",
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
        return _handle_move(verb, char, zone, current_room_id, world, seed, rng)

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
        return CommandResult(output, None, False, [])

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
        if "You slay" in output or "defeated" in output:
            events.append(f"Combat: {char.name} fought in {zone.name}")
        return CommandResult(output, None, char_changed, events)

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
            return f"You speak with {npc['name']}, the {npc.get('title', 'person')}.\n\"{dialog}\""

    return f"You don't see {noun} here to talk to."


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


def _handle_combat(
    noun: str | None,
    char: PlayerCharacter,
    zone: Zone,
    current_room_id: str,
    rng: random.Random,
) -> str:
    """Handle combat commands."""
    room = zone.rooms.get(current_room_id)
    if room is None:
        return "There's nothing here to fight."

    if not noun:
        return "Attack what?"

    noun_lower = noun.lower()

    # Check for NPCs to fight
    for npc in room.npcs[:]:
        if noun_lower in npc.get("name", "").lower() or noun_lower in npc.get("title", "").lower():
            combat_level = rng.randint(1, 10)
            player_power = sum(char.skills.values()) + (char.health // 10)
            npc_power = combat_level + rng.randint(1, 5)

            if player_power > npc_power:
                # Victory
                room.npcs.remove(npc)
                loot = rng.randint(1, 10)
                char.gold += loot
                # Gain XP
                if "combat" in char.skills:
                    char.skill_xp["combat"] = char.skill_xp.get("combat", 0) + rng.randint(5, 15)
                    old_level = char.skills["combat"]
                    from .embody import _skill_level_from_xp
                    new_level = _skill_level_from_xp(char.skill_xp["combat"])
                    char.skills["combat"] = min(new_level, 10)
                    level_up = f"\n  ⚡ Combat skill increased!" if new_level > old_level else ""
                # Health cost
                health_cost = rng.randint(5, 15)
                char.health = max(0, char.health - health_cost)
                return (
                    f"You engage {npc['name']} in battle!\n"
                    f"After a fierce struggle, you defeat them!\n"
                    f"You find {loot} gold coins on their body.{level_up}\n"
                    f"You took {health_cost} damage."
                )
            else:
                # Defeat
                health_cost = rng.randint(10, 25)
                char.health = max(0, char.health - health_cost)
                if char.health <= 0:
                    char.alive = False
                    return (
                        f"You attack {npc['name']}, but they are too strong!\n"
                        f"You are defeated. The world fades to darkness..."
                    )
                return (
                    f"You attack {npc['name']}, but they fight back fiercely!\n"
                    f"You take {health_cost} damage and retreat."
                )

    return f"There's no {noun} to fight here."


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
╔══════════════════════════════════════╗
║           wyrd — MUD Commands        ║
╠══════════════════════════════════════╣
║  Movement:                           ║
║    n/s/e/w      — cardinal directions ║
║    ne/nw/se/sw  — diagonal directions ║
║    up/down/u/d  — vertical movement   ║
║                                      ║
║  Actions:                            ║
║    look/l       — look around        ║
║    get/take     — pick up an item    ║
║    drop         — drop an item       ║
║    use          — use an item        ║
║    talk         — talk to someone    ║
║    say/tell     — say something      ║
║    yell/shout   — yell loudly        ║
║    kill/attack  — fight an enemy     ║
║                                      ║
║  Info:                               ║
║    inventory/i  — check your items   ║
║    status/st    — your current state ║
║    score/stats  — character summary  ║
║    help/h       — this help screen   ║
║    quit/q       — end your journey   ║
╚══════════════════════════════════════╝"""


def _handle_score(char: PlayerCharacter) -> str:
    """Handle the score command — character summary."""
    lines = []
    lines.append("╔══════════════════════════════════╗")
    lines.append(f"║  {char.name:<32} ║")
    lines.append(f"║  {char.profession:<32} ║")
    lines.append("╠══════════════════════════════════╣")
    lines.append(f"║  Health:  {char.health:>3}/100               ║")
    lines.append(f"║  Gold:    {char.gold:>5} coins            ║")
    lines.append(f"║  Age:     {char.age:>3} years              ║")
    lines.append(f"║  Year:    {char.year:>4}                   ║")
    lines.append("╠══════════════════════════════════╣")
    lines.append("║  Skills:                          ║")
    for skill_name in ["combat", "trade", "persuasion", "survival", "crafting"]:
        level = char.skills.get(skill_name, 1)
        bar = "█" * level + "░" * (10 - level)
        lines.append(f"║    {skill_name:<12} {bar:<12} ║")
    lines.append("╠══════════════════════════════════╣")
    lines.append(f"║  Location: {char.settlement:<23} ║")
    lines.append(f"║  Region:   {char.region:<23} ║")
    lines.append("╚══════════════════════════════════╝")
    return "\n".join(lines)


def _handle_status(char: PlayerCharacter, zone: Zone, current_room_id: str) -> str:
    """Handle status command — quick status check."""
    room = zone.rooms.get(current_room_id, Room(name="Unknown", description="", exits={}, room_id="unknown"))
    health_bar = "█" * (char.health // 10) + "░" * (10 - char.health // 10)
    return (
        f"{char.name} | {char.profession}\n"
        f"Health: {health_bar} ({char.health}/100)\n"
        f"Gold: {char.gold}  |  Age: {char.age}  |  Year: {char.year}\n"
        f"Location: {char.settlement} → {room.name}"
    )
