"""
wyrd — Conversational World Agent (Phase 8).

Ask natural-language questions about any generated world.
Two modes:
  - **LLM-powered** (default): Uses OpenAI-compatible API for rich, fluent answers.
    Configure with env vars: WYRD_LLM_API_KEY, WYRD_LLM_ENDPOINT, WYRD_LLM_MODEL
  - **Deterministic** (--no-llm): Builds on query.py's pattern matching. Always works.

Usage:
    wyrd ask --seed 42 "What's the most powerful city?"
    wyrd ask --seed 42 --year 150 "What happened during the war?"
    wyrd ask --seed 42 --no-llm "Tell me about the northern regions"
"""

import json
import os
import re
import urllib.request
import urllib.error
from typing import Optional

from .world import World, TERRAIN
from .query import query_world
from .render import ANSI_BOLD, ANSI_RESET, ANSI_DIM, ANSI_ITALIC, _color


# ── Context Gathering ─────────────────────────────────────────────────


def _world_stats(world: World) -> str:
    """Build a brief stat block for the world."""
    total_pop = sum(s.population for r in world.regions for s in r.settlements)
    land = sum(1 for row in world.terrain for t in row
               if t not in ("deep_water", "shallow"))
    water = world.tiles - land

    lines = [
        f"Seed: {world.seed}",
        f"Size: {world.width}×{world.height} ({world.tiles:,} tiles)",
        f"Land/Water: {land:,}/{water:,} ({land/world.tiles*100:.0f}% land)",
        f"Regions: {len(world.regions)}",
        f"Settlements: {sum(len(r.settlements) for r in world.regions)}",
        f"Population: {total_pop:,} souls",
    ]
    return "\n".join(lines)


def _regions_summary(world: World) -> str:
    """List all regions with biome, settlement count, and population."""
    lines = []
    for region in world.regions:
        pop = sum(s.population for s in region.settlements)
        settle_names = ", ".join(
            f"{s.name} ({s.kind}, {s.population})"
            for s in region.settlements[:5]
        )
        extra = f" + {len(region.settlements) - 5} more" if len(region.settlements) > 5 else ""
        lines.append(f"- {region.name} ({region.biome}): {len(region.settlements)} settlements, {pop:,} population")
        lines.append(f"  Settlements: {settle_names}{extra}")

        # Lore per region
        if world.lore:
            if region.name in world.lore.cultures:
                lines.append(f"  Culture: {world.lore.cultures[region.name]}")
            if region.name in world.lore.histories:
                lines.append(f"  History: {world.lore.histories[region.name]}")
    return "\n".join(lines)


def _lore_summary(world: World) -> str:
    """Summarize lore data: features, cultures, relationships."""
    if not world.lore:
        return "(No lore data)"

    lines = []
    if world.lore.features:
        lines.append("Geographical Features:")
        for feat in world.lore.features[:8]:
            lines.append(f"- {feat['name']}: {feat['desc']}")
        if len(world.lore.features) > 8:
            lines.append(f"- ... and {len(world.lore.features) - 8} more features")

    if world.lore.relationships:
        lines.append("\nSettlement Relationships:")
        for rel in world.lore.relationships[:6]:
            lines.append(f"- {rel['description']}")
        if len(world.lore.relationships) > 6:
            lines.append(f"- ... and {len(world.lore.relationships) - 6} more")

    return "\n".join(lines)


def _narrative_summary(world: World) -> str:
    """Summarize narrative data: characters, events, quests."""
    if not world.narrative:
        return "(No narrative data)"

    lines = []
    chars = world.narrative.characters
    if chars:
        by_occ = {}
        for c in chars:
            by_occ.setdefault(c.occupation, []).append(c.name)
        lines.append(f"Characters ({len(chars)} total):")
        notable = [c for c in chars if c.occupation in (
            "ruler", "general", "wizard", "high_priest", "merchant_prince",
            "spymaster", "admiral", "chancellor"
        )]
        for c in notable[:8]:
            lines.append(f"- {c.name} {c.surname} ({c.occupation}, {c.home_settlement})")
        if len(notable) > 8:
            lines.append(f"- ... and {len(notable) - 8} more notable figures")

    if world.narrative.events:
        lines.append(f"\nEvents ({len(world.narrative.events)} total):")
        for e in world.narrative.events[:4]:
            lines.append(f"- [{e.year}] {e.name}: {e.description[:120]}")
        if len(world.narrative.events) > 4:
            lines.append(f"- ... and {len(world.narrative.events) - 4} more events")

    if world.narrative.quests:
        lines.append(f"\nQuests ({len(world.narrative.quests)} total):")
        for q in world.narrative.quests[:3]:
            lines.append(f"- {q.name} ({q.difficulty}): {q.description[:100]}")
        if len(world.narrative.quests) > 3:
            lines.append(f"- ... and {len(world.narrative.quests) - 3} more quests")

    return "\n".join(lines)


