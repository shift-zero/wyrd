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

### Phase 19 polish — Gateway TUI bugfix

Fixed a visual bug where status messages in the gateway were invisible — rendered at the same line as the persistent status bar (h-3) which always overwrote them.

Changes:
1. **Moved status message to h-2, status bar to h-1** — status messages (e.g. "✅ Generated wyrd #42") now appear briefly above the persistent status bar before fading.
2. **Recovered vertical space** — updated `max_visible` from h-5 to h-3 and detail panel height from h-3 to h-1, giving the world list and mini-map more room.
3. **All 799 tests pass.**

### What to tackle next
- Explore alternative renderers (SDL, terminal graphic modes) — biggest open item
- Trade route map in gateway — full visualization of route network (render_trade_route_map exists but is terminal-only; consider curses inline overlay on detail card mini-map)
- TTRPG export polish — add faction and zone sections to campaign JSON (both already present; verify completeness against world data model)  
- Look for remaining visual bugs: check viewer, explorer, and embody TUI for similar overlay issues
