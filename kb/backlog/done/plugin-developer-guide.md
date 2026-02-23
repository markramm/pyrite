---
type: backlog_item
title: "Plugin Developer Guide"
kind: documentation
status: completed
priority: high
effort: M
tags: [documentation, plugins, developer-experience]
---

# Plugin Developer Guide

Write comprehensive documentation for building Pyrite plugins, based on patterns from the three existing extensions (Zettelkasten, Social, Encyclopedia).

## Scope

- Create `docs/plugin-guide.md` (or `kb/standards/plugin-developer-guide.md`)
- Cover all 11+ protocol methods with examples from real extensions
- Document how plugin types surface across CLI, API, MCP, and web UI
- Include testing patterns, fixture strategies, common pitfalls
- Document type metadata (ai_instructions, display hints, field descriptions)
- Include a "minimal plugin" walkthrough and a "full-featured plugin" reference
- Document entry point registration in pyproject.toml

## Sections

1. **Quick start** — Minimal plugin in 20 lines
2. **Plugin structure** — Entry points, plugin class, naming conventions
3. **Entry types** — Dataclass patterns, from_frontmatter/to_frontmatter, GenericEntry vs custom
4. **Type metadata** — AI instructions, field descriptions, display hints
5. **Validators** — Signature, context dict, error/warning dicts
6. **Hooks** — Lifecycle hooks, before/after patterns, permission enforcement
7. **Workflows** — State machines, transition rules, field binding
8. **CLI commands** — Typer integration, sub-apps vs single commands
9. **MCP tools** — Tier-aware tool registration, input schemas
10. **DB tables** — Custom tables vs metadata, when to use each
11. **KB presets** — Scaffolding new KBs with preset configurations
12. **Testing** — Test patterns, fixtures, integration testing
13. **Patterns & pitfalls** — Lessons from Zettelkasten, Social, Encyclopedia

## Key Sources

- `pyrite/plugins/protocol.py` — Protocol definition with docstrings
- `extensions/zettelkasten/` — Zettelkasten extension (types, relationships, workflows)
- `extensions/social/` — Social extension (hooks, DB tables, permissions)
- `extensions/encyclopedia/` — Encyclopedia extension (workflows, quality levels, reviews)
- `.claude/projects/*/memory/extension-building-learnings.md` — Patterns learned during extension building

## Acceptance Criteria

- [ ] Guide covers all protocol methods with real code examples
- [ ] Includes minimal plugin walkthrough that a developer can follow
- [ ] Documents testing patterns
- [ ] Documents how types appear in CLI, API, MCP, web UI
- [ ] Reviewed against all three existing extensions for accuracy

## References

- [ADR-0009](../adrs/0009-type-metadata-and-plugin-documentation.md)
- [ADR-0002](../adrs/0002-plugin-system-via-entry-points.md)
