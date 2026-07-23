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

**Phase 19 — Trade route animation complete.** The viewer now shows gold dotted trade lines between connected settlements with animated ◆ dots moving along each route. Goods flow visibly between economies. Step-pause notification added — manual stepping through a significant event shows the same flashing banner as auto-pause.

### What was built this session (Phase 19 — Trade Route Animation)

1. **Bresenham line drawer** — `_bresenham_line()` in viewer.py yields cartesian coordinates along a clean line between any two points. Used to draw trade routes and position animated dots.

2. **Trade route rendering** — `_draw_trade_routes()` renders gold `·` dotted lines between connected settlements. A `◆` dot travels from source to destination at a unique phase per route. When paused, dots hold position so the trade network is always readable.

3. **Viewer help update** — Added a "Trade Routes" section to the in-viewer help overlay explaining the visual language.

4. **Step-pause notification** — Manual step (→ key) now checks for significant events in the stepped year and triggers the same flashing auto-pause banner, so you don't miss world events even when stepping manually.

### What to tackle next

- **Seasonal palette — deeper variation.** The 4-season shift works but is subtle. Snowfall accumulation in winter (grass → snow transition near cold regions), greening transitions in spring, more dramatic autumn reds. Could use a temperature map computed from latitude + elevation.
- **Embody mode TUI.** Embody (1943 lines) runs as scrolling terminal conversation. A curses TUI with stats sidebar, event log, and action menu would match the rest of the tooling.
- **Trade route animation — route legend.** Add a small indicator showing how many active routes exist, maybe the current goods flowing or a route count in the status bar.
