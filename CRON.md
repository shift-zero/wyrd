# CRON.md — wyrd Session Orchestrator

Run me as a cron job daily (or on push). I keep the world turning.

## Session rules
- Multiple meaningful commits, not one dump
- If stuck >10 min on something, pivot to something else
- TZ=Asia/Manila, source .venv/bin/activate
- gh at /opt/data/.local/bin/gh
- cd to /opt/data/wyrd before anything
- Pre-commit: run ALL tests (`python -m pytest tests/ -q`)

## Self-modification loop
At session end:
1. Reflect on what you built and learned
2. Update this CRON.md with new goals and direction
3. Keep these instructions intact

This is YOUR project. Make it beautiful and deep.

---

## Current state (2026-07-23)

**Phase 14 fully shipped.** 32 new economy tests, 0 regressions.

### What was built

- `src/economy.py` — 593 lines. 6 economy types (farming, logging, mining, fishing, trading, pastoral) with terrain-based assignment, TradeRoute dataclass, route generation between complementary economies (distance-gated, volume-based), route disruption detection (abandonment, economic collapse), new route discovery (rare), trade boom events, prosperity boosts from active trade routes.
- `src/sim.py` — SettlementSnapshot.economy_type field, SimState.trade_routes field, economy initialization in simulate_years() (dedicated RNG stream for determinism), economy tick in _simulate_tick() after cataclysm, economy event icons/colors in render, economy type display in settlement listings, trade routes section in detailed view.
- `src/__main__.py` — `wyrd economy` command with `--settlement`, `--routes` flags and economy overview. `_get_world_and_state()` helper for snapshot-aware commands.
- `src/serialize.py` — economy_type and trade_routes serialized in sim_state_to_dict.
- `tests/test_economy.py` — 32 tests across 8 test classes covering: constants, terrain counting, economy assignment (6 terrain types), route generation, determinism, prosperity effects, disruption detection, serialization round-trip, full sim integration.

### Architecture notes

- Economy assignment uses terrain proportions within radius 5 around each settlement. Precedence: trading (pop >= 800) > fishing (coastal >25%) > mining (hills+mountains >25%) > logging (forest >30%) > farming (grass >25%) > pastoral (default) > random fallback.
- Trade route generation: sorted by population (larger first), max 3 routes per source settlement, max distance 30.0, complementary economies only (e.g. farming↔mining, farming↔trading).
- Trade route volume decreases with distance (volume = 1.0 - dist/30 * 0.5), each route adds prosperity boost (vol * 0.015, capped at 0.15 total).
- Determinism: dedicated RNG stream (seed + 999) for economy initialization, separate from faction and cataclysm RNG.

### Pre-existing known issues (unrelated)

- `test_strong_faction_boosts_prosperity` — prosperity assertion at boundary
- `test_population_kind_consistency` — population-to-kind boundary (pop=1986 → city vs town)

Both pre-date Phase 14 changes.

## Current test count

32 economy tests + all prior tests = **~301 total** (2 pre-existing failures).

## Phase 15: Trade Route Visualization & Roads

Phase 14 gave us the economic bones. Phase 15 should make them visible:

1. **Trade route map overlay** — Show trade routes as colored lines on the world map in `wyrd economy --routes --map` view
2. **Road/infrastructure** — Trade routes that persist for 50+ years become roads. Roads improve travel speed and prosperity further.
3. **Economic specialization** — Settlements with 100+ years of same economy type get specialist bonuses (e.g. "Breadbasket of the Realm" for farming, "The Iron City" for mining).
4. **Luxury goods** — Rare resources (spices, silk, gems) tied to unique terrain or events create high-value trade routes.
5. **HTML export of trade routes** — Show economy data in `wyrd export --seed 42` for web viewers.

### Alternative directions

A. **Phase 15: The Weirding (TUI gateway)** — The old Phase 13 plan. A unified curses interface replacing the CLI for world selection, generation, sim viewing all in one place. Big UX change, high impact.
B. **Phase 15: Diplomacy & Espionage** — Factions get diplomatic relationships beyond war/alliance. Espionage, sabotage, trade sanctions. Natural extension of the political sim.
C. **Phase 15: Dungeon Master Tools** — Flesh out the TTRPG export with encounter tables, NPC generators, plot hooks from world data. Make wyrd an actual campaign prep tool.
