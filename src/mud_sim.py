"""wyrd — Background world simulation for the MUD.

The world evolves while the player explores. Every N game-hours, the world
sim advances by a month. Events bubble up as news, and room states change
based on sim outcomes (ruins, new factions, prosperity shifts).
"""

from __future__ import annotations

import random
from typing import Optional

from .world import World
from .room import Zone, Room
from .embody import PlayerCharacter


# ── State tracking ─────────────────────────────────────────────────────

class MudSimState:
    """Tracks background simulation state for the MUD."""

    def __init__(self, world: World, seed: int):
        self.total_hours: int = 0
        self.last_sim_month: int = 0  # last sim month that was applied
        self.last_sim_year: int = 0
        self.pending_news: list[str] = []
        self.world = world
        self.rng = random.Random(seed + 9000000)
        self._sim_state = None  # lazy-init

    def _ensure_sim(self):
        """Initialize sim state if not yet done."""
        if self._sim_state is None:
            from .sim import initialize_sim_state
            self._sim_state = initialize_sim_state(self.world)

    HOURS_PER_MONTH = 720  # 30 days * 24 hours

    def advance(self, hours: int) -> list[str]:
        """Advance the clock by N game-hours. Returns news events."""
        self.total_hours += hours
        news: list[str] = []

        # Check if we've crossed a month boundary
        current_month = self.total_hours // self.HOURS_PER_MONTH
        months_elapsed = current_month - self.last_sim_month

        if months_elapsed >= 1:
            self._ensure_sim()
            for _ in range(months_elapsed):
                month_news = self._tick_one_month()
                news.extend(month_news)

            self.last_sim_month = current_month
            self.pending_news.extend(news)

        return news

    def _tick_one_month(self) -> list[str]:
        """Advance the world sim by one month. Returns news strings."""
        self._ensure_sim()
        from .sim import _simulate_month_tick

        events = []
        cur_year = self.last_sim_year
        cur_month = self.last_sim_month % 12

        # Tick one month
        tick_events = _simulate_month_tick(
            self.world, self._sim_state, self.rng,
            cur_year, cur_month, 0.3,
        )

        event_news = []
        for ev in tick_events:
            label = {
                "founding": "🏘 New settlement founded",
                "abandonment": "🏚 Settlement abandoned",
                "war": "⚔ War declared",
                "faction_war": "⚔ Faction war",
                "faction_collapse": "💥 Faction collapses",
                "plague": "☠ Plague spreads",
                "famine": "🌾 Famine strikes",
                "discovery": "✨ Discovery made",
                "trade_boom": "📈 Trade boom",
                "earthquake": "🌋 Earthquake",
                "volcanic_eruption": "🌋 Volcanic eruption",
                "great_fire": "🔥 Great fire",
                "meteor_strike": "☄ Meteor strike",
                "great_plague": "☠ Great plague",
                "tsunami": "🌊 Tsunami",
            }.get(ev.event_type, f"📰 {ev.event_type}")

            desc = ev.description[:120] if ev.description else ""
            event_news.append(f"[dim]{label}: {desc}[/]")

        # Advance month counter
        self.last_sim_month += 1
        if self.last_sim_month % 12 == 0:
            self.last_sim_year += 1

        return event_news

    def get_news(self) -> list[str]:
        """Get and clear pending news."""
        news = self.pending_news[:]
        self.pending_news.clear()
        return news

    def apply_to_rooms(self, zones: dict[str, Zone]) -> None:
        """Update room states based on sim outcomes."""
        self._ensure_sim()
        if not self._sim_state:
            return

        # Check for abandoned settlements
        abandoned = set()
        if hasattr(self._sim_state, 'settlements'):
            for name, ss in self._sim_state.settlements.items():
                if hasattr(ss, 'abandoned') and ss.abandoned:
                    abandoned.add(name)

        # Update zone rooms for abandoned settlements
        for zone_name, zone in zones.items():
            if zone_name in abandoned and zone.zone_type == "settlement":
                for room in zone.rooms.values():
                    if "ruin" not in room.tags:
                        room.tags.append("ruin")
                        room.description = (
                            f"This room lies in ruins. The roof has partially collapsed, "
                            f"and the wind whistles through cracked walls. "
                            f"Signs of former life are barely visible beneath the decay."
                        )
