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

### Current state (2026-07-31)

### Multi-world save/load in embody

**Character saves moved to `saves/` directory:** Previously, character saves were written directly to CWD as `wyrd-{seed}-char.json`, cluttering the working directory. Now:

- Saves go to `saves/wyrd-{seed}-char.json` (auto-creates `saves/` dir)
- Automatic migration from old path — `load_character()` checks old CWD first, moves the file to `saves/`
- Gateway's `scan_worlds()` filters out `-char.json` files from the world list (they were being picked up by `wyrd-*.json` glob and silently failing JSON parse)
- Gateway `has_save` badge checks both `saves/` and old CWD locations
- `saves/` added to `.gitignore`

**Character manager in gateway (`C` key):** Pressing `C` in the gateway opens a character management overlay showing:
- Character name, profession, age, year, location, gold, and health bar
- `r` key to reset/delete the character save
- Esc to cancel
- Shows "no save" message for worlds without a character

**Detail card character info:** The world detail panel (right side of gateway) now shows saved character info when a character exists — name, profession, age, year, gold, and health bar.

Tests: 799+ passed, no regressions.

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

### What to tackle next — wyrd is a single-user MUD

**👑 `wyrd` → drop in. No menu, no picker, no gateway. You're in a room.**

Like Minecraft. You run `wyrd`, it generates a world from a seed (or resumes your last one), and you're standing in a room. A character with skills, health, inventory. The world has deep history — civilizations, ruins, wars, trade routes — but you have to *walk around and discover it*. Every seed is a completely different experience.

**No more world picker.** The Textual WorldPicker gateway was a good first step but even that's too much UI. `wyrd` with no args should drop you straight into the game. If you want a new world, you type `wyrd --seed 42` or it auto-generates one fresh.

**What dies (all of it):**
- `gateway.py`, `viewer.py`, `explore.py`, `tui.py`, `embody_tui.py` — curses dead
- `tui_gateway.py` — even the Textual world picker dies. No gateway.
- `__main__.py` stripped — `wyrd` → MUD, `wyrd --seed N` → specific seed. That's it.
- `serve.py`, `export_*.py`, `query.py`, `ask.py`, `branch.py` — all dead

**What lives:**
- All engine modules: `world.py`, `generate.py`, `sim.py`, `economy.py`, `faction*.py`, `cataclysm.py`, `embody.py`, `shop.py`, `bestiary.py`, `magic.py`, `religion.py`, `narrative.py`, `lore.py`, `chronicles.py`, `serialize.py`, `render.py`, `adventure.py`

**What gets built:**

| # | What | Verifiable |
|---|------|------------|
| 1 🔲 | Strip everything — CLI, curses, exporters, web, gateway | `wyrd` drops into Textual MUD. No subcommands exist. |
| 2 🔲 | Textual MUD screen — room view, event log, command input, stats sidebar | See the room you're in, its description, exits, contents |
| 3 🔲 | Room system — WFC generates room layouts per-settlement. Each room has exits, description, contents, NPCs | Move n/s/e/w between rooms in a settlement. Walk outside to world map. |
| 4 🔲 | Command parser — `look`, `get`, `use`, `talk`, `n/s/e/w`, `inventory` | `look` shows room; `get sword` picks it up; `use bandage` heals |
| 5 🔲 | World map as explorable space — walk between settlements through wilderness tiles | Walk north from town → forest path → another settlement days away |
| 6 🔲 | Discovery — ruins, dungeons, lairs exist on the map; you find them by exploring | Walk into a ruin hex and enter its procedurally generated dungeon rooms |
| 7 🔲 | Background sim ticks while you play | Leave town for a week and come back to find it changed; news arrives |
| 8 🔲 | Gameplay loop — survive, explore, trade, fight, level | Clear progression from starter gear to exploring dangerous ruins |

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

### Completed this session (2026-08-01)

#### Bug fixes
- **Viewer map height fixed.** Layout math was `events_h = max(3, h - 7 - 2)` which ate nearly the full terminal height, leaving `map_h` stuck at 1 row. Now events_h is capped at 1/3 of available height, giving the map at least 4+ rows on any terminal ≥ 10 tall.
- **Viewer CPU burn fixed.** When paused, the main loop had `time.sleep(0.008)` only in the `not paused` branch — the paused branch spin-looped at 100% CPU. Added `time.sleep(0.033)` (~30fps) in the paused branch.
- **Play mode crash protected.** Gateway's `p` (embodied play) and `s` (simulation) handlers do `curses.endwin()` / `initscr()` dance. Wrapped `embody_tui_play` call and `_init_colors()` restart in try/except to survive terminal state issues on rapid endwin/initscr cycles.

#### Delete worlds from gateway
- Press `Del` on a selected world → confirmation popup → second `Del` confirms and deletes the world file, its character save, and sim file. Rescans world list and clears session/detail caches.
- `Del` key registered in status bar hints and help overlay.

#### Tests: 799 passed, no regressions.

#### Multi-world save/load in embody ✅
- Character saves moved to `saves/` directory — no more CWD clutter
- `_save_path()` now points to `saves/wyrd-{seed}-char.json`
- Automatic migration: `load_character()` migrates old CWD saves to `saves/`
- `scan_worlds()` filters out `-char.json` from world list glob
- Gateway `has_save` badge checks both `saves/` and old CWD

#### Character manager in gateway (`C` key)
- Overlay shows character name, profession, age, year, location, gold, health bar
- `r` key to delete character save; Esc to cancel
- World detail card shows saved character info inline
- Help screen updated with `C` binding

#### Fixes
- Gateway world list no longer silently ignores character saves as corrupt world files
- `saves/` added to `.gitignore`

### Completed this session (2026-08-03)

#### Textual gateway (WorldPicker) — first major Textual migration step

The curses gateway (`gateway.py`, 1755 lines) is now complemented by a Textual-based replacement (`tui_gateway.py`):

- **WorldPicker screen** — reactive, mouse-friendly world list with auto-scanning
- **Sorting** — press Tab to cycle seed→population→name with `↑↓` arrows on sort indicator
- **Detail card** — right-panel with mini-ASCII map (24×6 terrain preview with ANSI colors), settlement stats, region breakdown, feature badges (lore/narrative/chronicles/magic/save/sim), and character info
- **Overlay modals** — character manager (`C`), delete confirmation (Del), generate prompt (`n`/`G`), help screen (`?`)
- **Dispatch actions** — View (Enter → Textual SimScreen), Explore (`e`), Viewer (`v`), Play/embody (`p`) — all launch via `App.exit()` for clean lifecycle management
- **CLI integration** — `wyrd` (no args) launches Textual gateway by default (falls back to curses if Textual missing); `wyrd tui --gateway` / `-G` for explicit launch
- **Tests** — 8 new tests in `test_tui.py` covering imports, mini-map rendering, detail text building, sorting, overlay instantiation, and launch entry point
- **799 tests pass, no regressions.**
