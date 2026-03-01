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

## 0.5 — QA & Agent CLI (done)

**Theme:** Structural quality assurance and CLI completeness for agent workflows. Agents can validate their own work and interact with Pyrite entirely through structured output.

### Delivered

**QA Phase 1 — Structural Validation**

- `QAService` with `validate_entry()`, `validate_kb()`, `validate_all()`, `get_status()`
- 9 validation rules: missing titles, empty bodies, broken links, orphans, invalid dates, importance range, event missing dates, schema violations
- CLI: `pyrite qa validate [KB_NAME] [--entry ID] [--format json] [--severity]` + `pyrite qa status`
- MCP tools: `kb_qa_validate`, `kb_qa_status` (read tier)

**Agent CLI Completeness**

- `--format json/markdown/csv/yaml` added to 11 CLI commands: kb list/discover/validate, index stats/health, repo list/status, qa validate/status, auth status/whoami
- `pyrite init --template <name> --path <path>` — headless KB creation with 4 built-in templates (software, zettelkasten, research, empty), plugin preset lookup, idempotent
- `pyrite extension init <name>` — scaffolds 7-file extension with plugin class, entry types, validators, preset, tests
- `pyrite extension install/list/uninstall` — full extension lifecycle management

### Deferred to future

- QA Phase 1.5 (hooks + `--fix`) — post-save validation hook, auto-remediation for fixable issues

### Results

- 1086 tests passing (26 new tests over Phase 1 baseline)
- All CLI commands produce clean, parseable JSON with `--format json`
- Extension init → install → list round-trip works end-to-end

---

## 0.6 — Agent Coordination

**Theme:** Task management as a coordination primitive for agent swarms. Not a project management tool — an orchestration substrate.

### Coordination/Task Plugin (Phases 1-2)

| Phase | Description | Effort | Status |
|-------|-------------|--------|--------|
| Phase 1 | Core TaskEntry type, workflow state machine, CLI commands, MCP tools, validators, hooks | M | done |
| Phase 2 | Atomic task_claim, task_decompose, task_checkpoint, parent auto-rollup | M | done |

Phase 1 delivered: `extensions/task/` with TaskEntry (7-state workflow), 4 CLI commands (`task create/list/status/update`), 4 MCP tools (read: `task_list`/`task_status`, write: `task_create`/`task_update`), before_save workflow validation hook, after_save parent rollup detection, 36 tests.

Phase 2 delivered: `TaskService` wrapping KBService for task-specific atomic operations. Operative MCP tools (7 total: read: `task_list`/`task_status`, write: `task_create`/`task_update`/`task_claim`/`task_decompose`/`task_checkpoint`). Atomic `task_claim` via CAS (compare-and-swap on SQLite metadata JSON). Bulk `task_decompose` for subtask creation. `task_checkpoint` with timestamped progress logging and evidence tracking. Parent auto-rollup with cascading (grandparent rolls up when parent completes). CLI commands wired to TaskService (7 commands: `create/list/status/update/claim/decompose/checkpoint`). `old_status` propagation via `PluginContext.extra` for workflow transition validation. 64 tests (28 new).

### Plugin KB-Type Scoping (done)

| Item | Description | Effort | Status |
|------|-------------|--------|--------|
| Plugin KB-type scoping | Validators and hooks scoped by KB type at registry level | M | done |

Delivered: `PluginRegistry.get_validators_for_kb(kb_type)`, `get_hooks_for_kb(kb_type)`, `run_hooks_for_kb()`. `KBSchema.kb_type` field. `PluginContext.kb_type` field. All `validate_entry` and hook call sites threaded with `kb_type`. Removed fragile field-sniffing heuristic from task validator. 8 new integration tests.

### Programmatic Schema Provisioning (done)

| Item | Description | Effort | Status |
|------|-------------|--------|--------|
| [[programmatic-schema-provisioning]] | MCP and CLI tools to define types and fields without editing YAML | M | done |

Delivered: `SchemaService` with show/add_type/remove_type/set_schema. MCP: extended `kb_manage` with 4 new actions. CLI: `kb schema show/add-type/remove-type/set`. 11 tests.

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
