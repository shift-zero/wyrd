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

**Phase 19 — Human-First UX. 794 (+2 new monthly sim tests) tests pass.** Added persistent status bars to both the gateway and viewer TUIs, improved world picker layout with column alignment, and implemented a full sub-year month-tick middleware (`_simulate_month_tick`, `simulate_years_monthly`, `run_monthly_simulation`) that distributes population/food/event changes smoothly across 12 months per year while keeping seed determinism.

### What was done this session: Phase 19 — Human-First UX (items 1, 2, 3)

1. **Gateway TUI overhaul** (`gateway.py`) — Replaced old footer with a persistent status bar showing current mode (world seed/session), population of selected world, and context-aware key hints that change when no worlds exist. World list reworked with column-aligned display (Seed, Size, Population, Settlements, Features), section headers, and scrollable with `▸` selection markers.

2. **Viewer TUI cleanup** (`viewer.py`) — Replaced header/footer with clean two-bar layout: header shows wyrd title + mode (▶ RUNNING/⏸ PAUSED) + year + speed on one line, and a persistent bottom status bar shows mode indicator, seed, year progress, speed, and context-sensitive key hints (different hints for paused vs running). Moved keybinds from the old scattered header to the status bar so they're always visible.

3. **Sub-year time tick middleware** (`sim.py`) — Added `month` field to `SimEvent`, `sub_year_month` to `SimState`, and a complete `_simulate_month_tick` function that distributes ~1/24 of yearly population/food/health/prosperity changes per month (months 0-10) with the remainder (~0.54) in month 11. Year-end subsystems (economy, faction_sim, cataclysm, era transitions, settlement founding/abandonment, wars) fire only on month 11. Added `simulate_years_monthly` (12x month ticks per year) and `run_monthly_simulation` (full SimResult wrapper). The monthly sim is seed-deterministic (verified with dedicated test).

### What to tackle next — Phase 19: Human-First UX (remaining)

| # | What | Status |
|---|------|--------|
| 1 | TUI polish — Clean layouts, discoverable keybinds, persistent help/status | ✅ |
| 2 | Sub-year sim ticks — Months as base unit, economy/faction/event adapt | ✅ |
| 3 | Variable speed — Smooth control from slow (days) to fast (decades) | 🔲 |
| 4 | Embody uses sub-year — Travel takes days, rest takes weeks | 🔲 |
| 5 | Seasonal rendering — Map palette shifts subtly as months pass | 🔲 |
