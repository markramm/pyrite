---
id: epic-migrate-kleptocracy-timeline-to-pyrite-managed-kb
title: 'Epic: Migrate kleptocracy timeline to Pyrite-managed KB'
type: backlog_item
tags:
- cascade
- migration
- epic
- capturecascade
links:
- target: support-string-or-ref-actor-fields-in-cascade-events
  relation: has_subtask
  kb: pyrite
- target: actor-alias-suggestion-and-fuzzy-matching-tool
  relation: has_subtask
  kb: pyrite
- target: actor-extraction-and-migration-tool-for-cascade-timelines
  relation: has_subtask
  kb: pyrite
- target: backlink-indexing-for-string-based-actor-references
  relation: has_subtask
  kb: pyrite
- target: cascade-timeline-static-export-for-viewer-consumption
  relation: has_subtask
  kb: pyrite
- target: source-url-validation-and-content-verification-for-qa
  relation: has_subtask
  kb: pyrite
- target: source-content-verification-via-llm
  relation: has_subtask
  kb: pyrite
- target: ai-hallucination-detection-for-research-kbs
  relation: has_subtask
  kb: pyrite
kind: epic
status: done
priority: high
effort: XL
---

## Overview

Migrate the kleptocracy timeline project (capturecascade.org) from its current ad-hoc script-based management into a Pyrite-managed knowledge base. The timeline contains 4,400+ events spanning 1142-2026, with ~1,235 unique actors, custom validation scripts, actor alias normalization, source quality frameworks, and a React + Hugo viewer deployed to GitHub Pages.

## Current Architecture

**Repo:** github.com/markramm/CaptureCascadeTimeline (mono-repo)
- `timeline/data/events/` — 4,400+ markdown files with YAML frontmatter (source of truth)
- `timeline/data/actor_aliases.json` — 880-line alias mapping (~250 canonical actors)
- `timeline/scripts/` — custom Python validation, normalization, API generation, QA audit
- `timeline/viewer/` — React SPA consuming static JSON API files
- `hugo-site/` — Hugo static site reading markdown directly
- `.github/workflows/ci-cd.yml` — validate → build React + Hugo → deploy GitHub Pages
- `.claude/agents/` — research-executor and quality-improver agent configs

## Target Architecture

**KB managed by Pyrite** (Cascade plugin):
- Pyrite handles: validation, QA, search, normalization, actor management, MCP access
- Actor entries as first-class KB entries with aliases and backlinks
- Research agents create events via Pyrite MCP/CLI instead of raw file writes
- QA includes source URL validation and content verification

**Viewer remains custom** (same repo or separate):
- CI/CD runs `pyrite cascade export` to generate static JSON API files
- React viewer and Hugo site consume exported data (unchanged)
- Deployed to capturecascade.org via GitHub Pages

## Dependencies (Backlog Items)

1. **Support string-or-ref actor fields in Cascade events** — schema change to accept both formats
2. **Actor alias suggestion and fuzzy matching tool** — port alias detection from timeline project
3. **Actor extraction and migration tool** — create actor entries from event string references
4. **Backlink indexing for string-based actor references** — index string actors for backlinks/graph
5. **Cascade timeline static export for viewer consumption** — replace custom generate.py
6. **Source URL liveness checking** — verify source URLs return 200
7. **Source content verification via LLM** — verify sources support entry claims
8. **AI hallucination detection** — web search for independent corroboration

## Migration Steps

1. Add `kb.yaml` to kleptocracy timeline repo pointing Pyrite at `timeline/data/events/`
2. Verify Pyrite indexes all 4,400+ events correctly
3. Extract actors into KB entries using migration tool
4. Replace `generate.py` with `pyrite cascade export` in CI/CD
5. Replace custom validation scripts with `pyrite qa validate` + `pyrite ci`
6. Update .claude/agents to use Pyrite MCP for event creation
7. Run source URL validation on existing events
8. Update pre-commit hooks to use Pyrite validation

## Success Criteria

- All 4,400+ events indexed and searchable in Pyrite
- Actor entries with backlinks to all referencing events
- CI/CD pipeline uses Pyrite commands instead of custom scripts
- capturecascade.org viewer works identically (no visible changes)
- Research agents create events via Pyrite MCP
- QA includes URL validation and source verification
- No data loss during migration
