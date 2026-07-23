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

## Current state (2026-07-24)

### Phase 19+ — Deeper Seasonal Palette + Heir Confirmation + Mobile Feedback

Completed this session:

1. **Deeper seasonal palette in viewer** — Temperature factor computed per-tile from latitude + elevation + seasonal baseline. Three temperature-zone effects:
   - Winter snow accumulation: tiles with temp_factor < 0.2 (high elevation, polar) render as snow overlay instead of normal terrain
   - Autumn warm zone: forest on low-elevation warm tiles turns deep crimson (color 124)
   - Spring warm zone: grass on equatorial/warm tiles gets brilliant lime green (color 46)
   - 8 new color pairs (61-68) for temperature-zone variant rendering
   - Precomputed temp cache per frame for performance

2. **Heir confirmation overlay** — When dying in embody TUI, pressing `y` now shows a full preview overlay with:
   - Heir name, profession, age, gold, location
   - Skill bars for all 5 skills with inherited levels
   - Inherited items list
   - Press `y` again to confirm, `n` to go back
   - Uses new `heir_confirm` epilogue_mode state

3. **Mobile threshold feedback** — Brief status message when terminal crosses the 100-column boundary:
   - "Compact mode — terminal 89 cols < 100" when shrinking
   - "Full mode — terminal 108 cols ≥ 100" when expanding
   - Last state tracked via function attribute (`embody_tui_play._last_compact`)

### What to tackle next
- Explore alternative renderers (SDL, terminal graphic modes)
- Trade route map in gateway — full visualization of route network
- TTRPG export polish — add faction and zone sections to campaign JSON
