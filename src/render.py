"""
wyrd — Terminal renderer. ANSI-colored map output.
"""

from .world import World, TERRAIN


ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"


def _color(code: int, bg: bool = False) -> str:
    """Return ANSI escape for a 256-color code."""
    prefix = 48 if bg else 38
    return f"\033[{prefix};5;{code}m"


def render_map(world: World, show_settlements: bool = True) -> str:
    """Render the world as an ANSI-colored string."""
    lines = []

    # Title bar
    lines.append(f"{ANSI_BOLD}wyrd — seed {world.seed}{ANSI_RESET}")
    lines.append(f"{world.width}×{world.height} | {len(world.regions)} regions\n")

    # Map body
    for y in range(world.height):
        row_chars = []
        for x in range(world.width):
            terrain_key = world.terrain[y][x]
            info = TERRAIN[terrain_key]

            # Check for settlement at this position
            settlement_char = None
            for region in world.regions:
                for s in region.settlements:
                    if s.x == x and s.y == y and show_settlements:
                        settlement_char = s.char
                        break
                if settlement_char:
                    break

            if settlement_char:
                row_chars.append(f"{_color(226)}{ANSI_BOLD}{settlement_char}{ANSI_RESET}")
            else:
                row_chars.append(f"{_color(info['color'])}{info['char']}{ANSI_RESET}")
        lines.append("".join(row_chars))

    # Legend
    lines.append("")
    for key, info in TERRAIN.items():
        lines.append(f"  {_color(info['color'])}{info['char']}{ANSI_RESET}  {info['desc']}")

    lines.append(f"\n  {_color(226)}{ANSI_BOLD}●{ANSI_RESET}  Settlement (size: · hamlet ∘ village ● town ◉ city)")

    # Region list
    lines.append(f"\n{ANSI_BOLD}Regions:{ANSI_RESET}")
    for region in world.regions:
        settlements = ", ".join(
            f"{s.name} ({s.kind})" for s in region.settlements
        )
        lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET} — {settlements}")

    return "\n".join(lines)


def render_brief(world: World) -> str:
    """Render a compact one-line summary."""
    total_pop = sum(s.population for r in world.regions for s in r.settlements)
    land = sum(1 for row in world.terrain for t in row
               if t not in ("deep_water", "shallow"))
    return (
        f"wyrd #{world.seed} — "
        f"{world.width}×{world.height} | "
        f"{land / world.tiles * 100:.0f}% land | "
        f"{len(world.regions)} regions | "
        f"{total_pop:,} souls"
    )
