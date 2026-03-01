---
id: docs-kb-fixes
title: "Documentation & KB Fixes"
type: backlog_item
tags:
- improvement
- documentation
- kb
- code-hardening
kind: improvement
priority: high
effort: S
status: planned
links:
- roadmap
---

# Documentation & KB Fixes

**Wave 4 of 0.9 Code Hardening.** Fix stale counts, broken links, and inaccurate descriptions across docs and KB files. Zero code changes — doc-only.

## Items

| Item | Files | Effort |
|------|-------|--------|
| Fix test counts in README, CLAUDE.md | `README.md`, `CLAUDE.md` | XS |
| Fix MCP_SUBMISSION.md inaccuracies (tool names, config, counts) | `MCP_SUBMISSION.md` | S |
| Update BACKLOG.md staleness (In Progress, Prioritized Next Up) | `kb/backlog/BACKLOG.md` | S |
| Fix broken wikilinks in KB (`[[pyrite-db]]` → `[[storage-layer]]`, relative links) | `kb/components/mcp-server.md`, `kb/backlog/BACKLOG.md` | XS |
| Link ADR-0014/0015 in roadmap | `kb/roadmap.md` | XS |
| Fix README "SvelteKit 5" → "SvelteKit 2 with Svelte 5" | `README.md` | XS |

## Definition of Done

- All test counts match `pytest --co -q | tail -1`
- MCP_SUBMISSION.md tool names match actual MCP server tool list
- No broken `[[wikilinks]]` in KB (verified via `pyrite qa validate`)
- BACKLOG.md "In Progress" section reflects actual state
- README technology descriptions are accurate
