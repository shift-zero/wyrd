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

### Phase 19 — TTRPG export completeness + Gateway sort UX

Two fixes this session:

1. **TTRPG export: Added proper Faction dataclass data.** The `_build_faction_relationships` helper only read from `world.lore.relationships` (old region dicts), missing the full `Faction` dataclass in `world.factions`. Replaced with `_build_factions_section` that extracts influence, wealth, military, stability, goals, leader info, power_score, reputation, territory from proper Faction objects. Also extracts `FactionRelationship` objects from `world.faction_relationships`. Falls back to legacy `world.lore.relationships` for backward compatibility. All 24 TTRPG export tests pass.

2. **Gateway sort UX.** Added sort direction indicators (↑/↓ arrows) in the gateway status bar hint. Added Shift+Backtab (curses.KEY_BTAB) to toggle sort direction without resetting selection. Tab still cycles through sort keys (seed/population/name) and resets to natural order.

### What to tackle next
- **Fix: `TERRAIN` not imported in gateway.py** — `_render_mini_map()` at line 323 uses `TERRAIN.get(...)` but gateway.py only imports `World`, `generate_world`, and `load_world`, not `TERRAIN` from `.world`. Pressing `g` in the gateway generates a world then crashes when the detail panel renders the mini-map.
- **Explore alternative renderers (SDL, terminal graphic modes)** — biggest open item mentioned in CRON.md. Sixel graphics or a GTK/Qt viewer would give real map rendering instead of ASCII characters.
- **Gateway trade route overlay** — replace the current `t` key `endwin()`→print→`initscr()` cycle with a curses inline overlay showing trade routes on a map.
- **Look for remaining visual bugs** — check viewer, explorer, and embody TUI for overlay/rendering issues similar to the gateway fix in the previous session.
