"""
Tests for Phase 17 — Textual-based TUI viewer structure.

Verifies that the TUI module imports correctly and that its
widget classes can be instantiated (not in a terminal context).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.generate import generate_world


class TestTUIStructure:
    """Verify TUI module structure without launching an app."""

    def test_tui_import(self):
        """TUI module imports cleanly."""
        from src import tui
        assert hasattr(tui, "WyrdTUI")
        assert hasattr(tui, "SimScreen")
        assert hasattr(tui, "SimMapWidget")
        assert hasattr(tui, "SimInfoPanel")
        assert hasattr(tui, "EventLogWidget")
        assert hasattr(tui, "HelpScreen")
        assert hasattr(tui, "launch")

    def test_sim_screen_init(self):
        """SimScreen can be instantiated with a world."""
        from src.tui import SimScreen
        world = generate_world(42, width=30, height=20)
        screen = SimScreen(world)
        assert screen.world is world

    def test_sim_map_widget(self):
        """SimMapWidget can receive and render a world."""
        from src.tui import SimMapWidget
        from textual.widgets import Static
        world = generate_world(42, width=30, height=20)
        widget = SimMapWidget()
        # Verify it's a Static widget
        assert isinstance(widget, Static)
        # render_map should not throw
        widget.render_map(world)
        assert widget.world is world

    def test_event_log_widget(self):
        """EventLogWidget can be instantiated and log events."""
        from src.tui import EventLogWidget
        from textual.widgets import RichLog
        widget = EventLogWidget()
        assert isinstance(widget, RichLog)

    def test_launch_function_exists(self):
        """launch function accepts world or seed."""
        from src.tui import launch
        # Verify the function signature works
        world = generate_world(42, width=30, height=20)
        # Just verify it doesn't crash importing
        assert callable(launch)

    def test_help_screen_init(self):
        """HelpScreen can be instantiated."""
        from src.tui import HelpScreen
        screen = HelpScreen()
        assert screen is not None


class TestTUIGateway:
    """Verify tui_gateway module structure without launching an app."""

    def test_gateway_import(self):
        """tui_gateway module imports cleanly."""
        from src import tui_gateway
        assert hasattr(tui_gateway, "WyrdGateway")
        assert hasattr(tui_gateway, "WorldPickerScreen")
        assert hasattr(tui_gateway, "launch")

    def test_render_mini_map(self):
        """render_mini_map produces ANSI-colored output."""
        from src.tui_gateway import render_mini_map
        from src.generate import generate_world
        world = generate_world(42, width=30, height=20)
        mini = render_mini_map(world, width=24, height=6)
        assert len(mini) > 0
        assert "\x1b[38;2;" in mini  # ANSI color escape present

    def test_build_detail_text(self):
        """_build_detail_text returns content for a world."""
        from src.tui_gateway import _build_detail_text
        from src.gateway import scan_worlds
        from src.serialize import save_world
        from src.generate import generate_world
        world = generate_world(42, width=30, height=20)
        save_world(world, "wyrd-42.json")
        results = scan_worlds()
        assert len(results) > 0
        text = _build_detail_text(results[0])
        assert "wyrd #42" in text
        assert "Terrain" in text
        import os
        os.remove("wyrd-42.json")

    def test_sorting(self):
        """World sorting by seed works correctly."""
        from src.tui_gateway import WorldPickerScreen
        screen = WorldPickerScreen()
        screen.worlds = [
            {"seed": 99, "population": 100, "file": "a.json"},
            {"seed": 42, "population": 500, "file": "b.json"},
            {"seed": 7, "population": 200, "file": "c.json"},
        ]
        screen.sort_key = "seed"
        screen.sort_reverse = False
        screen._sort_worlds()
        seeds = [w["seed"] for w in screen.worlds]
        assert seeds == [7, 42, 99], f"Expected [7, 42, 99], got {seeds}"

    def test_sort_population(self):
        """Population sort is descending."""
        from src.tui_gateway import WorldPickerScreen
        screen = WorldPickerScreen()
        screen.worlds = [
            {"seed": 99, "population": 100, "file": "a.json"},
            {"seed": 42, "population": 500, "file": "b.json"},
            {"seed": 7, "population": 200, "file": "c.json"},
        ]
        screen.sort_key = "population"
        screen._sort_worlds()
        pops = [w["population"] for w in screen.worlds]
        assert pops == [500, 200, 100], f"Expected [500, 200, 100], got {pops}"

    def test_overlay_screens_init(self):
        """Overlay screens instantiate correctly."""
        from src.tui_gateway import CharacterManagerScreen, DeleteConfirmScreen, GatewayHelpScreen
        assert CharacterManagerScreen(seed=42) is not None
        assert DeleteConfirmScreen({"seed": 42}) is not None
        assert GatewayHelpScreen() is not None

    def test_launch_entry(self):
        """launch function is callable."""
        from src.tui_gateway import launch
        assert callable(launch)
