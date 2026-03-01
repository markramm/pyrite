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

## 0.6 — Agent Coordination (done)

**Theme:** Task management as a coordination primitive for agent swarms. Not a project management tool — an orchestration substrate.

### Delivered

**Coordination/Task Plugin (Phases 1-2)**

- `extensions/task/` with TaskEntry (7-state workflow), 7 CLI commands, 7 MCP tools
- Atomic `task_claim` via CAS (compare-and-swap on SQLite metadata JSON)
- Bulk `task_decompose` for subtask creation
- `task_checkpoint` with timestamped progress logging and evidence tracking
- Parent auto-rollup with cascading (grandparent rolls up when parent completes)
- `old_status` propagation via `PluginContext.extra` for workflow transition validation

**Plugin KB-Type Scoping**

- `PluginRegistry.get_validators_for_kb(kb_type)`, `get_hooks_for_kb(kb_type)`, `run_hooks_for_kb()`
- `KBSchema.kb_type` and `PluginContext.kb_type` fields
- All validate_entry and hook call sites threaded with `kb_type`

**Programmatic Schema Provisioning**

- `SchemaService` with show/add_type/remove_type/set_schema
- MCP: extended `kb_manage` with 4 new actions
- CLI: `kb schema show/add-type/remove-type/set`

**QA Phase 2 — Assessment Entries**

- `qa_assessment` entry type with target_entry, tier, status, issues list
- `QAService.assess_entry()` and `assess_kb()` with tiered evaluation
- `QAService.get_coverage()` for verification rate tracking
- MCP tools: `kb_qa_assess` (write tier)

**Post-Save QA Validation**

- `validate` param on `kb_create`/`kb_update` MCP tools for opt-in QA
- `qa_on_write: true` KB-level setting in `kb.yaml` for automatic validation
- `_maybe_validate()` helper runs `QAService.validate_entry()` after save, returns `qa_issues` in response

### Results

- 1154 tests passing (+68 over 0.5 baseline)
- All 0.6 DoD criteria met:
  - Orchestrator agent can decompose, dispatch, and track via task tools
  - `task_claim` is atomic (no double-claims in concurrent swarms)
  - Agent-authored entries are automatically validated on write
  - QA assessments are queryable KB entries linked to targets and tasks

---

## 0.7 — Web UI Polish (done)

**Theme:** Make the web experience demo-ready. Screenshots, screencasts, knowledge graph visualizations that tell the story.

### Wave 1

- **QA dashboard**: 4 REST endpoints (`/api/qa/status`, `/validate`, `/validate/{id}`, `/coverage`), Svelte dashboard page with status cards, coverage stats, issues table with severity badges, KB/severity filters. 9 backend tests.
- **Graph betweenness centrality**: Brandes' algorithm on the graph endpoint (`include_centrality=true`), node sizing by centrality in the frontend, opacity scaling, centrality toggle in graph controls. 10 backend tests.
- **Block-ID transclusion fix**: `![[entry^block-id]]` now fetches the specific block via the blocks API in both CodeMirror and Tiptap editors, with fallback to full body. 10 frontend tests.

### Wave 2

- **Collection embedding in transclusions**: `![[collection-id]]` renders inline as compact entry list (max 10, "View all →" link) in both CodeMirror and Tiptap editors. Folder icon distinguishes from entry transclusions.
- **WebSocket live updates for transclusions**: When a source entry is updated, all transclusion widgets showing that entry auto-refresh. Uses `destroy()` for cleanup.
- **Cycle detection**: Module-level `activeTransclusions` set prevents A→B→A infinite loops. Shows "⚠ Circular reference detected" warning. 7 tests.
- **1000+ entry performance test**: 1050 entries (notes + events), validates index sync <30s, FTS <500ms, list <200ms, graph+centrality <5s, QA validate <10s. All pass well within limits. 6 tests.

### Wave 3