def _chronicles_summary(world: World) -> str:
    """Summarize historical eras."""
    if not world.chronicles or not world.chronicles.eras:
        return "(No chronicles data)"

    lines = [f"World Age: {world.chronicles.world_age} years"]
    for era in world.chronicles.eras:
        mods = ", ".join(era.world_modifiers[:3]) if era.world_modifiers else ""
        mod_str = f" [{mods}]" if mods else ""
        lines.append(f"- {era.name} ({era.start_year}-{era.end_year}): {era.description[:100]}{mod_str}")

    return "\n".join(lines)


def _magic_summary(world: World) -> str:
    """Summarize magic system."""
    if not world.magic:
        return "(No magic system)"

    lines = [
        f"Source: {world.magic.source}",
        f"Practitioners: {world.magic.practitioners}",
        f"Description: {world.magic.description[:200]}",
    ]
    if world.magic.schools:
        lines.append(f"\nSchools ({len(world.magic.schools)}):")
        for s in world.magic.schools[:4]:
            lines.append(f"- {s.name} ({s.alignment}): {s.description[:80]}")
    if world.magic.traditions:
        lines.append(f"\nTraditions ({len(world.magic.traditions)}):")
        for t in world.magic.traditions[:4]:
            lines.append(f"- {t.name} (origin: {t.origin}): {t.description[:80]}")

    return "\n".join(lines)


def _gather_context(world: World) -> dict:
    """Gather all world context into a structured dict for the LLM."""
    return {
        "world_stats": _world_stats(world),
        "regions": _regions_summary(world),
        "lore": _lore_summary(world),
        "narrative": _narrative_summary(world),
        "chronicles": _chronicles_summary(world),
        "magic": _magic_summary(world),
        "terrain_tiles": {
            t_key: {
                "char": TERRAIN[t_key]["char"],
                "desc": TERRAIN[t_key]["desc"],
            }
            for t_key in ["deep_water", "shallow", "sand", "grass", "forest",
                          "hills", "mountains", "snow", "river"]
        },
    }


# ── LLM Mode ──────────────────────────────────────────────────────────


def _get_llm_config() -> dict:
    """Read LLM configuration from environment variables.

    Returns:
        dict with keys: api_key, endpoint, model
        Raises ValueError if WYRD_LLM_API_KEY is missing in LLM mode.
    """
    api_key = os.environ.get("WYRD_LLM_API_KEY", "")
    endpoint = os.environ.get(
        "WYRD_LLM_ENDPOINT",
        "https://api.openai.com/v1/chat/completions",
    )
    model = os.environ.get("WYRD_LLM_MODEL", "gpt-4o-mini")
    return {"api_key": api_key, "endpoint": endpoint, "model": model}


