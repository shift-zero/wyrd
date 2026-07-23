# wyrd — Generative Fantasy Sandbox

> *wyrd* (pronounced "weird") — Old English for fate, destiny, the cosmic pattern. Every world has one.

A terminal-native generative fantasy sandbox. Build a world, explore it, ask about it, watch it grow.

## Why This Project

Not another one-shot CLI wrapper. This is *mine* — conceived, planned, and built across dozens of sessions. It grows by compounding: each milestone makes the next one possible.

## Architecture

```
wyrd/
├── src/           # Core library
│   ├── generate.py   # World generation (terrain, rivers, settlements)
│   ├── world.py      # Core data models
│   ├── nore.rs       # (eventually Rust for performance)
│   ├── render.py     # ANSI/ASCII rendering + narrative rendering
│   ├── lore.py       # Procedural lore engine
│   ├── narrative.py  # Character, event, and quest generation
│   ├── chronicles.py # Era-based world history (Phase 5)
│   ├── sim.py        # Year-by-year world simulation (Phase 6)
│   ├── economy.py    # Trade & economy system (Phase 14)
│   ├── magic.py      # Magic system generation (Phase 8)
│   ├── religion.py   # Pantheon/religion system (Phase 9)
│   ├── cataclysm.py  # Cataclysmic events (Phase 13)
│   ├── serialize.py  # JSON save/load
│   ├── explore.py    # Interactive terminal explorer
│   ├── query.py      # Natural-language query engine
│   ├── export_html.py# HTML export
│   ├── serve.py      # Web dashboard server (Phase 8)
│   ├── export_chronicles_html.py  # Chronicles HTML export
│   └── __main__.py   # CLI entry point
├── tests/         # Test suite
│   ├── test_generate.py
│   ├── test_lore.py
│   ├── test_narrative.py
│   ├── test_chronicles.py
│   ├── test_sim.py
│   ├── test_phase3.py
│   ├── test_explore.py
│   ├── test_query.py
│   ├── test_export_ttrpg.py
│   ├── test_magic.py
│   ├── test_religion.py
│   ├── test_serve.py
│   ├── test_worlds.py
│   ├── test_cataclysm.py
│   ├── test_economy.py
│   └── conftest.py
└── output/        # Generated worlds (gitignored)
```

### Phase Strategy

**Phase 1 — World Generator** (done)
- Procedural ASCII map with terrain, biomes, elevation
- Named settlements with population tiers
- Rivers, coastlines, mountain ranges
- ANSI-colored terminal output
- Seed-based generation (same seed = same world)

**Phase 2 — Lore Engine** (done)
- Region names, culture names, settlement descriptions
- Named geographical features (The Whispering Strait, etc.)
- History snippets per region
- Conflicts and relationships between settlements

**Phase 3 — Explorer Mode** (done)
| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | World serialization (save/load JSON) | `wyrd save --seed 42` produces a JSON file; `wyrd load wyrd-42.json` restores it |
| 2 ✅ | Export to HTML | `wyrd export --seed 42` produces a self-contained HTML page |
| 3 ✅ | Pager-based explore | `wyrd explore --seed 42` shows map+lore in a pager |
| 4 ✅ | Interactive terminal UI (scroll, zoom, inspect) | Navigate a generated world in the terminal |
| 5 ✅ | Query the world: "tell me about the northlands" | `wyrd query --seed 42 "tell me about Blackland"` returns region lore, culture, history, settlements |

**Phase 4 — Narrative** (done)
| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Character generation grounded in world cultures | `wyrd characters --seed 42` lists named characters with occupations, traits, backstories |
| 2 ✅ | Event chains that unfold over time | `wyrd events --seed 42` shows chronological timeline with types and consequences |
| 3 ✅ | Generated quests grounded in geography and politics | `wyrd quests --seed 42` shows active quests with givers, locations, rewards |
| 4 ✅ | All narrative seed-deterministic (same seed → same narrative) | Same seed produces identical characters, events, and quests |
| 5 ✅ | Narrative serialization round-trip | Save/load preserves all narrative data; old saves without narrative still work |

