"""
wyrd — Textual-based Interactive World Viewer (Phase 17 TUI Overhaul).

A reactive terminal UI with simulation integration, event logging,
and discoverable controls. Bubbletea-inspired design.

Usage:
    wyrd tui --seed 42
    wyrd tui --load world.json
"""

from __future__ import annotations

import asyncio
import random

from pathlib import Path

try:
    from textual import work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.reactive import reactive
    from textual.widgets import (
        Header, Footer, Static, Label, RichLog, Button, Input,
    )
    from textual.screen import Screen
    from textual.timer import Timer
except ImportError:
    raise ImportError(
        "Textual is required for the TUI viewer. Install it with: pip install textual"
    )

from .world import World, TERRAIN
from .generate import generate_world
from .serialize import load_world
from .render import render_map, ANSI_RESET, ANSI_BOLD, ANSI_DIM
from .sim import (
    initialize_sim_state, _simulate_tick, simulate_years,
    apply_sim_state_to_world, SimState, SimEvent,
)

# ── Event icons (shared) ──────────────────────────────────────────────

_EVENT_ICON = {
    "plague": "☠", "famine": "🌾", "war": "⚔", "discovery": "✦",
    "prosperity": "↑", "disaster": "🌋", "exodus": "→",
    "founding": "▲", "abandonment": "✗", "trade_boom": "💰",
    "religious_tension": "✞", "divine_blessing": "✧",
    "holy_pilgrimage": "🚶", "heresy": "🔥",
    "faction_war": "⚔", "faction_alliance": "🤝",
    "faction_power_shift": "⬇", "faction_collapse": "💀",
    "faction_peace_treaty": "☮", "faction_leadership_change": "👑",
    "faction_trade_pact": "📦", "faction_vassal_revolt": "⚡",
    "faction_coup": "🗡",
    "earthquake": "〰", "volcanic_eruption": "🌋",
    "great_plague": "💀", "tsunami": "🌊",
    "meteor_strike": "☄", "great_fire": "🔥",
    "magical_cataclysm": "🌀",
    "trade_collapse": "📉",
    "unknown": "•",
}

_EVENT_COLORS = {
    "war": "#ff4444", "faction_war": "#ff4444",
    "famine": "#cc8800", "plague": "#aa44aa",
    "great_plague": "#aa44aa", "disaster": "#ff4444",
    "abandonment": "#666666", "exodus": "#888888",
    "founding": "#44ff44", "discovery": "#44ff44",
    "prosperity": "#44ff44", "trade_boom": "#ffcc00",
    "earthquake": "#ff8800", "volcanic_eruption": "#ff4400",
    "tsunami": "#4488ff", "meteor_strike": "#ff00ff",
    "great_fire": "#ff6600", "magical_cataclysm": "#aa44ff",
    "faction_collapse": "#ff4444", "faction_alliance": "#44ff44",
    "faction_peace_treaty": "#44ff44", "faction_trade_pact": "#ffcc00",
}


# ── Map Widget ────────────────────────────────────────────────────────


class SimMapWidget(Static):
    """Displays the world's ASCII map. Updates automatically during sim."""

    world: World | None = None
    show_settlements: bool = True
    year: int = 0
    pop: int = 0
    settlements_count: int = 0

    def render_map(self, world: World) -> None:
        """Render the world map as an ANSI-colored string."""
        self.world = world
        map_str = render_map(world, show_settlements=self.show_settlements)
        self.update(map_str)

    def on_mount(self) -> None:
        if self.world:
            self.render_map(self.world)


# ── Event Log Widget ──────────────────────────────────────────────────


