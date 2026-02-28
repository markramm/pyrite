---
id: roadmap
title: Pyrite Release Roadmap
type: note
tags:
- roadmap
- planning
---

# Pyrite Release Roadmap

## 0.3 — CLI Foundation (done)

Established the core CLI, storage layer, service architecture, and plugin system. Everything downstream builds on this.

Key deliverables: multi-KB support, FTS5 search, plugin protocol (12 methods), service layer enforcement, three-tier MCP server, SvelteKit web UI, content negotiation, collections, block references (phases 1-2), background embedding pipeline, REST API tier enforcement.

---

## 0.4 — MCP Server Hardening

**Theme:** Make the MCP server production-solid for agent-driven workflows. This is the primary interface for AI agents doing research through Claude Desktop and Claude Code.

### Bugs (7 failing tests)

| Item | Description | Effort |
|------|-------------|--------|
| MCP metadata passthrough | `kb_create` drops custom metadata fields for generic, event, and person types. 3 failing tests. | S |
| Integration event file paths | `test_create_event_and_search` and `test_deleted_file_syncs` fail — event entries saved to wrong path. | S |
| CLI body-file frontmatter merge | `--body-file` with YAML frontmatter doesn't merge extra fields (kind, etc.) into output. 2 failing tests. | S |

### Features

| # | Item | Description | Effort |
|---|------|-------------|--------|
| 72 | Capture Lane Validation | Controlled vocabulary in `kb.yaml`, validate capture lanes on save. Foundation for QA tier 1. | M |
| — | MCP error messages | Review error messages across all MCP tools for clarity. Agents waste tokens on opaque errors. | S |
| — | MCP tool documentation | Improve inputSchema descriptions so agents understand constraints without trial-and-error. | S |

### Definition of done

- All 1030+ tests pass (zero failures)
- All MCP tools have clear error messages and accurate inputSchema descriptions
- Capture lane validation enforced on `kb_create` and `kb_update`
- Manual verification: create entries with metadata via Claude Desktop, confirm round-trip

---

## 0.5 — QA Agent (Phases 1-2)

**Theme:** Automated quality assurance. Make KB quality a measurable, queryable property instead of an assumption.

### Phase 1: Structural Validation (effort: M)

Pure Python, no LLM. Runs on every save or as batch sweep.

| Deliverable | Description |
|-------------|-------------|
| `QAService` | `validate_entry()` and `validate_all()` methods |
| Validation rules | Per-type checks: required fields, date formats, importance range, controlled vocabulary, link targets resolve, non-empty bodies |
| CLI | `pyrite qa validate [--kb <name>] [--entry <id>] [--fix]` |
| MCP tool | `kb_qa_validate` (read tier) |
| Post-save hook | Optional automatic validation on entry create/update |

### Phase 2: QA Assessment Entries (effort: M)

QA results as first-class KB entries, queryable and trackable.

| Deliverable | Description |
|-------------|-------------|
| `qa_assessment` entry type | Schema with target_entry, tier, status (pass/warn/fail), issues list, confidence scores |
| Query interface | "Show all entries with open issues", "unassessed entries", "verification rate by capture lane" |
| CLI | `pyrite qa status [--kb <name>]` — dashboard of assessment coverage |
| MCP tool | `kb_qa_status` (read tier) |

### Definition of done

- Tier 1 validation catches: missing required fields, bad dates, out-of-range importance, broken wikilinks, vocabulary violations
- QA assessments are stored as entries, linked to targets, queryable via search and MCP
- `pyrite qa status` shows coverage: X% of entries assessed, Y open issues
- All existing tests still pass

---

## 0.6 — Web UI Polish

**Theme:** Bring the web experience up to parity with the agent experience. Complete unfinished UI features, improve usability.

### Core features

| # | Item | Description | Effort |
|---|------|-------------|--------|
| 60 | Block Refs Phase 3: Transclusion Rendering | Full `![[entry#heading]]` and `![[entry^block-id]]` rendering in Tiptap. WebSocket live updates, cycle detection, export modes. Frontend extension partially built. | L |
| 64 | Collections Phase 4: Embedding | Embed collections in entries, nested collection support. Blocked by #60. | M |
| — | QA dashboard | Web UI for QA assessment status — verification rates, issue trends, entries needing review. Builds on 0.5 QA data. | M |

### Graph enhancements (pick 1-2)

| # | Item | Description | Effort |
|---|------|-------------|--------|
| — | Graph betweenness centrality | Size nodes by BC to highlight bridging entries | M |
| — | Graph community detection | Detect clusters, color by community instead of type | M |
| — | Graph structural gap detection | Find missing links between distant clusters | L |

### Quality of life

| Item | Description | Effort |
|------|-------------|--------|
| AI writing assistant | Select text in editor → summarize/expand/rewrite/continue | L |
| Offline/performance | IndexedDB cache, virtual scrolling for large KBs | L |

### Definition of done

- Transclusions render inline with live updates
- QA assessment data visible in web UI
- At least one graph enhancement shipped
- Manual verification: navigate a 1000+ entry KB smoothly in the web UI

---

## Future (0.7+)

Items not yet scheduled, for consideration after 0.6:

- **QA Agent Phases 3-5** — LLM consistency checks, factual verification, continuous pipeline
- **Coordination/Task Plugin** — Structured task tracking within the knowledge graph
- **Canvas/Whiteboard** — Freeform spatial canvas
- **Git Sync Conflict Resolution UI** — Visual merge conflict resolution
- **Engagement Federation** — Sync engagement data across instances
- **Offline Support** (if not done in 0.6)

---

## Versioning notes

Milestones are scope-driven, not time-driven. Each milestone ships when its definition of done is met. Bug fixes and small improvements may land between milestones without bumping the version.
