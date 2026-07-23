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

## Current state (2026-07-26)

**Phase 23.5 — Auto-Pause on Viewer Events complete.** The viewer now auto-pauses on significant events (wars, cataclysms, foundings, discoveries, faction changes) with a flashing notification banner that explains what triggered the pause. This fixes the stroboscopic UX at high speeds — you no longer blink and miss world-changing events.

### What was built this session (Phase 23.5 — Auto-Pause)

1. **Auto-pause detection in viewer** — After each simulation tick, the loop scans the most recent events for pause-worthy types (founding, abandonment, war, faction_war, faction_collapse, faction_vassal_revolt, faction_coup, all cataclysms, discovery). When found while running, the viewer auto-pauses and stores the triggering event description.

2. **Flashing notification banner** — A `_draw_pause_notification` function renders a colored banner line at the top of the map area showing "⏸ Auto-paused <icon> <description>". The banner alternates colors (accent/status) for a flashing effect, persisting for ~60 frames (~0.5s at 60fps) before fading.

3. **Help section** — Updated the viewer help overlay to document the auto-pause feature with a dedicated "Auto-Pause" section.

### What to tackle next

- **Trade route animation.** Routes render as static lines. Animating goods flowing along routes in the viewer (a moving dot per route) would make the economy feel alive.
- **Embody mode TUI.** Embody runs as scrolling terminal conversation. A curses TUI for embody — with stats sidebar, event log, action menu — would match the rest of the tooling.
- **Seasonal palette — deeper variation.** The 4-season shift works but is subtle. Snowfall accumulation in winter, greening transitions in spring.
- **Pause-on-event — step update.** The auto-pause notification currently doesn't flash when the user steps (→ key). Could add notification display on step too.
