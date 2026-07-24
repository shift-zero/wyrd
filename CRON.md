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
Tests: 551 passed, no regressions in core modules (embody, generate, lore,
narrative, sim, faction, economy, magic, religion, chronicles, query,
serialize, bestiary, gateway, explorer, viewer, shop).

### What to tackle next

**All three remaining embody targets are now complete!** ✅

1. ✅ **NPC interaction** — `t` key to talk to nearby characters with
   personality-driven dialogue, rumors, and skill XP rewards
2. ✅ **Quest log & milestones** — `g` key shows available quests, skill
   progress bars, deeds, reputation, and life stats
3. ✅ **Ambient time flow** — `a` key enters ambient mode, Space toggles
   slow/fast speed, auto-pauses on major events

**Next directions (pick any):**
- Multi-world save/load in embody — world-independent character saves
- Deeper NPC relationships — faction alignment affects dialogue options
- Trade route visualization in the gateway viewer
- Embody event log persistence — keep events across ambient mode sessions
- Embody onboarding improvements — first-time tutorial skip option
- Visual polish: seasonal effects in embody status line
- New system: dungeon generation for point-of-interest exploration

### Completed this session (2026-07-24)

#### NPC interaction (`t` key)
- Press `t` to see nearby narrative characters in your current settlement
- Characters shown with name, occupation, and personality traits
- Dialogue varies by personality: warm NPCs are friendly, cool ones are gruff
- Three response options: ask about work (persuasion XP), ask about area
  (survival XP), or say goodbye
- NPCs share flavorful rumors about the world
- Small reputation (+1) and gold (0-2) gain for chatting
- Travel moved to `r` (roam) to free `t` for talk

#### Quest log & milestones (`g` key)
- Shows available quests from narrative engine, filtered to current settlement
- Each quest shows: name, description, difficulty (color-coded), and rewards
- Skill XP bars with filled/empty block visualization per skill
- Deeds & milestones tracker (up to 10 shown, with overflow indicator)
- Reputation by settlement with color-coded +/- values
- Life stats: age, year, gold earned, settlements visited, legacy events

#### Ambient time flow (`a` key)
- Time passes automatically in ticks (1.5s at slow speed)
- `Space` toggles between Slow (1 month/tick) and Fast (12 months/tick)
- Auto-pauses on major events (war, founding, cataclysm, discovery)
- Inline status bar: season, year, month, settlement, health, gold
- Any non-Space key exits back to normal mode
- ESC/q quits directly from ambient mode
- Uses raw terminal mode with `tty.setraw()` for non-blocking input
- Falls back gracefully on errors (restores terminal settings)
