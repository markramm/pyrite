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

### Wave 5 — Collections, packaging, and deep dependencies

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 52 | [Standalone MCP Server Packaging](standalone-mcp-packaging.md) | Core | feature | M | none | proposed |
| 51 | [Collections and Views](collections-and-views.md) | both | feature | XL | #42 ✅, #5 ✅ | proposed |
| 10 | [Research Flow Skill](research-flow-skill.md) | AI | feature | L | #2 ✅ | proposed |
| 11 | [Investigation Skill](investigation-skill.md) | AI | feature | L | #2 ✅ | proposed |
| 18 | [Typed Object References](typed-object-references.md) | Core | feature | M | #5 ✅ | proposed |
| 19 | [Pyrite Dev Workflow Skill](pyrite-dev-skill.md) | AI | feature | M | #2 ✅ | proposed |
| 16 | [Interactive Knowledge Graph](knowledge-graph-view.md) | UI | feature | L | #3 ✅ | proposed |
| 17 | [Block References and Transclusion](block-references.md) | UI | feature | XL | #3 ✅ | proposed |
| 20 | [Tag Hierarchy and Nested Tags](tag-hierarchy.md) | UI | feature | M | none | proposed |
| 21 | [Callouts and Admonitions](callouts-and-admonitions.md) | UI | feature | S | none | proposed |
| 22 | [Outline / Table of Contents](outline-table-of-contents.md) | UI | feature | S | none | proposed |
| 23 | [WebSocket Multi-Tab Awareness](websocket-multi-tab.md) | UI | feature | M | none | proposed |
| 24 | [Hooks Cannot Access DB Instance](hooks-db-access-gap.md) | both | bug | M | #25 (plugin DI) | proposed |
| 25 | [Replace Manual Plugin DI](plugin-dependency-injection.md) | both | improvement | M | none | proposed |

**Note on #51 (Collections):** This item subsumes #28 (Dataview-Style Queries), #29 (Database Views), and #43 (Display Hints). Those items are retired — their scope is now covered by Collections phases 1–3. See [ADR-0011](../adrs/0011-collections-and-views.md).

### Later Waves — Build on foundations

| # | Item | Track | Kind | Effort | Blocked by | Status |
|---|------|-------|------|--------|------------|--------|
| 26 | [Web AI: Summarize, Auto-Tag, Links](web-ai-summarize-and-tag.md) | AI | feature | M | #6 (LLM) | proposed |
| 27 | [AI Provider Settings in UI](ai-provider-settings-ui.md) | AI | feature | S | #6 (LLM), #30 (settings) | proposed |
| 30 | [Settings and User Preferences](settings-and-preferences.md) | UI | feature | M | none | proposed |
| 31 | [Plugin UI Extension Points](plugin-ui-hooks.md) | UI | feature | M | #25 (plugin DI) | proposed |
| 32 | [Web AI: Chat Sidebar (RAG)](web-ai-chat-sidebar.md) | AI | feature | L | #6 (LLM) | proposed |
| 33 | [Tiptap WYSIWYG Editor Mode](tiptap-wysiwyg-editor.md) | UI | feature | L | none | proposed |
| 34 | [Timeline Visualization](timeline-visualization.md) | UI | feature | M | none | proposed |
| 35 | [Git-Based Version History](version-history.md) | UI | feature | M | none | proposed |
| 36 | [Import/Export Support](import-export.md) | UI | feature | L | #44 ✅ | proposed |
| 37 | [Rewrite README for Pyrite](readme-rewrite.md) | both | bug | S | none | proposed |
| 38 | [Remove Legacy Files](legacy-file-cleanup.md) | both | improvement | S | none | proposed |
| 39 | [Custom Exception Hierarchy](custom-exception-hierarchy.md) | both | improvement | M | none | proposed |
| 40 | [Database Transaction Management](database-transaction-management.md) | both | improvement | M | none | proposed |
| 45 | [Ephemeral KBs for Agent Swarm Shared Memory](ephemeral-kbs.md) | AI | feature | M | none | proposed |

## Retired

Items subsumed by larger features:

| # | Item | Subsumed by | Reason |
|---|------|-------------|--------|
| 28 | [Dataview-Style Queries](dataview-queries.md) | #51 Collections (Phase 2) | Virtual collections with `source: query` are dataview |
| 29 | [Database Views (Table/Board/Gallery)](database-views.md) | #51 Collections (Phase 3) | Collection view types cover table, kanban, gallery |
| 43 | [Display Hints for Types](display-hints-for-types.md) | #51 Collections (Phase 1) | View configuration is per-collection, not just per-type |

## In Progress

| Item | Track | Kind | Effort | Status |
|------|-------|------|--------|--------|
| [Extension Builder Skill](extension-builder-skill.md) | AI | feature | L | in_progress |

