# Session: 2026-07-22 (Wednesday)
# What was built:
# - Phase 6 is fully complete (7/7 items, 215 tests pass)
# - Phase 7.1: Interactive curses sim viewer (src/viewer.py)
#   - wyrd view --seed 42 --years 300 shows map evolving year by year
#   - Pause/resume (Space), speed (+/-), step forward (→)
#   - Population chart overlay (p), event log panel
#   - 7 tests in tests/test_viewer.py
# - gitignore cleaned up for _test_*.py patterns
#
# Next session priority:
# Phase 7.2 — Named character integration in sim events
#   - Sim events should reference actual narrative characters (leaders, heroes)
#   - When founding: use a named character as founder
#   - When war: use named characters as commanders
#   - Requires: importing narrative.py's Character objects into sim.py
#
# Phase 7.3 — Character-driven founding events
#   - New settlements founded by named characters
#   - Migration events tied to character backstories
#   - Characters can be assigned to settlements as leaders
#
# Architecture notes for next session:
# - viewer.py imports _simulate_tick from sim.py (same-package import)
# - Settlement markers: yellow(active), green(new), dim(abandoned)
# - The map layout in viewer: header→stats→map→events→footer
# - sim.py simulate_years() signature unchanged — use _simulate_tick for
#   year-by-year control in viewer
# - apply_sim_state_to_world() creates deep copy with evolved settlements
# - initialize_sim_state() converts World settlements → SettlementSnapshots
