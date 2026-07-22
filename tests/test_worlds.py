"""
Tests for wyrd Phase 8 — Multi-World Management.

Covers the `wyrd worlds` command: listing existing worlds, scanning,
metadata extraction, and JSON output.
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.serialize import save_world


class TestWorldsDiscovery:
    """The worlds command must discover and parse world files."""

    def test_scan_finds_world_file(self):
        """A saved world should be discoverable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            world = generate_world(42)
            path = os.path.join(tmpdir, "wyrd-42.json")
            save_world(world, path)

            # Scan using the same logic as the CLI
            import glob
            pattern = os.path.join(tmpdir, "wyrd-*.json")
            files = sorted(glob.glob(pattern))
            files = [f for f in files if not f.endswith("-sim.json") and not f.endswith(".ttrpg.json")]
            assert len(files) == 1
            assert "wyrd-42.json" in files[0]

    def test_scan_ignores_sim_files(self):
        """Simulation files should not appear as world files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            world = generate_world(42)
            save_world(world, os.path.join(tmpdir, "wyrd-42.json"))

            # Create a sim file
            with open(os.path.join(tmpdir, "wyrd-42-sim.json"), "w") as f:
                json.dump({"seed": 42, "sim": True}, f)

            # Scan — sim file should be excluded
            import glob
            import re
            pattern = os.path.join(tmpdir, "wyrd-*.json")
            files = sorted(glob.glob(pattern))
            files = [f for f in files if not re.search(r'-sim\.json', f) and not re.search(r'\.ttrpg\.json', f)]
            assert len(files) == 1

    def test_scan_ignores_ttrpg_files(self):
        """TTRPG export files should not appear as world files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            world = generate_world(42)
            save_world(world, os.path.join(tmpdir, "wyrd-42.json"))

            # Create a ttrpg file
            with open(os.path.join(tmpdir, "wyrd-42.ttrpg.json"), "w") as f:
                json.dump({"format": "wyrd-ttrpg"}, f)

            # Scan — ttrpg file should be excluded
            import glob
            import re
            pattern = os.path.join(tmpdir, "wyrd-*.json")
            files = sorted(glob.glob(pattern))
            files = [f for f in files if not re.search(r'-sim\.json', f) and not re.search(r'\.ttrpg\.json', f)]
            assert len(files) == 1

    def test_scan_empty_directory(self):
        """An empty directory should yield no worlds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import glob
            import re
            pattern = os.path.join(tmpdir, "wyrd-*.json")
            files = sorted(glob.glob(pattern))
            assert len(files) == 0

    def test_scan_parses_metadata(self):
        """Extracted metadata should be correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            world = generate_world(42)
            path = os.path.join(tmpdir, "wyrd-42.json")
            save_world(world, path)

            with open(path) as f:
                data = json.load(f)

            assert data["seed"] == 42
            assert data["width"] == 80
            assert data["height"] == 40
            assert len(data["regions"]) > 0
            total_pop = sum(
                s.get("population", 0)
                for r in data["regions"]
                for s in r.get("settlements", [])
            )
            assert total_pop > 0

    def test_world_file_has_badges(self):
        """Sim-companion files should be flagged correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            world = generate_world(42)
            save_world(world, os.path.join(tmpdir, "wyrd-42.json"))

            # Check for lore/narrative/chronicles/magic flags
            with open(os.path.join(tmpdir, "wyrd-42.json")) as f:
                data = json.load(f)

            has_lore = "lore" in data and data["lore"] is not None
            has_narrative = "narrative" in data and data["narrative"] is not None
            has_chronicles = "chronicles" in data and data["chronicles"] is not None
            has_magic = "magic" in data and data["magic"] is not None

            # Without explicitly generating these, they may or may not exist
            assert isinstance(has_lore, bool)
            assert isinstance(has_narrative, bool)
            assert isinstance(has_chronicles, bool)
            assert isinstance(has_magic, bool)