- **Transclusion view options**: `![[collection-id]]{ view: "table", limit: 5 }` syntax parsed and rendered in both CodeMirror and Tiptap editors. Supports `list` (default) and `table` views with configurable `limit`. `parseOptionsString()` handles JSON-like syntax with unquoted keys. 7 frontend tests.
- **Collection nesting**: Sub-collections in a collection entry list render as collapsible `<details><summary>` elements with lazy-loaded nested entries on expand. Limited to 1 level deep to prevent recursion.

### Results

- 1179 backend tests, 115 frontend tests, all passing
- All DoD met: transclusions (heading + block-ID + collections + view options), QA dashboard, graph centrality, 1050-entry perf test

---

## 0.8 — UI Design & UX (done)

**Theme:** Brand identity, navigation polish, and demo-ready UX. Every screen a stranger sees should look intentional.

### Delivered

**P0 — Navigation & Error States**

- Sidebar active state highlighting via `$page.url.pathname` with conditional styling
- Reusable `ErrorState` component: red icon, message, retry button
- Reusable `EmptyState` component: icon, title, description, action CTA (used in Entries + Collections)

**P1 — Brand & Dashboard**

- Gold accent palette (`--color-gold-400/500/600`), "Py" monogram with gold gradient in sidebar
- DM Serif Display heading font via Google Fonts, `--font-display` CSS variable
- Dashboard redesign: stat cards with colored top stripes and icons, two-column layout (recent entries + quick actions), clickable top tags

**P2 — Polish**

- Page transitions: `{#key}` fade on route change in layout
- Entry toolbar: semantic button groups with dividers, icon-only panel toggles (Outline, Backlinks, Graph, History)
- Graph atmosphere: dot grid background pattern, node glow on hover via cytoscape underlay
- Toast redesign: slide from top-right with `fly` transition, type icons, shrinking progress bar

**Wave 4 — UX Improvements**

- Dedicated `/search` route with mode picker (keyword/semantic/hybrid), KB and type filters, snippet highlighting with `<mark>` tags, gold accent on active mode. Search added as first sidebar nav item. QuickSwitcher gains "See all results" link.
- Entry type distribution: `get_type_counts()` backend endpoint, SVG donut chart on dashboard with legend (3 backend tests)
- Keyboard shortcuts modal: `?` key opens overlay listing all shortcuts. `Cmd+/` toggles sidebar.
- Responsive sidebar: fixed overlay on mobile with backdrop blur, slide transition, auto-close on nav click, viewport-aware init. Hamburger toggle visible on narrow viewports.
- Settings improvements: gear icon in sidebar nav, new Editor section (default editor/search mode), Data section (import/export placeholders), keyboard shortcuts reference
- Template picker redesign: 2-column grid, colored left border per entry type, type dot + badge, line-clamp descriptions, tag pills, dashed blank entry card, gold hover accent

### Results

- 1182 backend tests, 115 frontend tests, all passing
- All DoD met: brand identity, dashboard with type chart, search page, responsive sidebar, keyboard shortcuts, settings, polished template picker

---

## 0.9 — Code Hardening (done)

**Theme:** Internal quality pass. Refactor, fix architecture gaps, and harden tests — before adding new capabilities.

### Delivered

**Wave 1 — Refactoring & Deduplication**

- `kb_schema` cached property on `KBConfig`, eliminating 12 redundant `KBSchema.from_yaml()` filesystem reads
- `pyrite/cli/context.py` with `cli_context()` context manager, replacing ~18 duplicated `PyriteDB + KBService` construction sites
- `pyrite/server/tool_schemas.py` with ~500 lines of extracted MCP tool schemas (READ_TOOLS, WRITE_TOOLS, ADMIN_TOOLS)
- Lazy `qa_svc` and `search_svc` properties on `PyriteMCPServer`, replacing 5 duplicate service constructions

**Wave 2 — Architecture Cleanup**