## Collaboration Bottleneck Notes

`api.py` was split into per-feature endpoint modules under `pyrite/server/endpoints/` to eliminate it as a merge bottleneck. See [parallel-agents.md](../../.claude/skills/pyrite-dev/parallel-agents.md) for the full merge protocol.

| File | Touched by | Risk |
|------|-----------|------|
| `pyrite/server/api.py` | Factory + deps only (~169 lines). Rarely needs modification. | **Low** — endpoints are in separate modules now |
| `pyrite/server/endpoints/entries.py` | #18 (object refs) | Low — sequential via dependency |
| `pyrite/server/endpoints/starred.py` | Standalone | None |
| `pyrite/server/endpoints/templates.py` | Standalone | None |
| `pyrite/schema.py` | #18 (object refs) | Low — sequential via dependency |
| `pyrite/plugins/protocol.py` | Standalone | None — #42 done |

**Rule of thumb:** Core, UI, and AI tracks have clean file separation. Items within the same track and wave need coordination. See the wave planning rules in [parallel-agents.md](../../.claude/skills/pyrite-dev/parallel-agents.md) before launching parallel agents.

## Future Ideas

Lower-priority items in [`future-ideas/`](future-ideas/):

- [Web AI: Writing Assistant in Editor](future-ideas/web-ai-writing-assist.md) — Select text → AI summarize/expand/rewrite/continue
- [Offline Support and Performance](future-ideas/offline-and-performance.md) — IndexedDB cache, virtual scrolling, service worker
- [Web Clipper](future-ideas/web-clipper.md) — Capture web content into Pyrite entries
- [Entry Aliases](future-ideas/entry-aliases.md) — Multiple names resolving to one entry
- [Canvas / Whiteboard](future-ideas/canvas-whiteboard.md) — Freeform spatial canvas for visual thinking
- [Git Sync Conflict Resolution UI](future-ideas/sync-conflict-resolution-ui.md) — Visual merge conflict resolution
- [Semantic Search for Plugins](future-ideas/semantic-search-for-plugins.md) — Vector search integration
- [Plugin Tool Collision Detection](future-ideas/plugin-tool-collision-detection.md) — Warn on duplicate tool names
- [Trim Required Dependencies](future-ideas/trim-required-dependencies.md) — Reduce install footprint
- [Engagement Federation](future-ideas/engagement-federation.md) — Sync engagement data across instances

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

---

## Dependencies

Numbers match the wave-based execution plan above.

```
entry-factory-dedup (#46) ✅                  ← TECH DEBT CRITICAL CHAIN
  └── split-database (#48) ✅
        └── service-layer-enforcement (#47) ✅ (endpoints + MCP)
              ├── cli-service-layer (#50) ✅   ← CLI parity for AI agents
              │     └── test-improvements (#49) ✅
              ├── type-metadata (#42) ✅
              │     └── collections (#51)      ← ADR-0011, unblocked
              │           ├── Phase 2: virtual collections
              │           ├── Phase 3: rich views (kanban, gallery, timeline, thread)
              │           ├── Phase 4: embedding (needs #17)
              │           └── Phase 5: plugin collection types
              ├── mcp-prompts (#13) ✅
              └── content-negotiation (#44) ✅
                    └── import-export (#36)

ruamel-yaml-migration (#1) ✅
  └── structured-data-schema (#5) ✅
        ├── typed-object-references (#18)
        ├── type-metadata-and-ai-instructions (#42) ✅ → also needs #47 ✅
        │     └── collections (#51)            ← subsumes #28, #29, #43, unblocked
        └── [RETIRED] dataview-queries (#28)   → now #51 Phase 2
        └── [RETIRED] database-views (#29)     → now #51 Phase 3

wikilinks-and-autocomplete (#3) ✅
  ├── backlinks-and-split-panes (#12) ✅
  ├── block-references (#17)
  │     └── collections (#51) Phase 4          ← embedding uses transclusion
  └── knowledge-graph-view (#16)

claude-code-plugin (#2) ✅
  ├── research-flow-skill (#10)
  ├── investigation-skill (#11)
  └── pyrite-dev-skill (#19)

llm-abstraction-service (#6) ✅
  ├── mcp-prompts-and-resources (#13) ✅ → also needs #47 ✅
  ├── web-ai-summarize-and-tag (#26)
  ├── web-ai-chat-sidebar (#32)
  └── ai-provider-settings-ui (#27)

templates-system (#8) ✅
  └── daily-notes (#15) ✅

settings-and-preferences (#30)
  └── ai-provider-settings-ui (#27)

plugin-dependency-injection (#25)
  ├── hooks-db-access-gap (#24)
  └── plugin-ui-hooks (#31)
```
