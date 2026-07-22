# Interactive Explorer

`src/explore.py` — Phase 3, Milestone 4. Curses-based terminal UI.

## Features

- **Pan** — arrow keys or WASD
- **Zoom** — `+`/`-` (zooms out by showing 2×2, 3×3 tiles per char)
- **Inspect** — `i` toggles cursor mode, shows elevation/moisture/settlement info at bottom panel
- **Region overview** — `r` overlays all regions with population stats
- **Lore viewer** — `l` shows culture, history, and relationships overlay
- **Help screen** — `h`/`?` for keybindings

## Colour Palette

16 color pairs initialized in `_init_colors()`. Uses 256-color terminal codes. Red cursor (`196`), yellow settlements (`226`), cycling region highlight colors.

## Fallback

If curses isn't available (non-TTY, import error), falls back to piping through `$PAGER` (default: `less -R`).

## See also

- [Rendering](rendering.md) — ANSI output used as fallback
- [CLI Reference](cli.md) — `wyrd explore` command
