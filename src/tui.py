"""
wyrd — Textual-based World Viewer (Phase 17 TUI Overhaul).

A reactive terminal UI for exploring generated worlds.
Uses the Textual framework (Bubbletea-inspired) with Rich for ANSI rendering.

Usage:
    wyrd tui --seed 42
    wyrd tui --load world.json
"""

from __future__ import annotations

import asyncio
from pathlib import Path

try:
    from textual import work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.reactive import reactive
    from textual.widgets import Header, Footer, Static, Label, RichLog, Button, Input
    from textual.screen import Screen
except ImportError:
    # Running without textual installed — provide a helpful error
    raise ImportError(
        "Textual is required for the TUI viewer. Install it with: pip install textual"
    )

from .world import World, TERRAIN, Region
from .generate import generate_world
from .serialize import load_world
from .render import render_map


# ── Map Widget ────────────────────────────────────────────────────────


class WorldMapWidget(Static):
    """Displays the world's ASCII map with ANSI colors via Rich."""

    world: World | None = None
    show_settlements: bool = True

    def render_map(self, world: World) -> str:
        """Render the world map as an ANSI-colored string."""
        self.world = world
        map_str = render_map(world, show_settlements=self.show_settlements)
        self.update(map_str)

    def on_mount(self) -> None:
        if self.world:
            self.render_map(self.world)


# ── Info Panel Widgets ────────────────────────────────────────────────


class WorldInfoPanel(VerticalScroll):
    """Sidebar showing world metadata."""

    def display_world(self, world: World) -> None:
        """Populate the panel with world information."""
        self.remove_children()

        sections = []

        # World header
        sections.append(Static(f"[bold cyan]wyrd[/] — seed [yellow]{world.seed}[/]", id="world-title"))

        # Stats
        stats = [
            f"Size: {world.width}×{world.height}",
            f"Regions: {len(world.regions)}",
        ]
        total_pop = sum(
            s.population for r in world.regions for s in r.settlements
        )
        total_settlements = sum(len(r.settlements) for r in world.regions)
        stats.append(f"Settlements: {total_settlements}")
        stats.append(f"Population: {total_pop:,}")
        stats.append("")

        # Regions list
        stats.append("[bold underline]Regions[/]")
        for r in world.regions:
            s_count = len(r.settlements)
            r_pop = sum(s.population for s in r.settlements)
            biome_emojis = {
                "deep_water": "🌊", "shallow": "🌊", "sand": "🏖",
                "grass": "🌿", "forest": "🌲", "hills": "⛰",
                "mountains": "🏔", "snow": "❄", "river": "🌊",
            }
            dominant = r.dominant_terrain if r.dominant_terrain else "grass"
            emoji = biome_emojis.get(dominant, "🗺")
            stats.append(f"  {emoji}[italic]{r.name}[/] ({s_count} settlements, {r_pop:,} pop)")

        stats.append("")
        stats.append(f"[dim]Seed: {world.seed} | Deterministic[/]")

        info = Static("\n".join(stats), id="world-info")
        self.mount_all([sections[0], info])


# ── Main Screen ───────────────────────────────────────────────────────


class WorldScreen(Screen):
    """Main world exploration screen."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "toggle_settlements", "Settlements"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "show_help", "Help"),
    ]

    def __init__(self, world: World, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.world = world

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="map-container", classes="column"):
                yield WorldMapWidget(id="world-map")
            with Vertical(id="sidebar", classes="column"):
                yield WorldInfoPanel(id="info-panel")
        yield Footer()

    def on_mount(self) -> None:
        map_widget = self.query_one(WorldMapWidget)
        map_widget.render_map(self.world)
        info_panel = self.query_one(WorldInfoPanel)
        info_panel.display_world(self.world)

    def action_toggle_settlements(self) -> None:
        map_widget = self.query_one(WorldMapWidget)
        map_widget.show_settlements = not map_widget.show_settlements
        map_widget.render_map(self.world)

    def action_refresh(self) -> None:
        map_widget = self.query_one(WorldMapWidget)
        map_widget.render_map(self.world)

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())


# ── Help Screen ───────────────────────────────────────────────────────


class HelpScreen(Screen):
    """Help overlay screen."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("wyrd — Help", classes="help-title")
        help_lines = [
            "",
            "[bold]Controls[/]",
            "  [yellow]q[/]        Quit",
            "  [yellow]s[/]        Toggle settlements on/off",
            "  [yellow]r[/]        Refresh map",
            "  [yellow]?[/]        Show this help",
            "",
            "[bold]What is wyrd?[/]",
            "  A terminal-native generative fantasy sandbox.",
            "  Build worlds, explore them, watch them grow.",
            "",
            "[bold]Phases (complete)[/]",
            "  1-6: World generation, lore, explorer, narrative,",
            "        chronicles, simulation engine",
            "  7-16: Living worlds, web dashboards, factions,",
            "        cataclysms, trade, gateway TUI, roads",
            "",
            "  [dim]Press Escape or 'q' to close[/]",
        ]
        yield Static("\n".join(help_lines), id="help-text")


# ── App ────────────────────────────────────────────────────────────────


class WyrdTUI(App):
    """Wyrd — Textual-based World Viewer."""

    CSS = """
    Screen {
        background: #1a1b26;
    }

    #map-container {
        width: 75%;
        height: 100%;
        border: solid $primary;
    }

    #world-map {
        width: 100%;
        height: 100%;
        overflow: auto;
        padding: 1;
    }

    #sidebar {
        width: 25%;
        height: 100%;
        border: solid $secondary;
        overflow: auto;
    }

    #world-info {
        padding: 0 1;
        color: $text;
    }

    .help-title {
        content-align: center middle;
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }

    #help-text {
        padding: 1 2;
        color: $text;
    }

    WorldInfoPanel {
        overflow: auto;
    }

    VerticalScroll {
        overflow: auto;
    }
    """

    TITLE = "wyrd"
    SUB_TITLE = "generative fantasy sandbox"

    def __init__(self, world: World | None = None, seed: int | None = None):
        super().__init__()
        self._world = world
        self._seed = seed

    def on_mount(self) -> None:
        """Set up the initial screen."""
        if self._world:
            self.push_screen(WorldScreen(self._world))
        elif self._seed is not None:
            self._generate_and_show()
        else:
            # Show a minimal picker/help
            lines = [
                "[bold cyan]wyrd[/] — generative fantasy sandbox",
                "",
                "Usage:",
                "  wyrd tui --seed 42     # Generate and show world",
                "  wyrd tui --load file.json  # Load saved world",
                "",
                "Press any key to quit.",
            ]
            self.mount(Static("\n".join(lines), id="landing"))

    @work(thread=True)
    def _generate_and_show(self) -> None:
        """Generate a world and show it (runs in worker thread)."""
        world = generate_world(self._seed)

        def _switch():
            self.push_screen(WorldScreen(world))

        self.call_from_thread(_switch)


def launch(world: World | None = None, seed: int | None = None) -> None:
    """Launch the Textual-based world viewer.

    Args:
        world: A pre-generated World object, or None
        seed: Seed to generate a world from, or None
    """
    app = WyrdTUI(world=world, seed=seed)
    app.run()
