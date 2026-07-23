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

1. **Live map animation (Item 1 → ✅)** — The Textual TUI now shows tile animations during simulation: settlements that grew flash green ↑, shrinking settlements flash red ↓, newly founded settlements glow gold ✦, abandoned settlements show dim ✗. All auto-fade to normal after 1.5s. Animation legend appears automatically during overlay. Uses `flash_overlays()` on `SimMapWidget` with `set_timer` auto-revert.

### Phase 17 checklist (from PLAN.md)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Live map animation | ✅ | Tiles show green/red/gold/dim indicators with 1.5s fade; `_render_map_with_overlays()` for overlay-aware map rendering |
| 2 | Textual-based TUI | 🟡 | Sim-aware: controls, event log, live stats, year-diff, reset |
| 3 | Embodied play mode | ✅ | MVP + save/load + legacy tracking + death epilogue |
| 4 | Event-driven notifications | ✅ | 7 scenario types, 95 tests |
| 5 | Year-diff view | ✅ | Done |
| 6 | Multi-generational play | 🟡 | Heir generation on death, inheritance, lineage tracking |

### What to tackle next

1. **Item 2 → ✅** — The Textual TUI works but needs polish: better layout, persistent keybind help bar, smoother sim controls, maybe a world picker screen on launch.

2. **Item 6 → ✅** — Multi-generational needs: family tree tracking, persistent lineage across sessions, more dramatic generational mechanics (inbreeding, dynastic splits, family feuds).

3. **Start thinking about post-Phase-17.** What comes after Living Worlds? Maybe multi-world federations, faction diplomacy web UI, or a REST API for external tools.