**Phase 5 — Chronicles** (done)
Generative world history. Not a static dump — a causally linked timeline of eras that shaped the world into what it is.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Era-based history generation (ages, cataclysms, golden ages) | `wyrd chronicles --seed 42` outputs a timeline of distinct eras with descriptions |
| 2 ✅ | Legendary events with named participants from the narrative engine | Events reference actual characters and settlements from the world |
| 3 ✅ | Era-dependent world state (ruins, fallen empires, contested borders) | Each era carries world_modifiers (ruins, monuments, contested borders) reflecting its type |
| 4 ✅ | Seed-deterministic: same seed + same era range → same history | Always identical across runs |
| 5 ✅ | History serialization + export to timeline HTML | `wyrd chronicles --seed 42 --format html` produces a readable chronicle page |

**Phase 6 — The Turning of the World** (done)
Year-by-year simulation in the Dwarf Fortress tradition. The world is no longer a static artifact — it *lives* and *changes*.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Tick-based simulator: settlements grow/decline year by year | `wyrd run --seed 42 --years 300` shows population changes, new settlements, founding events |
| 2 ✅ | Causal event chain: wars, famines, plagues, discoveries emerge from conditions | Viewing year 150+ shows wars, trade booms, and famines that result from crowding and scarcity |
| 3 ✅ | Dynamic map evolution: borders shift, ruins appear, new roads form | Settlements multiply from ~11 to 88+ over 500 years; new names appear from emigration |
| 4 ✅ | Pause-and-inspect: stop the sim at any year and use explore/query | `--snapshot-year` flag on explore/query/export/save; sim state serialization (JSON save/load) with intermediate snapshots |
| 5 ✅ | Seed-deterministic with optional branching | Same seed + same params → same outcome; `--seed-offset` enables branching |
| 6 ✅ | Export any snapshot as TTRPG-ready campaign doc | `wyrd export --seed 42 --year 127 --format ttrpg` produces Foundry/WorldAnvil-ready JSON
| 7 ✅ | Polish: compact sim output, snapshot-aware HTML map | `wyrd run --seed 42 --years 500 --compact` saves gzip sim; HTML shows snapshot state

### Design Principles

1. **Every output is beautiful.** ANSI color, careful layout, no debug spew.
2. **Worlds feel real.** Generated geography constrains lore, not the other way around.
3. **Composable.** Phase 1 doesn't need to know about Phase 4. Each layer builds on the previous.
4. **Seed-deterministic.** Same seed = same world, always. Share seeds, not world files.

## Milestones

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | ASCII map renders terrain, water, forests, mountains, settlements | `wyrd generate --seed 42` outputs a beautiful map |
| 2 ✅ | Lore engine names regions, cultures, and features | `wyrd describe --seed 42` shows lore |
| 3 ✅ | Interactive terminal UI (scroll, zoom, inspect) | Navigate a generated world in the terminal |
| 4 ✅ | Export to HTML and SVG | `wyrd export --seed 42` produces HTML; `wyrd export --seed 42 --format svg` produces SVG |
| 5 ✅ | Narrative engine with character generation | Characters with backstories grounded in the world |
| 6 ✅ | Chronicles engine — era-based world history | `wyrd chronicles --seed 42` shows a causally linked timeline |
| 7 ✅ | Simulation engine — year-by-year world evolution (6/6 + Polish complete) | `wyrd run --seed 42 --years 500` evolves settlements, generates events, founding/abandonment/war |

## Phase 7 — The Living World (complete ✅)
Interactive simulation viewing and character-driven world evolution. The world doesn't just tick silently — you watch it grow, and the stories write themselves.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Interactive curses sim viewer: watch the map evolve year by year | `wyrd view --seed 42 --years 300` shows real-time map evolution with pause/speed controls |
| 2 ✅ | Named character integration in sim events | Sim events reference actual Narrative characters as leaders, generals, heroes when available; character selection is seed-deterministic and prefers occupation-relevant NPCs |
| 3 ✅ | Character-driven founding events | New settlements are founded by named characters with backstory context; migration events tied to character backstories |
| 4 ✅ | Era transitions in simulation | Simulation triggers era transitions every 50 years based on world conditions (population, abandonment, expansion); dynamic world modifiers |
| 5 ✅ | Sim event consequences on narrative | NPCs die in plagues/wars and are reflected in narrative; quests from dead characters become inactive; new quests emerge from sim events |
| 6 ✅ | Branching timeline visualization | `wyrd branch --seed 42 --years 300` shows alternative sim paths side-by-side with event/era comparisons |

