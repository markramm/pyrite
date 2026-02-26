---
type: note
title: "Pyrite Prioritized Backlog"
tags: [backlog, roadmap]
---

# Pyrite Prioritized Backlog

Active items in priority order across three tracks: **UI** (web application features), **AI** (agent workflows, LLM integration), and **Core** (data model, storage, schema). See [README.md](README.md) for folder structure and workflow rules.

See [ADR-0007](../adrs/0007-ai-integration-architecture.md) for AI integration architecture decisions.
See [ADR-0008](../adrs/0008-structured-data-and-schema.md) for structured data and schema-as-config decisions.
See [ADR-0009](../adrs/0009-type-metadata-and-plugin-documentation.md) for type metadata, AI instructions, and plugin documentation.
See [ADR-0010](../adrs/0010-content-negotiation-and-format-support.md) for content negotiation and multi-format support.
See [ADR-0011](../adrs/0011-collections-and-views.md) for collections, folder metadata, and views.

---

## Execution Plan

Work is organized into **waves** based on dependency analysis. Items within a wave can run in parallel. A wave's dependent items cannot start until their blocker completes.

### Wave 1 — Start immediately (no dependencies, all parallel)

These are root items that unblock the most downstream work:

| # | Item | Track | Kind | Effort | Unblocks | Status |
|---|------|-------|------|--------|----------|--------|
| 1 | [Migrate to ruamel.yaml](done/ruamel-yaml-migration.md) | Core | improvement | S | #2→#7→#28,#29 (longest chain) | **done** |
| 2 | [Claude Code Plugin Manifest](done/claude-code-plugin.md) | AI | feature | S | #10, #11, #19 | **done** |
| 3 | [Wikilinks with Autocomplete](done/wikilinks-and-autocomplete.md) | UI | feature | L | #5, #12, #16 | **done** |
| 4 | [Harden API Layer Security](done/api-security-hardening.md) | both | improvement | M | none (but security = early) | **done** |

**Parallelism:** All four items touch different files/tracks. (Note: `api.py` has been split into per-feature endpoint modules — see Collaboration Bottleneck Notes below.)

### Wave 2 — Start as dependencies complete

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 5 | [Schema-as-Config: Rich Field Types](done/structured-data-schema.md) | Core | feature | M | #1 (ruamel) | **done** |
| 6 | [LLM Abstraction Service](done/llm-abstraction-service.md) | AI | feature | M | none | **done** |
| 7 | [Quick Switcher and Command Palette](done/quick-switcher-and-command-palette.md) | UI | feature | M | none | **done** |
| 8 | [Templates System](done/templates-system.md) | UI | feature | M | none | **done** |
| 9 | [Starred/Pinned Entries](done/starred-entries.md) | UI | feature | S | none | **done** |
| 41 | [Plugin Developer Guide](done/plugin-developer-guide.md) | both | documentation | M | none | **done** |

**Note:** #6–#9, #41 have no blockers and could start in Wave 1 if capacity allows. They're here because Wave 1 items have higher unblock leverage.

### Wave 3A — Parallel (3 agents, zero file contention)

Tech debt + newly-unblocked features. File footprints validated — no shared modified files.

| # | Item | Track | Kind | Effort | Blocked by | File Footprint | Status |
|---|------|-------|------|--------|------------|----------------|--------|
| 46 | [Entry Factory Deduplication](done/entry-factory-deduplication.md) | Core | improvement | S | none | `models/factory.py`, `kb_service.py`, `mcp_server.py`, `endpoints/entries.py` | **done** |
| 12 | [Backlinks Panel and Split Panes](done/backlinks-and-split-panes.md) | UI | feature | M | #3 ✅ | `BacklinksPanel.svelte`, `SplitPane.svelte`, `entries/[id]/+page.svelte`, `ui.svelte.ts` | **done** |
| 15 | [Daily Notes with Calendar](done/daily-notes.md) | UI | feature | M | #8 ✅ | `endpoints/daily.py`, `DailyNote.svelte`, `Calendar.svelte`, `daily/+page.svelte`, `client.ts` | **done** |

