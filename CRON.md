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

**Phase 20 — Living Gazetteer complete. All 6 checklist items ✅.** 794+ tests pass.

### What was built this session (Phase 20 — Living Gazetteer)

1. **Settlement inspection in viewer** — Added cursor-driven settlement navigation (`[` and `]` keys) that cycles through active settlements on the map. Press `i` to open a detail popup showing: type, region, population, prosperity bar (█░), health bar, food stores, economy type, religion, and founding year. Cursor shows as reverse-video highlight. Status bar and help updated.

2. **Gazetteer mode in gateway** — Press `G` in the gateway to open a unified entity browser. Collects all 7 entity types: settlements, characters, factions, faction relationships, creatures (bestiary), adventure zones, and deities (pantheon). Filter by type with number keys [1] All [2] S [3] C [4] F [5] B [6] Z [7] D. Up/down navigation, Enter for detail popup with full stats. Persistent filter bar and status bar.

3. **`wyrd lookup <name>` CLI command** — New `src/lookup.py` module with fuzzy-matching engine that scores results by: exact match (1.0), prefix match (0.9), word overlap, sequence similarity, and substring. Searches across settlements, regions, characters (first/surname/full), factions, creatures, zones, and deities. Returns top 8 results with score bars. ANSI-colored output with type icons.

### What to tackle next — Phase 21: ???
