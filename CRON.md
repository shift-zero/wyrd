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

**Phase 18 depth work ongoing. 794 tests pass.** Added swamp/desert terrain types with full ecosystem integration — economy, bestiary, lore, adventure zones, rendering, and docs. Fixed pre-existing serve.py routing bug.

### What was done this session: Phase 18 — World Generation Variety

1. **Swamp terrain** (`≡`, color 64) — High-moisture lowlands (9-20% of map), settlements avoid swamps. New lore features (Bog, Marsh, Fen), new bestiary creatures (Bog Wraith, Hydra swamp variety, Blight Treant), new caravansary economy type for desert settlements.

2. **Desert terrain** (`:`, color 179) — Very-low-moisture midlands (0-0.3% of map, ~60% of seeds). New lore features (Wastes, Dunes, Barrens), new bestiary creatures (Sun Elemental, Sphinx, Dust Devil), adventure zones in deserts (dungeons, caves, ruins, towers).

3. **Bestiary integration** — `_get_habitats()` now scans terrain for swamp/desert tiles and adds them as habitats. Creature templates, naming patterns, and type biases for both habitats.

4. **Economy: caravansary type** — Desert settlements get a "caravansary" economy (spices, salt). New icon 🧭, color 179, trade goods, specialization titles.

5. **Bugfix: serve.py routing** — `/world/{seed}/events` route was broken (`parts[1]` IndexError due to wrong `len(parts) >= 3` guard). Fixed to check `len(parts) >= 2` for events endpoint.

6. **Docs** — Updated world.md (terrain table), generation.md (classification thresholds with swamp/desert).

### What to tackle next — Phase 19: Human-First UX

| # | What | Status |
|---|------|--------|
| 1 | TUI polish — Clean layouts, discoverable keybinds, persistent help/status | 🔲 |
| 2 | Sub-year sim ticks — Months as base unit, economy/faction/event adapt | 🔲 |
| 3 | Variable speed — Smooth control from slow (days) to fast (decades) | 🔲 |
| 4 | Embody uses sub-year — Travel takes days, rest takes weeks | 🔲 |
| 5 | Seasonal rendering — Map palette shifts subtly as months pass | 🔲 |
