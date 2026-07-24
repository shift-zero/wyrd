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

## Current state (2026-07-28)

### Lookup false-positive bug fix

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
- No rendering artifacts at edge cases found

### What to tackle next

**🚨 PRIORITY SHIFT: Embody is now the primary experience.** The gateway, viewer, and generation CLI support it — embody is the main mode users interact with.

**User feedback on embody (critical — fix before adding anything new):**

1. ✅ **No onboarding** — dropped in with skills, gold, health, no idea what anything means. Need a welcome screen explaining your character, location, and first steps. *(Fixed: welcome overlay on character creation)*
2. ✅ **Text gets truncated** — long event descriptions cut off mid-sentence in the event log. *(Fixed: word-wrapped event log)*
3. ✅ **No map** — can't see where you are in the world. Need mini-map overlay showing player position, nearby terrain, and known settlements. *(Fixed: `v` key minimap)*
4. ✅ **Health/gold/family opaque** — what damages health? What's gold for? Heir system exists but no family visible while alive. *(Fixed: `i` key info panel)*
5. ~~**No NPC interaction**~~ — narrative engine generates characters but you can't talk to anyone. Need `t` key to talk to nearby NPCs (leaders, merchants, strangers).
6. ~~**No clear goals**~~ — skills exist but why level them? What's the progression? Need visible milestones, a quest system, or reputation unlocks.
7. ~~**Time doesn't flow ambiently**~~ — pressing keys to pass time feels mechanical. Need idle time flow (hours/days pass slowly), `Space` to speed up, auto-pause on events.

**Remaining embody targets:**

- **No NPC interaction** — narrative engine generates characters but you can't talk. Need `t` to talk to nearby characters.
- **No clear goals** — skills exist but why level them? Need visible milestones, quest system, or reputation unlocks.
- **Time doesn't flow ambiently** — pressing keys feels mechanical. Need idle time flow, `Space` to speed up.

### Completed this session (2026-07-29)

#### Word-wrapped event log
Event descriptions were truncated at 70-80 characters (lines 1266, 107, 493),
cutting off mid-sentence. Added `_wrap_text()` function that splits text at word
boundaries, and rewired `_render_event_log()` and `_add_events_to_log()` to use it.
Lines now flow naturally across multiple visual lines. Scroll indicator and
scrolling logic preserved.

#### Welcome/onboarding overlay
New characters (not loaded from save) now see a full-screen welcome overlay
explaining their character, what health/gold/skills mean, first steps (n, 1, t, m, v),
and the philosophy of the wyrd. Dismissed with any keypress. Skipped for loaded saves.

#### Info panel (`i` key)
Press `i` to see an explanation of health (0-100, how it depletes/recovers),
gold (earning, spending, inheritance), skills (5 types, XP system),
deeds & legacy (permanent achievements, passed to heirs),
and heir system (inherits half gold, partial skills, some inventory).

#### Mini-map overlay (`v` key)
Press `v` to see an 11×21 terrain minimap centered on the player's settlement.
Shows terrain characters/colors matching the explorer/viewer scheme, other
settlements as gold ● markers, and player position as a green ☺. Includes
compass (N↑) and legend. Uses dedicated color pairs 21-31 to avoid conflicts
with the UI color palette.

#### Documentation
Created `docs/embody.md` documenting embody mode, TUI layout, keybindings,
character systems, the new overlays, and minimap. Added to AGENTS.md doc map.

Tests: 799 passed, no regressions.

#### Viewer infinite mode fix
Viewer was hardcoded to 100 years (`view_simulation(world, 100, 0.3)` in gateway,
`num_years: int = 100` default in viewer.py). Changed default to `None` (infinite)
and gateway passes `None`. Loop condition, header display, status bar, and step-forward
logic all handle `None` via `(years is None or cur_year < years)` guard. Displays
`∞` in the header/status bar year counter for infinite runs.