## Phase 8 — The Web Awakens (complete ✅)
Bring wyrd out of the terminal and onto the web. Interactive map viewers, persistent world management, and LLM-powered storytelling.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Web overview dashboard: serve world stats, map HTML, sim state in browser | `wyrd serve --seed 42` starts a web server; browser shows interactive world dashboard with stats, map, regions, and JSON API |
| 2 ✅ | Sim-state-aware HTML map | `wyrd export --seed 42 --year 150` produces HTML showing evolved map with new settlements, ruins (⁂), population timeline, and event counts |
| 3 ✅ | Conversational world agent | `wyrd ask "What's the most powerful city?"` uses LLM to answer from world data; deterministic fallback when no API key |
| 4 ✅ | Multi-world management | `wyrd worlds` lists all generated worlds; `wyrd worlds --json` outputs structured metadata |
| 5 ✅ | Magic system generation | `wyrd magic --seed 42` renders color-coded schools and traditions tied to world biomes and cultures |

## Phase 9 — The Pantheon (complete ✅)
Generative religion system. Every world gets a pantheon of named deities, organized into 1–2 religions, with holy sites grounded in actual settlements. TTRPG-ready deity stats, encounter levels for holy sites, and seed-deterministic generation.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Deity generation with domains, alignment, symbols, holy animals | `wyrd pantheon --seed 42` shows named deities with descriptions, symbols, and assigned domains |
| 2 ✅ | Religion organization (1–2 religions per world) | Pantheon generates 1–2 religions with distinct tenets, clergy titles, and holy days |
| 3 ✅ | Holy sites tied to settlements | Each religion generates temples, shrines, monasteries, oracles, groves, and sanctuaries at existing settlements |
| 4 ✅ | Region-to-religion mapping | Every world region is assigned a religion based on biome affinity and alignment |
| 5 ✅ | Pantheon in TTRPG export | `wyrd export --seed 42 --format ttrpg` includes full pantheon section with deity stat blocks and encounter levels |
| 6 ✅ | Serialization round-trip | Pantheon survives save/load; works with worlds that don't have one yet |
| 7 ✅ | Religious conflict events in simulation | Deities and religious tensions influence sim events and era transitions |
| 8 ✅ | Religious NPCs and quest hooks | Clergy characters with quests tied to holy sites and religious goals |
| 9 ✅ | Religion-aware chronicle eras | Chronicle era types can be influenced by religious dominance shifts |

## Phase 10 — Adventure Zones (complete ✅)
Points of interest scatter across the world map — dungeons, caves, ruins, towers, groves, lairs, shrines, and mines — each with descriptions, inhabitants, difficulty ratings, treasure tiers, and quest hooks. Visible on the map with distinct markers. Integrated into TTRPG export.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Dungeon zones placed on suitable terrain | `wyrd generate --seed 42` includes 8+ adventure zones on terrain-appropriate hexes |
| 2 ✅ | Map rendering shows zone markers (D, C, R, T, G, L, S, M) | `wyrd zones --seed 42` shows zones on the map with coloured markers and legend |
| 3 ✅ | Zone detail: descriptions, inhabitants, difficulty | `wyrd zones --seed 42 --id 0` shows full details for a single zone |
| 4 ✅ | Quest hooks attached to every zone | Each zone has a unique quest hook its listing |
| 5 ✅ | Treasure tiers scaled by difficulty | Harder zones contain more valuable treasure |
| 6 ✅ | Seed-deterministic placement | Same seed → same zones in the same locations |
| 7 ✅ | Zone rendering in HTML export | Adventure zones show on HTML map with tooltips |
| 8 ✅ | Interactive zone inspection in explorer | `wyrd explore` can hover/click zones for details |
| 9 ✅ | Zone serialization round-trip | Zones survive save/load |

## Phase 11 — Faction System (complete ✅)
Political, economic, and cultural entities with territories, leaders, power scores, reputation, goals, and inter-faction relationships. 12 faction types with distinct icons, colors, and leader titles.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Faction generation with 12 types | `wyrd factions --seed 42` lists all factions with power bars and colored icons |
| 2 ✅ | Inter-faction relationships | Auto-generated alliance/trade/rivalry/hostility between all faction pairs |
| 3 ✅ | Faction detail view | `wyrd factions --seed 42 --id 0` shows name, type, leader, stats, goals, territory |
| 4 ✅ | Seed-deterministic generation | Same seed → same factions, same relationships |
| 5 ✅ | Faction serialization round-trip | Factions and relationships survive save/load |
| 6 ✅ | Factions in explorer overlay | `wyrd explore --seed 42` → press `f` for factions |
| 7 ✅ | Factions in HTML export | Collapsible faction section with relationship listings |

