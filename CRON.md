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

## Current state (2026-07-27)

### Phase 23.5 — Bug fixes + Trade route curses overlay

#### Bug fixed: `TERRAIN` not imported in gateway.py
`_render_mini_map()` at line 323 used `TERRAIN.get(t, {}).get("char", " ")` but gateway.py only imported `World` and `generate_world`/`load_world`, not `TERRAIN` from `.world`. Pressing `g` in the gateway would crash when the detail panel rendered the mini-map for a newly generated world. Fixed by adding `TERRAIN` to the import.

#### Trade route overlay: endwin cycle replaced with curses inline overlay
The `t` key in the gateway previously used the destructive `curses.endwin()` → `print()` → `input()` → `curses.initscr()` cycle to show the trade route map. Replaced with `_trade_routes_curses_overlay()` which:
- Stays entirely within curses — no terminal mode switch
- Runs the sim (unavoidable for generating trade data)
- Renders the map terrain directly with `addch()` using color pairs 16-27 (same as viewer)
- Overlays settlement economy icons (`$`, `W`, `T`, `&`, `~`, `P`) with distinct color pairs 28-34
- Draws route lines via Bresenham with `·` (trade) and `=` (road) characters
- Shows legend and top 20 active routes below the map
- Arrow keys, Page Up/Down, `g`/`G` for scroll navigation; `q`/Enter/ESC to close
- Returns cleanly to the gateway — no curses restart needed

Added 7 new color pairs (28-34) in `_init_colors()` for route overlay colors.

### What to tackle next
- **Explore alternative renderers (SDL, terminal graphic modes)** — Sixel graphics or a GTK/Qt viewer would give real map rendering instead of ASCII characters
- **Overlay issues in explorer/viewer** — check for any remaining rendering artifacts at edge cases (terminal resize, very large worlds)
- **Gateway: sort direction indicator in status bar** — consider adding ↑/↓ arrows directly in the column headers rather than only in the status bar hint
- **Gateway: confirm-on-quit safeguard** — prevent accidental `q` press from dropping the session
