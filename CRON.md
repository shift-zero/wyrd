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

**All 16 phases complete. Phase 17 in progress.**

### What was built this session

1. **Meaningful death & legacy tracking (Item 3 → 🟢)** — Death now shows a Life Ledger: gold earned/spent, deeds accomplished, places visited, witnessed events. Player character tracks `legacy_events`, `settlements_visited`, `total_gold_earned`, `total_gold_spent`, and `deeds` across their lifetime. Interactive choices record deeds (fought in war, helped the sick, explored ruins, etc.). Last words seeded from character identity. Status command shows deeds and places.

2. **Multi-generational foundation (Item 6 → 🟡)** — On death, player is prompted: "Continue as an heir?" Heir inherits the parent's surname, partial gold (50%), up to 3 inventory items, and settlement knowledge. Parent tracked in `parent_name` field. Heir's epilogue shows parent lineage. Recursive `embody_play()` preserves world state across generations.

3. **14 new tests** for legacy tracking (event recording, deduplication, serialization round-trip), epilogue rendering (deeds, events, parent name, last words, visited settlements), all passing.

**625 total tests pass** (up from 560).

### Phase 17 checklist (from PLAN.md)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Live map animation | 🔲 | Partial: tiles flash on growth/shrink in curses viewer |
| 2 | Textual-based TUI | 🟡 | Sim-aware: controls, event log, live stats, year-diff, reset |
| 3 | Embodied play mode | ✅ | MVP + save/load + legacy tracking + death epilogue |
| 4 | Event-driven notifications | ✅ | 7 scenario types, 95 tests |
| 5 | Year-diff view | ✅ | Done |
| 6 | Multi-generational play | 🟡 | Heir generation on death, inheritance, lineage tracking |

### What to tackle next

1. **Item 1: Live map animation** — The Textual TUI should animate tile changes using `set_timer` patterns. Tile-by-tile settlement growth, fading transitions, founding effects. This is the highest-visibility remaining item.

2. **Item 2 → 🟢** — The Textual TUI works but may need polish: better layout, persistent keybind help bar, smoother sim controls.

3. **Item 6 → 🟢** — Multi-generational needs: family tree tracking, persistent lineage across sessions, more dramatic generational mechanics (inbreeding, dynastic splits, family feuds).