class EventLogWidget(RichLog):
    """Scrollable log of simulation events."""

    MAX_EVENTS = 200

    def log_event(self, ev: SimEvent) -> None:
        """Add a single event to the log."""
        icon = _EVENT_ICON.get(ev.event_type, "•")
        color = _EVENT_COLORS.get(ev.event_type, "#cccccc")
        desc = ev.description[:120]
        self.write(f"[{color}]{icon}[/] Y{ev.year} [{color}]{desc}[/]")

    def log_events(self, events: list[SimEvent], start: int = 0) -> None:
        """Add a batch of events from the given index onward."""
        for ev in events[start:]:
            self.log_event(ev)

    def clear_events(self) -> None:
        """Clear all events."""
        self.clear()


# ── Info Panel (enhanced) ─────────────────────────────────────────────


class SimInfoPanel(VerticalScroll):
    """Sidebar showing world metadata and live simulation stats."""

    def display_world(self, world: World) -> None:
        """Populate the panel with world information."""
        self.remove_children()

        # World header
        self.mount(
            Static(f"[bold cyan]wyrd[/] — seed [yellow]{world.seed}[/]",
                   id="sim-title")
        )

        # Static stats
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

        # Regions
        stats.append("")
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
            stats.append(
                f"  {emoji}[italic]{r.name}[/] "
                f"({s_count} settlements, {r_pop:,} pop)"
            )

        stats.append("")
        stats.append("[dim]Seed: {} | Deterministic[/]".format(world.seed))

        self.mount(Static("\n".join(stats), id="sim-info"))

    def update_stats(self, year: int, pop: int, settlements: int,
                     abandoned: int, speed: float) -> None:
        """Update live simulation stats in the panel."""
        # Find or create the stats display
        existing = self.query("#sim-live-stats")
        if existing:
            existing.remove()

        lines = [
            "",
            "[bold underline]Simulation[/]",
            f"  Year: [yellow]{year:,}[/]",
            f"  Population: [green]{pop:,}[/]",
            f"  Settlements: [cyan]{settlements}[/] active, "
            f"[dim]{abandoned}[/] abandoned",
            f"  Speed: [yellow]{speed:.1f}x[/]",
        ]

        self.mount(Static("\n".join(lines), id="sim-live-stats"))


# ── Main Screen ────────────────────────────────────────────────────────


