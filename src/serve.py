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

    def do_GET(self):
        path = self.path.rstrip("/") or "/"
        try:
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
            elif path == "/api/worlds":
                self._handle_api_worlds()
            elif path.startswith("/api/world/"):
                parts = path[len("/api/world/"):].split("/")
                seed = int(parts[0])
                if len(parts) >= 3 and parts[1] == "snapshot":
                    self._handle_api_world(seed, int(parts[2]))
                else:
                    self._handle_api_world(seed)
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

    def _send_json(self, data: dict):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

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
):
    """Start the wyrd web dashboard server."""
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
