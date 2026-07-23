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
│   ├── render.py     # ANSI/ASCII rendering + narrative rendering
│   ├── lore.py       # Procedural lore engine
│   ├── narrative.py  # Character, event, and quest generation
│   ├── chronicles.py # Era-based world history
│   ├── sim.py        # Year-by-year world simulation
│   ├── economy.py    # Trade & economy system
│   ├── magic.py      # Magic system generation
│   ├── religion.py   # Pantheon/religion system
│   ├── cataclysm.py  # Cataclysmic events
│   ├── faction.py    # Faction system
│   ├── bestiary.py   # Creature generation
│   ├── embody.py     # Embodied play mode (character, skills, heir)
│   ├── shop.py       # Market & shop system
│   ├── serialize.py  # JSON save/load
│   ├── gateway.py    # Unified curses gateway TUI
│   ├── viewer.py     # Sim evolution curses viewer
│   ├── explore.py    # Interactive terminal explorer
│   ├── query.py      # Natural-language query engine
│   ├── export_html.py# HTML export
│   ├── serve.py      # Web dashboard + REST API v1
│   ├── export_chronicles_html.py  # Chronicles HTML export
│   ├── tui.py        # Textual TUI (alternative interface)
│   └── __main__.py   # CLI entry point (25 subcommands)
├── tests/         # Test suite (796 tests)
│   ├── test_generate.py
│   ├── test_lore.py
│   ├── test_narrative.py
│   ├── test_chronicles.py
│   ├── test_sim.py
│   ├── test_api.py        # REST API v1 tests (36)
│   ├── test_economy.py
│   └── ...
└── output/        # Generated worlds (gitignored)
```

## Phase 19 — Human-First UX (complete ✅)

**Thesis:** wyrd has deep systems but the interface is still a dev tool's face. The TUI is messy, hard to navigate, and everything happens in year-sized chunks that are too fast to follow and too slow to feel real.

Two priorities:

### 1. TUI overhaul (top priority)

The TUI works but isn't *pleasant*. Problems:
- Keybinds aren't discoverable — you have to know them or press `?`
- Screen layout is cluttered, no visual hierarchy
- Navigation between views feels janky
- No persistent status bar showing what mode you're in

Target: clean, Bubbletea-inspired feel. Modal panels, consistent navigation, visual hierarchy, smooth transitions. Even if the Textual foundation exists, the UX needs iteration — better world picker, clearer maps, easier inspection.

### 2. Variable time passage

Right now the sim ticks in year increments. For embodied play this means your character ages a year every decision. For the viewer it means map changes are sudden jumps.

The sim needs sub-year granularity:
- **Days/weeks/months as the base tick** in embody mode — travel takes days, news arrives weekly, you don't age a year every time you breathe
- **Variable speed control** — slow (days visible) to fast (years flying by), with smooth transitions
- **In the viewer:** sub-year map ticks so you can *watch* seasons change, armies march, trade caravans move — not just see the map after the fact
- **In embody:** days go by as you rest/travel/craft. A year passes meaningfully. Your character doesn't jump from 25 to 26 in one screen refresh

The simulation engine (`sim.py`) currently ticks in whole years. This is a deep change — the economy, faction sim, cataclysm, and event systems all assume year ticks. But even a simple decorator that interpolates year-level events into month-level pulses would make the world feel alive instead of stroboscopic.

### Checklist

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | TUI layout overhaul — clean panels, status bar, consistent navigation | Navigating the TUI feels natural without pressing `?` first | 2026-07-23 |
| 2 ✅ | Keybind discoverability — persistent help hints, modal context labels | You always know what keys do in the current view | 2026-07-23 |
| 3 ✅ | Sub-year time tick in sim engine — months as base unit | `wyrd run` can tick in months; events schedule at month granularity | 2026-07-23 |
| 4 ✅ | Variable speed control in viewer — smooth from slow (days) to fast (decades) | `v` viewer has speed slider + labels (Crawl→Zoom) and uses month-level ticks | 2026-07-24 |
| 5 ✅ | Embody mode uses sub-year ticks — travel days, rest weeks, age yearly | Moving between settlements takes 1-2 months, not instant teleport; `1m` / `1w` time options | 2026-07-24 |
|| 6 ✅ | Seasonal rendering — map colors shift subtly as months pass | A year of sim shows 4 distinct seasonal palette shifts on the viewer map | 2026-07-24 |
|
## Phase 20 — Living Gazetteer (complete ✅)

**Thesis:** wyrd generates deep data but it's scattered across CLI subcommands. A unified in-TUI browser makes everything discoverable.

### Items

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Settlement detail popup in viewer — press `i` on a settlement | Popup shows name, pop, prosperity, trade goods, recent events | 2026-07-24 |
| 2 ✅ | Gazetteer mode in gateway — press `G` for browsable index | Filterable listing of settlements, characters, factions, creatures, zones, deities | 2026-07-24 |
| 3 ✅ | Character browser — list all narrative chars, filter by status | Inline detail for each character: name, title, status, home | 2026-07-24 |
| 4 ✅ | Faction viewer — browse factions with relationships, holdings | View shows allies, rivals, territory, recent history | 2026-07-24 |
| 5 ✅ | Bestiary browser — filter by habitat/tier, view full stats | Creature cards with tier, habitat, behavior, loot table | 2026-07-24 |
| 6 ✅ | `wyrd lookup <name>` — CLI quick-lookup across all data types | Searches settlements, chars, creatures, zones, returns best match | 2026-07-24 |
|
|## Phase 21 — Living Gateway (complete ✅)|
|
|**Thesis:** The gateway world picker was a flat text table — functional but not visual. The surface matters because it's the first thing you see.|
|
|### Items|
|
|| # | What | Verifiable |
||---|------|------------|
|| 1 ✅ | World detail card with mini-ASCII map — shows terrain preview, stats, features | Select a world in the gateway → detail panel appears with a colored mini-map of the terrain, settlement/region/population stats, and feature badges | 2026-07-24 |
|| 2 ✅ | Interactive world list — sort by seed/population/name | Press Tab to cycle sort keys (seed→population→name), world list reorders immediately | 2026-07-24 |
||| 3 ✅ | Compact gateway splash when worlds exist | ASCII splash art hidden when worlds are present, giving more room for the world list and detail card | 2026-07-24 |
||
|## Phase 22 — Surface Polish (2026-07-25 ✅)|
||
||**Thesis:** The TUI and viewer had accumulated UI jank and code repetition. Fixing the surface quality — flicker, rendering performance, and code rot — makes the whole project feel more polished.|
||
||### Items|
||
||| # | What | Verifiable |
||---|------|------------|
||| 1 ✅ | Viewer flicker elimination — `stdscr.clear()` → `stdscr.erase()` in viewer, gateway, and explorer | No blank-flash between frames |
||| 2 ✅ | Batched terrain rendering — `addstr()` spans instead of per-char `addch()` in viewer | ~95% fewer curses API calls per frame for terrain |
||| 3 ✅ | Gateway code deduplication — 9 key handlers use shared `_resolve_world()` helper | 80+ lines of duplicated world-resolution code removed |
|||| 4 ✅ | Gateway & explorer flicker fix — same `clear()`→`erase()` in both gateways | All 3 TUI surfaces have smooth rendering |
|||
||## Phase 23 — Surface Depth (2026-07-25 ✅)|
|||
||**Thesis:** The TUI surfaces are flicker-free and render efficiently — now deepen them. Batch-rendering explore mode, add above-year viewer speeds, and overlay change indicators on the settlement map.|
||
||### Items|
||
||| # | What | Verifiable |
||---|------|------------|
||| 1 ✅ | Explore mode batch rendering — port span-based `addstr()` from viewer to explore's `_draw_map` with pre-built zone lookup | ~95% fewer curses API calls per frame for explore terrain |
||| 2 ✅ | Speeds beyond zoom — Decade (128x), Century (256x), Epoch (512x) with labels and speed bar extension | `+` key cycles through Crawl→Epoch, Epoch simulates ~43 years/second |
||| 3 ✅ | Context-sensitive viewer overlays — green ▲/red ▼/grey · on changed settlements when paused | Pause the viewer to see ▲ on growing towns, ▼ on shrinking ones, · on abandoned ||
||
```