### Wave 3B — Sequential Core cleanup (after 3A merges)

These items have overlapping file footprints and must run sequentially: #48 → #47 → #50 → #49.

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 48 | [Split database.py Into Focused Modules](done/split-database-module.md) | Core | improvement | M | #46 | **done** |
| 47 | [Route All Data Access Through Service Layer](done/service-layer-enforcement.md) | Core | improvement | M | #48 | **done** |
| 50 | [Route CLI Data Access Through Service Layer](done/cli-service-layer.md) | Core | improvement | M | #47 | **done** |
| 49 | [Shared Test Fixtures and Coverage Gaps](done/test-improvements.md) | Core | improvement | M | #50 | **done** |

**Note:** #47 routed endpoints and MCP through KBService. #50 completes the job for CLI — critical because AI agents (Claude Code, Gemini CLI, Codex) use the CLI as their primary interface for long-running research orchestration.

### Wave 4 — Features needing clean service layer

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 42 | [Type Metadata and AI Instructions](done/type-metadata-and-ai-instructions.md) | Core/AI | feature | M | #5 ✅, #47 ✅ | **done** |
| 13 | [MCP Prompts and Resources](done/mcp-prompts-and-resources.md) | AI | feature | M | #6 ✅, #47 ✅ | **done** |
| 14 | [Slash Commands in Editor](done/slash-commands.md) | UI | feature | M | none | **done** |
| 44 | [Content Negotiation and Multi-Format Support](done/content-negotiation-and-formats.md) | both | feature | L | #47 ✅ | **done** |

**Parallelism:** All four items had zero file overlap. #42 + #13 ran in parallel (schema/protocol vs mcp_server), then #14 + #44 ran in parallel (frontend editor vs backend formats module).

### Wave 5A — Skills + cleanup (zero file contention, all parallel)

Pure skill files and docs — no backend/frontend code overlap.

| # | Item | Track | Kind | Effort | File Footprint | Status |
|---|------|-------|------|--------|----------------|--------|
| 10 | [Research Flow Skill](done/research-flow-skill.md) | AI | feature | L | `.claude/skills/research-flow/` | **done** |
| 11 | [Investigation Skill](done/investigation-skill.md) | AI | feature | L | `.claude/skills/investigation/` | **done** |
| 19 | [Pyrite Dev Workflow Skill](done/pyrite-dev-skill.md) | AI | feature | M | `.claude/skills/pyrite-dev/` | **done** |
| 37 | [Rewrite README for Pyrite](done/readme-rewrite.md) | both | bug | S | `README.md` | **done** |

### Wave 5B — Isolated UI features (zero file contention, all parallel)

Each touches a different frontend route/component with no shared files.

| # | Item | Track | Kind | Effort | File Footprint | Status |
|---|------|-------|------|--------|----------------|--------|
| 21 | [Callouts and Admonitions](done/callouts-and-admonitions.md) | UI | feature | S | `web/` Lezer grammar + CSS only | **done** |
| 22 | [Outline / Table of Contents](done/outline-table-of-contents.md) | UI | feature | S | New `OutlinePanel.svelte`, `entries/[id]/+page.svelte` | **done** |
| 34 | [Timeline Visualization](done/timeline-visualization.md) | UI | feature | M | `web/src/routes/timeline/` only | **done** |
| 38 | [Remove Legacy Files](done/legacy-file-cleanup.md) | both | improvement | S | `read_cli.py`, `write_cli.py`, `pyproject.toml` entry points | **done** |

### Wave 5C — Core infrastructure (zero file contention across groups, sequential within)

