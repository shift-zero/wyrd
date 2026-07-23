"""Build a settlement coordinate lookup map for a world."""
import json, sys
sys.path.insert(0, 'src')
from world import World
from generate import generate_world
from render import render_map, ANSI_RESET, ANSI_BOLD, _color

def build_settlement_grid(world):
    """Return dict mapping (x,y) -> {name, kind, char, region}."""
    grid = {}
    for region in world.regions:
        for s in region.settlements:
            grid[(s.x, s.y)] = {
                'name': s.name,
                'kind': s.kind,
                'char': s.char,
                'region': region.name,
                'population': s.population,
            }
    return grid

def render_map_with_overlays(world, overlays=None, show_settlements=True):
    """Render map with optional overlay colors at specific positions.
    
    overlays: dict mapping (x,y) -> {'color': int, 'char': str, 'bold': bool}
    """
    from world import TERRAIN
    lines = []
    
    # Title bar
    lines.append(f"{ANSI_BOLD}wyrd — seed {world.seed}{ANSI_RESET}")
    lines.append(f"{world.width}×{world.height} | {len(world.regions)} regions\n")
    
    # Build settlement lookup
    settlement_grid = {}
    for region in world.regions:
        for s in region.settlements:
            if (s.x, s.y) not in settlement_grid or show_settlements:
                settlement_grid[(s.x, s.y)] = s
    
    overlay = overlays or {}
    
    # Map body
    for y in range(world.height):
        row_chars = []
        for x in range(world.width):
            # Check overlay first
            if (x, y) in overlay:
                ov = overlay[(x, y)]
                if ov.get('bold', True):
                    row_chars.append(f"{_color(ov['color'])}{ANSI_BOLD}{ov['char']}{ANSI_RESET}")
                else:
                    row_chars.append(f"{_color(ov['color'])}{ov['char']}{ANSI_RESET}")
                continue
            
            terrain_key = world.terrain[y][x]
            info = TERRAIN[terrain_key]
            
            if (x, y) in settlement_grid and show_settlements:
                s = settlement_grid[(x, y)]
                row_chars.append(f"{_color(226)}{ANSI_BOLD}{s.char}{ANSI_RESET}")
            else:
                # Check landmark
                landmark_char = None
                landmark_color = None
                for lm in world.landmarks:
                    if lm.x == x and lm.y == y:
                        landmark_char = lm.char
                        landmark_color = lm.color
                        break
                if landmark_char:
                    row_chars.append(f"{_color(landmark_color)}{ANSI_BOLD}{landmark_char}{ANSI_RESET}")
                else:
                    # Check adventure zone
                    zone_char = None
                    zone_color = None
                    for z in world.adventure_zones:
                        if z.x == x and z.y == y:
                            zone_char = z.char
                            zone_color = z.color
                            break
                    if zone_char and show_settlements:
                        row_chars.append(f"{_color(zone_color)}{ANSI_BOLD}{zone_char}{ANSI_RESET}")
                    else:
                        row_chars.append(f"{_color(info['color'])}{info['char']}{ANSI_RESET}")
        lines.append("".join(row_chars))
    
    # Legend
    lines.append("")
    for key, info in TERRAIN.items():
        lines.append(f"  {_color(info['color'])}{info['char']}{ANSI_RESET}  {info['desc']}")
    lines.append(f"\n  {_color(226)}{ANSI_BOLD}●{ANSI_RESET}  Settlement")
    
    # Animation legend (if overlays active)
    if overlays:
        lines.append(f"  {_color(46)}{ANSI_BOLD}↑{ANSI_RESET}  Growing")
        lines.append(f"  {_color(196)}{ANSI_BOLD}↓{ANSI_RESET}  Declining")
        lines.append(f"  {_color(220)}{ANSI_BOLD}✦{ANSI_RESET}  Newly founded")
        lines.append(f"  {_color(243)}{ANSI_BOLD}✗{ANSI_RESET}  Abandoned")
    
    # Region list
    lines.append(f"\n{ANSI_BOLD}Regions:{ANSI_RESET}")
    for region in world.regions:
        settlements = ", ".join(f"{s.name} ({s.kind})" for s in region.settlements)
        lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET} — {settlements}")
    
    return "\n".join(lines)

# Quick test
w = generate_world(42, width=40, height=20)
grid = build_settlement_grid(w)
print(f"Settlement grid: {len(grid)} settlements")

# Test with an overlay
test_overlay = {}
for i, ((x, y), info) in enumerate(grid.items()):
    if i == 0:
        test_overlay[(x, y)] = {'color': 46, 'char': '↑', 'bold': True}
    elif i == 1:
        test_overlay[(x, y)] = {'color': 196, 'char': '↓', 'bold': True}
    elif i == 2:
        test_overlay[(x, y)] = {'color': 220, 'char': '✦', 'bold': True}
    break

map_str = render_map_with_overlays(w, overlays=test_overlay)
# Print just the map portion (no full output)
for line in map_str.split('\n')[:25]:
    print(line.strip()[:80] if len(line) > 80 else line)
print("\nOverlay test OK")
