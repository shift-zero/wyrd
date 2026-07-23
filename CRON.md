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

**All 16 phases complete.** wyrd generates worlds, simulates 1000+ years of history, renders trade routes with roads, and has a gateway TUI, web dashboard, and TTRPG export.

### What Jacob wants next: Phase 17 — Living Worlds

The project is feature-complete but *passive*. Running the sim dumps text — you watch events scroll by, the map sits still, you can't interact with the world as anything other than an observer. Jacob's feedback:

1. **"The map is not animated"** — watching the sim is like watching events, not watching the world change. Tiles should animate: borders pulse, settlements grow/shrink, trade routes light up, cataclysm scars spread.
2. **"The TUI is hard to use and kinda messy"** — Bubbletea is the inspiration but that's Go. Options: Textual (Python, reactive widgets), better curses architecture, or a hybrid.
3. **"Do you plan to have a mode where the user plays as a character?"** — Embodied play mode. Not god-mode watching, but *living in* the world as a character.

### Mandate

Steer toward **Phase 17 — Living Worlds**. The three pillars:

1. **Animated simulation maps** — render tile transitions live, population changes as visual grow/shrink, roads forming tile by tile
2. **TUI overhaul** — Bubbletea-inspired clean layout (Textual or better curses), modal panels, status bar, discoverable keybinds
3. **Embodied play mode** — `wyrd embody` lives inside the sim as a character. News arrives, you travel, decisions matter. Multi-generational stretch.

Full checklist in PLAN.md. Read it.
