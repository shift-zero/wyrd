# Terminal Rendering

`src/render.py` — ANSI-colored terminal output for world, lore, narrative, and chronicles.

## Color System

Uses 256-color ANSI codes:

```python
def _color(code, bg=False):
    prefix = 48 if bg else 38
    return f"\033[{prefix};5;{code}m"
```

## Key Functions

| Function | Renders |
|----------|---------|
| `render_map()` | Title bar + terrain grid + legend + region list |
| `render_brief()` | One-line summary |
| `render_lore()` | Per-region culture, features, relationships |
| `render_characters()` | Characters grouped by region |
| `render_events()` | Chronological event timeline |
| `render_quests()` | Quest cards with difficulty/type/rewards |
| `render_narrative()` | Characters + events + quests combined |
| `render_chronicles()` | Era timeline with years, events, modifiers |

## Visual Conventions

- `ANSI_BOLD` for titles and names
- `ANSI_DIM` for metadata and labels
- Color-coded terrains (blue=water, green=grass, brown=highlands)
- Color-coded event types (red=conflict, blue=discovery, etc.)
- Icons for each event and quest type

## See also

- [Export](export.md) — for platform-independent output
- [Explorer](explorer.md) — curses-based rendering
