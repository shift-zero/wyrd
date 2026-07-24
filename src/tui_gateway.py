"""wyrd — Textual-based Gateway (World Picker).

A reactive, mouse-friendly world picker that replaces the curses gateway.
Supports world listing, sorting, detail cards with mini-maps, character
management, and dispatch to explore/sim/embody/view.

Run with:
    wyrd tui --gateway
    wyrd           (when Textual gateway is default)
"""

from __future__ import annotations

import glob
import json
import os
import random
import re
import sys

from pathlib import Path
from typing import ClassVar

try:
    from textual import work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.reactive import reactive
    from textual.widgets import (
        Header, Footer, Static, Label, Button, Input, ListView, ListItem, Log,
    )
    from textual.screen import ModalScreen, Screen
    from textual.widget import Widget
except ImportError:
    raise ImportError(
        "Textual is required for the gateway TUI. Install with: pip install textual"
    )

from .world import TERRAIN, World
from .generate import generate_world
from .serialize import load_world
# ── World scanning & character save helpers (moved from deleted gateway.py) ─


def scan_worlds(search_dir: str = ".") -> list[dict]:
    """Scan for wyrd world files and return metadata list."""
    pattern = os.path.join(search_dir, "wyrd-*.json")
    world_files = sorted(glob.glob(pattern))
    world_files = [
        wf for wf in world_files
        if not re.search(r'-sim\.json', wf)
        and not re.search(r'-char\.json', wf)
        and not re.search(r'-chronicles\.html', wf)
        and not re.search(r'\.ttrpg\.json', wf)
    ]

    results = []
    for wf in world_files:
        try:
            with open(wf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        seed = data.get("seed", 0)
        results.append({
            "seed": seed,
            "file": os.path.basename(wf),
            "path": wf,
            "dimensions": f'{data.get("width", 0)}x{data.get("height", 0)}',
            "regions": len(data.get("regions", [])),
            "population": sum(
                s.get("population", 0)
                for r in data.get("regions", [])
                for s in r.get("settlements", [])
            ),
            "has_lore": "lore" in data and data["lore"] is not None,
            "has_narrative": "narrative" in data and data["narrative"] is not None,
            "has_chronicles": "chronicles" in data and data["chronicles"] is not None,
            "has_magic": "magic" in data and data["magic"] is not None,
            "has_save": os.path.exists(f"saves/wyrd-{seed}-char.json") or os.path.exists(f"wyrd-{seed}-char.json"),
        })
    return results


def _has_sim_file(seed: int) -> bool:
    """Check if a sim file exists for the given seed."""
    return any(
        os.path.exists(f) for f in [
            f"wyrd-{seed}-sim.json",
            f"wyrd-{seed}-sim.json.gz",
        ]
    )


def _char_save_path(seed: int) -> str:
    """Get the path to a character save file (checks new saves/ dir then old CWD)."""
    new = os.path.join("saves", f"wyrd-{seed}-char.json")
    if os.path.exists(new):
        return new
    old = f"wyrd-{seed}-char.json"
    if os.path.exists(old):
        return old
    return new  # Return new path even if doesn't exist (for creation)


def _load_char_save_info(seed: int) -> dict | None:
    """Load character save metadata for a given seed. Returns None if no save."""
    path = _char_save_path(seed)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        char = data.get("character", {})
        if not char:
            return None
        health = char.get("health", 0)
        bars = max(1, health // 10) if health else 0
        empty = max(0, 10 - bars)
        health_bar = "❤" * bars + "♡" * empty
        return {
            "name": char.get("name", "Unknown"),
            "profession": char.get("profession", "?"),
            "age": char.get("age", 0),
            "year": char.get("year", 0),
            "gold": char.get("gold", 0),
            "health": health,
            "health_bar": health_bar,
            "settlement": char.get("settlement", "?"),
            "region": char.get("region", "?"),
        }
    except Exception:
        return None


def _delete_char_save(seed: int) -> bool:
    """Delete the character save for a given seed. Returns True if deleted."""
    path = _char_save_path(seed)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

# ── Color helpers (shared) ───────────────────────────────────────────────

TERRAIN_COLORS = {
    "deep_water": "#0055aa",
    "shallow": "#2288cc",
    "sand": "#eeddaa",
    "grass": "#44bb44",
    "forest": "#228833",
    "hills": "#88aa44",
    "mountains": "#886644",
    "snow": "#ddeeff",
    "river": "#22aadd",
    "tundra": "#88aabb",
    "swamp": "#557744",
    "desert": "#ccbb66",
}


def _ansi_color(css_hex: str) -> str:
    """Wrap text in an ANSI 24-bit color escape."""
    r, g, b = int(css_hex[1:3], 16), int(css_hex[3:5], 16), int(css_hex[5:7], 16)
    return f"\x1b[38;2;{r};{g};{b}m"


_DIM = "\x1b[2m"
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


def render_mini_map(world: World, width: int = 30, height: int = 10) -> str:
    """Render a compact coloured ASCII mini-map of the world."""
    if not world.terrain:
        return "[dim](no terrain data)[/]"

    lines = []
    step_y = max(1, world.height // height)
    step_x = max(1, world.width // width)

    for y in range(0, world.height, step_y):
        row_chars = []
        for x in range(0, world.width, step_x):
            t = world.terrain[y][x]
            char = TERRAIN.get(t, {}).get("char", "·")
            css = TERRAIN_COLORS.get(t, "#888888")
            row_chars.append(f"[{css}]{char}[/]")
        lines.append("".join(row_chars))

    return "\n".join(lines)


def _build_detail_text(world_info: dict) -> str:
    """Build the detail card text for a world."""
    seed = world_info["seed"]
    lines = [
        f"[bold cyan]wyrd #{seed}[/]",
        "",
        f"[dim]File:[/] {world_info['file']}",
        f"[dim]Dimensions:[/] {world_info['dimensions']}",
        f"[dim]Regions:[/] {world_info['regions']}",
        f"[dim]Population:[/] [green]{world_info['population']:,}[/]",
    ]

    # Feature badges
    badges = []
    if world_info["has_lore"]:
        badges.append("[bold yellow]✦ Lore[/]")
    if world_info["has_narrative"]:
        badges.append("[bold magenta]◆ Narrative[/]")
    if world_info["has_chronicles"]:
        badges.append("[bold cyan]◈ Chronicles[/]")
    if world_info["has_magic"]:
        badges.append("[bold blue]◇ Magic[/]")
    if world_info["has_save"]:
        badges.append("[bold green]● Save[/]")
    if _has_sim_file(seed):
        badges.append("[bold yellow]▶ Sim[/]")
    if badges:
        lines.append("")
        lines.append("[bold underline]Features[/]")
        lines.append("  " + "  ".join(badges))

    # Load world for terrain preview + region details
    world = load_world(world_info["path"])
    if world:
        # Mini-map
        lines.append("")
        lines.append("[bold underline]Terrain[/]")
        mini = render_mini_map(world, width=24, height=6)
        lines.append(mini)

        # Settlement details
        all_settlements = []
        for r in world.regions:
            for s in r.settlements:
                all_settlements.append((r.name, s.name, s.kind, s.population))
        all_settlements.sort(key=lambda x: -x[3])

        lines.append("")
        lines.append("[bold underline]Largest Settlements[/]")
        for r_name, s_name, kind, pop in all_settlements[:5]:
            kind_icon = {
                "village": "▸", "town": "▹", "city": "●", "fortress": "▲",
                "outpost": "·", "hamlet": "·", "keep": "▲", "port": "⚓",
            }.get(kind, "·")
            lines.append(f"  {kind_icon} [italic]{s_name}[/] ({kind}, {pop:,})")

        # Regions
        lines.append("")
        lines.append("[bold underline]Regions[/]")
        for r in world.regions:
            r_pop = sum(s.population for s in r.settlements)
            biome_icons = {
                "deep_water": "🌊", "shallow": "🌊", "sand": "🏖",
                "grass": "🌿", "forest": "🌲", "hills": "⛰",
                "mountains": "🏔", "snow": "❄", "river": "🌊",
            }
            dom = r.biome if r.biome else "grass"
            emoji = biome_icons.get(dom, "🗺")
            lines.append(f"  {emoji} [italic]{r.name}[/] ({len(r.settlements)} settlements, {r_pop:,} pop)")

    # Character save
    char_info = _load_char_save_info(seed)
    if char_info:
        lines.append("")
        lines.append("[bold underline]Character[/]")
        lines.append(f"  {char_info['name']} ([italic]{char_info['profession']}[/])")
        lines.append(f"  Age: {char_info['age']} | Year: {char_info['year']} | Gold: [yellow]{char_info['gold']}[/]")
        lines.append(f"  Health: {char_info['health_bar']}")
        lines.append(f"  At: {char_info['settlement']}, {char_info['region']}")

    return "\n".join(lines)


# ── World List Item ──────────────────────────────────────────────────────

class WorldItem(Static):
    """A single world entry in the list."""

    def __init__(self, world_info: dict, selected: bool = False) -> None:
        super().__init__()
        self.world_info = world_info
        self._selected = selected
        self._update_content()

    def _update_content(self) -> None:
        w = self.world_info
        prefix = "[bold]▸[/] " if self._selected else "  "
        save_mark = "[green]●[/] " if w["has_save"] else ""
        lore_mark = "[yellow]✦[/] " if w["has_lore"] else ""
        pop_str = f"[green]{w['population']:,}[/]" if w["population"] > 0 else "[dim]0[/]"
        self.update(
            f"{prefix}[yellow]#{w['seed']}[/]  {save_mark}{lore_mark}{pop_str}  "
            f"[dim]{w['dimensions']}[/]  {w['regions']:>2} regions"
        )

    def set_selected(self, selected: bool) -> None:
        if self._selected != selected:
            self._selected = selected
            self._update_content()


# ── Character Manager Overlay ────────────────────────────────────────────

class CharacterManagerScreen(ModalScreen):
    """Overlay for viewing/deleting character saves."""

    def __init__(self, seed: int) -> None:
        super().__init__()
        self.seed = seed

    def compose(self) -> ComposeResult:
        info = _load_char_save_info(self.seed)
        with Vertical(id="char-manager-box"):
            yield Static(f"[bold cyan]wyrd #{self.seed} — Character Management[/]", id="char-title")
            if info:
                yield Static(f"[bold]{info['name']}[/]")
                yield Static(f"[dim]Profession:[/] {info['profession']}")
                yield Static(f"[dim]Age:[/] {info['age']}")
                yield Static(f"[dim]Year:[/] {info['year']}")
                yield Static(f"[dim]Location:[/] {info['settlement']}, {info['region']}")
                yield Static(f"[dim]Gold:[/] [yellow]{info['gold']}[/]")
                yield Static(f"[dim]Health:[/] {info['health']}/100 {info['health_bar']}")
                yield Static("")
                yield Button("Delete Save (r)", variant="error", id="delete-char-btn")
            else:
                yield Static("No saved character for this world.")
                yield Static("Start one with [bold]p[/] Play to create a save.")
            yield Button("Cancel (Esc)", variant="default", id="cancel-char-btn")

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
        Binding("r", "delete_save", "Delete"),
        Binding("q", "dismiss", "Close"),
    ]

    def action_delete_save(self) -> None:
        if _delete_char_save(self.seed):
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-char-btn":
            self.action_delete_save()
        else:
            self.dismiss(None)


# ── Delete Confirmation Overlay ──────────────────────────────────────────

class DeleteConfirmScreen(ModalScreen):
    """Confirm permanent world deletion."""

    def __init__(self, world_info: dict) -> None:
        super().__init__()
        self.world_info = world_info

    def compose(self) -> ComposeResult:
        w = self.world_info
        with Vertical(id="delete-confirm-box"):
            yield Static("[bold red]Delete World?[/]", id="del-title")
            yield Static(f"Seed: [yellow]#{w['seed']}[/]")
            yield Static(f"File: [dim]{w['file']}[/]")
            yield Static(f"Population: {w['population']:,}")
            yield Static("")
            yield Static("[bold]This cannot be undone.[/] Press [red]Del[/] again to confirm, any other key to cancel.")

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("q", "cancel", "Cancel"),
        Binding("delete", "confirm", "Confirm"),
    ]

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)


# ── Generate Seed Input Overlay ──────────────────────────────────────────

class GenerateScreen(ModalScreen):
    """Prompt for seed or generate random."""

    def compose(self) -> ComposeResult:
        with Vertical(id="generate-box"):
            yield Static("[bold cyan]Generate New World[/]", id="gen-title")
            yield Static("Enter a seed (number) or leave blank for random:")
            yield Input(placeholder="42", id="seed-input")
            yield Static("")
            with Horizontal(id="gen-buttons"):
                yield Button("Generate", variant="primary", id="gen-go-btn")
                yield Button("Generate + Lore", variant="default", id="gen-lore-btn")
                yield Button("Cancel", variant="default", id="gen-cancel-btn")

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    def action_submit(self) -> None:
        input_widget = self.query_one("#seed-input", Input)
        text = input_widget.value.strip()
        seed = int(text) if text and text.isdigit() else random.randint(0, 999999)
        self.dismiss(seed)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "gen-cancel-btn":
            self.dismiss(None)
            return
        input_widget = self.query_one("#seed-input", Input)
        text = input_widget.value.strip()
        seed = int(text) if text and text.isdigit() else random.randint(0, 999999)
        if bid == "gen-lore-btn":
            self.dismiss((seed, True))
        else:
            self.dismiss(seed)


# ── Help Overlay ─────────────────────────────────────────────────────────

class GatewayHelpScreen(ModalScreen):
    """Help overlay for the gateway."""

    def compose(self) -> ComposeResult:
        help_lines = [
            "[bold cyan]wyrd — Gateway Help[/]",
            "",
            "[bold]Navigation[/]",
            "  [yellow]↑ ↓ / j k[/]    Move selection up/down",
            "  [yellow]Enter[/]         View selected world (Textual TUI)",
            "",
            "[bold]Actions[/]",
            "  [yellow]n[/]             Generate a new world",
            "  [yellow]G[/]             Generate with lore",
            "  [yellow]p[/]             Play — enter the MUD",
            "  [yellow]C[/]             Character manager",
            "  [yellow]Tab[/]           Cycle sort (seed → pop → name)",
            "  [yellow]Del[/]           Delete selected world",
            "  [yellow]r[/]             Refresh world list",
            "",
            "[bold]General[/]",
            "  [yellow]? / h[/]         Toggle this help",
            "  [yellow]q / Esc[/]        Quit",
            "",
            "[dim]Press any key to close[/]",
        ]
        with Vertical(id="help-box"):
            yield Static("\n".join(help_lines), id="help-text")

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("h", "dismiss", "Close"),
        Binding("?", "dismiss", "Close"),
    ]


