# Documentation Conventions

Docs are not optional. They're the orientation layer that replaces re-reading the codebase every session. Maintain them like code.

## File Size Rule

Every doc file **must be < 100 lines** (target: 30-60 lines). If a doc exceeds 100 lines, it has too much content — split it into sub-docs that link to each other. Single responsibility applies to docs too.

## The Doc Web Pattern

Docs form a **linked web**, not a hierarchy. Each doc:

1. **Covers one topic** — one concept, one module, one system
2. **Links to others** via a "See also" section at the bottom
3. **Is reachable** from the hub (`AGENTS.md` doc map table)

Hub → sub-hubs → topic docs. Sub-hubs are for complex features (e.g. `export.md` links to `svg-export.md`).

## What Every Doc Should Have

- **Title** — H1 with the module/concept name
- **Body** — key facts, code snippets, data models, algorithms
- **See also** — links to related docs at the bottom

No fluff. No preamble. Get to the point.

## When to Update

- **New feature added?** Create a new doc + add it to the `AGENTS.md` doc map
- **Existing feature changed?** Update the relevant doc
- **Module renamed/split?** Update the doc, update links, update AGENTS.md

Treat docs as part of the feature — not an afterthought. If a cron session modifies wyrd source code, it must update or add docs in the same session.

## File Location

All docs live in `docs/`. The hub is `AGENTS.md` at the project root (portable for Hermes, Codex, Claude Code, etc.).

## Style

- Markdown only (`.md`)
- Links use relative paths: `[Architecture](docs/architecture.md)`
- Code blocks with language tags (```python)
- Tables for structured data
- No YAML frontmatter, no HTML (except export docs if needed)

## See also

- [AGENTS.md](../AGENTS.md) — the hub, doc map table
- [Overview](overview.md) — project overview
