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

**Phase 19 — Embody mode TUI complete.** The print/input embody mode now has a proper curses TUI (`embody_tui.py`, 750 lines) with stats sidebar, scrollable event log, action bar, and overlay dialogs for choices, travel, and market.

### What was built this session (Phase 19 — Embody Mode TUI)

1. **Embodied Play TUI** — `src/embody_tui.py` (750 lines) provides a full curses TUI for embody mode:
   - **Stats sidebar** — character name, profession, health bar (animated), gold, age, season/year, location, all 5 skills with progress bars, deeds, visited settlements, reputation
   - **Event log** — scrollable right panel with color-coded event types (red for combat, green for prosperity, blue for discoveries) — scroll with ↑↓/PgUp/PgDn
   - **Action bar** — persistent bottom bar showing all available keybinds
   - **Choice overlays** — transparent overlay for interactive events (1/2/3 choices) with result feedback flowing into the event log
   - **Travel overlay** — scrollable destination picker inside the TUI
   - **Market overlay** — buy/sell interface within the TUI
   - **Help overlay** — `?` key shows contextual help (same panel pattern as gateway)
   - **Scrollable log** — up/down/page-up/page-down navigation
   - **Heir system** — death shows epilogue, offers heir continuation (terminal fallback)

2. **CLI integration** — `wyrd embody --seed 42 --tui` launches the TUI. Gateway defaults to TUI. Legacy `print()` mode still available without `--tui`.

3. **Gateway integration** — `p` key in gateway launches the TUI instead of print mode. Old `embody_play` is preserved for CLI users who don't want curses.

### What to tackle next

- **Seasonal palette — deeper variation.** Snow accumulation on cold terrain, greening transitions in spring, dramatic autumn reds using temperature maps from latitude + elevation.
- **Heir TUI integration** — the heir prompt currently drops to terminal after character death in TUI mode. Could present options within curses.
- **Embody TUI mobile support** — handle small terminal sizes more gracefully (collapse sidebar at <100 columns).
- **Trade route legend** — small route count indicator in the viewer status bar.
