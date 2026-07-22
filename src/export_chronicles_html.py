"""
wyrd — Chronicles HTML exporter.

Generates a standalone HTML chronicle page from generated world history.
Styling is self-contained (inline CSS), no external dependencies.
"""

import html as html_mod

from .world import World


_ERA_TYPE_EMOJIS = {
    "founding": "🏛️",
    "golden_age": "✨",
    "cataclysm": "🌋",
    "dark_age": "🌑",
    "age_of": "📜",
    "decline": "📉",
    "rebirth": "🌱",
    "schism": "⚔️",
}

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Georgia', 'Times New Roman', serif;
  background: #0f0f12;
  color: #d4d4dc;
  line-height: 1.7;
  padding: 2rem;
  max-width: 900px;
  margin: 0 auto;
}
h1 {
  color: #e8c87a;
  font-size: 2.2rem;
  text-align: center;
  margin-bottom: 0.5rem;
  letter-spacing: 0.05em;
}
.subtitle {
  text-align: center;
  color: #6a6a72;
  margin-bottom: 3rem;
  font-style: italic;
}
.era {
  background: #1a1a22;
  border-left: 4px solid #555;
  margin-bottom: 2rem;
  padding: 1.5rem 2rem;
  border-radius: 0 8px 8px 0;
  position: relative;
}
.era.founding { border-left-color: #4caf50; }
.era.golden_age { border-left-color: #ffd54f; }
.era.cataclysm { border-left-color: #f44336; }
.era.dark_age { border-left-color: #616161; }
.era.age_of { border-left-color: #42a5f5; }
.era.decline { border-left-color: #ff7043; }
.era.rebirth { border-left-color: #ce93d8; }
.era.schism { border-left-color: #ef5350; }
.era.present {
  border-left-width: 6px;
  background: #1e1e2a;
  box-shadow: 0 0 20px rgba(232, 200, 122, 0.08);
}
.era-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}
.era-number {
  color: #555;
  font-size: 0.85rem;
  min-width: 3.5rem;
}
.era-emoji { font-size: 1.3rem; }
.era-name {
  color: #e8c87a;
  font-size: 1.3rem;
  font-weight: bold;
}
.era-type {
  color: #888;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  background: #2a2a35;
  padding: 0.15rem 0.6rem;
  border-radius: 3px;
}
.era-date {
  color: #6a6a72;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  font-style: italic;
}
.era-description {
  margin-bottom: 1rem;
  color: #c8c8d0;
}
.modifiers {
  margin-bottom: 0.8rem;
}
.modifier {
  color: #a68b5b;
  font-size: 0.9rem;
  margin-left: 0.5rem;
}
.modifier::before { content: "◊ "; }
.events-title {
  color: #6a6a72;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-bottom: 0.5rem;
  margin-top: 0.5rem;
}
.event {
  margin-bottom: 0.8rem;
  padding-left: 1.5rem;
  border-left: 1px solid #333;
}
.event-year {
  color: #555;
  font-size: 0.85rem;
  font-family: 'Courier New', monospace;
}
.event-name {
  color: #a5d6ff;
  font-weight: bold;
}
.event-desc { color: #b0b0b8; }
.event-participants {
  color: #6a6a72;
  font-size: 0.85rem;
  font-style: italic;
}
.footer {
  text-align: center;
  color: #444;
  margin-top: 3rem;
  font-size: 0.85rem;
  border-top: 1px solid #222;
  padding-top: 1.5rem;
}
"""


def export_chronicles_html(world: World) -> str:
    """Generate standalone HTML chronicle page."""
    chronicles = getattr(world, "chronicles", None)
    if not chronicles or not chronicles.eras:
        return "<html><body><p>No chronicles available.</p></body></html>"

    parts = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('  <meta charset="UTF-8">')
    parts.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append(f"  <title>wyrd #{world.seed} — The Chronicles</title>")
    parts.append(f"  <style>{_CSS}</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append(f'  <h1>📖 wyrd #{html_mod.escape(str(world.seed))}</h1>')
    parts.append(f'  <p class="subtitle">The Chronicles — {chronicles.num_eras} eras spanning {chronicles.world_age} years</p>')

    for i, era in enumerate(chronicles.eras):
        era_num = i + 1
        era_type = era.era_type
        emoji = _ERA_TYPE_EMOJIS.get(era_type, "📜")
        present_class = " present" if era.is_present else ""
        era_type_display = era_type.replace("_", " ")

        parts.append(f'  <div class="era {html_mod.escape(era_type)}{present_class}">')

        # Header
        parts.append('    <div class="era-header">')
        parts.append(f'      <span class="era-number">Era {era_num}</span>')
        parts.append(f'      <span class="era-emoji">{emoji}</span>')
        parts.append(f'      <span class="era-name">{html_mod.escape(era.name)}</span>')
        parts.append(f'      <span class="era-type">{html_mod.escape(era_type_display)}</span>')
        parts.append("    </div>")

        # Date
        date_str = f"Year {era.start_year} — Year {era.end_year}"
        if era.is_present:
            date_str += " (Present Age)"
        parts.append(f'    <div class="era-date">{html_mod.escape(date_str)}</div>')

        # Description
        parts.append(f'    <div class="era-description">{html_mod.escape(era.description)}</div>')

        # World modifiers
        if era.world_modifiers:
            parts.append('    <div class="modifiers">')
            for mod in era.world_modifiers:
                parts.append(f'      <span class="modifier">{html_mod.escape(mod)}</span><br>')
            parts.append("    </div>")

        # Events
        if era.events:
            parts.append('    <div class="events-title">── Events ──</div>')
            for ev in era.events:
                ev_year = ev.get("year", "?")
                ev_name = ev.get("name", "Unknown Event")
                ev_desc = ev.get("description", "")
                ev_chars = ev.get("characters", [])

                parts.append('    <div class="event">')
                parts.append(f'      <span class="event-year">[{ev_year}]</span>')
                parts.append(f'      <span class="event-name">{html_mod.escape(ev_name)}</span>')
                parts.append(f'      <div class="event-desc">{html_mod.escape(ev_desc)}</div>')
                if ev_chars:
                    chars_str = ", ".join(ev_chars)
                    parts.append(f'      <div class="event-participants">Legendary participants: {html_mod.escape(chars_str)}</div>')
                parts.append("    </div>")

        parts.append("  </div>")

    # Footer
    parts.append(f'  <div class="footer">')
    parts.append(f'    Generated by <strong>wyrd</strong> — seed {world.seed}')
    parts.append("  </div>")
    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts)