| # | Item | Track | Kind | Effort | Status |
|---|------|-------|------|--------|--------|
| 39 | [Custom Exception Hierarchy](done/custom-exception-hierarchy.md) | both | improvement | M | **done** |
| 25 | [Replace Manual Plugin DI](done/plugin-dependency-injection.md) | both | improvement | M | **done** |
| 24 | [Hooks Cannot Access DB Instance](done/hooks-db-access-gap.md) | both | bug | M | **done** |
| 52 | [Standalone MCP Server Packaging](done/standalone-mcp-packaging.md) | Core | feature | M | **done** |

### Wave 5D — Data model + new endpoints (parallel across groups)

**Group 1 — Core data model additions** (parallel — different DB tables):

| # | Item | Track | Kind | Effort | File Footprint | Status |
|---|------|-------|------|--------|----------------|--------|
| 18 | [Typed Object References](done/typed-object-references.md) | Core | feature | M | `database.py` (new `entry_refs` table), `index.py`, `endpoints/entries.py`, `schema.py` | **done** |
| 20 | [Tag Hierarchy and Nested Tags](done/tag-hierarchy.md) | UI | feature | M | `database.py` (tag prefix queries), `web/` tag tree component | **done** |

**Group 2 — New endpoint modules** (parallel — each adds isolated endpoint):

| # | Item | Track | Kind | Effort | File Footprint | Status |
|---|------|-------|------|--------|----------------|--------|
| 30 | [Settings and User Preferences](done/settings-and-preferences.md) | UI | feature | M | New `endpoints/settings_ep.py`, `database.py` (settings table), new settings page | **done** |
| 35 | [Git-Based Version History](done/version-history.md) | UI | feature | M | New `endpoints/versions.py`, new `VersionHistoryPanel.svelte` | **done** |

### Wave 6A — Graph + realtime (parallel — different stacks)

| # | Item | Track | Kind | Effort | File Footprint | Status |
|---|------|-------|------|--------|----------------|--------|
| 16 | [Interactive Knowledge Graph](knowledge-graph-view.md) | UI | feature | L | New `endpoints/graph.py`, `database.py` (graph query), `GraphView.svelte` + Cytoscape.js | **done** |
| 23 | [WebSocket Multi-Tab Awareness](websocket-multi-tab.md) | UI | feature | M | New `websocket.py`, `api.py` (WS route), `web/` stores + toast | **done** |
| 33 | [Tiptap WYSIWYG Editor Mode](tiptap-wysiwyg-editor.md) | UI | feature | L | New `TiptapEditor.svelte`, `entries/[id]/+page.svelte`, Tiptap npm deps | **done** |

**Contention note:** #33 touches `entries/[id]/+page.svelte` which #22 (Wave 5B) also modifies. Ensure 5B merges first. #16 and #23 are fully independent of each other and #33.

### Wave 6B — AI features (sequential: #26 → #27, #32)

