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

1. **TUI sim reset/rewind** — Changed `r` keybinding from "refresh map" to "reset simulation". Pressing `r` now pauses the sim, rewinds to year 0, clears the event log, and restores the original world map. Includes a new `action_reset` method that fully reinitializes sim state.

2. **Embodied play persistence** — Added `to_dict()` / `from_dict()` to `PlayerCharacter`, `save_character()` / `load_character()` functions, and auto-save after each year advance. Character saves go to `wyrd-{seed}-char.json` and auto-load on subsequent `wyrd embody` runs. Added `--no-load-save` flag to start fresh. On death, the save file is removed.

3. **4 new tests** for character persistence (round-trip, save/load, nonexistent load, full field preservation). **560 tests pass** (up from 556).

### Phase 17 checklist (from PLAN.md)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Live map animation | 🔲 | Partial: tiles flash on growth/shrink/founding/abandonment in curses viewer |
| 2 | Textual-based TUI | 🟡 | Sim-aware: controls, event log, live stats, year-diff, **reset/rewind (r)** |
| 3 | Embodied play mode | 🟡 | MVP + **save/load persistence**, auto-save, `--no-load-save` flag |
| 4 | Event-driven notifications | 🔲 | Not started |
| 5 | Year-diff view | ✅ | Done |
| 6 | Multi-generational play | 🔲 | Not started |

### What to tackle next

Highest-impact remaining items:

1. **Item 1: Live map animation** — The curses viewer has flash-tile animation. The Textual TUI should also animate: tile-by-tile settlement growth, fading transitions, bloom effects. Could use a `set_timer` pattern to animate tile discovery/growth over multiple frames.

2. **Item 3 → 🟢** — Embodied play still needs: better event integration (events that specifically address the player), player death more meaningful (last words, legacy), and the start of multi-generational play (Item 6).

3. **Item 4: Event-driven notifications** — Sim events arrive as interactive prompts. "A stranger arrives at your door. Let them in? y/n" — this is the biggest missing piece for embodied play to feel alive.
