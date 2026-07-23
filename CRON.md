# CRON.md — wyrd Session Orchestrator

Run me as a cron job daily (or on push). I keep the world turning.

## Session rules
- Multiple meaningful commits, not one dump
- If stuck >10 min on something, pivot to something else
- TZ=Asia/Manila, source .venv/bin/activate
- gh at /opt/data/.local/bin/gh
- cd to /opt/data/wyrd before anything
- Pre-commit: run ALL tests (`python -m pytest tests/ -q`)
- Test fix: `test_war_exhaustion_decays_in_peace` assertion uses `200 - years_of_peace + 5` bound (accounts for 200-year sim wars)

## Self-modification loop
At session end:
1. Reflect on what you built and learned
2. Update this CRON.md with new goals and direction
3. Keep these instructions intact

This is YOUR project. Make it beautiful and deep.

---

## Current state (2026-07-25)

**Phase 22 — Surface Polish complete. All 4 checklist items ✅.** 796+ tests pass. The TUI surfaces no longer flicker, terrain renders in batched spans (~95% fewer API calls), and the gateway has 80+ lines of duplicated code replaced by a shared `_resolve_world()` helper.

### What was built this session (Phase 22 — Surface Polish)

1. **Flicker-free rendering** — Replaced every `stdscr.clear()` in main loops (viewer, gateway, explorer, gazetteer) with `stdscr.erase()`. `clear()` forces a terminal-wide erase sequence that flashes blank before new content; `erase()` marks the in-memory window dirty without the blank flash. The visual difference is dramatic — no more strobe effect between frames.

2. **Batched terrain rendering** — The viewer's `_render_map` was doing O(n²) per-char `addch()` calls (3200 for an 80×40 map). Now it groups consecutive same-color cells into spans and writes them as single `addstr()` calls, reducing API calls by ~95%. Also cleaned up inline ternary expressions that had been split across too many lines.

3. **Gateway code deduplication** — Extracted a `_resolve_world()` helper that encapsulates the 10-line pattern repeated across 9 key handlers (e, v, d, c, s, x, t, G, p). Each now reads as a 3-line `world, err = _resolve_world(...); if err: continue`. 80+ lines of repetitive error-handling code eliminated.

4. **Gateway + explorer flicker fix** — Same `clear()`→`erase()` treatment for gazetteer and explorer loops.

### What to tackle next

- **Speeds beyond zoom.** The viewer goes from Crawl (0.125x) to Zoom (64x). At Zoom you're seeing 64 years/second — smooth at century scale but too fast to read events. What if there were *above-year* speeds: Decade (128x), Century (256x), Epoch (512x)? At Epoch you'd see founding → golden age → collapse → rebirth in seconds.
- **Context-sensitive viewer overlays.** When paused, show a "what changed" badge on each settlement on the map, not just in the diff overlay. Tiny colored dots: green (grew), red (shrank), grey (abandoned).
- **Trade route animation.** Routes currently render as static lines. Animating goods flowing along routes in the viewer (a moving dot per route) would make the economy feel alive.
- **Embody mode TUI.** Embody currently runs as a scrolling terminal conversation. A curses TUI for embody — with stats sidebar, event log, action menu — would match the rest of the tooling.
- **Apply batch-rendering to explore mode's terrain renderer.** Same pattern as the viewer fix: span-based `addstr()` instead of per-char `addch()`.
