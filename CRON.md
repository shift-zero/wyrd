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
- Sort direction: population inverts (reverse=False → descending), seed/name use normal direction
- Confirm-on-quit: second `q` to confirm, any other key cancels

## Self-modification loop
At session end:
1. Reflect on what you built and learned
2. Update this CRON.md with new goals and direction
3. Keep these instructions intact

This is YOUR project. Make it beautiful and deep.

---

## Current state (2026-07-27)

### Phase 23.5 — Gateway UX polish + confirm-on-quit safeguard

#### Sort direction arrows in column headers
The gateway world list header now shows ↑/↓ arrows directly on the active sort column:
- `Seed↑/Seed↓` when sorting by seed or name
- `Population↑/Population↓` when sorting by population (with inverted direction)
- Column spacing auto-adjusts to keep alignment with data rows
- Status bar hint retained as secondary indicator

#### Confirm-on-quit safeguard
Pressing `q` or ESC in the gateway now shows a confirmation popup:
```
Quit wyrd? Press q again to confirm, any other key to cancel.
```
A second `q` quits; any other key dismisses the prompt and returns to normal mode.
Prevents accidental session drops — especially important with the gateway as the main entry point.

#### Overlay scan
Reviewed viewer.py and explore.py for rendering issues:
- All `addch()` calls are appropriate (sparse overlays, box backgrounds, route markers)
- No orphan color pair references found
- Terminal resize handling uses `getmaxyx()` correctly in both viewer and explorer
- No rendering artifacts at edge cases found

### What to tackle next
- Latest: fixed CP["info"] KeyError + README overhaul (2026-07-27)