def _build_llm_prompt(context: dict, question: str) -> list[dict]:
    """Build the messages array for the LLM chat completion API.

    Includes a system prompt that establishes the agent's persona as a
    wise scholar of the world, grounded in the provided context data.
    """
    context_json = json.dumps(context, indent=2, ensure_ascii=False)

    system_prompt = (
        "You are a wise scholar and chronicler of a fantasy world called wyrd. "
        "You have access to the world's complete data — its geography, cultures, "
        "settlements, history, notable characters, and even its magic system. "
        "Answer the user's question in a natural, engaging way, as if you've "
        "personally studied this world for years. Be specific and reference "
        "actual names, places, and events from the data provided. "
        "If the question asks about something not in the data, say so directly "
        "rather than making things up. Keep your answer concise (2-4 paragraphs "
        "typically) but vivid. Use the world's own names and terminology."
        "\n\nHere is the complete world data:\n\n"
        f"{context_json}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]


def _call_llm(messages: list[dict], config: dict) -> str:
    """Call the OpenAI-compatible chat completion API.

    Args:
        messages: List of message dicts with role/content.
        config: LLM config dict from _get_llm_config().

    Returns:
        The model's response text.

    Raises:
        ValueError: On API errors, network failures, or bad responses.
    """
    api_key = config["api_key"]
    endpoint = config["endpoint"]
    model = config["model"]

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ValueError(
            f"LLM API returned HTTP {e.code}: {detail[:200]}"
        ) from e
    except (urllib.error.URLError, OSError) as e:
        raise ValueError(
            f"Could not reach LLM API at {endpoint}: {e}"
        ) from e
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM API returned non-JSON response: {e}") from e

    choices = result.get("choices", [])
    if not choices:
        raise ValueError(
            f"LLM API returned empty choices: {json.dumps(result)[:200]}"
        )

    return choices[0].get("message", {}).get("content", "").strip()


# ── Deterministic Fallback Mode ────────────────────────────────────────


def _deterministic_answer(world: World, question: str) -> str:
    """Answer a question using deterministic pattern matching.

    Builds on query.py's structured query engine, then adds context-aware
    enhancements for richer answers.

    Args:
        world: A World object.
        question: Natural-language question.

    Returns:
        A formatted answer string.
    """
    # Try the existing query engine first
    result = query_world(world, question)
    if result.found:
        # Strip ANSI for clean output; use the rendered form
        rendered = result.render(color=True)
        return rendered

    # Fallback: keyword search with richer formatting
    from .query import _handle_keyword
    kw_result = _handle_keyword(world, question)
    if kw_result.found:
        return kw_result.render(color=True)

    # Ultimate fallback: summary of what we know
    lines = [
        f"{ANSI_BOLD}I don't have a direct answer to that question.{ANSI_RESET}",
        "",
        "Here's what I know about this world:",
        "",
    ]

    total_pop = sum(s.population for r in world.regions for s in r.settlements)
    lines.append(f"  {ANSI_BOLD}World:{ANSI_RESET} wyrd #{world.seed} — "
                 f"{world.width}×{world.height}, {total_pop:,} souls across "
                 f"{sum(len(r.settlements) for r in world.regions)} settlements "
                 f"in {len(world.regions)} regions.")

    if world.lore:
        feat_count = len(world.lore.features)
        rel_count = len(world.lore.relationships)
        lines.append(f"  {ANSI_BOLD}Lore:{ANSI_RESET} {feat_count} geographical features, "
                     f"{rel_count} settlement relationships.")

    if world.narrative:
        char_count = len(world.narrative.characters)
        event_count = len(world.narrative.events)
        lines.append(f"  {ANSI_BOLD}History:{ANSI_RESET} {char_count} notable characters, "
                     f"{event_count} recorded events.")

    if world.magic:
        lines.append(f"  {ANSI_BOLD}Magic:{ANSI_RESET} {world.magic.name} — "
                     f"{len(world.magic.schools)} schools of magic.")

    lines.append("")
    lines.append(f"{ANSI_DIM}Try a more specific question, like:")
    lines.append(f"  \"What's the largest city?\"")
    lines.append(f"  \"Tell me about the cultures\"")
    lines.append(f"  \"What events happened in the north?\"{ANSI_RESET}")

    return "\n".join(lines)


# ── Main Interface ─────────────────────────────────────────────────────


def ask_about_world(
    world: World,
    question: str,
    use_llm: bool = True,
) -> str:
    """Answer a natural-language question about a world.

    Args:
        world: A generated World object.
        question: Natural-language question string.
        use_llm: If True (default), attempt LLM-powered answer.
                 If False, use deterministic pattern matching.

    Returns:
        A formatted answer string.
    """
    if not question or not question.strip():
        question = "Give me an overview of this world."

    if use_llm:
        try:
            config = _get_llm_config()
            if not config["api_key"]:
                # No API key configured — fall through to deterministic
                # with a note
                return (
                    f"{ANSI_DIM}(No WYRD_LLM_API_KEY set; falling back to "
                    f"deterministic mode){ANSI_RESET}\n\n"
                    + _deterministic_answer(world, question)
                )

            context = _gather_context(world)
            messages = _build_llm_prompt(context, question)
            answer = _call_llm(messages, config)
            return answer

        except ValueError as e:
            # LLM failed — fall back with explanation
            return (
                f"{ANSI_DIM}(LLM query failed: {e}. "
                f"Falling back to deterministic mode.){ANSI_RESET}\n\n"
                + _deterministic_answer(world, question)
            )

    # Deterministic mode
    return _deterministic_answer(world, question)
