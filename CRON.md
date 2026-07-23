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

**Phase 18 (Depth & Quality) in progress. 690 tests pass (+65).**

### What was done this session
1. **Bestiary tests (65 new)** — The bestiary module had 597 lines of content but zero tests. Now covered: determinism, creature structure, habitats, faction integration, unique creatures, tier/CR calculations, stat blocks, loot tables, name generation, creature type selection, zone-specific creatures, rendering, serialization round-trip, body plans, and edge cases.

2. **Bugfix: render_creature_detail() returned None** — The function was missing a `return "\n".join(lines)` at the end, so `wyrd bestiary --seed 42 --id 0` silently produced no output. (c69d349)

3. **Bugfix: creature name collisions** — Creature names could duplicate across habitats (e.g. "Chimera" in both temperate + faction), and faction creatures bypassed the per-habitat name check. Fixed with global `seen_names_global` set in `generate_bestiary()`. (c69d349)

4. **Creature encounters during travel** — When traveling in embodied play mode (`wyrd embody --seed 42`), there's a 30% chance of encountering a creature from the world's bestiary matching your region's biome. Fight / flee / distract choices with consequences scaled by creature tier and behavior. Unique creatures get ★ markers. Encounters consume the travel year with deeds and legacy tracking. (c69d349)

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