# ── World Picker Screen ──────────────────────────────────────────────────

class WorldPickerScreen(Screen):
    """Main world picker / gateway screen."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("up", "cursor_up", "Up", key_display="↑"),
        Binding("down", "cursor_down", "Down", key_display="↓"),
        Binding("k", "cursor_up", "Up"),
        Binding("j", "cursor_down", "Down"),
        Binding("enter", "select_world", "View"),
        Binding("n", "generate_world", "New"),
        Binding("G", "generate_lore", "Lore"),
        Binding("p", "play_world", "Play"),
        Binding("C", "character_manager", "Char"),
        Binding("tab", "cycle_sort", "Sort"),
        Binding("delete", "delete_world", "Del"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "show_help", "Help", key_display="?"),
        Binding("h", "show_help", "Help"),
    ]

    sort_key: reactive[str] = reactive("seed")
    sort_reverse: reactive[bool] = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.worlds: list[dict] = []
        self.selected_idx: int = 0
        self._current_detail: str = "[dim]No world selected[/]"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="gateway-main"):
            # Left panel: world list
            with Vertical(id="world-list-panel", classes="panel"):
                yield Static("[bold]Worlds[/]", id="world-list-title")
                yield Static("", id="sort-indicator")
                yield ListView(id="world-list")
            # Right panel: detail card
            with VerticalScroll(id="detail-panel", classes="panel"):
                yield Static("[dim]Select a world to see details[/]", id="detail-content")
        yield Footer()

    def on_mount(self) -> None:
        self._scan_and_populate()

    def _sort_worlds(self) -> None:
        """Sort world list in-place."""
        key = self.sort_key
        rev = self.sort_reverse
        if key == "population":
            self.worlds.sort(key=lambda w: w.get("population", 0), reverse=True)
        elif key == "name":
            self.worlds.sort(key=lambda w: str(w.get("seed", 0)))
        else:
            self.worlds.sort(key=lambda w: w.get("seed", 0))
        # population always descending; seed/name use the reverse flag
        if key != "population" and rev:
            self.worlds.reverse()

    def _update_sort_label(self) -> None:
        key = self.sort_key
        arrow = "↑" if self.sort_reverse else "↓"
        label_map = {"seed": "Seed", "population": "Pop", "name": "Name"}
        label = label_map.get(key, key)
        self.query_one("#sort-indicator", Static).update(
            f"[dim]Sorted by: [yellow]{label}{arrow}[/][/]"
        )

    def _scan_and_populate(self) -> None:
        """Scan for worlds and populate the list."""
        self.worlds = scan_worlds()
        self._sort_worlds()
        list_view = self.query_one("#world-list", ListView)
        list_view.clear()
        for w in self.worlds:
            list_view.append(ListItem(WorldItem(w)))
        self.selected_idx = 0
        self._update_detail()
        self._update_sort_label()

    def _update_detail(self) -> None:
        """Update the detail card for the selected world."""
        detail = self.query_one("#detail-content", Static)

        if not self.worlds or self.selected_idx >= len(self.worlds):
            detail.update("[dim]No world selected[/]")
            return

        world_info = self.worlds[self.selected_idx]
        try:
            text = _build_detail_text(world_info)
            detail.update(text)
        except Exception as e:
            detail.update(f"[red]Error loading world: {e}[/]")

    def _get_selected_world(self) -> dict | None:
        if not self.worlds or self.selected_idx >= len(self.worlds):
            return None
        return self.worlds[self.selected_idx]

    # ── Actions ──────────────────────────────────────────────────────

    def action_cursor_up(self) -> None:
        if self.selected_idx > 0:
            self.selected_idx -= 1
            self._update_detail()

    def action_cursor_down(self) -> None:
        if self.worlds and self.selected_idx < len(self.worlds) - 1:
            self.selected_idx += 1
            self._update_detail()

    def action_select_world(self) -> None:
        """Enter the MUD with the selected world."""
        w = self._get_selected_world()
        if w:
            world = load_world(w["path"])
            if world:
                from .tui_mud import MudScreen
                self.app.push_screen(MudScreen(world=world))

    def action_generate_world(self) -> None:
        self.app.push_screen(GenerateScreen(), self._on_generate_result)

    def action_generate_lore(self) -> None:
        def _handler(result):
            if result is not None:
                seed, with_lore = result if isinstance(result, tuple) else (result, False)
                self._do_generate(seed, with_lore=True)
        self.app.push_screen(GenerateScreen(), _handler)

    def _on_generate_result(self, result) -> None:
        if result is not None:
            if isinstance(result, tuple):
                seed, with_lore = result
                self._do_generate(seed, with_lore)
            else:
                self._do_generate(result, False)

    def _do_generate(self, seed: int, with_lore: bool = False) -> None:
        """Generate a world and add it to the list."""
        world = generate_world(seed)
        from .serialize import save_world
        save_world(world)
        if with_lore:
            from .lore import generate_lore
            from .narrative import generate_narrative
            from .religion import generate_pantheon
            from .magic import generate_magic
            from .faction import generate_factions
            from .chronicles import generate_chronicles
            from .bestiary import generate_bestiary
            world.lore = generate_lore(world)
            world.narrative = generate_narrative(world)
            world.pantheon = generate_pantheon(world)
            world.magic = generate_magic(world)
            world.factions = generate_factions(world)
            world.chronicles = generate_chronicles(world)
            world.bestiary = generate_bestiary(world)
            save_world(world)
        # Refresh the list
        self._scan_and_populate()
        # Select the new world
        self.selected_idx = 0
        self._update_detail()

    def action_play_world(self) -> None:
        """Enter the MUD with the selected world."""
        w = self._get_selected_world()
        if w:
            world = load_world(w["path"])
            if world:
                from .tui_mud import MudScreen
                self.app.push_screen(MudScreen(world=world))

    def action_character_manager(self) -> None:
        w = self._get_selected_world()
        if w:
            self.app.push_screen(CharacterManagerScreen(w['seed']), self._on_char_mgr_done)

    def _on_char_mgr_done(self, result) -> None:
        if result is not None:
            # Refresh detail card
            self._update_detail()

    def action_cycle_sort(self) -> None:
        keys = ["seed", "population", "name"]
        idx = keys.index(self.sort_key)
        if self.sort_reverse:
            # Toggle direction for current key, then next key with default direction
            if self.sort_key == "population":
                # population default is reverse (descending already)
                pass
            self.sort_key = keys[(idx + 1) % len(keys)]
            self.sort_reverse = False
        else:
            self.sort_reverse = True
        self._scan_and_populate()

    def action_delete_world(self) -> None:
        w = self._get_selected_world()
        if w:
            self.app.push_screen(DeleteConfirmScreen(w), self._on_delete_result)

    def _on_delete_result(self, confirmed) -> None:
        if confirmed:
            w = self._get_selected_world()
            if w:
                path = w["path"]
                # Also delete character save and sim file
                _delete_char_save(w["seed"])
                sim_path = f"wyrd-{w['seed']}-sim.json"
                for p in [path, sim_path, sim_path + ".gz"]:
                    if os.path.exists(p):
                        os.remove(p)
                self._scan_and_populate()

    def action_refresh(self) -> None:
        self._scan_and_populate()

    def action_show_help(self) -> None:
        self.app.push_screen(GatewayHelpScreen())


# ── App ──────────────────────────────────────────────────────────────────

CSS = """
Screen {
    background: #1a1b26;
}