- `get_search_service()` FastAPI dependency factory, fixing DI bypass in `search.py` and `ai_ep.py`
- 24 `_raw_conn` calls eliminated across `qa_service.py` (12), `repo_service.py` (7), `kb_service.py` (5)
- `WikilinkService` extracted from `KBService` (148 lines: `list_entry_titles`, `resolve_entry`, `resolve_batch`, `get_wanted_pages`)
- 4 thin settings wrappers removed from `KBService`; callers use `db.*` directly
- `AIPanel.svelte` extracted from entry detail page (228 lines, 36% reduction in `+page.svelte`)

**Wave 3 — Test Hardening**

- `_make_mcp_server()` context manager consolidating 7 duplicated MCP test setup sites (~105 lines removed)
- 58 unit tests for all 10 QA `_check_*` validation rules with targeted fixtures
- 18 integration tests for KB git operations (`commit_kb`, `push_kb`) with real temp git repos
- Cytoscape type bindings: 6 `any` annotations replaced with `cytoscape.Core`, `EventObject`, `NodeSingular`

### Results

- 1258 tests passing (+76 over 0.8 baseline)
- `mcp_server.py`: 1537 → 1046 lines (32% reduction); tool schemas in separate module
- No `_raw_conn` usage outside `storage/`; SearchService uses proper FastAPI DI
- `KBService`: 1204 → 1100 lines; wikilink logic extracted to standalone service

---

## 0.10 — Schema Versioning + ODM + LanceDB

**Theme:** Storage architecture that matches the data model. Schema evolution without breakage, document-native search.

### Schema Versioning (pre-launch critical)

| Item | Description | Effort |
|------|-------------|--------|
| [[schema-versioning]] | `_schema_version` tracking, `since_version` field semantics, `MigrationRegistry`, `pyrite schema migrate` command | M |

Hooks into existing `KBRepository` load/save paths. Without this, the first schema change after launch breaks every existing KB.

### ODM Layer

| Item | Description | Effort |
|------|-------------|--------|
| [[odm-layer]] Phase 1 | `SearchBackend` protocol, `SQLiteBackend` wrapping existing code, `DocumentManager` | M |
| LanceDB spike | Implement `LanceDBBackend` behind `SearchBackend`, benchmark hybrid search quality vs SQLite/FTS5 + separate semantic | M |

**Hypothesis:** LanceDB is a better fit than SQLite for Pyrite's flexible schema system. Document-native columnar storage eliminates the impedance mismatch (`json_extract()` for metadata, separate FTS5 virtual tables, separate embedding pipeline). Native hybrid search (vector + FTS in a single query) should produce better results than the current duct-taped approach. The spike validates this.

### Definition of done

- Schema versioning works: `since_version` on fields, `pyrite schema migrate` produces reviewable git diff
- `SearchBackend` protocol defined, `SQLiteBackend` passes full test suite
- LanceDB spike completed: benchmark results, go/no-go decision on replacing SQLite as default index backend

---

## 0.11 — Announceable Alpha

**Theme:** Distribution and first impressions. Everything a stranger needs to go from "interesting" to "I'm trying this."

### Packaging & Distribution

| Item | Description | Effort |
|------|-------------|--------|
| [[pypi-publish]] | Publish `pyrite` and `pyrite-mcp` to PyPI | S |
| Update MCP_SUBMISSION.md | Accurate tool count, test count, configuration examples | S |
| Consolidate docs/ | Trim to essentials: install, tutorial, MCP setup | S |
| Getting Started tutorial | Zero to working MCP connection in 5 minutes | S |
| Release notes | CHANGELOG for 0.11 tag | S |

### Definition of done

- `pip install pyrite && pyrite init --template software` works from a clean venv
- `pip install pyrite-mcp` works and connects to Claude Desktop
- An autonomous agent can: install Pyrite, create a KB, build an extension, test it, install it, and start populating — entirely via CLI
- README, tutorial, and docs are accurate and newcomer-friendly
- Demo screencast recorded

---

## Future (1.0+)

### Storage Backends (contingent on LanceDB spike results)

- **Postgres backend** — Only if LanceDB doesn't cover multi-user / hosted deployment needs. If LanceDB works well, Postgres may never be needed.

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
