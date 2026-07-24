# Embodied Play Mode

Embody lets you live inside a generated world as a character. Birth, adventure, death, and inheritance — all in the terminal.

## Usage

```bash
wyrd embody --seed 42              # Print mode
wyrd embody --seed 42 --tui        # Curses TUI mode
wyrd embody --seed 42 --tui --name "Rikard"
```

## TUI Layout

- **Sidebar (left)** — Character stats: name, health, gold, age, season, year, location, skills, deeds, reputation
- **Event log (right)** — World events, character actions, scrollable with arrow keys
- **Status bar (bottom)** — Keybinding hints, season/year
- **Overlays** — Welcome, info, help, travel, market, choice, minimap, epilogue

## Key Bindings

| Key | Action |
|-----|--------|
| `n` | Advance one year (12 months) |
| `1` | Advance one month |
| `t` | Travel to another settlement |
| `m` | Open market / shop |
| `v` | View minimap of surroundings |
| `i` | Info — explain stats and systems |
| `?` / `h` | Help overlay |
| `↑` / `↓` | Scroll event log |
| `PgUp` / `PgDn` | Page scroll event log |
| `q` | Quit |

## Character Systems

- **Health (0-100):** Reduced by combat, disaster, old age. Recovers with time.
- **Gold:** Earned through trade, quests, events. Spent at markets.
- **Skills:** Combat, Trade, Persuasion, Survival, Crafting — gain XP through use.
- **Deeds:** Permanent record of achievements, passed to heir.
- **Heir:** On death, heir inherits half gold, partial skills, some inventory.

## Word-Wrapped Event Log

Event descriptions are now word-wrapped instead of truncated mid-sentence,
making long events readable without scrolling.

## Welcome & Info Overlays

- **Welcome screen** appears on character creation (skipped for loaded saves).
- **Info panel** (`i`) explains health, gold, skills, heir system.

## Minimap

Press `v` for a terrain minimap centered on your settlement.
Shows terrain tiles, other settlements (●), and player position (☺).
Uses the same terrain color scheme as the explorer and viewer.

## See also

- [CLI Reference](docs/cli.md)
- [Simulation](docs/simulation.md)
- [Narrative Engine](docs/narrative.md)
- [Architecture](docs/architecture.md)
