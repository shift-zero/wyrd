"""wyrd — Textual MUD screen (Phase 26: Single-User MUD).

The main game interface. Room view, event log, command input, stats sidebar.
Replaces all curses TUIs and CLI commands. This is the entire game surface.
"""

from __future__ import annotations

import random

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Header, Footer, Static, Input, RichLog
from textual.widget import Widget

from .world import World
from .embody import (
    PlayerCharacter,
    _generate_character,
)
from .room import generate_zones, Zone, Room
from .mud_parser import parse_command, handle_command, CommandResult
from .mud_sim import MudSimState


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
            "\n"
            "[bold]Meta[/]\n"
            "  help              This screen\n"
            "  q / quit          Quit to gateway\n"
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
        self.seed = world.seed
        self.rng = random.Random(world.seed + 5000000)
        self.zones: dict[str, Zone] = {}
        self.current_zone_name: str | None = None
        self.current_room_id: str | None = None

        # Generate or load character
        if character:
            self.char = character
        else:
            self.char = _generate_character(world, self.rng)

        # Generate zones
        self._init_zones()

        # Background sim
        self.sim_state = MudSimState(world, self.seed)
        self._hours_since_sim_update = 0

    def _init_zones(self) -> None:
        """Generate the room/zones for the world."""
        self.zones = generate_zones(self.world, self.seed)
        # Start player in their settlement's entry room
        settlement = self.char.settlement
        if settlement in self.zones:
            self.current_zone_name = settlement
            zone = self.zones[settlement]
            self.current_room_id = zone.entry_room
        else:
            # Fallback to first zone
            zone_names = list(self.zones.keys())
            if zone_names:
                self.current_zone_name = zone_names[0]
                zone = self.zones[zone_names[0]]
                self.current_room_id = zone.entry_room

    @property
    def current_zone(self) -> Zone | None:
        if self.current_zone_name and self.current_zone_name in self.zones:
            return self.zones[self.current_zone_name]
        return None

    @property
    def current_room(self) -> Room | None:
        if self.current_zone and self.current_room_id:
            return self.current_zone.rooms.get(self.current_room_id)
        return None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            # Left sidebar — stats and inventory
            with Vertical(id="sidebar", classes="panel"):
                yield Static(id="char-stats", classes="stat-panel")

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
        self._log(f"[bold cyan]✦ You are {self.char.name}, a {self.char.profession} in {self.char.settlement}.[/]")
        self._log("[dim]Type [bold]help[/] for commands, or start exploring![/]")
        self.query_one("#command-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle a typed command."""
        cmd_text = event.value.strip()
        if not cmd_text:
            return

        self.query_one("#command-input", Input).value = ""
        self._log(f"[dim]> {cmd_text}[/]")
        # Parse and handle
        parsed = parse_command(cmd_text)

        # Estimate hours for this action (for sim advancement)
        verb = parsed.get("verb", "")
        action_hours = {
            "north": 1, "south": 1, "east": 1, "west": 1,
            "northeast": 1, "northwest": 1, "southeast": 1, "southwest": 1,
            "kill": 2, "attack": 2, "fight": 2,
            "talk": 1, "say": 1, "yell": 1,
            "use": 1, "get": 0, "take": 0, "drop": 0,
            "look": 0, "inventory": 0, "score": 0, "status": 0,
            "help": 0, "quit": 0,
        }.get(verb, 1)

        result = handle_command(
            parsed, self.char, self.current_zone,
            self.current_room_id or "", self.world, self.seed
        )

        # Output result text
        if result.output:
            self._log(result.output)

        # Move to new room if changed
        if result.new_room and self.current_zone:
            self.current_room_id = result.new_room
            self._update_room_view()

        # Update stats if character changed
        if result.char_changed:
            self._update_stats()

        # Log events
        for ev in result.events:
            self._log(f"[dim]{ev}[/]")

        # Advance background sim
        if action_hours > 0:
            news = self.sim_state.advance(action_hours)
            for item in news:
                self._log(item)
            self._hours_since_sim_update += action_hours
            if self._hours_since_sim_update >= 168:  # ~1 week
                self.sim_state.apply_to_rooms(self.zones)
                self._hours_since_sim_update = 0
                self._update_room_view()

        self.query_one("#command-input", Input).focus()

    def _update_room_view(self) -> None:
        """Update the room description display."""
        room = self.current_room
        if not room:
            self.query_one("#room-view", Static).update("[red]You are nowhere.[/]")
            return

        lines = []
        lines.append(f"[bold yellow]══ {room.name} ══[/]")
        if self.current_zone:
            lines.append(f"[dim]{self.current_zone.name}[/]")
        lines.append("")
        lines.append(f"[bold white]{room.description}[/]")

        if room.exits:
            exits_str = ", ".join(
                f"[cyan]{d}[/] → [dim]{n}[/]"
                for d, n in room.exits.items()
            )
            lines.append("")
            lines.append(f"[bold]Exits:[/] {exits_str}")

        if room.contents:
            items = ", ".join(
                f"[yellow]{it['name']}[/]"
                for it in room.contents
            )
            lines.append("")
            lines.append(f"[bold]You see:[/] {items}")

        if room.npcs:
            npcs = ", ".join(
                f"[green]{n['name']}[/][dim] ({n.get('title', '')})[/]"
                for n in room.npcs
            )
            lines.append("")
            lines.append(f"[bold]Here:[/] {npcs}")

        month_names = ["Deepwinter", "Frostfall", "Springthaw", "Blossom",
                       "Meadow", "Summerheat", "Harvestsun", "Goldfields",
                       "Fruitfall", "Leafdrift", "Mistmoon", "Frostfang"]
        season = month_names[self.char.month % 12] if hasattr(self.char, 'month') and self.char.month else ""
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
            f"[bold cyan]╔══ {c.name} ══╗[/]",
            f"  [{hp_color}]{hp_bar}[/] [bold]{c.health}[/] HP",
            f"  [bold yellow]{c.gold}[/] gold",
            f"  [dim]Age {c.age} · Year {c.year}[/]",
            f"  [dim]{c.profession}[/]",
        ]

        if c.skills:
            stats.append("")
            stats.append("[bold cyan]── Skills ──[/]")
            for skill, level in sorted(c.skills.items()):
                bar = "▓" * level + "░" * (10 - level)
                stats.append(f"  [dim]{skill}:[/] [magenta]{level}[/] {bar}")

        if c.inventory:
            stats.append("")
            stats.append("[bold cyan]── Items ──[/]")
            for item in c.inventory[:8]:
                stats.append(f"  [yellow]•[/] {item}")
            if len(c.inventory) > 8:
                stats.append(f"  [dim]...and {len(c.inventory) - 8} more[/]")
        else:
            stats.append("")
            stats.append("[dim]── No items ──[/]")

        if self.current_zone and self.current_room:
            stats.append("")
            stats.append("[bold cyan]── Location ──[/]")
            stats.append(f"  [dim]{self.current_zone.name}[/]")
            stats.append(f"  [dim]{self.current_room.name}[/]")

        self.query_one("#char-stats", Static).update("\n".join(stats))

    def _log(self, text: str) -> None:
        """Add text to the event log."""
        log = self.query_one("#event-log", RichLog)
        log.write(text)

    def action_show_help(self) -> None:
        """Show the help overlay."""
        self.push_screen(MudHelp())

    def action_quit_to_gateway(self) -> None:
        """Return to the world picker."""
        self.dismiss(True)