## Phase 23.5 — Auto-Pause on Viewer Events (2026-07-26 ✅)

**Thesis:** When running the viewer at high speeds (Decade/Epoch), significant events flash by invisibly. Auto-pausing on wars, cataclysms, foundings, and discoveries makes the world feel alive and lets you *see* history unfold instead of watching it strobe past.

### Items

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Auto-pause on significant events in viewer — wars, cataclysms, foundings, discoveries, faction changes | Run viewer at Epoch speed; it auto-pauses on the first major event with a flashing banner explaining why |
| 2 ✅ | Flashing notification banner — shows event icon + description, alternates colors for attention | Banner persists ~60 frames with alternating accent/satus colors, then fades |
| 3 ✅ | Help documentation — new section in viewer help overlay | Press ? in viewer to see Auto-Pause section |

### What to tackle next
- **Seasonal palette — deeper variation.** Snow accumulation on cold terrain, greening transitions in spring, dramatic autumn reds using temperature maps from latitude + elevation. (Tracked in CRON.md)
- **Embody TUI heir epilogue polish** — add heir generation confirmation overlay (name, stats preview) before committing to heir restart.
- **Embody TUI mobile threshold** — active resizing feedback when terminal crosses the 100-col boundary.

## Design Principles

1. **Every output is beautiful.** ANSI color, careful layout, no debug spew.
2. **Worlds feel real.** Generated geography constrains lore, not the other way around.
3. **Composable.** Each layer builds on the previous.
4. **Seed-deterministic.** Same seed = same world, always.
