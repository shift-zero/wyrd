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

**Phase 19 — Embody mode TUI complete.** The print/input embody mode now has a proper curses TUI (`embody_tui.py`, 1146 lines) with stats sidebar, scrollable event log, action bar, and overlay dialogs for choices, travel, market, and death epilogue.

### Phase 19 — Heir TUI integration + mobile support + route legend (this session)

1. **Heir TUI integration** — Death epilogue is now rendered as a full-screen overlay within curses instead of dropping to terminal. Press `y` to continue as heir or `n` to quit, all within the TUI. Heir generation and restart happen cleanly inside curses.
   - `_draw_epilogue_overlay()` — full-screen Life Ledger overlay with curses colors
   - `_generate_heir_in_tui()` — extracted heir generation helper
   - Old terminal prompt code removed (~100 lines)

2. **Trade route legend** — Viewer stats bar now shows "Routes: N" with the count of active trade routes, next to population and speed indicators.

3. **Embody TUI mobile support** — Terminals narrower than 100 columns get a compact sidebar (name, health, gold, age, season, location only). Full sidebar with skills, deeds, visited, and reputation restored at ≥100 columns.

### What to tackle next
- **Seasonal palette — deeper variation.** Snow accumulation on cold terrain, greening transitions in spring, dramatic autumn reds using temperature maps from latitude + elevation.
- **Embody TUI heir epilogue polish** — add heir generation confirmation overlay (name, stats preview) before committing to heir restart.
- **Embody TUI mobile threshold** — active resizing feedback when terminal crosses the 100-col boundary.
