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

**Phase 19 — Human-First UX complete. All 6 checklist items ✅.** 800+ tests pass.

### What was done this session: Phase 19 (items 4, 5, 6)

1. **Seasonal rendering (item 6)** — `viewer.py` now has 4 complete seasonal color palettes (Spring: fresh greens/cyan, Summer: warm sun-bleached, Autumn: russet/orange/brown, Winter: frosty blue/grey). The `_season_name()` and `_season_cp()` functions map month (0-11) to season, and all terrain rendering uses seasonal variants. The header and status bar show current season. Even with year-level ticks, `cur_month = (year * 3) % 12` cycles through all 4 seasons every 4 years.

2. **Variable speed control (item 4)** — The viewer now ticks at month-level granularity. `_simulate_month_tick` replaces `_simulate_tick` in both auto-advance and step modes. Speed values are labeled with qualitative descriptors (Crawl→Slow→Walk→Flow→Trot→Run→Dash→Fly→Blink→Zoom). A visual speed bar (`████░░░░`) in the stats line shows speed level. The accumulator tracks months (speed * 12 months/sec) for smooth progression from ~1.5 months/sec at 0.125x to 768 months/sec at 64x.

3. **Embody sub-year ticks (item 5)** — `PlayerCharacter` gains a `month` field (0-11). `_advance_year` replaced by `_advance_time(char, months=N)` which ticks N months via `_simulate_month_tick`, increments age on birthday (month rollover), and applies health decay at year boundaries. Travel takes 1-2 months instead of a full year. Prompt offers `[n]ext year`, `[1m] one month`, `[1w] one week` commands. Status shows current season and month number.

### What to tackle next — Phase 19: Human-First UX (remaining)

| # | What | Status |
|---|------|--------|
| 1 | TUI polish — Clean layouts, discoverable keybinds, persistent help/status | ✅ |
| 2 | Sub-year sim ticks — Months as base unit, economy/faction/event adapt | ✅ |
| 3 | Variable speed — Smooth control from slow (days) to fast (decades) | 🔲 |
| 4 | Embody uses sub-year — Travel takes days, rest takes weeks | 🔲 |
| 5 | Seasonal rendering — Map palette shifts subtly as months pass | 🔲 |
