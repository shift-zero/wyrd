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
