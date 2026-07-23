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

## Current state (2026-07-25)

**Phase 23 — Surface Depth complete. All 3 checklist items ✅.** Explore mode now uses batched `addstr()` spans (~95% fewer curses API calls) with pre-built zone lookup. Viewer speed extends beyond Zoom to Decade (128x), Century (256x), and Epoch (512x). When paused, the viewer shows colored change indicators (▲ green growth, ▼ red shrinkage, · grey abandoned) directly on settlement positions.

### What was built this session (Phase 23 — Surface Depth)

1. **Explore mode batch rendering** — Ported the span-based `addstr()` pattern from viewer's `_render_map` to explore's `_draw_map`. Also replaced the O(n) per-tile adventure zone scan with a pre-built `zone_map` dict for O(1) lookups. Same behavioral output, dramatically fewer curses API calls.

2. **Speeds beyond zoom** — Added Decade (128x), Century (256x), and Epoch (512x) speed levels to the viewer. Updated the speed bar denominator to use the new max (511.875 instead of 63.875) and the speed cap from 64.0 to 512.0. Pressing `+` now cycles through: Crawl → Slow → Walk → Flow → Trot → Run → Dash → Fly → Blink → Zoom → Decade → Century → Epoch.

3. **Context-sensitive viewer overlays** — When the viewer is paused and a year-diff is available, colored indicators appear directly on settlement positions on the map: green ▲ for settlements that grew, red ▼ for those that shrank, and grey · for abandoned ones. The overlay only draws for settlements visible within the map area.

### What to tackle next

- **Trade route animation.** Routes currently render as static lines. Animating goods flowing along routes in the viewer (a moving dot per route) would make the economy feel alive.
- **Embody mode TUI.** Embody currently runs as a scrolling terminal conversation. A curses TUI for embody — with stats sidebar, event log, action menu — would match the rest of the tooling.
- **Seasonal palette — deeper variation.** The 4-season shift works but is subtle. Could add snowfall accumulation in winter, greening transitions in spring.
- **Pause-on-event.** The viewer could auto-pause on significant events (cataclysm, founding, war declaration) so you don't blink and miss them.
