# CLI Reference

Entry point: `src/__main__.py`. Registers subcommands via `argparse`.

## Common Flags

| Flag | Description |
|------|-------------|
| `--seed N` | World seed (random if omitted) |
| `--width N` | Map width (default: 80) |
| `--height N` | Map height (default: 40) |
| `--load FILE` | Load world from JSON |

## Commands

| Command | Description |
|---------|-------------|
| `generate` | Generate and display a world |
| `describe` | Show lore-only output |
| `save` | Save world to JSON |
| `load FILE` | Load and display a saved world |
| `export` | Export to HTML / SVG / TTRPG JSON |
| `explore` | Interactive curses explorer |
| `query "..."` | Natural language query |
| `characters` | List generated characters |
| `events` | Show event timeline |
| `quests` | Show available quests |
| `narrative` | Full narrative (chars + events + quests) |
| `run` | Year-by-year simulation |
| `chronicles` | Era-based world history |

## `generate` Flags

`--brief`, `--lore`, `--narrative`, `--no-settlements`, `--save PATH`

## `run` Flags

`--years N` (default: 100), `--chaos F` (0.0-1.0), `--summary`, `--compact`, `--seed-offset N`, `--snapshot-year N`

## `export` Flags

`--format html|svg|ttrpg`, `--snapshot-year N`, `--open`

## `chronicles` Flags

`--format text|html`, `--output PATH`

## See also

- [Rendering](rendering.md) — what generate/describe/load display
- [Export](export.md) — what `export --format` produces
