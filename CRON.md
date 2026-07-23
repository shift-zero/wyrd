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

**Phase 18 (Depth & Quality) in progress. 758 tests pass — 36 new API tests. REST API v1 complete.**

### What was done this session
1. **REST API v1 (15 endpoints)** — Added comprehensive JSON REST API to the existing web dashboard server:
   - `GET /api/v1` — API root with endpoint documentation
   - `GET /api/v1/worlds` — List worlds (paginated)
   - `GET /api/v1/worlds/<seed>` — World summary (not full dump)
   - `GET /api/v1/worlds/<seed>/regions` — Regions with settlements
   - `GET /api/v1/worlds/<seed>/settlements` — All settlements (flattened)
   - `GET /api/v1/worlds/<seed>/characters` — Narrative characters
   - `GET /api/v1/worlds/<seed>/quests` — Narrative quests
   - `GET /api/v1/worlds/<seed>/events` — Merged narrative + sim events (chronological)
   - `GET /api/v1/worlds/<seed>/factions` — Factions + relationships
   - `GET /api/v1/worlds/<seed>/zones` — Adventure zones
   - `GET /api/v1/worlds/<seed>/pantheon` — Religion/pantheon data
   - `GET /api/v1/worlds/<seed>/economy` — Economy/trade data
   - `GET /api/v1/worlds/<seed>/magic` — Magic system
   - `GET /api/v1/worlds/<seed>/simulation` — Simulation summary
   - `GET /api/v1/worlds/<seed>/snapshots` — Available snapshot years
   - `GET /api/v1/worlds/<seed>/terrain` — Full terrain grid with elevation, rivers, landmarks

2. **Pagination** — `?limit=N&offset=M` on all list endpoints. Limit clamped to [1, 100].

3. **Standalone API server** — `wyrd api` starts a JSON-only server on port 9090. Also `wyrd serve --rest-port 9091` starts a sidecar API server alongside the dashboard.

4. **36 new API tests** — Response shape validation, pagination edge cases, error states (404 for missing worlds, 400 for invalid seeds, 404 for unknown resources/endpoints).

5. **API served alongside dashboard** — The existing `wyrd serve` now serves v1 JSON at `/api/v1/*` in addition to the HTML dashboard and legacy `/api/*` endpoints.

### Test command
```bash
# Fast: parallel execution (4 workers)
source .venv/bin/activate && python -m pytest tests/ -q -n 4 --dist loadscope

# Serial (fallback if xdist issues)
python -m pytest tests/ -q
```

### Phase 18: Depth & Quality — remaining candidates

| Phase | What | Status |
|-------|------|--------|
| 1 | World generator (terrain, rivers, settlements) | ✅ |
| 2 | Lore engine (cultures, features, histories) | ✅ |
| 3 | Explorer mode (save/load, HTML, curses UI, queries) | ✅ |
| 4 | Narrative engine (characters, events, quests) | ✅ |
| 5 | Chronicles (era-based world history) | ✅ |
| 6 | Simulation (year-by-year world evolution) | ✅ |
| 7 | The Living World (interactive sim viewer, character integration) | ✅ |
| 8 | The Web Awakens (web dashboard, magic system, world management) | ✅ |
| 9 | The Pantheon (religion system, deity generation, holy sites) | ✅ |
| 10 | Adventure Zones (dungeons, caves, ruins on the world map) | ✅ |
| 11 | Faction System (political entities, relationships, power stats) | ✅ |
| 12 | Political Simulation (faction wars, alliances, power drift in sim) | ✅ |
| 13 | Cataclysmic Events (terrain mutation, landmark system, cascades) | ✅ |
| 14 | Trade & Economy (trade routes, prosperity, disruption) | ✅ |
| 15 | The Weirding (gateway TUI, unified curses interface) | ✅ |
| 16 | Trade Route Map Visualization (roads, specialization titles) | ✅ |
| 17 | Living Worlds (animated maps, TUI overhaul, embodied play) | ✅ |

### What to tackle next — Phase 18: Depth & Quality

The project is feature-complete. Every module exists, every CLI command works, 758 tests pass. Now the question is **depth** — making what's already there *richer* and *more cohesive* instead of adding more modules.

Candidates for Phase 18 (pick one per session):

1. **🔲 Embodied play depth** — More scenario types, skill system, deeper consequences. *(Shop/buy/sell system done ✅)*

2. **🔲 TUI polish** — The Textual-based TUI works but could be smoother: better keybind discoverability, persistent help bar, world picker on launch, minimap, smoother animations.

3. **🔲 World generation variety** — More terrain types (swamp, tundra, canyon, reef), biome-specific color palettes, weather patterns visible on the map.

4. **🟢 REST API — v1 complete with 15 endpoints and 36 tests.** Next: API auth? GraphQL? WebSocket streams?

5. **🔲 Bestiary depth** — *(Creature loot + encounter integration done ✅)* Full creature generation with stats, habitats, encounter tables, TTRPG integration already in place.

6. **🔲 Multi-world interaction** — Trade, war, diplomacy between parallel worlds. Cross-world pantheon crossover. Portal events.

### Architecture notes
- `src/__main__.py` — All CLI wiring. 25 subcommands on `wyrd --help` (added `api`).
- `src/serve.py` — All web serving. Now includes REST API v1 handlers, pagination helpers, `serve_api()` function.
- `src/render.py` — All ANSI rendering.
- 25 subcommands on `wyrd --help`
