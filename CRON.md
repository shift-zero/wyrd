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

**Phase 18 (Depth & Quality) in progress. 794 tests pass — 36 new embody depth tests. Embodied play: skill system, reputation, 3 new scenarios.**

### What was done this session
1. **Skill system (5 skills)** — Added `skills` and `skill_xp` fields to `PlayerCharacter`:
   - Combat, Trade, Persuasion, Survival, Crafting — each levels 1-10
   - Triangular XP thresholds (level 2=15, level 3=45, level 4=90, level 5=150…)
   - `_gain_skill_xp()` auto-levels and prints level-up messages
   - `_skill_bonus()` returns +5% per level over 1 for outcome improvement
   - Skills shown in status screen (`s` command)
   - Skills persist through save/load and multi-generational inheritance (2/3 of parent's XP)

2. **Reputation system** — Per-settlement reputation (-10 to +10):
   - `_change_reputation()` modifies standing and returns flavor text
   - Affects: sheltering strangers (+1), bandit fighting (+2), festival organizing (+2), religious joining (+1), robbing (-2)
   - Reputation shown in status screen, persists through save/load
   - Heirs inherit partial reputation

3. **3 new interactive event scenarios** (10 total now):
   - **🗡 Bandit raid** — Fight/pay/hide. Higher chance during war. Skills matter for fight outcome.
   - **🎉 Festival** — Join/organize/skip. Higher during prosperity. Organize gives crafting XP.
   - **🐉 Monster hunt** — Hunt/hire/ignore. Requires world bestiary with aggressive creatures. Uses combat + survival skills.

4. **Skill integration in all existing scenarios** — Every existing scenario now grants skill XP and uses skill bonuses:
   - Stranger: persuasion affects item drop chance
   - War: combat skill improves survival (0.6 base + up to 0.45 bonus)
   - Merchant: trade skill shifts profit pool toward gains
   - Discovery: survival skill unlocks rare items + more gold
   - Religious: persuasion increases health restoration
   - Exodus: survival + crafting XP for different choices

5. **36 new tests** — Skills (12), Reputation (8), Bandit (6), Festival (4), Monster Hunt (6)

### What to tackle next — Phase 18 remaining candidates
| # | What | Status |
|---|------|--------|
| 1 | Embodied play depth (skills ✅, scenarios ✅, reputation ✅) | 🟢 |
| 2 | TUI polish | 🔲 |
| 3 | World generation variety | 🔲 |
| 4 | REST API — v1 complete | 🟢 |
| 5 | Bestiary depth — done | 🟢 |
| 6 | Multi-world interaction | 🔲 |
