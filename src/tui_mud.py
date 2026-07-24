"""wyrd — Textual MUD screen (Phase 26: Single-User MUD).

The main game interface. Room view, event log, command input, stats sidebar.
Replaces all curses TUIs and CLI commands. This is the entire game surface.
"""

from __future__ import annotations

import random
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Header, Footer, Static, Label, Button, Input, ListView, ListItem, Log, RichLog,
)
from textual.widget import Widget

from .world import World
from .embody import (
    PlayerCharacter,
    _generate_character,
    _advance_time,
    _handle_interactive_events,
    _status_line,
)
from .room import generate_zones, Zone, Room
from .mud_parser import parse_command, handle_command, CommandResult


# ── Color theme ─────────────────────────────────────────────────────────

class MudColors:
    """Color names for the MUD interface."""
    ROOM_DESC = "bold white"
    EXIT = "cyan"
    ITEM = "yellow"
    NPC = "green"
    EVENT = "white"
    GOOD = "green"
    BAD = "red"
    INFO = "blue"
    DIM = "grey50"
    STAT = "bold cyan"
    GOLD = "bold yellow"
    HEALTH = "bold red"
    SKILL = "magenta"


# ── Help screen ─────────────────────────────────────────────────────────

class MudHelp(ModalScreen):
    """Help overlay for the MUD."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold yellow]wyrd MUD — Help[/]\n\n"
            "[bold]Movement[/]\n"
            "  n / s / e / w     Move in a direction\n"
            "\n"
            "[bold]Exploration[/]\n"
            "  look / l          Look around the room\n"
            "  look at <item>    Examine an item\n"
            "\n"
            "[bold]Items[/]\n"
            "  get <item>        Pick up an item\n"
            "  drop <item>       Drop an item\n"
            "  use <item>        Use an item (bandage, potion, etc.)\n"
            "  inventory / i     Show your inventory\n"
            "\n"
            "[bold]Combat[/]\n"
            "  kill <target>     Attack something\n"
            "  fight <target>    Fight something\n"
            "\n"
            "[bold]Social[/]\n"
            "  talk <npc>        Talk to someone\n"
            "  say <text>        Say something\n"
            "\n"
            "[bold]Character[/]\n"
            "  score / status    Show your stats\n"
            "  skills            Show your skills\n"
            "\n"
            "[bold]Meta[/]\n"
            "  help              This screen\n"
            "  q / quit          Quit to gateway\n"
            "  save              Save game\n"
            "\n"
            "Press any key to close.",
            id="help-text",
        )

    def on_key(self, event) -> None:
        self.dismiss()


# ── Mud Screen ──────────────────────────────────────────────────────────

class MudScreen(Screen):
    """The main MUD game screen."""

    BINDINGS = [
        Binding("q", "quit_to_gateway", "Quit"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(self, world: World, character: PlayerCharacter | None = None):
        super().__init__()
        self.world = world
        self.rng = random.Random(world.seed + 5000000)
        self.zones: dict[str, Zone] = {}
        self.current_zone: Zone | None = None
        self.current_room: Room | None = None
        self.event_log_entries: list[str] = []
        self.auto_pause = True

        # Generate or load character
        if character:
            self.char = character
        else:
            self.char = _generate_character(world, self.rng)

        # Generate zones
        self._init_zones()

    def _init_zones(self) -> None:
        """Generate the room/zones for the world."""
        self.zones = generate_zones(self.world, self.rng)
        # Start player in their settlement's entry room
        settlement = self.char.settlement
        if settlement in self.zones:
            self.current_zone = self.zones[settlement]
            self.current_room = self.current_zone.rooms[self.current_zone.entry_room]
        else:
            # Fallback to first zone
            zone_names = list(self.zones.keys())
            if zone_names:
                self.current_zone = self.zones[zone_names[0]]
                self.current_room = self.current_zone.rooms[self.current_zone.entry_room]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            # Left sidebar — stats and inventory
            with Vertical(id="sidebar", classes="panel"):
                yield Static(id="char-stats", classes="stat-panel")
                yield Static(id="char-inventory", classes="stat-panel")

            # Main area — room view + log + input
            with Vertical(id="main-area", classes="panel"):
                yield Static(id="room-view", classes="room-panel")
                yield RichLog(id="event-log", highlight=True, markup=True, max_lines=100)
                yield Input(id="command-input", placeholder="What do you do? ")

        yield Footer()

    def on_mount(self) -> None:
        """Initial render."""
        self._update_room_view()
        self._update_stats()
        self._log_event(f"[bold cyan]✦ You are {self.char.name}, a {self.char.profession} in {self.char.settlement}.[/]")
        self._log_event(f"[dim]Type [bold]help[/] for commands, or start exploring![/]")
        self.query_one("#command-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle a typed command."""
        cmd_text = event.value.strip()
        if not cmd_text:
            return

        # Clear input
        self.query_one("#command-input", Input).value = ""

        # Echo command
        self._log_event(f"[dim]> {cmd_text}[/]")

        # Parse and handle
        parsed = parse_command(cmd_text)
        result = handle_command(
            parsed, self.char, self.current_zone, self.current_room,
            self.world, self.zones, self.rng
        )

        # Output results
        for line in result.output:
            self._log_event(line)

        # Move to new room if changed
        if result.new_room_id and self.current_zone:
            if result.new_room_id in self.current_zone.rooms:
                self.current_room = self.current_zone.rooms[result.new_room_id]
                self._update_room_view()

        # Switch zone if needed
        if result.new_zone:
            self.current_zone = result.new_zone
            self.current_room = self.current_zone.rooms[self.current_zone.entry_room]
            self._update_room_view()
            self._log_event(f"[bold]You arrive in {self.current_zone.name}.[/]")

        # Update stats if character changed
        if result.char_changed:
            self._update_stats()

        # Process background sim events
        for ev in result.events:
            self._log_event(f"[dim]{ev}[/]")

        # Handle special commands
        if result.quit:
            self._quit_to_gateway()

        # Re-focus input
        self.query_one("#command-input", Input).focus()

    def _update_room_view(self) -> None:
        """Update the room description display."""
        if not self.current_room:
            self.query_one("#room-view", Static).update("[red]You are nowhere.[/]")
            return

        room = self.current_room
        lines = []

        # Room name
        lines.append(f"[bold yellow]══ {room.name} ══[/]")

        # Zone context
        if self.current_zone:
            lines.append(f"[dim]{self.current_zone.name}, {self.current_zone.zone_type}[/]")

        # Description
        lines.append("")
        lines.append(f"[{MudColors.ROOM_DESC}]{room.description}[/]")

        # Exits
        if room.exits:
            exits_str = ", ".join(
                f"[{MudColors.EXIT}]{dir}[/] → [dim]{name}[/]"
                for dir, name in room.exits.items()
            )
            lines.append("")
            lines.append(f"[bold]Exits:[/] {exits_str}")

        # Contents (items on ground)
        if room.contents:
            items = ", ".join(
                f"[{MudColors.ITEM}]{item['name']}[/]"
                for item in room.contents
            )
            lines.append("")
            lines.append(f"[bold]You see:[/] {items}")

        # NPCs present
        if room.npcs:
            npcs = ", ".join(
                f"[{MudColors.NPC}]{npc['name']}[/][dim] ({npc.get('title', '')})[/]"
                for npc in room.npcs
            )
            lines.append("")
            lines.append(f"[bold]Here:[/] {npcs}")

        # Season/year context
        month_names = ["Deepwinter", "Frostfall", "Springthaw", "Blossom",
                       "Meadow", "Summerheat", "Harvestsun", "Goldfields",
                       "Fruitfall", "Leafdrift", "Mistmoon", "Frostfang"]
        season = month_names[self.char.month % 12] if hasattr(self.char, 'month') else ""
        year_str = f"Year {self.char.year}, {season}" if season else f"Year {self.char.year}"
        lines.append("")
        lines.append(f"[dim]{year_str}[/]")

        self.query_one("#room-view", Static).update("\n".join(lines))

    def _update_stats(self) -> None:
        """Update the stats sidebar."""
        c = self.char
        hp_bar = "█" * max(1, c.health // 10) + "░" * max(0, 10 - max(1, c.health // 10))
        hp_color = "red" if c.health < 30 else "yellow" if c.health < 60 else "green"

        stats = [
            f"[{MudColors.STAT}]╔══ {c.name} ══╗[/]",
            f"  [{hp_color}]{hp_bar}[/] [bold]{c.health}[/] HP",
            f"  [{MudColors.GOLD}]{c.gold}[/] gold",
            f"  [dim]Age {c.age} · Year {c.year}[/]",
            f"  [dim]{c.profession}[/]",
        ]

        # Skills
        if c.skills:
            stats.append("")
            stats.append(f"[{MudColors.STAT}]── Skills ──[/]")
            for skill, level in sorted(c.skills.items()):
                bar = "▓" * level + "░" * (10 - level)
                stats.append(f"  [dim]{skill}:[/] [{MudColors.SKILL}]{level}[/] {bar}")

        # Inventory
        if c.inventory:
            stats.append("")
            stats.append(f"[{MudColors.STAT}]── Items ──[/]")
            for item in c.inventory[:8]:
                stats.append(f"  [{MudColors.ITEM}]•[/] {item}")
            if len(c.inventory) > 8:
                stats.append(f"  [dim]...and {len(c.inventory) - 8} more[/]")
        else:
            stats.append("")
            stats.append(f"[dim]── No items ──[/]")

        # Location
        if self.current_zone:
            stats.append("")
            stats.append(f"[{MudColors.STAT}]── Location ──[/]")
            stats.append(f"  [dim]{self.current_zone.name}[/]")
            if self.current_room:
                stats.append(f"  [dim]{self.current_room.name}[/]")

        self.query_one("#char-stats", Static).update("\n".join(stats))

    def _log_event(self, text: str) -> None:
        """Add an event to the log."""
        log = self.query_one("#event-log", RichLog)
        log.write(text)
        self.event_log_entries.append(text)

    def action_show_help(self) -> None:
        """Show the help overlay."""
        self.push_screen(MudHelp())

    def action_quit_to_gateway(self) -> None:
        """Return to the world picker."""
        self.dismiss(True)

    def _quit_to_gateway(self) -> None:
        self.dismiss(True)