class SimScreen(Screen):
    """Main simulation-aware world exploration screen."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("s", "toggle_settlements", "Settlements"),
        Binding("r", "reset", "Reset Sim"),
        Binding("space", "toggle_sim", "Run/Pause"),
        Binding("right", "step_year", "Step →"),
        Binding("plus", "speed_up", "Speed +"),
        Binding("minus", "slow_down", "Speed -"),
        Binding("d", "toggle_diff", "Diff"),
        Binding("c", "toggle_chart", "Chart"),
        Binding("?", "show_help", "Help"),
    ]

    # Simulation state
    sim_running: bool = False
    sim_speed: float = 2.0
    sim_year: int = 0
    sim_max_years: int = 200
    sim_chaos: float = 0.3

    def __init__(self, world: World, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.world = world
        self.sim_state: SimState | None = None
        self.sim_rng: random.Random | None = None
        self.sim_events: list[SimEvent] = []
        self.sim_timer: Timer | None = None
        self._event_count: int = 0
        self._prev_snapshot: dict | None = None
        self._last_diff: dict | None = None
        self._show_diff: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="map-container", classes="column"):
                yield SimMapWidget(id="world-map")
                # Control bar
                with Horizontal(id="control-bar"):
                    yield Label("▶ Sim ", id="sim-status")
                    yield Label("  1.0x", id="sim-speed-display")
            with Vertical(id="sidebar", classes="column"):
                yield SimInfoPanel(id="info-panel")
                yield Static("[bold]Events[/]", id="events-header")
                yield EventLogWidget(id="event-log", max_lines=100, highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen."""
        map_widget = self.query_one(SimMapWidget)
        map_widget.render_map(self.world)
        info_panel = self.query_one(SimInfoPanel)
        info_panel.display_world(self.world)
        events_log = self.query_one(EventLogWidget)
        events_log.write("[dim]Ready. Press [bold]Space[/] to start simulation.[/]")
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        """Update UI labels and info panel stats."""
        status = self.query_one("#sim-status", Label)
        speed_lbl = self.query_one("#sim-speed-display", Label)
        if self.sim_running:
            status.update(f"[green]▶ Running[/] Y{self.sim_year}")
        else:
            status.update(f"[yellow]⏸ Paused[/] Y{self.sim_year}")
        speed_lbl.update(f" {self.sim_speed:.1f}x")

        # Update info panel stats
        if self.sim_state:
            info = self.query_one(SimInfoPanel)
            active = self.sim_state.num_settlements
            abandoned = self.sim_state.num_abandoned
            pop = self.sim_state.total_population
            info.update_stats(
                self.sim_year, pop, active, abandoned, self.sim_speed
            )

    # ── Actions ─────────────────────────────────────────────────────

    def action_toggle_settlements(self) -> None:
        map_widget = self.query_one(SimMapWidget)
        map_widget.show_settlements = not map_widget.show_settlements
        map_widget.render_map(self.world)

    def action_refresh(self) -> None:
        """Refresh the map display (re-draw from current state)."""
        map_widget = self.query_one(SimMapWidget)
        if self.sim_state is not None:
            sim_world = apply_sim_state_to_world(self.world, self.sim_state)
            map_widget.render_map(sim_world)
        else:
            map_widget.render_map(self.world)

    def action_reset(self) -> None:
        """Reset the simulation: rewind to year 0, clear events."""
        # Stop sim if running
        if self.sim_running:
            self._pause_sim()
        # Reset sim state
        self.sim_state = initialize_sim_state(self.world)
        self.sim_rng = random.Random(self.world.seed + 4000000)
        self.sim_events = []
        self.sim_year = 0
        self._event_count = 0
        self._prev_snapshot = None
        self._last_diff = None
        self._show_diff = False
        # Clear event log
        log = self.query_one(EventLogWidget)
        log.clear_events()
        log.write("[dim]Simulation reset. Press [bold]Space[/] to start again.[/]")
        # Restore original world map
        map_widget = self.query_one(SimMapWidget)
        map_widget.render_map(self.world)
        self._update_ui_state()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_diff(self) -> None:
        self._show_diff = not self._show_diff
        if self._show_diff and self._last_diff:
            self._display_diff()
        elif not self._show_diff:
            self._clear_diff()

    def _display_diff(self) -> None:
        """Show year-diff overlay in the event log."""
        log = self.query_one(EventLogWidget)
        if not self._last_diff:
            return
        d = self._last_diff
        log.write("")
        log.write(f"[bold cyan]══ Year {d['year']} Changes ══[/]")
        if d["new"]:
            log.write("[green]◆ New Settlements:[/]")
            for name, pop, pros in d["new"][:5]:
                log.write(f"  +{name} (pop {pop:,})")
        if d["grew"]:
            log.write("[green]↑ Population Growth:[/]")
            for name, old, new_, delta in d["grew"][:5]:
                log.write(f"  {name}: {old:,} → {new_:,} (+{delta:,})")
        if d["shrank"]:
            log.write("[red]↓ Population Decline:[/]")
            for name, old, new_, delta in d["shrank"][:5]:
                log.write(f"  {name}: {old:,} → {new_:,} ({delta:,})")
        if d["abandoned"]:
            log.write("[dim]✗ Abandoned:[/]")
            for name in d["abandoned"][:5]:
                log.write(f"  ✗ {name}")
        if not any([d["new"], d["grew"], d["shrank"], d["abandoned"]]):
            log.write("[dim](no significant changes)[/]")
        log.write("")

    def _clear_diff(self) -> None:
        """Signal that diff mode was turned off."""
        pass  # Events log continues normally

    def action_toggle_chart(self) -> None:
        self.query_one(EventLogWidget).write(
            "[dim]Chart overlay coming soon — use [bold]wyrd view[/] for now.[/]"
        )

    # ── Simulation Actions ──────────────────────────────────────────

    def action_toggle_sim(self) -> None:
        """Start or pause the simulation."""
        if self.sim_running:
            self._pause_sim()
        else:
            self._start_sim()

    def _lazy_init_sim(self) -> None:
        """Initialize simulation state if not already done."""
        if self.sim_state is not None:
            return
        self.sim_state = initialize_sim_state(self.world)
        self.sim_rng = random.Random(self.world.seed + 4000000)
        self.sim_events = []
        self.sim_year = 0
        self._event_count = 0
        self._prev_snapshot = None

    def _start_sim(self) -> None:
        """Start the simulation timer."""
        self._lazy_init_sim()
        self.sim_running = True
        # Set up a periodic timer (8 FPS feels smooth in terminal)
        self.sim_timer = self.set_interval(1 / 8, self._sim_tick)
        self._update_ui_state()
        self.query_one(EventLogWidget).write(
            "[green]▶ Simulation running...[/]"
        )

    def _pause_sim(self) -> None:
        """Pause the simulation."""
        self.sim_running = False
        if self.sim_timer:
            self.sim_timer.stop()
            self.sim_timer = None
        self._update_ui_state()

    def action_step_year(self) -> None:
        """Step forward one year."""
        if self.sim_running:
            self._pause_sim()
        self._lazy_init_sim()
        if self.sim_year < self.sim_max_years:
            self._do_tick()
            self._update_ui_state()

    def action_speed_up(self) -> None:
        """Increase simulation speed."""
        self.sim_speed = min(self.sim_speed * 2, 64.0)
        self._update_ui_state()

    def action_slow_down(self) -> None:
        """Decrease simulation speed."""
        self.sim_speed = max(self.sim_speed / 2, 0.125)
        self._update_ui_state()

    def _sim_tick(self) -> None:
        """Called by the timer on each frame."""
        if not self.sim_running or self.sim_state is None:
            return

        # How many years per tick based on speed
        years_per_tick = max(1, int(self.sim_speed))
        for _ in range(years_per_tick):
            if self.sim_year >= self.sim_max_years:
                self._pause_sim()
                self.query_one(EventLogWidget).write(
                    "[dim]Simulation complete. Press [bold]r[/] to reset or [bold]q[/] to quit.[/]"
                )
                return
            self._do_tick()

        # Update display
        self._update_ui_state()
        map_widget = self.query_one(SimMapWidget)
        sim_world = apply_sim_state_to_world(self.world, self.sim_state)
        map_widget.render_map(sim_world)

    def _do_tick(self) -> None:
        """Run one sim tick and capture events."""
        if self.sim_state is None or self.sim_rng is None:
            return

        self.sim_year += 1

        # Snapshot before tick for diff
        if self._prev_snapshot is None:
            self._prev_snapshot = self._snapshot_populations()

        tick_events = _simulate_tick(
            self.world, self.sim_state, self.sim_rng,
            self.sim_year, self.sim_chaos,
        )

        # Log new events
        if tick_events:
            log = self.query_one(EventLogWidget)
            for ev in tick_events:
                log.log_event(ev)

        self.sim_events.extend(tick_events)

        # Compute diff
        self._last_diff = self._compute_diff(self._prev_snapshot)
        self._prev_snapshot = self._snapshot_populations()

        # If diff overlay is open, update it
        if self._show_diff:
            self._display_diff()

    def _snapshot_populations(self) -> dict:
        """Snapshot settlement populations for diff computation."""
        if self.sim_state is None:
            return {}
        return {
            name: {
                "pop": ss.population,
                "pros": ss.prosperity,
                "active": ss.is_active,
            }
            for name, ss in self.sim_state.settlements.items()
        }

    def _compute_diff(self, prev: dict) -> dict:
        """Compare prev snapshot to current SimState; return structured diff."""
        if self.sim_state is None:
            return {"year": 0}
        grew = []
        shrank = []
        new_settlements = []
        abandoned = []
        rebuilt = []

        current = {
            name: {
                "pop": ss.population,
                "pros": ss.prosperity,
                "active": ss.is_active,
            }
            for name, ss in self.sim_state.settlements.items()
        }

        for name, cur in current.items():
            if name in prev:
                prev_info = prev[name]
                if not prev_info["active"] and cur["active"]:
                    rebuilt.append(name)
                elif prev_info["active"] and not cur["active"]:
                    abandoned.append(name)
                elif cur["active"]:
                    pop_diff = cur["pop"] - prev_info["pop"]
                    if pop_diff > 0:
                        grew.append((name, prev_info["pop"], cur["pop"], pop_diff))
                    elif pop_diff < 0:
                        shrank.append((name, prev_info["pop"], cur["pop"], pop_diff))
            else:
                if cur["active"]:
                    new_settlements.append((name, cur["pop"], cur["pros"]))

        grew.sort(key=lambda x: -abs(x[3]))
        shrank.sort(key=lambda x: -abs(x[3]))

        return {
            "grew": grew[:15],
            "shrank": shrank[:15],
            "new": new_settlements[:10],
            "abandoned": abandoned[:10],
            "rebuilt": rebuilt[:10],
            "year": self.sim_year,
        }


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
            "[bold]Navigation[/]",
            "  [yellow]q[/]        Quit the viewer",
            "  [yellow]?[/]        Show this help",
            "",
            "[bold]Map Controls[/]",
            "  [yellow]s[/]        Toggle settlement markers",
            "  [yellow]r[/]        Reset simulation (rewind to year 0)",
            "",
            "[bold]Simulation[/]",
            "  [yellow]Space[/]    Start / Pause simulation",
            "  [yellow]→[/]        Step one year forward",
            "  [yellow]+[/]        Speed up (2x, 4x, 8x...)",
            "  [yellow]-[/]        Slow down",
            "",
            "[bold]Overlays[/]",
            "  [yellow]d[/]        Toggle year-diff view",
            "  [yellow]c[/]        Population chart (coming soon)",
            "",
            "[bold]What is wyrd?[/]",
            "  A terminal-native generative fantasy sandbox.",
            "  Procedurally generated worlds with deep lore,",
            "  living simulation, and embodied play.",
            "",
            "  [dim]Press Escape or 'q' to close[/]",
        ]
        yield Static("\n".join(help_lines), id="help-text")