#gateway-main {
    height: 100%;
}

.panel {
    border: solid $primary;
    height: 100%;
}

#world-list-panel {
    width: 40%;
    min-width: 30;
}

#world-list-title {
    padding: 0 1;
    background: #242538;
    color: $primary;
    text-style: bold;
    height: 1;
}

#sort-indicator {
    padding: 0 1;
    height: 1;
    color: $text;
    background: #1e1f2e;
    border-bottom: solid $secondary;
}

#world-list {
    width: 100%;
    height: 100%;
    overflow-y: auto;
}

#detail-panel {
    width: 60%;
    min-width: 40;
    overflow-y: auto;
}

#detail-content {
    padding: 1 2;
    color: $text;
}

#detail-content Static {
    margin: 0;
}

/* ── Modal styling ── */

#char-manager-box, #delete-confirm-box, #generate-box, #help-box {
    width: 50;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: #1e1f2e;
    margin: 1 2;
    align: center middle;
}

#char-title, #gen-title, #del-title {
    content-align: center top;
    text-style: bold;
}

#generate-box Input {
    margin: 1 0;
}

#gen-buttons {
    align: center middle;
    height: auto;
}

#gen-buttons Button {
    margin: 0 1;
}

#help-text {
    padding: 1 2;
    color: $text;
}

#help-box {
    width: 52;
    height: auto;
    max-height: 100%;
}
"""


class WyrdGateway(App):
    """Textual-based world picker gateway."""

    CSS = CSS
    TITLE = "wyrd"
    SUB_TITLE = "generative fantasy sandbox"

    def on_mount(self) -> None:
        self.push_screen(WorldPickerScreen(), self._on_picker_result)

    def _on_picker_result(self, result) -> None:
        """Handle result from picker screen."""
        # WorldPickerScreen now pushes MudScreen directly for play/view,
        # so this only needs to handle the None case (quit).
        if result is None:
            self.exit(None)
        else:
            self.set_screen(WorldPickerScreen)


def launch() -> None:
    """Launch the Textual gateway."""
    app = WyrdGateway()
    app.run()
