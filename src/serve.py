"""
wyrd — Web Dashboard Server (Phase 8: The Web Awakens).

Serves a beautiful dark-themed web dashboard for any generated world.
Uses only Python stdlib — no external dependencies.

Usage:
    wyrd serve --seed 42              # Serve a specific world
    wyrd serve                        # List all worlds
    wyrd serve --port 8080            # Custom port
"""

import json
import os
import re
import webbrowser
from datetime import date
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from .world import World, TERRAIN
from .export_html import (
    export_world_html,
    _terrain_color_hex,
    _ruin_color_hex,
)


# ── Helpers ────────────────────────────────────────────────────────

def _load_world(seed: int) -> Optional[World]:
    """Load a world by seed from JSON file."""
    from .serialize import load_world
    path = f"wyrd-{seed}.json"
    if not os.path.exists(path):
        return None
    try:
        return load_world(path)
    except Exception:
        return None


def _load_sim_data(seed: int) -> Optional[dict]:
    """Load simulation data for a world seed."""
    from .serialize import load_sim_state
    sim_file = f"wyrd-{seed}-sim.json"
    data = load_sim_state(sim_file)
    if data is None:
        data = load_sim_state(sim_file + ".gz")
    return data


def _find_worlds() -> list[dict]:
    """Find all world files and return metadata."""
    import glob
    scan_dir = "."
    pattern = os.path.join(scan_dir, "wyrd-*.json")
    world_files = sorted(glob.glob(pattern))
    world_files = [
        wf for wf in world_files
        if not re.search(r'-sim\.json', wf)
        and not re.search(r'\.ttrpg\.json', wf)
    ]

    # Check for sim files — extract seed from filename
    sim_seeds = set()
    sim_pattern = os.path.join(scan_dir, "wyrd-*-sim.json*")
    for sf in sorted(glob.glob(sim_pattern)):
        fname = os.path.basename(sf)
        if fname.endswith(".gz"):
            fname = fname[:-3]
        m = re.match(r"wyrd-(\d+)-sim\.json", fname)
        if m:
            sim_seeds.add(int(m.group(1)))
    worlds = []
    for wf in world_files:
        try:
            with open(wf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        seed = data.get("seed", 0)
        total_pop = sum(
            s.get("population", 0)
            for r in data.get("regions", [])
            for s in r.get("settlements", [])
        )
        num_settlements = sum(
            len(r.get("settlements", []))
            for r in data.get("regions", [])
        )
        worlds.append({
            "seed": seed,
            "dimensions": f'{data.get("width", 0)}×{data.get("height", 0)}',
            "population": total_pop,
            "settlements": num_settlements,
            "regions": len(data.get("regions", [])),
            "has_lore": "lore" in data and data["lore"] is not None,
            "has_narrative": "narrative" in data and data["narrative"] is not None,
            "has_chronicles": "chronicles" in data and data["chronicles"] is not None,
            "has_magic": "magic" in data and data["magic"] is not None,
            "has_sim": seed in sim_seeds,
            "file": os.path.basename(wf),
        })
    return worlds


def _get_snapshot_years(seed: int) -> list[int]:
    """Get available snapshot years for a world."""
    sim_data = _load_sim_data(seed)
    if not sim_data:
        return []
    return sorted(int(k) for k in sim_data.get("snapshots", {}).keys())


def _apply_snapshot(world: World, year: int) -> World:
    """Apply sim snapshot state to a world."""
    from .sim import apply_sim_state_to_world, SimState, SettlementSnapshot
    sim_data = _load_sim_data(world.seed)
    if not sim_data:
        return world
    raw = sim_data.get("snapshots", {}).get(str(year))
    if raw is None:
        return world
    state = SimState(year=raw["year"])
    for name, sd in raw.get("settlements", {}).items():
        state.settlements[name] = SettlementSnapshot(**sd)
    state.world_modifiers = raw.get("world_modifiers", [])
    for pr in raw.get("population_record", []):
        state.population_record.append(pr)
    return apply_sim_state_to_world(world, state)


# ── HTML Templates ─────────────────────────────────────────────────

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>wyrd — {title}</title>
<style>
  :root {{
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #1c2333;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #e94560;
    --gold: #ffd700;
    --green: #3fb950;
    --blue: #58a6ff;
    --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    min-height: 100vh;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
  a {{ color: var(--blue); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
  h1 .seed-tag {{ color: var(--muted); font-weight: normal; font-size: 1rem; }}
  .subtitle {{ color: var(--muted); margin-bottom: 1.5rem; font-size: 0.9rem; }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }}
  .badge {{
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
    font-size: 0.75rem; font-weight: 600; margin-right: 0.25rem;
  }}
  .badge-lore {{ background: #1a3a1a; color: var(--green); }}
  .badge-narrative {{ background: #1a2a3a; color: var(--blue); }}
  .badge-chronicles {{ background: #3a3a1a; color: var(--gold); }}
  .badge-magic {{ background: #2a1a3a; color: var(--purple); }}
  .badge-sim {{ background: #3a1a1a; color: var(--accent); }}
  .card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1rem; margin-bottom: 1rem;
  }}
  .card:hover {{ border-color: #484f58; }}
  .stat-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem; margin-bottom: 1.5rem;
  }}
  .stat-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1rem; text-align: center;
  }}
  .stat-value {{ font-size: 1.5rem; font-weight: 700; color: var(--gold); }}
  .stat-label {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.25rem; }}
  .map {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: {font_size}px; line-height: 1.15; white-space: pre; background: var(--surface2); padding: 1rem; border-radius: 8px; overflow-x: auto; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.75rem 0; font-size: 0.85rem; }}
  .legend-item {{ display: flex; align-items: center; gap: 0.4rem; }}
  .btn {{
    display: inline-block; padding: 0.4rem 1rem; border-radius: 6px;
    font-size: 0.85rem; font-weight: 600; cursor: pointer;
    border: 1px solid var(--border); background: var(--surface2);
    color: var(--text); text-decoration: none;
  }}
  .btn:hover {{ background: #21262d; text-decoration: none; }}
  .btn-primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
  .btn-primary:hover {{ background: #d63850; }}
  .snapshot-nav {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }}
  .snapshot-nav a {{ padding: 0.3rem 0.7rem; border-radius: 4px; background: var(--surface2); border: 1px solid var(--border); font-size: 0.8rem; }}
  .snapshot-nav a.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--muted); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  tr:hover {{ background: var(--surface2); }}
  .footer {{ color: var(--muted); font-size: 0.75rem; text-align: center; margin-top: 2rem; border-top: 1px solid var(--border); padding-top: 1rem; }}
  .event {{ padding: 0.5rem 0; border-bottom: 1px solid var(--border); font-size: 0.85rem; }}
  .event:last-child {{ border-bottom: none; }}
  .event-year {{ color: var(--gold); font-weight: 600; margin-right: 0.5rem; }}
  .event-type {{ display: inline-block; padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.7rem; text-transform: uppercase; margin-right: 0.5rem; }}
  .type-war {{ background: #3a1a1a; color: #ff6b6b; }}
  .type-plague {{ background: #3a1a2a; color: #ff8cc8; }}
  .type-famine {{ background: #3a2a1a; color: #ffb347; }}
  .type-founding {{ background: #1a3a1a; color: #69db7c; }}
  .type-discovery {{ background: #1a2a3a; color: #74c0fc; }}
  .type-trade {{ background: #2a2a1a; color: #ffd43b; }}
  .type-abandonment {{ background: #2a1a1a; color: #868686; }}
  .nav-bar {{
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 0.75rem 2rem; display: flex; align-items: center; gap: 1rem;
  }}
  .nav-bar .brand {{ font-weight: 700; font-size: 1.1rem; color: var(--accent); }}
  .nav-bar .nav-link {{ color: var(--muted); font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="nav-bar">
  <span class="brand">⚄ wyrd</span>
  <a class="nav-link" href="/">Worlds</a>
  <span class="nav-link" style="color:var(--muted);">— {title}</span>
</div>
<div class="container">
"""

PAGE_FOOT = """
<div class="footer">
  Generated by <a href="https://github.com/shift-zero/wyrd">wyrd</a>
  &mdash; {date}
</div>
</div>
</body>
</html>"""


# ── Server Logic ───────────────────────────────────────────────────

PORT = 8080

class WyrdHandler(BaseHTTPRequestHandler):
    """HTTP request handler for wyrd dashboard."""

    def _parse_pagination(self) -> tuple[int, int]:
        """Parse limit/offset query params. Returns (offset, limit)."""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            limit = max(1, min(100, int(params.get("limit", ["20"])[0])))
        except (ValueError, TypeError):
            limit = 20
        try:
            offset = max(0, int(params.get("offset", ["0"])[0]))
        except (ValueError, TypeError):
            offset = 0
        return offset, limit

    def _paginated(self, items: list, total: int | None = None) -> dict:
        offset, limit = self._parse_pagination()
        page = items[offset:offset + limit]
        return {
            "data": page,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "returned": len(page),
                "total": total if total is not None else len(items),
            },
        }

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            # ── HTML Dashboard (existing) ─────────────────────────────
            if path == "/" or path == "/worlds":
                self._handle_worlds()
            elif path.startswith("/world/"):
                parts = path[len("/world/"):].split("/")
                seed_str = parts[0]
                try:
                    seed = int(seed_str)
                except ValueError:
                    self._send_error(400, f"Invalid seed: {seed_str}")
                    return
                if len(parts) >= 3 and parts[1] == "snapshot":
                    year = int(parts[2])
                    self._handle_world_detail(seed, year)
                elif len(parts) >= 3 and parts[1] == "events":
                    year = int(parts[2]) if len(parts) > 2 else None
                    self._handle_world_events(seed, year)
                else:
                    self._handle_world_detail(seed)

            # ── Legacy /api/* (backward compat) ──────────────────────
            elif path == "/api/worlds":
                self._handle_api_worlds()
            elif path.startswith("/api/world/"):
                parts = path[len("/api/world/"):].split("/")
                seed = int(parts[0])
                if len(parts) >= 3 and parts[1] == "snapshot":
                    self._handle_api_world(seed, int(parts[2]))
                else:
                    self._handle_api_world(seed)

            # ── REST API v1 ──────────────────────────────────────────
            elif path.startswith("/api/v1/") or path == "/api/v1":
                self._handle_api_v1()

            else:
                self._send_error(404, f"Not found: {path}")
        except Exception as e:
            self._send_error(500, f"Server error: {e}")
            import traceback
            traceback.print_exc()

    def _send_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_json_error(self, status: int, message: str):
        self._send_json({"error": message}, status=status)

    def _send_error(self, code: int, message: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<!DOCTYPE html><html><head><title>{code}</title>
<style>body{{background:#0d1117;color:#e6edf3;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;}}
h1{{color:#e94560;}}p{{color:#8b949e;}}</style></head>
<body><div><h1>{code}</h1><p>{message}</p>
<a href="/" style="color:#58a6ff;">← Back to worlds</a></div></body></html>"""
        self.wfile.write(html.encode("utf-8"))

    def _handle_worlds(self):
        worlds = _find_worlds()
        if not worlds:
            html = PAGE_HEAD.format(title="Worlds", font_size=14)
            html += '<h1>⚄ wyrd</h1><p class="subtitle">No worlds found. Generate one with <code>wyrd generate --seed 42</code></p>'
            html += PAGE_FOOT.format(date=date.today().isoformat())
            self._send_html(html)
            return

        rows = []
        for w in worlds:
            badges = []
            if w["has_lore"]: badges.append('<span class="badge badge-lore">L</span>')
            if w["has_narrative"]: badges.append('<span class="badge badge-narrative">N</span>')
            if w["has_chronicles"]: badges.append('<span class="badge badge-chronicles">C</span>')
            if w["has_magic"]: badges.append('<span class="badge badge-magic">M</span>')
            if w["has_sim"]: badges.append('<span class="badge badge-sim">S</span>')
            badge_str = " ".join(badges) if badges else '<span style="color:var(--muted);font-size:0.8rem;">(base)</span>'

            snapshots = _get_snapshot_years(w["seed"])
            snap_str = ""
            if snapshots:
                yr_range = f"{snapshots[0]}–{snapshots[-1]}" if len(snapshots) > 1 else str(snapshots[0])
                snap_str = f'<br><span style="font-size:0.75rem;color:var(--muted);">📸 {len(snapshots)} snapshots (Y{yr_range})</span>'

            rows.append(f"""<tr>
  <td><a href="/world/{w['seed']}" style="font-weight:600;">#{w['seed']}</a></td>
  <td style="color:var(--muted);">{w['dimensions']}</td>
  <td>{w['population']:,}</td>
  <td>{w['settlements']}</td>
  <td>{w['regions']}</td>
  <td>{badge_str}{snap_str}</td>
</tr>""")

        html = PAGE_HEAD.format(title="Worlds", font_size=14)
        html += f"""<h1>⚄ wyrd</h1>
<p class="subtitle">{len(worlds)} world{'s' if len(worlds) != 1 else ''} found</p>
<div class="card" style="padding:0;">
<table>
<thead><tr>
  <th>Seed</th><th>Size</th><th>Population</th><th>Settlements</th><th>Regions</th><th>Features</th>
</tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</div>"""
        html += PAGE_FOOT.format(date=date.today().isoformat())
        self._send_html(html)

    def _handle_world_detail(self, seed: int, snapshot_year: Optional[int] = None):
        world = _load_world(seed)
        if world is None:
            self._send_error(404, f"World #{seed} not found. Generate it first with `wyrd generate --seed {seed}`")
            return

        # Apply snapshot if requested
        if snapshot_year is not None:
            world = _apply_snapshot(world, snapshot_year)

        sim_data = _load_sim_data(seed) if os.path.exists(f"wyrd-{seed}-sim.json") else None
        snapshots = _get_snapshot_years(seed)

        # Stats
        total_pop = sum(s.population for r in world.regions for s in r.settlements)
        total_settlements = sum(len(r.settlements) for r in world.regions)
        has_modifiers = getattr(world, 'world_modifiers', []) or (sim_data and sim_data.get("world_modifiers", []))

        # Render map using export_html
        abandoned = []
        pop_record = []
        sim_events_count = 0
        if snapshot_year is not None and sim_data:
            raw = sim_data.get("snapshots", {}).get(str(snapshot_year), {})
            abandoned = [
                {"name": n, "x": s.get("x", 0), "y": s.get("y", 0)}
                for n, s in raw.get("settlements", {}).items()
                if s.get("status") == "abandoned"
            ]
            pop_record = raw.get("population_record", sim_data.get("population_record", []))
            sim_events_count = len(sim_data.get("events", []))

        map_html = export_world_html(
            world,
            snapshot_year=snapshot_year,
            abandoned_settlements=abandoned or None,
            population_record=pop_record or None,
            sim_events_count=sim_events_count,
        )

        # Extract just the map + legend from exported HTML
        map_start = map_html.find('<div class="map">')
        legend_start = map_html.find('<div class="legend">')
        legend_end = map_html.find("</div>", legend_start) + 6 if legend_start >= 0 else -1
        map_content = map_html[map_start:legend_end] if map_start >= 0 else "<p>Map unavailable</p>"
        # Clean up — extract just the map and legend divs
        if map_start >= 0 and legend_end >= 0:
            map_content = map_html[map_start:legend_end]
        elif map_start >= 0:
            map_end = map_html.find("</div>", map_start) + 6
            map_content = map_html[map_start:map_end]

        # Title
        if snapshot_year is not None:
            title = f"World #{seed} — Year {snapshot_year}"
        else:
            title = f"World #{seed}"

        # Snapshot navigation
        snap_nav = ""
        if len(snapshots) > 1:
            items = []
            for y in snapshots[:20]:  # Show first 20
                active = y == snapshot_year if snapshot_year else False
                cls = ' class="active"' if active else ""
                items.append(f'<a{cls} href="/world/{seed}/snapshot/{y}">Y{y}</a>')
            if len(snapshots) > 20:
                items.append(f'<span style="color:var(--muted);font-size:0.8rem;">… +{len(snapshots)-20} more</span>')
            snap_nav = f"""
<div class="snapshot-nav">
  <span style="color:var(--muted);font-size:0.8rem;margin-right:0.25rem;">📸 Snapshots:</span>
  {"".join(items)}
</div>"""

        font_size = max(6, min(14, int(600 / max(world.width, 1))))

        html = PAGE_HEAD.format(title=title, font_size=font_size)

        # Stats grid
        stats = f"""<div class="stat-grid">
  <div class="stat-card"><div class="stat-value">{total_pop:,}</div><div class="stat-label">Population</div></div>
  <div class="stat-card"><div class="stat-value">{total_settlements}</div><div class="stat-label">Settlements</div></div>
  <div class="stat-card"><div class="stat-value">{len(world.regions)}</div><div class="stat-label">Regions</div></div>
  <div class="stat-card"><div class="stat-value">{world.width}×{world.height}</div><div class="stat-label">Map Size</div></div>
"""
        if snapshot_year is not None:
            stats += f"""  <div class="stat-card"><div class="stat-value">Y{snapshot_year}</div><div class="stat-label">Snapshot Year</div></div>
"""
        if len(abandoned) > 0:
            stats += f"""  <div class="stat-card"><div class="stat-value" style="color:var(--muted);">{len(abandoned)}</div><div class="stat-label">Ruins</div></div>
"""
        stats += "</div>"

        html += f"""<h1>⚄ World <span class="seed-tag">#{seed}</span></h1>
<p class="subtitle">
  <a href="/">← All worlds</a>
  &nbsp;·&nbsp;
  <a href="/api/world/{seed}" target="_blank">JSON</a>
  {f'&nbsp;·&nbsp;<a href="/api/world/{seed}/snapshot/{snapshot_year}" target="_blank">JSON @ Y{snapshot_year}</a>' if snapshot_year else ''}
</p>
{snap_nav}
{stats}
"""

        # World modifiers
        if snapshot_year is not None and has_modifiers:
            mods = sim_data.get("snapshots", {}).get(str(snapshot_year), {}).get("world_modifiers", [])
            if mods:
                html += '<div class="card"><span style="font-size:0.8rem;color:var(--muted);">🌍 World Modifiers:</span> '
                html += " · ".join(f'<span style="color:var(--gold);font-size:0.85rem;">{m}</span>' for m in mods)
                html += "</div>"

        html += f"""<h2 style="font-size:1rem;margin-bottom:0.5rem;">🗺 Map</h2>
{map_content}
"""

        # Region info
        html += '<h2 style="font-size:1rem;margin:1rem 0 0.5rem;">🏞 Regions</h2>'
        html += '<div class="card" style="padding:0;"><table><thead><tr><th>Region</th><th>Biome</th><th>Settlements</th></tr></thead><tbody>'
        for r in world.regions:
            s_list = ", ".join(f'{s.name}' for s in r.settlements[:5])
            if len(r.settlements) > 5:
                s_list += f" … +{len(r.settlements)-5} more"
            html += f'<tr><td style="font-weight:600;color:var(--gold);">{r.name}</td><td style="color:var(--muted);">{r.biome}</td><td>{s_list or "<span style=color:var(--muted);>—</span>"}</td></tr>'
        html += '</tbody></table></div>'

        html += PAGE_FOOT.format(date=date.today().isoformat())
        self._send_html(html)

    def _handle_world_events(self, seed: int, snapshot_year: Optional[int] = None):
        """Show sim/narrative events for a world."""
        world = _load_world(seed)
        if world is None:
            self._send_error(404, f"World #{seed} not found.")
            return

        sim_data = _load_sim_data(seed)
        events = []

        if sim_data:
            for evt in sim_data.get("events", []):
                events.append({
                    "year": evt.get("year", 0),
                    "type": evt.get("event_type", "unknown"),
                    "description": evt.get("description", ""),
                })
        elif world.narrative and world.narrative.events:
            for evt in world.narrative.events:
                events.append({
                    "year": evt.year,
                    "type": evt.event_type,
                    "description": evt.description,
                })

        events.sort(key=lambda e: e["year"])

        html = PAGE_HEAD.format(title=f"World #{seed} Events", font_size=14)
        html += f'<h1>⚄ World <span class="seed-tag">#{seed}</span> — Events</h1>'
        html += f'<p class="subtitle"><a href="/world/{seed}">← Back to world</a> &nbsp;·&nbsp; {len(events)} events</p>'

        if not events:
            html += '<div class="card"><p style="color:var(--muted);">No events recorded for this world.</p></div>'
        else:
            html += '<div class="card">'
            for evt in events:
                type_class = f'type-{evt["type"]}'
                html += f"""<div class="event">
  <span class="event-year">Y{evt['year']}</span>
  <span class="event-type {type_class}">{evt['type']}</span>
  {evt['description']}
</div>"""
            html += '</div>'

        html += PAGE_FOOT.format(date=date.today().isoformat())
        self._send_html(html)

    def _handle_api_worlds(self):
        worlds = _find_worlds()
        self._send_json({"worlds": worlds})

    def _handle_api_world(self, seed: int, snapshot_year: Optional[int] = None):
        world = _load_world(seed)
        if world is None:
            self._send_error(404, f"World #{seed} not found.")
            return
        if snapshot_year is not None:
            world = _apply_snapshot(world, snapshot_year)
        from .serialize import world_to_dict
        data = world_to_dict(world)
        if snapshot_year is not None:
            data["snapshot_year"] = snapshot_year
        self._send_json(data)

    # ── REST API v1 ────────────────────────────────────────────────────

    def _handle_api_v1(self):
        """Dispatch REST API v1 requests."""
        path = self.path.split("?")[0].rstrip("/")
        rest = path[len("/api/v1/"):]

        # GET /api/v1
        if not rest:
            self._send_json({
                "wyrd": "Generative Fantasy Sandbox",
                "version": "0.1.0",
                "endpoints": {
                    "GET /worlds": "List all generated worlds",
                    "GET /worlds/<seed>": "World summary",
                    "GET /worlds/<seed>/regions": "All regions with settlements",
                    "GET /worlds/<seed>/settlements": "All settlements across regions",
                    "GET /worlds/<seed>/characters": "Narrative characters",
                    "GET /worlds/<seed>/quests": "Narrative quests",
                    "GET /worlds/<seed>/events": "Narrative + sim events",
                    "GET /worlds/<seed>/factions": "Factions with relationships",
                    "GET /worlds/<seed>/zones": "Adventure zones",
                    "GET /worlds/<seed>/pantheon": "Religion/pantheon data",
                    "GET /worlds/<seed>/economy": "Economy and trade routes",
                    "GET /worlds/<seed>/magic": "Magic system",
                    "GET /worlds/<seed>/simulation": "Simulation state",
                    "GET /worlds/<seed>/snapshots": "Available snapshot years",
                    "GET /worlds/<seed>/terrain": "Full terrain grid",
                },
                "docs": "https://github.com/shift-zero/wyrd",
            })
            return

        parts = rest.split("/")
        endpoint = parts[0]

        if endpoint == "worlds":
            if len(parts) == 1:
                self._api_list_worlds()
            elif len(parts) == 2:
                try:
                    seed = int(parts[1])
                except ValueError:
                    self._send_json({"error": f"Invalid seed: {parts[1]}"}, status=400)
                    return
                self._api_get_world(seed)
            elif len(parts) == 3:
                try:
                    seed = int(parts[1])
                except ValueError:
                    self._send_json({"error": f"Invalid seed: {parts[1]}"}, status=400)
                    return
                self._api_get_world_resource(seed, parts[2])
            else:
                self._send_json({"error": f"Unknown path: /api/v1/{rest}"}, status=404)
        else:
            self._send_json_error(404, f"Unknown endpoint: {endpoint}")

    def _load_api_world(self, seed: int):
        """Load a world for API use, returning None on failure."""
        world = _load_world(seed)
        if world is None:
            self._send_json_error(404, f"World #{seed} not found. Generate it with `wyrd generate --seed {seed}`")
            return None
        return world

    def _api_list_worlds(self):
        """GET /api/v1/worlds — List all generated worlds (paginated)."""
        worlds = _find_worlds()
        self._send_json(self._paginated(worlds))

    def _api_get_world(self, seed: int):
        """GET /api/v1/worlds/<seed> — World summary (not full dump)."""
        world = self._load_api_world(seed)
        if world is None:
            return
        total_pop = sum(s.population for r in world.regions for s in r.settlements)
        total_settlements = sum(len(r.settlements) for r in world.regions)
        terrain_counts = {}
        for row in world.terrain:
            for t in row:
                terrain_counts[t] = terrain_counts.get(t, 0) + 1
        data = {
            "seed": world.seed,
            "width": world.width,
            "height": world.height,
            "tiles": world.tiles,
            "regions": len(world.regions),
            "settlements": total_settlements,
            "population": total_pop,
            "rivers": len(world.rivers),
            "adventure_zones": len(world.adventure_zones),
            "factions": len(world.factions),
            "has_lore": world.lore is not None,
            "has_narrative": world.narrative is not None,
            "has_chronicles": world.chronicles is not None,
            "has_magic": world.magic is not None,
            "has_pantheon": world.pantheon is not None,
            "has_bestiary": len(world.bestiary) > 0,
            "terrain_distribution": terrain_counts,
        }
        self._send_json(data)

    def _api_get_world_resource(self, seed: int, resource: str):
        """GET /api/v1/worlds/<seed>/<resource> — Specific resource."""
        if resource in ("simulation", "snapshots", "terrain"):
            world = _load_world(seed)
            if world is None:
                self._send_json_error(404, f"World #{seed} not found.")
                return
        else:
            world = self._load_api_world(seed)
        if world is None:
            return

        if resource == "regions":
            result = []
            for r in world.regions:
                s_list = [{"name": s.name, "x": s.x, "y": s.y,
                           "population": s.population, "kind": s.kind}
                          for s in r.settlements]
                result.append({"name": r.name, "biome": r.biome,
                               "settlements": s_list,
                               "settlement_count": len(s_list),
                               "total_population": sum(s.population for s in r.settlements)})
            self._send_json(self._paginated(result))

        elif resource == "settlements":
            result = []
            for r in world.regions:
                for s in r.settlements:
                    result.append({
                        "name": s.name, "x": s.x, "y": s.y,
                        "population": s.population, "kind": s.kind,
                        "region": r.name, "biome": r.biome,
                    })
            self._send_json(self._paginated(result))

        elif resource == "characters":
            if world.narrative and world.narrative.characters:
                chars = []
                for c in world.narrative.characters:
                    chars.append({
                        "name": c.name, "surname": c.surname,
                        "full_name": c.full_name, "age": c.age,
                        "gender": c.gender, "occupation": c.occupation,
                        "personality_traits": c.personality_traits,
                        "home_region": c.home_region,
                        "home_settlement": c.home_settlement,
                        "backstory": c.backstory, "status": c.status,
                    })
                self._send_json(self._paginated(chars))
            else:
                self._send_json({"data": [], "pagination": {"offset": 0, "limit": 20, "returned": 0, "total": 0}})

        elif resource == "quests":
            if world.narrative and hasattr(world.narrative, 'quests') and world.narrative.quests:
                quests = []
                for q in world.narrative.quests:
                    quests.append({
                        "name": q.name, "quest_type": q.quest_type,
                        "difficulty": q.difficulty, "description": q.description,
                        "giver_character": q.giver_character,
                        "giver_settlement": q.giver_settlement,
                        "target_region": q.target_region,
                        "rewards": q.rewards, "is_active": q.is_active,
                    })
                self._send_json(self._paginated(quests))
            else:
                self._send_json({"data": [], "pagination": {"offset": 0, "limit": 20, "returned": 0, "total": 0}})

        elif resource == "events":
            events = []
            # Sim events
            sim_data = _load_sim_data(seed)
            if sim_data:
                for evt in sim_data.get("events", []):
                    events.append({
                        "year": evt.get("year", 0),
                        "type": evt.get("event_type", "unknown"),
                        "description": evt.get("description", ""),
                        "source": "simulation",
                    })
            # Narrative events
            if world.narrative and hasattr(world.narrative, 'events'):
                for evt in world.narrative.events:
                    events.append({
                        "year": evt.year,
                        "type": evt.event_type,
                        "description": evt.description,
                        "source": "narrative",
                        "regions_involved": evt.regions_involved,
                        "settlements_involved": evt.settlements_involved,
                        "characters_involved": evt.characters_involved,
                    })
            events.sort(key=lambda e: e["year"])
            self._send_json(self._paginated(events))

        elif resource == "factions":
            if world.factions:
                facs = []
                for f in world.factions:
                    facs.append({
                        "name": f.name, "faction_type": f.faction_type,
                        "icon": f.icon, "territory": f.territory,
                        "leader_name": f.leader_name, "leader_title": f.leader_title,
                        "influence": f.influence, "wealth": f.wealth,
                        "military": f.military, "stability": f.stability,
                        "power_score": f.power_score, "reputation": f.reputation,
                        "goals": f.goals, "description": f.description,
                    })
                result = {
                    "factions": facs,
                    "relationships": [
                        {
                            "faction_a": r.faction_a,
                            "faction_b": r.faction_b,
                            "rel_type": r.rel_type,
                            "description": r.description,
                        }
                        for r in world.faction_relationships
                    ],
                }
                self._send_json(result)
            else:
                self._send_json({"factions": [], "relationships": []})

        elif resource == "zones":
            if world.adventure_zones:
                zones = []
                for z in world.adventure_zones:
                    zones.append({
                        "name": z.name, "zone_type": z.zone_type,
                        "char": z.char, "x": z.x, "y": z.y,
                        "region": z.region, "difficulty": z.difficulty,
                        "inhabitants": z.inhabitants, "description": z.description,
                        "treasure_tier": z.treasure_tier, "quest_hook": z.quest_hook,
                    })
                self._send_json(self._paginated(zones))
            else:
                self._send_json({"data": [], "pagination": {"offset": 0, "limit": 20, "returned": 0, "total": 0}})

        elif resource == "pantheon":
            if world.pantheon:
                from .religion import PantheonSystem
                p = world.pantheon
                religions = []
                for rel in p.religions:
                    deities = []
                    for d in rel.deities:
                        deities.append({
                            "name": d.name, "surname": d.surname,
                            "full_name": f"{d.name} {d.surname}",
                            "domains": d.domains, "alignment": d.alignment,
                            "symbol": d.symbol, "holy_animal": d.holy_animal,
                            "description": d.description,
                        })
                    holy_sites = []
                    for hs in rel.holy_sites:
                        holy_sites.append({
                            "name": hs.name, "deity_name": hs.deity_name,
                            "site_type": hs.site_type, "settlement": hs.settlement,
                            "region": hs.region, "description": hs.description,
                        })
                    religions.append({
                        "name": rel.name, "description": rel.description,
                        "tenets": rel.tenets, "clergy_title": rel.clergy_title,
                        "holy_day": rel.holy_day, "alignment": rel.alignment,
                        "deities": deities, "holy_sites": holy_sites,
                    })
                self._send_json({"religions": religions,
                                 "total_deities": sum(len(r.deities) for r in p.religions),
                                 "total_holy_sites": sum(len(r.holy_sites) for r in p.religions)})
            else:
                self._send_json({"religions": [], "total_deities": 0, "total_holy_sites": 0})

        elif resource == "economy":
            # Check if sim data has economy info
            sim_data = _load_sim_data(seed)
            route_data = None
            if sim_data:
                routes = sim_data.get("trade_routes", [])
                economies = sim_data.get("settlement_economies", {})
                route_data = {
                    "routes": routes,
                    "settlement_economies": economies,
                }
            self._send_json({
                "has_economy_data": route_data is not None,
                "economy_data": route_data,
                "settlements": [
                    {"name": s.name, "region": r.name, "population": s.population}
                    for r in world.regions for s in r.settlements
                ],
            })

        elif resource == "magic":
            if world.magic:
                m = world.magic
                magic_data = {
                    "seed": m.seed,
                    "schools": [
                        {
                            "name": s.name, "color": s.color,
                            "description": s.description,
                            "traditions": [
                                {
                                    "name": t.name, "description": t.description,
                                    "color": t.color,
                                }
                                for t in getattr(s, 'traditions', [])
                            ],
                            "biome": getattr(s, 'biome', None),
                            "culture": getattr(s, 'culture', None),
                        }
                        for s in m.schools
                    ],
                }
                self._send_json(magic_data)
            else:
                self._send_json({"seed": seed, "schools": []})

        elif resource == "simulation":
            sim_data = _load_sim_data(seed)
            if sim_data:
                summary = {
                    "total_years": sim_data.get("year", 0),
                    "total_events": len(sim_data.get("events", [])),
                    "total_snapshots": len(sim_data.get("snapshots", {})),
                    "snapshot_years": sorted(int(k) for k in sim_data.get("snapshots", {}).keys()),
                    "population_record": sim_data.get("population_record", [])[-100:],
                    "world_modifiers": sim_data.get("world_modifiers", []),
                }
                self._send_json(summary)
            else:
                self._send_json({"total_years": 0, "total_events": 0,
                                 "total_snapshots": 0, "snapshot_years": [],
                                 "message": "No simulation data for this world."})

        elif resource == "snapshots":
            years = _get_snapshot_years(seed)
            sim_data = _load_sim_data(seed)
            snapshots = []
            for y in years:
                raw = sim_data.get("snapshots", {}).get(str(y), {}) if sim_data else {}
                settlements = raw.get("settlements", {})
                total_pop = sum(s.get("population", 0) for s in settlements.values())
                snapshots.append({
                    "year": y,
                    "settlements": len(settlements),
                    "population": total_pop,
                })
            self._send_json({"snapshots": snapshots})

        elif resource == "terrain":
            # Full terrain grid — useful for mapping tools
            grid = []
            for y in range(world.height):
                row = []
                for x in range(world.width):
                    t = world.terrain[y][x]
                    cell = {
                        "x": x, "y": y, "terrain": t,
                        "elevation": round(world.elevation[y][x], 4) if world.elevation else 0,
                    }
                    # Check for river
                    if (x, y) in world.rivers:
                        cell["river"] = True
                    # Check for landmark
                    for lm in getattr(world, 'landmarks', []):
                        if lm.x == x and lm.y == y:
                            cell["landmark"] = lm.name
                            cell["landmark_type"] = lm.landmark_type
                    row.append(cell)
                grid.append(row)
            self._send_json({"width": world.width, "height": world.height,
                             "grid": grid})

        else:
            self._send_error(404, f"Unknown resource: {resource}")

    def log_message(self, format, *args):
        """Quiet logging — only log actual requests, not favicon etc."""
        import sys
        msg = format % args
        if "/favicon" in msg:
            return
        sys.stderr.write(f"[wyrd] {self.client_address[0]} - {msg}\n")
        sys.stderr.flush()


def serve_world(
    seed: Optional[int] = None,
    port: int = 8080,
    open_browser: bool = True,
    rest_port: Optional[int] = None,
):
    """Start the wyrd web dashboard server, optionally with API-only server."""
    if rest_port is not None and rest_port != port:
        # Start a dedicated API-only server on rest_port
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class ApiHandler(WyrdHandler):
            """API-only handler — serves JSON, never HTML."""
            def _send_html(self, html: str):
                self._send_json({"error": "This server only serves JSON API. Use the dashboard server for HTML."})

            def do_GET(self):
                path = self.path.split("?")[0].rstrip("/") or "/"
                try:
                    if path.startswith("/api/v1/") or path == "/api/v1" or path == "/v1":
                        self._handle_api_v1()
                    elif path == "/":
                        self._send_json({
                            "wyrd": "Generative Fantasy Sandbox API",
                            "version": "0.1.0",
                            "docs": "http://127.0.0.1:{port}/api/v1/".format(port=rest_port),
                        })
                    else:
                        self._send_error(404, f"API endpoint not found: {path}")
                except Exception as e:
                    self._send_error(500, f"API error: {e}")
                    import traceback
                    traceback.print_exc()

        api_server = HTTPServer(("127.0.0.1", rest_port), ApiHandler)
        api_thread = threading.Thread(target=api_server.serve_forever, daemon=True)
        api_thread.start()
        print(f"⚄ wyrd API server running at http://127.0.0.1:{rest_port}/api/v1/")

    server = HTTPServer(("127.0.0.1", port), WyrdHandler)
    url = f"http://127.0.0.1:{port}"

    if seed is not None:
        world = _load_world(seed)
        if world is None:
            print(f"⚠ World #{seed} not found. Starting dashboard without target.")
        else:
            url += f"/world/{seed}"

    print(f"⚄ wyrd dashboard running at {url}")
    print(f"  Press Ctrl+C to stop.")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  wyrd server stopped.")
        server.server_close()


def serve_api(
    seed: Optional[int] = None,
    port: int = 9090,
):
    """Start a standalone REST API-only server."""
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class ApiHandler(WyrdHandler):
        """API-only handler."""
        def _send_html(self, html: str):
            self._send_json({"error": "This server only serves JSON API."})

        def do_GET(self):
            path = self.path.split("?")[0].rstrip("/") or "/"
            try:
                if path.startswith("/api/v1/") or path == "/api/v1" or path == "/v1":
                    self._handle_api_v1()
                elif path == "/":
                    self._send_json({
                        "wyrd": "Generative Fantasy Sandbox API",
                        "version": "0.1.0",
                        "docs": f"http://127.0.0.1:{port}/api/v1/",
                    })
                else:
                    self._send_error(404, f"API endpoint not found: {path}")
            except Exception as e:
                self._send_error(500, f"API error: {e}")
                import traceback
                traceback.print_exc()

    server = HTTPServer(("127.0.0.1", port), ApiHandler)
    print(f"⚄ wyrd API server running at http://127.0.0.1:{port}/api/v1/")
    print(f"  Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  wyrd API server stopped.")
        server.server_close()
