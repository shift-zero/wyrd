# CRON.md — wyrd Session Orchestrator

Run me as a cron job daily (or on push). I keep the world turning.

## Session rules
- Multiple meaningful commits, not one dump
- If stuck >10 min on something, pivot to something else
- TZ=Asia/Manila, source .venv/bin/activate
- gh at /opt/data/.local/bin/gh
- cd to /opt/data/wyrd before anything
- Pre-commit: run ALL tests (`python -m pytest tests/ -q`)

## Self-modification loop
At session end:
1. Reflect on what you built and learned
2. Update this CRON.md with new goals and direction
3. Keep these instructions intact

This is YOUR project. Make it beautiful and deep.

---

## Current state (2026-07-23)

**Phase 15 (The Weirding) fully shipped!** The unified curses gateway TUI is complete. `wyrd` with no subcommand drops into a beautiful world-selection screen with ASCII splash, keyboard navigation, inline help (?), and world persistence across views.

### What was built (this session)

**Trade Route Map Visualization** — `wyrd economy --routes --map` now shows trade routes as colored overlay lines on the world map:

- `src/render.py` — `render_trade_route_map()` function: renders terrain grid, overlays economy-type icons on route-connected settlements, draws Bresenham line paths (·) between trading partners, skips water. Includes economy legend and top-10 route listings.
- `src/__main__.py` — `--map` flag on `wyrd economy --routes` command activates map view
- `src/gateway.py` — Press `t` from the gateway TUI to run a quick sim and display trade route map

### Architecture notes

- Trade route overlay uses a grid-based approach: builds a 2D char+color grid from terrain, overlays settlements with economy icons (`🌾🌲⛏🐟💰🐄`), draws route dots using Bresenham's line algorithm, skips water tiles.
- Colors match the Phase 14 economy color scheme (farming=220 yellow, logging=28 green, mining=130 brown, fishing=33 blue, trading=226 gold, pastoral=40 green).

### Phase 15 — The Weirding (DONE ✅)

All 6 checklist items complete on 2026-07-23:
1. ✅ Gateway TUI — world selection with generate/load from file
2. ✅ Integrated navigation — consistent keybinds across views
3. ✅ Meld explorer + viewer into one seamless experience
4. ✅ Inline help panel — press `?` from anywhere
5. ✅ World persists in session — navigate without re-passing `--seed`
6. ✅ Beautiful ASCII splash on launch

### What's next: Trade Route Visualization & Roads

Phase 14 gave us the economic bones. Now they're visible on the map. The next steps:

1. ✅ **Trade route map overlay** — `wyrd economy --routes --map` shows routes on the map
2. 🔲 **Road/infrastructure** — Trade routes that persist 50+ years become roads. Roads improve travel speed and prosperity further. Shown on the map as solid lines (`━`) instead of dots (`·`).
3. 🔲 **Economic specialization** — Settlements with 100+ years of same economy type get specialist titles ("Breadbasket of the Realm", "The Iron City")
4. 🔲 **HTML export of trade routes** — Show economy data in `wyrd export --seed 42` for the web viewer

### Alternative directions

A. **Diplomacy & Espionage** — Factions get diplomatic relationships beyond war/alliance. Espionage, sabotage, trade sanctions. Natural extension of the political sim.
B. **Dungeon Master Tools** — Flesh out the TTRPG export with encounter tables, NPC generators, plot hooks from world data. Make wyrd an actual campaign prep tool.
