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

**465 tests pass across all test files.**

Phase 13 is fully shipped:
- `src/cataclysm.py` — 651 lines, 7 cataclysm types, terrain mutation, settlement destruction, landmark generation, cascade events, epicentre selection
- `tests/test_cataclysm.py` — 37 tests (30 original + 7 rendering) all passing, covers: core types, terrain mutation, settlement destruction, landmark creation, epicentre selection, cascade events, full execution, integration with sim, serialization, landmark rendering on world map
- Full integration: sim.py imports and calls `_simulate_cataclysm_tick()` and `cataclysm_to_sim_event()` inside try/except blocks
- Serialization: world.landmarks survive save/load via serialize.py
- Rendering: cataclysm event icons and colors in sim.py render functions; landmarks now appear on the world map via render_map() with their unique chars (≋ chasm, ⊙ crater, ▒ ash waste, etc.) at creation coordinates; dedicated `render_landmarks()` function for detailed view
- Fix: removed broken "glass" terrain fallback in magical_cataclysm mutation table
- Event-driven quests: cataclysm events generate quest hooks in `_apply_narrative_consequences()`

Pre-existing known issue: sim.py war event character rendering checks for None already (lines 417-426), so the reported "crash" doesn't actually occur with current code.

## Phase 14: Trade & Economy System

Settlements don't exist in isolation — they trade. A farming village produces grain, a mining town produces ore, a forest hamlet produces timber. Trade routes form between complementary economies. Prosperity flows along these routes, and when they're disrupted (by war, cataclysm, abandonment), economies suffer.

### Design

Each settlement gets an **economy_type** field:
- `"farming"` — grain, livestock (grass, river terrain)
- `"logging"` — timber, charcoal (forest terrain)
- `"mining"` — ore, stone (hills, mountains terrain)
- `"fishing"` — fish, pearls (coastal, river terrain)
- `"trading"` — commerce, goods (large settlements, crossroads)
- `"pastoral"` — herds, wool (hills, grass terrain)

Trade routes are generated between settlements with **complementary** economy types (farming ↔ mining, logging ↔ fishing, etc.). Each route has:
- A distance-based travel time
- A volume of goods flowing
- A prosperity boost for both endpoints

Route disruption triggers economic events:
- Trade collapse when a settlement is destroyed
- Trade boom when a new route forms
- Piracy/banditry on established routes

### Suggested milestone items

1. `EconomyType` enum and `SettlementEconomy` dataclass
2. Economy assignment to settlements based on local terrain
3. Trade route generation (complementary economies, distance-gated)
4. Trade route prosperity modifiers on settlements
5. Route disruption events (war, cataclysm, abandonment)
6. New settlement economy-based events (boom, collapse, new route)
7. SimState integration: economy data in SettlementSnapshot
8. Render/display: show economy type and trade routes in sim output
9. Serialization: economy data survives save/load
10. Tests: determinism, route generation, economy assignment, disruption events

### Implementation approach

- New module: `src/economy.py` (TradeRoute dataclass, EconomyType, `assign_economies()`, `generate_trade_routes()`, `apply_trade_effects()`)
- Extend: `SettlementSnapshot` in sim.py with `economy_type: str`
- Integration: call from `_simulate_tick()` after settlement growth — apply trade prosperity, check for disruptions
- Render: show economy types in sim detailed view, show trade route count
- Tests: `tests/test_economy.py` — 15-20 tests covering economy assignment, routes, determinism, disruption

### Stretch goals (if time)
- Roads/infrastructure: trade routes become roads over time
- Economic specialization: settlements with long-running trade become "trading post" / "market town"
- Luxury goods: rare resources (spices, silk, gems) from unique terrain create high-value trade routes
