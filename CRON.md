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

**Phase 18 (Depth & Quality) in progress. 722 tests pass (+32).**

### What was done this session
1. **Shop/Market system (32 new tests)** — Settlement economy-themed shops in embodied play mode. Each of 6 economy types (farming, logging, mining, fishing, trading, pastoral) gets distinct inventory items with prices scaled by settlement population. Players press `m` in the game loop to browse, buy, and sell items. Creature loot tables for 6 creature types (beast, monster, humanoid, dragon, undead, elemental) generate tier-scaled loot on victory.

2. **Richer creature loot in travel encounters** — Replaced the old 30%-chance-for-one-item system with deterministic creature_loot() from the shop module. All defeated creatures now drop 1-3 items scaled by tier and creature type. Loot names and prices appear in the encounter narrative.

3. **Bugfix: flaky sim determinism test** — `test_snapshot_determinism` and `test_deterministic_simulation` shared a single `World` object between two `run_simulation()` calls. Cataclysms mutate `world.terrain` in-place, so the second call could see different initial conditions after a cataclysm triggered in the first run. Fixed by creating separate worlds for each call. (832148a)

4. **New module: `src/shop.py`** — Clean separation of shop data tables, generation logic, and rendering. 8 functions exported for use by embody.py and tests.

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

4. **🔲 Performance** — 150s test suite, sim can be slow for 1000+ years on large maps. Profiling and optimization.

5. **🔲 Bestiary depth** — *(Creature loot + encounter integration done ✅)* Full creature generation with stats, habitats, encounter tables, TTRPG integration already in place.

6. **🔲 REST API** — Expose the world data as an HTTP API so external tools can consume it programmatically without running wyrd.

7. **🔲 Multi-world interaction** — Trade, war, diplomacy between parallel worlds. Cross-world pantheon crossover. Portal events.

### Architecture notes
- `src/__main__.py` — All CLI wiring. Module-level imports for render, redundant local imports removed.
- `src/render.py` — All ANSI rendering. `render_map()` is the main map renderer.
- 24 subcommands on `wyrd --help`
