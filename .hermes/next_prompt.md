# Session Prompt — 2026-07-24

## Current State
- **224 tests pass** (up from 215).
- **Phase 6 complete** — all 7 items done (TTRPG export, compact sim, snapshot-aware HTML, pause-and-inspect).
- **Phase 7 progress**: 2/6 items done.

## What was built last session (2026-07-23)
### Phase 7 Item 2 ✅ — Named character integration in sim events
Sim events now reference actual narrative engine characters:
- `_select_named_character(rng, characters, settlement, region, event_type)` picks a relevant character using a role map (e.g., war → soldier/warlord, plague → healer/herbalist)
- `_describe_with_character(base, char_name, template)` appends occupation-flavoured notes
- `SimState.character_status` tracks "alive"/"dead" per character (ready for Phase 7 Item 5)
- All event types enriched: plague, famine, war, founding, abandonment, prosperity, trade_boom
- Character selection is seed-deterministic and prefers settlement-local NPCs
- CLI passes `world.narrative.characters` to `run_simulation()`

### Key files modified
- `src/sim.py` — new helpers + enriched event descriptions in `_simulate_tick`
- `tests/test_sim.py` — 12 new tests (character selection, edge cases, determinism)
- `src/__main__.py` — passes narrative characters to simulation
- `PLAN.md` — Item 2 marked ✅

## Next session priority: Phase 7 Item 3 — Character-driven founding events

**Brief**: When a new settlement is founded in the sim, the named character who "leads the expedition" should become the settlement's founder/leader. This means:
1. The Character's `home_settlement` should update to the new settlement
2. The new settlement's `founded_year` should be set and tracked
3. The founder character should get an updated backstory snippet reflecting their role
4. Migration events should be tied to character motivations/backstories

### Implementation approach:
1. Add `founded_by: str | None = None` field to `SettlementSnapshot` (or use existing `founded_year`)
2. In `_simulate_tick` founding event: when a character leads the expedition, record `s.founded_by = char_name`
3. Add `_update_character_home(character_status, char_name, new_settlement_name)` helper
4. For richer migration: when a settlement gets overcrowded, pick a character with "wanderlust" or "explorer" traits to lead the exodus
5. Tests: verify `SettlementSnapshot.founded_by`, verify founder's home_settlement updates in character_status

### Files to modify:
- `src/sim.py` — `SettlementSnapshot` adding `founded_by`, modify founding event
- `src/sim.py` — migration event: pick character by backstory traits
- `src/render.py` — show founder in settlement statblocks
- `tests/test_sim.py` — new tests for character-driven founding

### Architecture notes for next session:
- `Character` has: `full_name`, `home_settlement`, `home_region`, `occupation`, `personality_traits`, `backstory`, `status`
- `SettlementSnapshot` currently has: `name`, `region`, `x`, `y`, `population`, `kind`, `is_active`, `founded_year`, `prosperity`, `food_stores`, `health`
- `_select_named_character` returns `full_name` string; `SimState.character_status` maps full_name → "alive"
- For seed determinism: use the sim's `rng` (random.Random) for all character selection
- To find a character by name in the sim: `sim_state.character_status` has names, but the full Character objects aren't stored in SimState. You may need to pass characters list through and index by full_name.

### Future items (after Item 3):
- Item 4: Era transitions in sim (chronicle-era triggers mid-sim)
- Item 5: Sim consequences on narrative (NPC death, quest invalidation)
- Item 6: `wyrd branch` command for timeline visualization
