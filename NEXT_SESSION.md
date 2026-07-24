# Session: 2026-07-28

## What was done

- **Lookup false-positive bug fix.** `wyrd lookup <query>` was returning irrelevant
  results for unrelated queries (e.g. "nonexistent" → "Fallen Bones"). Root cause:
  `_score()` accepted any SequenceMatcher ratio >0.4 even when the longest matching
  block was a short accidental trigram ("one" in "nonexistent" and "Fallen Bones").
  
  Fix: The SM path now requires **≥4 contiguous matching characters** before
  accepting the ratio. Substring matching and word-overlap matching are unaffected.
  
  Removed unused `import re`.

## Next directions

- Project is in maintenance/surface-polish mode — all 6 major phases (19–23.5) complete.
- Look for visual bugs, rendering glitches, or UX edge cases.
- Doc drift check: 4 undocumented modules (embody_tui, export_chronicles_html,
  faction_sim, shop). pantheon.md is 1 line over the 100-line doc limit.
- NEXT_SESSION.md cleanup — keep this file current after each session.
