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

**Phase 21 — Living Gateway complete. All 3 checklist items ✅.** 796+ tests pass.

### What was built this session (Phase 21 — Living Gateway)

1. **World detail card & mini-map** — When a world is selected in the gateway, a detail card appears to the right of the list showing a scaled ASCII terrain map (colored by biome using 12 terrain color pairs), key stats (settlements, population, regions), and feature badges (Lore, Narrative, Magic, Pantheon, Factions, Bestiary, Adventure Zones). The map is lazily loaded and cached per world path, so navigation between worlds is snappy.

2. **Interactive world list** — Press **Tab** to cycle the sort key through seed → population → name. The list reorders immediately. Current sort key is shown in the status bar (`[Tab] sort:seed`).

3. **Compact splash** — The full ASCII art splash is shown only when no worlds exist. Once worlds are detected (even one), it collapses to just the tagline "generative fantasy sandbox". This frees ~10 lines for the world list and detail card, making the gateway feel less cramped.

### What to tackle next — Phase 22: Deepening the Surface
