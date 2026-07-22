# Session: 2026-07-22

## What was built
- **Phase 6 complete** — All 7 items done. 215 tests pass.
- **Phase 7.1: Interactive sim viewer** (`src/viewer.py`)
  - `wyrd view --seed 42 --years 300` launches curses viewer
  - Map shows evolving settlements (active yellow, new green, abandoned dim)
  - Pause/resume (Space), speed (+/-), step forward (→)
  - Population chart overlay (p)
  - Event log with color-coded entries
  - 7 tests in `tests/test_viewer.py`
- Pushed 3 commits to master

## Next: Phase 7.2 — Named Character Integration 🎭
The sim events (war, founding, discovery, plague) currently reference only settlement names. They should reference **actual narrative characters** — leaders, heroes, generals, founders.

### Implementation plan:
1. **`sim.py`**: Import `Narrative` characters into the tick loop. When generating events:
   - `founding`: Pick a character from the source settlement as founder. Add "under {name}'s leadership" to description
   - `war`: Pick commanders from each warring settlement. Add "led by {name} against {name2}"
   - `discovery`: Assign to a named explorer/scholar character
   - `plague/famine`: Reference a known healer or leader who tried/failed to help

2. **`narrative.py`**: Add a helper `pick_character(settlement_name, narrative, role_filter=None)` that finds a character from a settlement by occupation/role

3. **Character data model**: Add a `home_settlement` field if not already present on Character (check first — it exists from Phase 4)

4. **Tests**: Update `test_sim.py` to verify character references in events when narrative exists

### Files to modify:
- `src/sim.py` — `_simulate_tick()` signature may need `narrative` param
- `src/narrative.py` — add `pick_character()` helper (or just put it in sim)
- `tests/test_sim.py` — character reference tests
- `src/run.py` — pass narrative through

## Phase 7.3 (after 7.2):
Character-driven founding events — new settlements are founded *by* named characters who then become their leaders.

## Scratch file cleanup
The repo has lingering `_test_polish.py`, `_test_polish_full.py`, `_test_ttrpg.py` in root. These are harmless but should be removed and gitignored. The .gitignore now has `_test_*.py` and `_test_*.json.gz` patterns.

## Architecture notes
- `viewer.py` imports `_simulate_tick` from `sim.py` (same-package, works fine)
- Map layout in viewer: header(0) → stats(1) → map(2+) → events → footer(last)
- `apply_sim_state_to_world()` creates a deepcopy with evolved settlements
- `initialize_sim_state()` converts World settlements → SettlementSnapshots
- 215 total tests: `python -m pytest tests/ -q`