# ── App ────────────────────────────────────────────────────────────────


class WyrdTUI(App):
    """Wyrd — Textual-based Interactive World Viewer."""

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
        height: 70%;
        overflow: auto;
        padding: 1;
    }

    #control-bar {
        height: 3;
        padding: 0 1;
        background: #242538;
        align: center middle;
    }

    #sim-status {
        padding: 0 1;
        color: $text;
    }

    #sim-speed-display {
        padding: 0 1;
        color: $secondary;
    }

    #sidebar {
        width: 25%;
        height: 100%;
        border: solid $secondary;
        overflow: auto;
    }

    #sim-info {
        padding: 0 1;
        color: $text;
    }

    #sim-live-stats {
        padding: 0 1;
        color: $text;
    }

    #events-header {
        height: 1;
        padding: 0 1;
        background: #242538;
        color: $primary;
        text-style: bold;
    }

    #event-log {
        width: 100%;
        height: 30%;
        padding: 0 1;
        color: $text;
        background: #1e1f2e;
        border-top: solid $secondary;
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

    SimInfoPanel {
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
            self.push_screen(SimScreen(self._world))
        elif self._seed is not None:
            self._generate_and_show()
        else:
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
            self.push_screen(SimScreen(world))

        self.call_from_thread(_switch)


def launch(world: World | None = None, seed: int | None = None) -> None:
    """Launch the Textual-based interactive world viewer.

    Args:
        world: A pre-generated World object, or None
        seed: Seed to generate a world from, or None
    """
    app = WyrdTUI(world=world, seed=seed)
    app.run()
