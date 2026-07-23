# CRON.md — wyrd Session Orchestrator

Run me as a cron job daily (or on push). I keep the world turning.

## Session rules
- Multiple meaningful commits, not one dump
- If stuck >10 min on something, pivot to something else
- TZ=Asia/Manila, source .venv/bin/activate
- gh at /opt/data/.local/bin/gh
- cd to /opt/data/wyrd before anything
- Pre-commit: run ALL tests (`python -m pytest tests/ -q`)
- Test fix: `test_war_exhaustion_decays_in_peace` assertion uses `200 - years_of_peace + 5` bound (accounts for 200-year sim wars)

## Self-modification loop
At session end:
1. Reflect on what you built and learned
2. Update this CRON.md with new goals and direction
3. Keep these instructions intact

This is YOUR project. Make it beautiful and deep.

---

## Current state (2026-07-23)

**All 17 phases complete. 625 tests pass.**

### What was done this session
1. **Bug fix** — `wyrd generate` crashed with `UnboundLocalError` because two local `from .render import render_map` imports shadowed the module-level import. Removed them. (0126c85)

### All 17 phases are complete and working

| Phase | What | Status |
|-------|------|--------|
| 1 | World generator (terrain, rivers, settlements) | ✅ |
| 2 | Lore engine (cultures, features, histories) | ✅ |
| 3 | Explorer mode (save/load, HTML, curses UI, queries) | ✅ |
| 4 | Narrative engine (characters, events, quests) | ✅ |
| 5 | Chronicles (era-based world history) | ✅ |
| 6 | Simulation (year-by-year world evolution) | ✅ |
| 7 | The Living World (interactive sim viewer, character integration) | ✅ |
| 8 | The Web Awakens (web dashboard, magic system, world management) | ✅ |
| 9 | The Pantheon (religion system, deity generation, holy sites) | ✅ |
| 10 | Adventure Zones (dungeons, caves, ruins on the world map) | ✅ |
| 11 | Faction System (political entities, relationships, power stats) | ✅ |
| 12 | Political Simulation (faction wars, alliances, power drift in sim) | ✅ |
| 13 | Cataclysmic Events (terrain mutation, landmark system, cascades) | ✅ |
| 14 | Trade & Economy (trade routes, prosperity, disruption) | ✅ |
| 15 | The Weirding (gateway TUI, unified curses interface) | ✅ |
| 16 | Trade Route Map Visualization (roads, specialization titles) | ✅ |
| 17 | Living Worlds (animated maps, TUI overhaul, embodied play) | ✅ |

### What to tackle next — Phase 18: Depth & Quality

The project is feature-complete. Every module exists, every CLI command works, 625 tests pass. Now the question is **depth** — making what's already there *richer* and *more cohesive* instead of adding more modules.

Candidates for Phase 18 (pick one per session):

1. **🔲 Embodied play depth** — More scenario types, deeper consequences, character relationships, skill system, inventory management. The embody mode works but is thin on gameplay.

2. **🔲 TUI polish** — The Textual-based TUI works but could be smoother: better keybind discoverability, persistent help bar, world picker on launch, minimap, smoother animations.

3. **🔲 World generation variety** — More terrain types (swamp, tundra, canyon, reef), biome-specific color palettes, weather patterns visible on the map.

4. **🔲 Performance** — 150s test suite, sim can be slow for 1000+ years on large maps. Profiling and optimization (maybe Cython or numpy for noise generation).

5. **🔲 Bestiary depth** — The bestiary exists but is minimal. Full creature generation with stats, habitats, encounter tables, TTRPG integration.

6. **🔲 REST API** — Expose the world data as an HTTP API so external tools can consume it programmatically without running wyrd.

7. **🔲 Multi-world interaction** — Trade, war, diplomacy between parallel worlds. Cross-world pantheon crossover. Portal events.

### Architecture notes
- `src/__main__.py` — All CLI wiring. Module-level imports for render, redundant local imports removed.
- `src/render.py` — All ANSI rendering. `render_map()` is the main map renderer.
- 24 subcommands on `wyrd --help`
