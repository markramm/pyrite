---
id: roadmap
title: Pyrite Release Roadmap
type: note
tags:
- roadmap
- planning
---

# Pyrite Release Roadmap

## BHAG: Self-Configuring Knowledge Infrastructure for Agent Swarms

An autonomous agent encounters a domain, builds a Pyrite extension for it, provisions a KB, and starts working — all without human intervention. The schema is the program. Pyrite is the runtime. See [[bhag-self-configuring-knowledge-infrastructure]] for the full vision.

Every milestone below moves toward this goal.

---

## 0.3 — CLI Foundation (done)

Established the core CLI, storage layer, service architecture, and plugin system. Everything downstream builds on this.

Key deliverables: multi-KB support, FTS5 search, plugin protocol (15 methods), service layer enforcement, three-tier MCP server, SvelteKit web UI, content negotiation, collections, block references (phases 1-2), background embedding pipeline, REST API tier enforcement.

---

## 0.4 — MCP Server Hardening (done)

**Theme:** Make the MCP server production-solid for agent-driven workflows. This is the primary interface for AI agents doing research through Claude Desktop and Claude Code.

### Delivered

- **Fixed 7 failing tests**: metadata passthrough (3), event file paths (2), CLI body-file frontmatter merge (2)
- **Root causes**: `build_entry` plugin path was spreading metadata as top-level fm keys (lost by `from_frontmatter`); `_infer_subdir` didn't check plugin subtypes' parent core types; CLI extra kwargs dropped by same plugin path
- **Capture lane validation (#72)**: `allow_other: bool` on `FieldSchema` — unknown select/multi-select values produce warnings not errors when `allow_other: true`. Flexible vocabulary for agents.
- **Schema validation on all write paths**: `_kb_update` and `_kb_bulk_create` now call `KBSchema.validate_entry()` and surface warnings
- **MCP schema descriptions**: All `kb_update` parameters documented, validation behavior described in tool descriptions

### Results

- 1040 tests pass (zero failures, +10 new tests)
- All MCP tools have clear error messages and accurate inputSchema descriptions
- Capture lane validation enforced on `kb_create`, `kb_update`, and `kb_bulk_create`

---

## 0.5 — QA & Agent CLI (in progress)

**Theme:** Structural quality assurance and CLI completeness for agent workflows. Agents can validate their own work and interact with Pyrite entirely through structured output.

### QA Phase 1 — Structural Validation (done)

| Deliverable | Status |
|-------------|--------|
| `QAService` — `validate_entry()`, `validate_kb()`, `validate_all()`, `get_status()` | done |
| 9 validation rules: missing titles, empty bodies, broken links, orphans, invalid dates, importance range, event missing dates, schema violations | done |
| CLI: `pyrite qa validate [KB_NAME] [--entry ID] [--format json] [--severity]` + `pyrite qa status` | done |
| MCP tools: `kb_qa_validate`, `kb_qa_status` (read tier) | done |
| 17 new tests (15 service + 2 MCP), 1060 total passing | done |

### QA Phase 1.5 — Hooks & Remediation

| Deliverable | Description | Effort |
|-------------|-------------|--------|
| Post-save validation hook | Optional automatic validation on entry create/update | S |
| `--fix` flag | Auto-remediation for fixable issues (e.g., generate missing dates from ID) | S |

### Agent CLI Completeness

| Item | Description | Effort |
|------|-------------|--------|
| [[headless-kb-init]] | `pyrite init --template <domain>` with zero interactive prompts | M |
| [[cli-json-output-audit]] | Consistent `--format json` on every CLI command | M |
| [[extension-init-cli]] | `pyrite extension init <name>` scaffolding command | S |
| [[extension-install-cli]] | `pyrite extension install <path>` with verification | S |

### Definition of done

- `pyrite init --template software` creates a working KB non-interactively
- `--format json` returns clean JSON on every CLI command
- `pyrite qa validate` catches missing fields, bad dates, broken links, schema violations
- Extension scaffolding and install commands work end-to-end
- 1060+ tests passing

---

## 0.6 — Agent Coordination

**Theme:** Task management as a coordination primitive for agent swarms. Not a project management tool — an orchestration substrate.

### Coordination/Task Plugin (Phases 1-2)

| Phase | Description | Effort |
|-------|-------------|--------|
| Phase 1 | Core TaskEntry type, workflow state machine, CLI commands, validators | M |
| Phase 2 | MCP tools with atomic task_claim, task_decompose, task_checkpoint | M |

### Programmatic Schema Provisioning

| Item | Description | Effort |
|------|-------------|--------|
| [[programmatic-schema-provisioning]] | MCP and CLI tools to define types and fields without editing YAML | M |

### QA Phase 2 — Assessment Entries

| Deliverable | Description |
|-------------|-------------|
| `qa_assessment` entry type | Schema with target_entry, tier, status, issues list |
| Query interface | Entries with open issues, unassessed entries, verification rates |
| QA tasks | QA agent creates tasks via coordination plugin, links assessments as evidence |

### Definition of done

- An orchestrator agent can decompose a research question into subtasks, dispatch to agents, and track completion
- `task_claim` is atomic (no double-claims in concurrent swarms)
- Agent-authored entries are automatically validated on write
- QA assessments are queryable KB entries linked to targets and tasks

---

## 0.7 — Web UI Polish

**Theme:** Make the web experience demo-ready. Screenshots, screencasts, knowledge graph visualizations that tell the story.

### Content Features

| Item | Description | Effort |
|------|-------------|--------|
| Block Refs Phase 3: Transclusion Rendering | Full `![[entry#heading]]` and `![[entry^block-id]]` rendering in Tiptap. WebSocket live updates, cycle detection. | L |
| Collections Phase 4: Embedding | Embed collections in entries, nested collection support. | M |
| QA dashboard | Web UI for QA status — verification rates, issue trends, entries needing review. | M |

### Graph Enhancements (pick 1-2)

| Item | Description | Effort |
|------|-------------|--------|
| Graph betweenness centrality | Size nodes by BC to highlight bridging entries | M |
| Graph community detection | Detect clusters, color by community | M |
| Graph structural gap detection | Find missing links between distant clusters | L |

### Definition of done

- Transclusions render inline in the web editor
- QA assessment data visible in web UI
- At least one graph enhancement shipped
- Navigate a 1000+ entry KB smoothly

---

## 0.8 — Announceable Alpha

**Theme:** Distribution and first impressions. Everything a stranger needs to go from "interesting" to "I'm trying this."

### Packaging & Distribution

| Item | Description | Effort |
|------|-------------|--------|
| [[pypi-publish]] | Publish `pyrite` and `pyrite-mcp` to PyPI | S |
| Update MCP_SUBMISSION.md | Accurate tool count, test count, configuration examples | S |
| Consolidate docs/ | Trim to essentials: install, tutorial, MCP setup | S |
| Getting Started tutorial | Zero to working MCP connection in 5 minutes | S |
| Release notes | CHANGELOG for 0.8 tag | S |

### Definition of done

- `pip install pyrite && pyrite init --template software` works from a clean venv
- `pip install pyrite-mcp` works and connects to Claude Desktop
- An autonomous agent can: install Pyrite, create a KB, build an extension, test it, install it, and start populating — entirely via CLI
- README, tutorial, and docs are accurate and newcomer-friendly
- Demo screencast recorded

---

## Future (0.9+)

### Agent Swarm Infrastructure

- **Coordination/Task Plugin Phases 3-4** — DAG queries, critical path analysis, QA integration
- **Agent provenance tracking** — Structured identity, capability recording, change attribution
- **Conflict resolution at content level** — Semantic merge for concurrent agent writes to same entry
- **Observable state for orchestrators** — Event stream (WebSocket) for KB modifications, indexing, validation failures
- **Read-your-own-writes guarantees** — Synchronous indexing mode for agent workflows where step N depends on step N-1

### QA Agent Phases 3-5

- **Tier 2**: LLM consistency checks against type instructions and editorial guidelines
- **Tier 3**: Factual verification with web search and source chain checking
- **Phase 5**: Continuous QA pipeline with post-save hooks and scheduled sweeps

### Polish and Scale

- **Canvas/Whiteboard** — Freeform spatial canvas
- **Git Sync Conflict Resolution UI** — Visual merge conflict resolution
- **Engagement Federation** — Sync engagement data across instances
- **Offline Support** — IndexedDB cache, virtual scrolling for large KBs
- **AI writing assistant** — Select text → summarize/expand/rewrite/continue

---

## Versioning notes

Milestones are scope-driven, not time-driven. Each milestone ships when its definition of done is met. Bug fixes and small improvements may land between milestones without bumping the version.
