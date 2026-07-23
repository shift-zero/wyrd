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

**Phase 19 — Human-First UX complete. All 6 checklist items ✅.** 796 tests pass.

### What was built this session (Phase 19 polish)

1. **Gateway embody integration** — Added `P` badge (gold, `[P]`) on worlds with saved character files (`wyrd-*-char.json`). Added `[p]` keybind in gateway to launch embodied play mode directly. Now the gateway shows "has save" status and lets you jump into your character without remembering CLI flags.

2. **Discoverability** — Updated gateway help panel and status bar to include `[p]` for embody mode. Players don't need to know `wyrd embody --seed X` exists — it's visible in the TUI.

### What to tackle next — Phase 20: Living Gazetteer & Interactive World Browser

**Thesis:** wyrd generates deep, interconnected data — settlements, characters, factions, creatures, deities, trade goods, adventure zones — but there's no unified browser. You can `wyrd factions --seed X` in the CLI, or view lore in a popup, but each dataset lives in its own silo. The trick is: use data that already exists, make it browsable from within the TUI.

| # | What | Priority |
|---|------|----------|
| 1 | **Settlement detail popup in viewer** — press `i` (inspect) on a settlement to see its stats, inhabitants, trade goods, recent events from sim | High |
| 2 | **Gazetteer mode in gateway** — press `G` to open a browsable index of everything: settlements, characters, factions, creatures, zones, deities. Filter by letter, region, type | High |
| 3 | **Character browser** — list all narrative characters, filter by region/status/alive, inline detail | Medium |
| 4 | **Faction viewer** — browse factions with their relationships, holdings, members, recent history | Medium |
| 5 | **Bestiary browser** — browse creatures by habitat/tier, view full stats, encounter table | Medium |
| 6 | `wyrd lookup <name>` — CLI quick-lookup that searches across all data types and returns the best match | Low |

### Architecture notes
- Gazetteer data is already in world fields — no new generation needed
- Settlement popup needs a mouse-enabled viewer mode or a selected-settlement cursor
- `wyrd lookup` can use the existing query.py engine with a broader search scope
