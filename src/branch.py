"""
wyrd — Branching Timeline Visualisation (Phase 7).

Shows alternative simulation paths from the same starting world.
Compares population, settlements, events, and era histories
across different seed offsets.

Usage:
    wyrd branch --seed 42 --years 300
    wyrd branch --load world.json --years 200 --from-year 100
"""

from .sim import run_simulation, SimResult, render_sim_detailed
from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color


def run_branch_comparison(world, num_years: int = 200,
                          chaos_factor: float = 0.3,
                          offsets: list[int] | None = None) -> dict[int, SimResult]:
    """Run multiple sims with different seed offsets and return results."""
    if offsets is None:
        offsets = [0, 1]

    characters = None
    if world.narrative:
        characters = world.narrative.characters

    results = {}
    for offset in offsets:
        result = run_simulation(
            world,
            num_years=num_years,
            seed_offset=offset,
            chaos_factor=chaos_factor,
            snapshot_interval=50,
            characters=characters,
        )
        results[offset] = result

    return results


def render_branch_comparison(world, results: dict[int, SimResult]) -> str:
    """Render a side-by-side comparison of branching timelines."""
    lines = []
    offsets = sorted(results.keys())
    cyan = _color(45)
    yellow = _color(226)
    green = _color(28)
    red = _color(196)
    dim = _color(240)

    # ── Header ────────────────────────────────────────────────────
    lines.append(f"{ANSI_BOLD}{cyan}═══ wyrd Branch Comparison ═══{ANSI_RESET}")
    lines.append(f"{ANSI_DIM}Seed: {world.seed}  |  Years: {results[offsets[0]].num_years}{ANSI_RESET}")
    lines.append("")

    # ── Summary per branch ────────────────────────────────────────
    for offset in offsets:
        r = results[offset]
        s = r.summary
        pop_change = s["end_population"] - s["start_population"]
        pop_sign = "+" if pop_change >= 0 else ""
        pop_pct = (pop_change / max(s["start_population"], 1)) * 100

        lines.append(f"  {ANSI_BOLD}Branch {offset}{ANSI_RESET}  "
                      f"(seed {r.seed})")
        lines.append(f"    {yellow}Population:{ANSI_RESET} "
                      f"{s['start_population']:,} → {s['end_population']:,} "
                      f"({pop_sign}{pop_change:,} / {pop_pct:+.0f}%)")
        lines.append(f"    {yellow}Settlements:{ANSI_RESET} "
                      f"{s['start_settlements']} → {s['end_settlements']} "
                      f"({s['abandoned']} abandoned)")
        lines.append(f"    {yellow}Events:{ANSI_RESET} {s['events']}")
        lines.append(f"    {yellow}Final Era:{ANSI_RESET} "
                      f"{r.final_state.current_era}")
        lines.append("")

    # ── Divergence — Events ───────────────────────────────────────
    if len(offsets) >= 2:
        lines.append(f"{ANSI_BOLD}{cyan}Event Comparison{ANSI_RESET} "
                      f"(last 8 events per branch){ANSI_DIM}")
        lines.append(f"{'':─^60}{ANSI_RESET}")

        # Show events by year, interleaved
        r0 = results[offsets[0]]
        r1 = results[offsets[1]]

        event_icons = {
            "plague": "☠", "famine": "🌾", "war": "⚔",
            "discovery": "✦", "prosperity": "↑", "disaster": "🌋",
            "exodus": "→", "founding": "▲", "abandonment": "✗",
            "trade_boom": "💰",
        }

        # Collect and merge last N events
        max_events = 8
        recent_0 = r0.events[-max_events:] if len(r0.events) >= max_events else r0.events[:]
        recent_1 = r1.events[-max_events:] if len(r1.events) >= max_events else r1.events[:]

        # Show paired by index
        max_idx = max(len(recent_0), len(recent_1))
        for i in range(max_idx):
            line_parts = []
            for ri, offset in [(recent_0, offsets[0]), (recent_1, offsets[1])]:
                if i < len(ri):
                    ev = ri[i]
                    icon = event_icons.get(ev.event_type, "·")
                    desc = ev.description[:45]
                    line_parts.append(
                        f"[{ev.year:>3}] {icon} {desc}"
                    )
                else:
                    line_parts.append(f"{'—':^52}")

            # Truncate to terminal width
            combined = f"  {green}B{offsets[0]}:{ANSI_RESET} {line_parts[0][:55]}  "
            combined += f"  {red}B{offsets[1]}:{ANSI_RESET} {line_parts[1][:55]}"
            lines.append(combined)

        lines.append("")

    # ── Era progression comparison ────────────────────────────────
    if len(offsets) >= 2:
        lines.append(f"{ANSI_BOLD}{cyan}Era Progression{ANSI_RESET}{ANSI_DIM}")
        lines.append(f"{'':─^60}{ANSI_RESET}")

        era_0 = results[offsets[0]].final_state.era_history
        era_1 = results[offsets[1]].final_state.era_history

        max_era = max(len(era_0), len(era_1))
        for i in range(max_era):
            parts = []
            for era_list, offset in [(era_0, offsets[0]), (era_1, offsets[1])]:
                if i < len(era_list):
                    e = era_list[i]
                    parts.append(f"Y{e['year']:>3}: {e['era_name']:<25}")
                else:
                    parts.append(f"{'':<32}")
            lines.append(f"  {green}B{offsets[0]}:{ANSI_RESET} {parts[0]}  "
                          f"{red}B{offsets[1]}:{ANSI_RESET} {parts[1]}")

        lines.append("")

    # ── Divergence stats ──────────────────────────────────────────
    if len(offsets) >= 2:
        r0 = results[offsets[0]]
        r1 = results[offsets[1]]

        pop_diff = abs(r0.summary["end_population"] - r1.summary["end_population"])
        settle_diff = abs(r0.summary["end_settlements"] - r1.summary["end_settlements"])
        event_overlap = len(set(e.description for e in r0.events) & set(e.description for e in r1.events))
        total_events_both = max(len(r0.events) + len(r1.events), 1)

        lines.append(f"{ANSI_BOLD}{cyan}Divergence Metrics{ANSI_RESET}")
        lines.append(f"  Population difference: {yellow}{pop_diff:,}{ANSI_RESET}")
        lines.append(f"  Settlement difference: {yellow}{settle_diff}{ANSI_RESET}")
        lines.append(f"  Shared events: {dim}{event_overlap}/{total_events_both - event_overlap} "
                      f"unique{ANSI_RESET}")
        lines.append("")

    # ── Footer ────────────────────────────────────────────────────
    for offset in offsets:
        r = results[offset]
        lines.append(f"{ANSI_DIM}Branch {offset}: {r.summary['end_population']} souls "
                      f"across {r.summary['end_settlements']} settlements "
                      f"at year {r.summary['years_simulated']}{ANSI_RESET}")

    return "\n".join(lines)
