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

### Current state (2026-07-30)

### TUI ambient mode + seasonal status bar

**Ambient mode (`a` key) in the curses TUI:** The TUI now has native ambient time flow, implemented entirely within curses — no terminal takeovers, no print-based output. Press `a` to enter ambient mode:

- Time passes automatically in ticks: 1 month (slow) or 12 months (fast)
- Space toggles between slow/fast speeds
- Auto-pauses on major events (wars, cataclysms, foundings, discoveries)
- Events logged directly into `log_lines` — full history preserved across ambient/normal transitions
- Character death during ambient mode triggers the epilogue overlay
- Any non-Space key exits ambient mode back to normal control
- Ambient overlay panel shows speed, season, year, month, health, and gold
- Status bar updated to show `[a] Ambient` keybinding
- Help overlay updated with ambient mode section

**Seasonal icons in status bar:** Spring (🌸) in green, Summer (☀) in yellow, Autumn (🍂) in cyan, Winter (❄) in dim. The right side of the status bar now shows color-coded seasonal information.

Tests: 799 passed, no regressions.

`wyrd lookup <query>` was returning false positive results for totally unrelated
queries. For example, `wyrd lookup --seed 42 "nonexistent"` returned "Fallen Bones"
and "Gwyn Longmere" because `_score()` accepted any SequenceMatcher ratio >0.4 —
and "nonexistent" shares "one" (3 chars) with "Fallen Bones" and "on" with "Gwyn
Longmere", producing ratios of 0.43 and 0.42.

**Fix:** The SequenceMatcher path now requires at least **4 contiguous matching
characters** before accepting the ratio. Short accidental trigrams (3-char matches
like "one", "ste", "the") no longer trigger false positives. Substring matching
(q in n → 0.5) and word-overlap matching are unaffected.

Verified: `wyrd lookup --seed 42 "nonexistent"` → "No results found"
Verified: `wyrd lookup --seed 42 "embervale"` → 5 correct results
Tests: 799 passed, no regressions.

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
Tests: 799 passed, no regressions.

### What to tackle next

**Ambient mode is now natively in the TUI curses loop** — no terminal takeovers needed. ✅

**Next directions (pick any):**
- Multi-world save/load in embody — world-independent character saves
- Deeper NPC relationships — faction alignment affects dialogue options
- Trade route visualization in the gateway viewer
- Embody onboarding improvements — first-time tutorial skip option
- New system: dungeon generation for point-of-interest exploration
- TUI ambient mode: add variable speed slider (like viewer's Crawl→Zoom)
- TUI ambient mode: add event count/flash indicator during fast ticks

### Completed this session (2026-07-30)

#### TUI ambient mode ($a$ key)
- Time passes automatically in ticks: 1 month (slow) or 12 months (fast)
- Space toggles between slow/fast speeds
- Auto-pauses on major events (wars, cataclysms, foundings, discoveries)
- Events logged directly into `log_lines` — full history preserved across ambient/normal transitions
- Character death during ambient mode triggers the epilogue overlay
- Any non-Space key exits ambient mode back to normal control
- Ambient overlay panel shows speed, season, year, month, health, and gold
- All implemented natively in curses — no terminal takeovers, no print-based output
- Uses `stdscr.timeout()` for non-blocking input within the curses context

#### Seasonal icons in status bar
- Spring (🌸) in green, Summer (☀) in yellow, Autumn (🍂) in cyan, Winter (❄) in dim
- Matches `_render_sidebar` seasonal color scheme
- Status bar now shows `[a] Ambient` keybinding