## Phase 12 — Political Simulation (complete ✅)
Factions rise and fall during year-by-year simulation. Wars erupt between rival factions, alliances form, power shifts, and faction strength affects settlement prosperity. Political events woven into `wyrd run` output with power bars and end-state faction summary.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Faction power drift each sim year | Stats change based on faction type biases and territory count |
| 2 ✅ | Faction wars between rival/hostile factions | `wyrd run --seed 42 --years 200` shows war events with casualties |
| 3 ✅ | Faction alliances between peaceful factions | Alliance events appear in sim output |
| 4 ✅ | Power shift and collapse events | Rare dramatic events with settlement effects |
| 5 ✅ | Faction→settlement prosperity effects | Strong factions boost territory prosperity |
| 6 ✅ | Political events in render output | War/alliance/power shift icons + Faction Power section at end |
| 7 ✅ | Seed-deterministic political simulation | Same seed → identical wars and power scores |
| 8 ✅ | 28 tests for deterministic state, events, drift | All pass, zero regressions |
| 9 ✅ | Peace treaties ending wars with formal treaty events | ☮ icon, formal treaty language with terms and effects; distinct from alliances |
| 10 ✅ | War exhaustion modifier affecting sim | FactionSnapshot.war_exhaustion tracks cumulative war duration; settlements in war-exhausted territory lose food stores and prosperity |
| 11 ✅ | Catastrophic events (earthquakes, volcanos, plagues of legend) that reshape the map | 37 tests for terrain mutation, settlement destruction, landmark generation, cascade events, rendering |

## Phase 13 — Cataclysmic Events (complete ✅)
Very rare simulation events that permanently alter terrain, destroy settlements, and create lasting landmarks. 7 cataclysm types, terrain mutation tables, settlement destruction, landmark system with named features, cascade events (earthquake→tsunami, volcanic→great_fire, etc.), refugee/exodus events, and full serialization.

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Cataclysm module (src/cataclysm.py) with 7 cataclysm types, terrain mutation, settlement destruction, landmark generation | `wyrd run --seed 42 --years 1000` shows cataclysm events with icons and descriptions |
| 2 ✅ | Landmark system: named features persist through sim and survive serialization | Landmarks (crater ⊙, chasm ≋, ash waste ▒, etc.) appear on world map with unique chars |
| 3 ✅ | Cascade events (15% chance): one cataclysm triggers another | earthquake→tsunami/great_fire, meteor_strike→great_fire/earthquake |
| 4 ✅ | Terrain mutation: terrain changes permanently based on cataclysm type | Forests burn to grass, mountains shatter to hills, craters scar the earth |
| 5 ✅ | Settlement destruction with death toll, refugee events | Settlements destroyed or devastated with population loss and exodus events |
| 6 ✅ | Full integration: sim tick, sim events, render icons/colors | Cataclysm events visible in `wyrd run` output with distinct icons and colors |
| 7 ✅ | 37 tests across core types, terrain mutation, settlement destruction, landmarks, cascades, integration, serialization, rendering | `python -m pytest tests/test_cataclysm.py -q` all pass |

## Phase 14 — Trade & Economy (current)
Settlements don't exist in isolation — they trade. Farming villages produce grain, mining towns produce ore, forest hamlets produce timber. Trade routes form between complementary economies. Prosperity flows along these routes, and when they're disrupted, economies suffer.

| # | What | Verifiable |
|---|------|------------|
| 1 🔲 | EconomyType enum and settlement economy assignment based on local terrain | `wyrd run --seed 42 --years 100` shows economy types in settlement listings |
| 2 🔲 | Trade route generation between complementary economies (farming↔mining, etc.) | Trade routes visible in sim detailed output with goods volume |
| 3 🔲 | Trade route prosperity modifiers | Settlements with trade routes have higher prosperity |
| 4 🔲 | Route disruption events (war, cataclysm, abandonment) | Trade collapse events appear when routes break |
| 5 🔲 | New settlement economy-based events (trade boom, collapse, new route) | distinct economy event types in sim output |
| 6 🔲 | Economy display in sim detailed view | Economy icons and trade route count in settlement listings |
| 7 🔲 | Serialization: economy data survives save/load | Economy types and trade routes persist through serialization |
| 8 🔲 | Tests for determinism, route generation, economy assignment, disruption | 15+ tests in test_economy.py |