Depends on #30 (settings) from Wave 5D.

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 26 | [Web AI: Summarize, Auto-Tag, Links](done/web-ai-summarize-and-tag.md) | AI | feature | M | #30 ✅ | **done** |
| 27 | [AI Provider Settings in UI](done/ai-provider-settings-ui.md) | AI | feature | S | #30 ✅ | **done** |
| 32 | [Web AI: Chat Sidebar (RAG)](done/web-ai-chat-sidebar.md) | AI | feature | L | #26 ✅ | **done** |
| 45 | [Ephemeral KBs for Agent Swarm Shared Memory](done/ephemeral-kbs.md) | AI | feature | M | none (but benefits from #25) | **done** |
| 53 | [Cross-KB Shortlinks](done/cross-kb-shortlinks.md) | Core | feature | L | none | **done** |

### Wave 6C — Plugin UI + import/export

Depends on #25 (plugin DI) from Wave 5C.

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 31 | [Plugin UI Extension Points](done/plugin-ui-hooks.md) | UI | feature | M | #25 (plugin DI) | **done** |
| 36 | [Import/Export Support](done/import-export.md) | UI | feature | L | none | **done** |

### Wave 7A — Access control + git automation (parallel — zero file contention)

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 54 | [Implement pyrite-read CLI](done/implement-pyrite-read-cli.md) | Core | feature | S | none | **done** |
| 55 | [Add kb_commit MCP Tool and REST Endpoint](done/mcp-commit-tool.md) | Core | feature | M | none | **done** |
| 56 | [REST API Tier Enforcement](done/rest-api-tier-enforcement.md) | Core | feature | L | none | **done** |
| 57 | [Background Embedding Pipeline](done/background-embedding-pipeline.md) | AI | improvement | M | none | **done** |

**Parallelism:** #54 touches `read_cli.py` + `pyproject.toml`. #55 touches `mcp_server.py` + `endpoints/admin.py` + `cli/kb_commands.py`. #56 touches `api.py` + config. #57 touches `embedding_service.py` + `database.py` (new table). Zero overlap.

### Wave 7B — DB transaction cleanup (foundation for 7C/7D)

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 40 | [Database Transaction Management](done/database-transaction-management.md) | both | improvement | L | #25 ✅ | **done** |

See [ADR-0013](../adrs/0013-unified-database-connection-and-transaction-model.md). Consolidate dual-connection model, add `execute_raw()` API, `raw_transaction()` context manager. Foundation for block table and collection table work in 7C/7D.

### Wave 7C — Block References (3 phases, sequential)

#17 broken into 3 phases per [ADR-0012](../adrs/0012-block-references-and-transclusion.md):

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 58 | [Block Refs Phase 1: Storage + Heading Links](done/block-refs-phase1-storage-and-heading-links.md) | both | feature | M | #40 ✅ | **done** |
| 59 | [Block Refs Phase 2: Block ID References](block-refs-phase2-block-id-references.md) | both | feature | M | #58 ✅ | proposed |
| 60 | [Block Refs Phase 3: Transclusion Rendering](block-refs-phase3-transclusion.md) | UI | feature | L | #59 | proposed |

### Wave 7D — Collections (5 phases, mostly sequential)

#51 broken into 5 phases per [ADR-0011](../adrs/0011-collections-and-views.md):

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 61 | [Collections Phase 1: Foundation](done/collections-phase1-foundation.md) | both | feature | M | none | **done** |
| 62 | [Collections Phase 2: Virtual Collections](done/collections-phase2-virtual-collections.md) | both | feature | M | #61 ✅ | **done** |
| 63 | [Collections Phase 3: Rich Views](done/collections-phase3-rich-views.md) | UI | feature | L | #61 ✅ | **done** |
| 64 | [Collections Phase 4: Embedding](collections-phase4-embedding.md) | UI | feature | M | #62 ✅, #60 | proposed |
| 65 | [Collections Phase 5: Plugin Types](collections-phase5-plugin-types.md) | both | feature | S | #61 ✅ | proposed |

**Parallelism:** #61 (Collections Phase 1) and #58 (Block Refs Phase 1) can run in parallel — different tables, different file footprints. #62 and #63 can run in parallel after #61. #64 depends on both #62 and #60 (transclusion).

**Note on #51 (Collections):** This item subsumes #28 (Dataview-Style Queries), #29 (Database Views), and #43 (Display Hints). Those items are retired — their scope is now covered by Collections phases 1–3. See [ADR-0011](../adrs/0011-collections-and-views.md).

## Retired

Items subsumed by larger features:

| # | Item | Subsumed by | Reason |
|---|------|-------------|--------|
| 28 | [Dataview-Style Queries](dataview-queries.md) | #51 Collections (Phase 2) | Virtual collections with `source: query` are dataview |
| 29 | [Database Views (Table/Board/Gallery)](database-views.md) | #51 Collections (Phase 3) | Collection view types cover table, kanban, gallery |
| 43 | [Display Hints for Types](display-hints-for-types.md) | #51 Collections (Phase 1) | View configuration is per-collection, not just per-type |

## In Progress

*No items currently in progress.*

## Collaboration Bottleneck Notes

`api.py` was split into per-feature endpoint modules under `pyrite/server/endpoints/` to eliminate it as a merge bottleneck. See [parallel-agents.md](../../.claude/skills/pyrite-dev/parallel-agents.md) for the full merge protocol.

**Key shared files and which waves touch them:**

| File | Touched by | Risk | Mitigation |
|------|-----------|------|------------|
| `pyrite/storage/database.py` | #18, #20, #30 (5D), #16 (6A), #40 (7) | **Medium** — all add new methods/tables | Additive changes only; wave ordering prevents conflicts |
| `pyrite/services/kb_service.py` | #25, #24 (5C), #39 (5C) | **Medium** — plugin DI + exceptions | Run #39 after #25 chain merges |
| `pyrite/plugins/protocol.py` | #25, #24 (5C) | **Low** — sequential within chain | #24 blocked by #25 |
| `pyrite/server/api.py` | #30, #35 (5D), #16, #23 (6A) | **Low** — one-line router includes | Trivial merge conflicts |
| `web/src/routes/entries/[id]/+page.svelte` | #22 (5B), #33 (6A), #35 (5D) | **Medium** — layout changes | Wave ordering: 5B → 5D → 6A |
| `pyrite/server/endpoints/entries.py` | #18 (5D), #17 (7) | **Low** — sequential via dependency | #17 blocked by #18 |

**Rule of thumb:** Core, UI, and AI tracks have clean file separation. Items within the same track and wave need coordination. Max 3–4 parallel agents per wave. See [parallel-agents.md](../../.claude/skills/pyrite-dev/parallel-agents.md) before launching parallel agents.

## Future Ideas

Lower-priority items in [`future-ideas/`](future-ideas/):

- [Web AI: Writing Assistant in Editor](future-ideas/web-ai-writing-assist.md) — Select text → AI summarize/expand/rewrite/continue
- [Offline Support and Performance](future-ideas/offline-and-performance.md) — IndexedDB cache, virtual scrolling, service worker
- [Web Clipper](future-ideas/web-clipper.md) — Capture web content into Pyrite entries
- [Entry Aliases](future-ideas/entry-aliases.md) — Multiple names resolving to one entry
- [Canvas / Whiteboard](future-ideas/canvas-whiteboard.md) — Freeform spatial canvas for visual thinking
- [Git Sync Conflict Resolution UI](future-ideas/sync-conflict-resolution-ui.md) — Visual merge conflict resolution
- [Plugin Tool Collision Detection](future-ideas/plugin-tool-collision-detection.md) — Warn on duplicate tool names
- [Trim Required Dependencies](future-ideas/trim-required-dependencies.md) — Reduce install footprint
- [Engagement Federation](future-ideas/engagement-federation.md) — Sync engagement data across instances
- [Graph Betweenness Centrality Sizing](future-ideas/graph-betweenness-centrality.md) — Size nodes by BC to highlight bridging entries
- [Graph Community Detection](future-ideas/graph-community-detection.md) — Detect topical clusters, color by community instead of type
- [Graph Structural Gap Detection](future-ideas/graph-structural-gap-detection.md) — Find missing links between distant clusters
- [Graph Influence-per-Occurrence](future-ideas/graph-influence-per-occurrence.md) — Surface entries with outsized connective importance

## Completed

Items in [`done/`](done/):

- [Migrate to ruamel.yaml](done/ruamel-yaml-migration.md) — Round-trip safe YAML with pyrite/utils/yaml.py wrappers
- [Claude Code Plugin Manifest](done/claude-code-plugin.md) — .claude-plugin/ with autoDiscover
- [Wikilinks with Autocomplete](done/wikilinks-and-autocomplete.md) — `[[` autocomplete, pill decorations, resolve endpoint
- [Harden API Layer Security](done/api-security-hardening.md) — slowapi rate limiting, CORS config, API key setting
- [Schema-as-Config: Rich Field Types](done/structured-data-schema.md) — FieldSchema with 10 types, field-level validation, plugin protocol extension
- [LLM Abstraction Service](done/llm-abstraction-service.md) — Provider-agnostic LLMService with Anthropic, OpenAI, OpenRouter, Ollama, stub
- [Quick Switcher and Command Palette](done/quick-switcher-and-command-palette.md) — Cmd+O quick switcher, Cmd+K command palette with fuse.js fuzzy matching
- [Templates System](done/templates-system.md) — TemplateService with `_templates/*.md`, variable rendering, API endpoints, TemplatePicker UI
- [Starred/Pinned Entries](done/starred-entries.md) — StarredEntry ORM model, CRUD endpoints, Svelte store/components
- [Plugin Developer Guide](done/plugin-developer-guide.md) — 1856-line comprehensive guide covering all 11 protocol methods with real examples
- [Web Server Implementation](done/web-server-implementation.md) — `pyrite serve` with SvelteKit frontend
- [CLI Entry Point Consolidation](done/cli-entry-point-consolidation.md) — Single `pyrite` Typer CLI
- [Entry Factory Deduplication](done/entry-factory-deduplication.md) — Single `build_entry()` factory replacing 3x duplicated if/elif chains
- [Backlinks Panel and Split Panes](done/backlinks-and-split-panes.md) — BacklinksPanel sidebar, SplitPane component, Cmd+Shift+B toggle
- [Daily Notes with Calendar](done/daily-notes.md) — GET /daily/{date} auto-create, Calendar.svelte, DailyNote.svelte, Cmd+D shortcut
- [Split database.py Into Focused Modules](done/split-database-module.md) — Mixin pattern: ConnectionMixin, CRUDMixin, QueryMixin, KBOpsMixin, UserOpsMixin
- [Route All Data Access Through Service Layer](done/service-layer-enforcement.md) — Endpoints + MCP routed through KBService with hooks
- [Route CLI Data Access Through Service Layer](done/cli-service-layer.md) — CLI CRUD and queries routed through KBService for hook/validation parity with API and MCP
- [Shared Test Fixtures and Coverage Gaps](done/test-improvements.md) — conftest.py shared fixtures, 39 new tests (endpoint errors, MCP tiers, CLI commands), pytest markers
- [Type Metadata and AI Instructions](done/type-metadata-and-ai-instructions.md) — CORE_TYPE_METADATA for 8 types, 4-layer resolution, get_type_metadata() plugin protocol, GET /api/kbs/{kb}/schema endpoint
- [MCP Prompts and Resources](done/mcp-prompts-and-resources.md) — 4 prompts (research, summarize, connections, briefing), 3 resource URIs, resource templates
- [Slash Commands in Editor](done/slash-commands.md) — 14 slash commands via CodeMirror CompletionSource, headings/callouts/code/table/link/date/divider/todo
- [Content Negotiation and Multi-Format Support](done/content-negotiation-and-formats.md) — pyrite/formats/ module, Accept header negotiation, JSON/Markdown/CSV/YAML, CLI --format flag
- [Rewrite README for Pyrite](done/readme-rewrite.md) — New README covering installation, quick start, architecture overview
- [Pyrite Dev Workflow Skill](done/pyrite-dev-skill.md) — TDD, debugging, verification, backlog management, parallel agent work
- [Research Flow Skill](done/research-flow-skill.md) — Gather→Connect→Analyze→Synthesize methodology with source assessment rubric
- [Investigation Skill](done/investigation-skill.md) — Entity investigation with source chain tracking, relationship mapping, confidence-rated findings
- [Callouts and Admonitions](done/callouts-and-admonitions.md) — Obsidian-compatible `> [!type]` callout blocks with CSS styling and 12 types
- [Outline / Table of Contents](done/outline-table-of-contents.md) — Auto-generated TOC sidebar panel with heading scroll-to, Cmd+Shift+O toggle
- [Timeline Visualization](done/timeline-visualization.md) — Visual vertical timeline with month grouping, importance-colored markers, date/importance filters
- [Remove Legacy Files](done/legacy-file-cleanup.md) — Removed read_cli.py, write_cli.py, requirements.txt, stale entry points; fixed pyrite CLI entry point
- [Custom Exception Hierarchy](done/custom-exception-hierarchy.md) — PyriteError hierarchy replacing ValueError/PermissionError, fixed _run_hooks silent swallowing
- [Replace Manual Plugin DI](done/plugin-dependency-injection.md) — PluginContext dataclass with dict-style compat, eliminating 13x self-bootstrapping patterns
- [Hooks Cannot Access DB Instance](done/hooks-db-access-gap.md) — Hooks receive DB via PluginContext, social hooks now write to DB
- [Standalone MCP Server Packaging](done/standalone-mcp-packaging.md) — pyrite-mcp package with optional dependency groups, init + serve CLI
- [Typed Object References](done/typed-object-references.md) — `entry_refs` table, typed relation indexing, backlink resolution for object references
- [Tag Hierarchy and Nested Tags](done/tag-hierarchy.md) — Hierarchical tag tree with prefix queries, TagTree component, GET /api/tags/tree endpoint
- [Settings and User Preferences](done/settings-and-preferences.md) — Settings DB table, CRUD endpoints, settings page with appearance/general sections, Svelte store
- [Git-Based Version History](done/version-history.md) — GitService commit log, GET /api/versions endpoint, VersionHistoryPanel with diff viewer
- [AI Provider Settings in UI](done/ai-provider-settings-ui.md) — AI provider section in settings (Anthropic/OpenAI/OpenRouter/Ollama), test connection, get_llm_service DI
- [Web AI: Summarize, Auto-Tag, Links](done/web-ai-summarize-and-tag.md) — POST /api/ai/summarize, /auto-tag, /suggest-links with AI dropdown menu on entry page
- [Web AI: Chat Sidebar (RAG)](done/web-ai-chat-sidebar.md) — SSE streaming chat endpoint, ChatSidebar component, RAG pipeline with KB context, Cmd+Shift+K toggle
- [Cross-KB Shortlinks](done/cross-kb-shortlinks.md) — `[[kb:entry-id]]` wikilink syntax, shortname config, cross-KB resolution in backend + frontend
- [Ephemeral KBs for Agent Swarm Shared Memory](done/ephemeral-kbs.md) — TTL-based temporary KBs, `POST /api/kbs` create, `POST /api/kbs/gc` garbage collection
- [Plugin UI Extension Points](done/plugin-ui-hooks.md) — `GET /api/plugins` list, plugin detail page, capability display (entry types, tools, hooks)
- [Import/Export Support](done/import-export.md) — JSON/Markdown/CSV importers, `POST /api/entries/import`, `GET /api/entries/export`, round-trip support
- [Implement pyrite-read CLI](done/implement-pyrite-read-cli.md) — Read-only CLI entry point (`pyrite-read`) with 7 commands, no write/admin operations
- [Add kb_commit MCP Tool and REST Endpoint](done/mcp-commit-tool.md) — `kb_commit`/`kb_push` MCP tools (admin tier), REST endpoints, CLI commands for programmatic git operations
- [REST API Tier Enforcement](done/rest-api-tier-enforcement.md) — Role-based access control (read/write/admin) on REST API, `api_keys` config with hashed keys, `requires_tier()` dependency, backwards-compatible
- [Background Embedding Pipeline](done/background-embedding-pipeline.md) — SQLite-backed embed_queue, EmbeddingWorker with retry/batch, queue-based _auto_embed in KBService, GET /api/index/embed-status
- [Database Transaction Management](done/database-transaction-management.md) — Unified DB connection model per ADR-0013, execute_raw() API, raw_transaction() context manager
- [Block Refs Phase 1: Storage + Heading Links](done/block-refs-phase1-storage-and-heading-links.md) — Block table (migration v5), markdown block extraction, `[[entry#heading]]` links, GET /api/entries/{id}/blocks
- [Collections Phase 1: Foundation](done/collections-phase1-foundation.md) — `__collection.yaml` parsing, folder collections, list/table views, /collections routes
- [Collections Phase 2: Virtual Collections](done/collections-phase2-virtual-collections.md) — Query DSL parser, cached evaluation, virtual collections, `pyrite collections` CLI commands
- [Collections Phase 3: Rich Views](done/collections-phase3-rich-views.md) — Kanban view with drag-drop, gallery view with card grid, PATCH /api/entries/{id}, extended ViewSwitcher
- [Extension Builder Skill](done/extension-builder-skill.md) — Claude Code skill for scaffolding new pyrite extensions from description
- [Semantic Search for Plugins](future-ideas/semantic-search-for-plugins.md) — `PluginContext.search_semantic()` with vector search fallback to FTS5
- [Health Check Timezone Fix](health-check-timezone-fix.md) — Fixed false stale entries from UTC vs local time mismatch in `IndexManager.check_health()`

---

## Bugs

| # | Item | Track | Kind | Effort | Status |
|---|------|-------|------|--------|--------|
| 66 | [Health Check Timezone False Positives](health-check-timezone-fix.md) | Core | bug | S | **done** |
| 67 | [pyrite create --body-file Nested YAML Bug](create-body-file-nested-yaml-bug.md) | Core | bug | S | proposed |

---

## Dependencies

Wave assignments shown in brackets. Items within the same wave group have validated file separation.

```
claude-code-plugin (#2) ✅
  ├── research-flow-skill (#10) ✅     [5A]
  ├── investigation-skill (#11) ✅     [5A]
  └── pyrite-dev-skill (#19) ✅        [5A]

plugin-dependency-injection (#25) ✅   [5C group 2]
  ├── hooks-db-access-gap (#24) ✅     [5C group 2, after #25]
  ├── plugin-ui-hooks (#31) ✅         [6C]
  └── database-txn-mgmt (#40)          [7]

custom-exception-hierarchy (#39) ✅    [5C group 3, after #25 merges]

typed-object-references (#18) ✅       [5D group 1]
  └── block-references (#17)           [7]
        └── collections (#51) Phase 4

settings-and-preferences (#30) ✅      [5D group 2]
  ├── web-ai-summarize-and-tag (#26) ✅ [6B]
  │     └── web-ai-chat-sidebar (#32) ✅ [6B]
  └── ai-provider-settings-ui (#27) ✅  [6B]

knowledge-graph-view (#16) ✅           [6A]
websocket-multi-tab (#23) ✅            [6A]
tiptap-wysiwyg-editor (#33) ✅          [6A, after #22 merges]

collections (#51)                      [7] — subsumes #28, #29, #43
  ├── Phase 2: virtual collections
  ├── Phase 3: rich views (kanban, gallery, timeline, thread)
  ├── Phase 4: embedding (needs #17)
  └── Phase 5: plugin collection types

import-export (#36) ✅                 [6C]
ephemeral-kbs (#45) ✅                 [6B]
cross-kb-shortlinks (#53) ✅           [6C]

implement-pyrite-read-cli (#54) ✅     [7A]
mcp-commit-tool (#55) ✅               [7A]
rest-api-tier-enforcement (#56) ✅     [7A]
background-embedding-pipeline (#57) ✅ [7A]

database-txn-mgmt (#40) ✅             [7B]
  └── block-refs-phase1 (#58) ✅       [7C]
        └── block-refs-phase2 (#59)    [7C]
              └── block-refs-phase3 (#60) [7C]
                    └── collections-phase4 (#64) [7D]

collections-phase1 (#61) ✅           [7D]
  ├── collections-phase2 (#62) ✅      [7D]
  │     └── collections-phase4 (#64)   [7D]
  ├── collections-phase3 (#63) ✅      [7D]
  └── collections-phase5 (#65)         [7D]
```
