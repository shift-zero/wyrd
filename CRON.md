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

**Phase 18 (Depth & Quality) in progress. 722 tests pass — 44% faster test suite (87s vs 156s).**

### What was done this session
1. **Resource map precomputation** — `_precompute_resource_maps()` in sim.py generates carrying capacity, food, and wealth maps for every cell at sim initialization. `_calculate_carrying_capacity()` and `_resource_availability()` use cached O(1) lookups instead of looping over a 11×11 radius per call. Maps are invalidated when cataclysm mutates terrain. Isolated lookup speedup: 125x.

2. **pytest-xdist parallel test execution** — Installed `pytest-xdist>=3.6`, added to `pyproject.toml` dev deps. Fixed test_serve.py fixture dependencies so all 722 tests pass with `--dist loadscope`. Tests run in 87s (4 workers) vs 156s serial — 44% faster.

3. **Updated .gitignore** — `_profile_*` files ignored.

### Test command
```bash
# Fast: parallel execution (4 workers)
source .venv/bin/activate && python -m pytest tests/ -q -n 4 --dist loadscope

# Serial (fallback if xdist issues)
python -m pytest tests/ -q
```

### Phase 18: Depth & Quality — remaining candidates

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

The project is feature-complete. Every module exists, every CLI command works, 722 tests pass. Now the question is **depth** — making what's already there *richer* and *more cohesive* instead of adding more modules.

Candidates for Phase 18 (pick one per session):

1. **🔲 Embodied play depth** — More scenario types, skill system, deeper consequences. *(Shop/buy/sell system done ✅)*

2. **🔲 TUI polish** — The Textual-based TUI works but could be smoother: better keybind discoverability, persistent help bar, world picker on launch, minimap, smoother animations.

3. **🔲 World generation variety** — More terrain types (swamp, tundra, canyon, reef), biome-specific color palettes, weather patterns visible on the map.

4. **🟡 Performance — 87s test suite (was 156s).** Resource map precomputation + pytest-xdist parallel execution. Next: profile and optimize noise gen, sim loop per-tick overhead.

5. **🔲 Bestiary depth** — *(Creature loot + encounter integration done ✅)* Full creature generation with stats, habitats, encounter tables, TTRPG integration already in place.

6. **🔲 REST API** — Expose the world data as an HTTP API so external tools can consume it programmatically without running wyrd.

7. **🔲 Multi-world interaction** — Trade, war, diplomacy between parallel worlds. Cross-world pantheon crossover. Portal events.

### Architecture notes
- `src/__main__.py` — All CLI wiring. Module-level imports for render, redundant local imports removed.
- `src/render.py` — All ANSI rendering. `render_map()` is the main map renderer.
- 24 subcommands on `wyrd --help`
