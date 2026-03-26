# Changelog

All notable changes to Pyrite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Static Site Rendering (`/site/`)**
  - Python-served static HTML cache for SEO-friendly KB pages (replaces earlier Node SSR approach)
  - Sitemap.xml generation from cached pages with per-entry lastmod dates
  - robots.txt with crawler directives
  - JSON-LD structured data, Open Graph meta tags, canonical URLs on every page
  - Custom homepage support via `_homepage` KB entries with designed template rendering
  - Progressive JS enhancements: live search widget, auto-generated TOC, heading anchors, back-to-top
  - Editorial dark theme with Source Serif 4 body + DM Sans headings
  - `/site/search` page with live API-backed hybrid search and URL state sync
  - Cache invalidation per-entry and per-KB, auto-render on index sync

- **Web UI Feature Parity (Phase 4-5)**
  - KB orientation page with type breakdown, recent changes, and tag cloud
  - Advanced search filters: date range, tag filter, saved searches with localStorage
  - Daily notes calendar widget
  - User management: list users, role editing, per-KB permission grants/revokes
  - Index management: sync, rebuild, health check, embedding status in settings
  - Entry creation with full metadata fields (type, tags, date, importance, status)
  - Graph centrality sizing (betweenness centrality from API)
  - Review & Publish workflow: pending changes view with entry-level diffs and commit dialog
  - KB landing page at `/` with directory of knowledge bases
  - Dashboard moved to `/overview`

- **Search Improvements**
  - `group_by_kb` and `limit_per_kb` query params for cross-KB result diversity
  - Prevents large-KB dominance by returning top N results per KB with round-robin interleaving

- **Multi-Site Deployment**
  - Shared Docker network (`pyrite-shared`) for multiple Pyrite instances on one VPS
  - Caddy routing for multiple domains (demo.pyrite.wiki + capturecascade.org)
  - Independent container lifecycle per site

- **Export System**
  - NotebookLM renderer with source bundling and manifest generation
  - Quartz static site renderer for KB publishing
  - CLI `export` command group with collection and site subcommands

### Fixed

- **Security**
  - Fix 6 XSS vulnerabilities in site cache (title escaping, search widget, markdown links, ChatSidebar, search highlight)
  - Fix YAML frontmatter injection in export service (string interpolation → proper quoting)
  - Fix path traversal via entry IDs used as filenames (new `sanitize_filename()` utility)
  - Block javascript:/data:/vbscript: URLs in markdown link rendering
  - Add single-quote escaping to HTML `_esc()` function
  - Set `no-cache` on SPA index.html to prevent stale chunk hash errors after deploy

- **Bugs**
  - Fix graph KB filter SQL precedence: `WHERE (A OR B) AND C` not `WHERE A OR (B AND C)`
  - Fix Sidebar.svelte `$derived` value called as function (`{userInitials()}` → `{userInitials}`)
  - Fix QuickSwitcher full page reload (window.location.href → goto())
  - Fix anonymous access when auth not configured (anonymous_tier None handling)
  - Fix editor blank content when switching to edit mode
  - Fix layout clipping issues (flex-col, min-h-0, overflow)
  - Fix graph page zero-height container

- **Performance**
  - Site cache render_all() runs in background thread (asyncio.to_thread) instead of blocking event loop
  - Reduce N+1 queries in site cache: eliminate redundant list_entries and get_entry calls

### Changed

- Decouple `/site` and `/viewer` routes from SPA dist (work without SvelteKit build)
- Update README: MCP tools 14/6/4 → 23/11/8, extension points 15 → 19, tests 1468 → ~2500, ADRs 16 → 22
- Replace `task` with `journalism-investigation` in extensions table

## [0.20.0] - 2026-03-23

First public beta release. This release consolidates 8 milestones of development (0.10–0.18) into a single distributable package with comprehensive documentation, deployment options, and a hardened web UI.

### Highlights

- **GitHub OAuth & per-KB permissions** — multi-user access control with read/write/admin tiers
- **Docker & one-click deploy** — Dockerfile, Docker Compose, Railway, Render, and Fly.io deploy buttons
- **Web UI hardening** — 14 UX fixes, accessibility audit, Playwright E2E tests, mobile responsive
- **Agent DX overhaul** — 8 MCP tool improvements, structured error responses, batch operations
- **Architecture refactors** — KBService decomposed into 4 focused services, schema module split into 6 submodules
- **Two domain plugins** — software-kb and journalism-investigation prove the platform is general-purpose
- **Edge entities** — typed relationships as first-class entities with endpoint schemas
- **Export system** — NotebookLM and Quartz static site renderers

### Added

- **Authentication & Access Control**
  - GitHub OAuth sign-in (`oauth-providers` Phase 1)
  - Per-KB read/write/admin permissions with ephemeral KB sandboxes
  - MCP per-client per-tier rate limiting

- **Deployment**
  - Multi-stage Dockerfile and Docker Compose configuration
  - One-click deploy buttons for Railway, Render, and Fly.io
  - Self-hosted deployment scripts with Caddy reverse proxy
  - Demo site deployment tooling

- **Web UI**
  - Logout button, version history fix, type color consolidation
  - Browser tab page titles, loading state standardization
  - Accessibility fixes (aria-labels, keyboard navigation, screen reader support)
  - Mobile responsive viewport fixes
  - Collection view persistence, first-run onboarding experience
  - Starred entries restoration, dead code cleanup
  - Alpha banner with feedback button and error reporting links
  - Comprehensive Playwright E2E test suite (search, collections, QA, settings, daily, entry CRUD, auth)

- **Agent Developer Experience (MCP + CLI)**
  - `kb_batch_read` — multi-entry retrieval in one call
  - `kb_list_entries` — lightweight KB index browsing
  - `kb_recent` — orientation queries for what changed recently
  - Search `fields` parameter for token-efficient results across CLI, MCP, and REST
  - Smart field routing: top-level vs metadata field mapping clarified
  - Structured JSON error responses with `suggestion` field across all surfaces
  - MCP body chunking with auto-truncation and `kb_read_body` for large entries

- **Architecture**
  - `SearchBackend` protocol — 13-method structural protocol for pluggable storage
  - `SQLiteBackend` — wraps PyriteDB + FTS5 + sqlite-vec (default)
  - `PostgresBackend` — tsvector FTS + pgvector embeddings for server deployments
  - KBService decomposed into `GraphService`, `EphemeralKBService`, `QuotaService`, `ExportService`
  - Schema module split into 6 focused submodules (`enums`, `validators`, `provenance`, `field_schema`, `kb_schema`, `core_types`)
  - `DocumentManager` for write-path coordination
  - Entry protocol mixins for composable field patterns (ADR-0017)
  - Edge entities — typed relationships as first-class entries with endpoint schemas (ADR-0022)
  - Dynamic subdirectory paths with template variables (`{status}`, `{type}`)

- **Export System**
  - `pyrite export collection` — export entries for NotebookLM with bundling and source redaction
  - `pyrite export site` — export KB as Quartz static site for GitHub Pages
  - Quartz renderer with wikilink normalization, frontmatter mapping, project scaffolding

- **KB Quality & Lifecycle**
  - `pyrite schema validate` — frontmatter validation with ID collision detection
  - `pyrite ci` — CI/CD schema and link validation command
  - `pyrite qa fix` — auto-fix safe structural issues
  - `pyrite qa gaps` — structural coverage analysis
  - `pyrite links check` — cross-KB broken link validation
  - `pyrite links suggest` — FTS5-based link suggestions
  - `pyrite links bulk-create` — batch link creation
  - `pyrite db backup` / `pyrite db restore` — database backup and restore
  - `pyrite kb compact` — detect archival candidates with type-aware staleness
  - Entry `lifecycle` field with archive-aware search filtering
  - Intent layer: guidelines, goals, rubrics, deterministic and LLM-assisted evaluation
  - Named rubric checkers with explicit binding and CLI discoverability
  - Source URL liveness checking for QA

- **Agent Workflow (Kanban for Agent Teams)**
  - Milestone entry type with board configuration (`board.yaml`)
  - Review workflow with DoR/DoD quality gates
  - `sw_pull_next`, `sw_claim`, `sw_submit`, `sw_review`, `sw_log` MCP tools
  - `sw_context_for_item` for pulling work context
  - Work session logging with `WorkLogEntry`

- **Plugins**
  - `software-kb` plugin: ADRs, components, backlog items, standards, runbooks, kanban workflow
  - `journalism-investigation` plugin: persons, organizations, events, claims, evidence, sources with reliability tiers, ownership chains, money flow tracking, FtM interop, cross-KB entity correlation
  - `cascade` plugin: timeline events, actors, capture lanes, static JSON export for viewer consumption
  - Plugin preset registration for `pyrite init --template`
  - Init templates: `research`, `software`, `zettelkasten`, `intellectual-biography`, `movement`, `empty`

- **Documentation**
  - Getting Started tutorial
  - Plugin writing tutorial
  - OpenAI / Codex MCP integration guide
  - Gemini CLI / Antigravity MCP integration guide
  - Awesome plugins directory page

- **Infrastructure**
  - Async/queue-based index rebuild with background thread worker
  - Embedding service pre-warming to reduce cold-start latency
  - Import cycle detection guard
  - Plugin discovery strict mode (surfaces load failures during development)
  - Plugin hook atomicity (transactional wrapping for before_save hooks)
  - Bulk import CLI with `--body-file` and `--stdin` support

### Changed
- Default CLI output format changed to JSON for agent-friendly consumption
- Priority field changed from Integer to String across storage and protocols
- API module-level singletons replaced with `app.state` for test isolation
- Plugin registry deduplication on reload
- Factory pattern refactored to open/closed principle
- Incremental link sync (diff-based instead of delete-all/insert-all)
- LanceDB backend evaluated and rejected (49-66x slower indexing — see ADR-0016)

### Fixed
- Entry ID collisions across types (explicit `id` fields added)
- MCP `kb_create` placing entries at KB root instead of type directory
- MCP `kb_update` returning PosixPath serialization errors
- `sw adrs` reading date from metadata instead of DB column
- `sw_*` MCP tools reading status from metadata JSON instead of DB column
- Template filename filter dropping legitimate KB entries
- Duplicate tags and duplicate entry IDs during index sync
- Test suite clobbering `~/.pyrite/config.yaml`
- Collection type safety and endpoint hardening
- `str(None)` safety across enum validation

## [0.12.0] - 2026-03-01

### Added
- **PyPI publishing** — `pip install pyrite` and `pip install pyrite-mcp` now work
- **GitHub Actions publish workflow** — automated PyPI release on GitHub Release creation
- **MANIFEST.in** — controls sdist contents, excludes tests/extensions/web/kb
- **Schema Migration System** (`storage/migrations.py`)
  - Version tracking via `schema_version` table
  - Forward and rollback migration support
  - Auto-migration on database initialization
- **Service Layer** (`services/`)
  - `KBService` for KB operations (CRUD, indexing)
  - `SearchService` for search with FTS5 query sanitization
- **Pre-commit Hooks** (`.pre-commit-config.yaml`)
  - Ruff linting and formatting
  - Basic file checks (trailing whitespace, YAML validation)
  - Pytest quick check on commit
- **GitHub Actions CI** (`.github/workflows/ci.yml`)
  - Python 3.11/3.12/3.13 matrix testing
  - Ruff lint + format, mypy type checking
  - Separate job for full test suite with optional deps
- **Open Source Governance**
  - `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
  - `SECURITY.md` (vulnerability reporting policy)
  - GitHub issue templates and PR template
- **SvelteKit Web UI** (`web/`)
  - Entry browser, search, graph visualization
  - Entry editor with live markdown preview
- **Documentation**
  - `CONTRIBUTING.md` with development setup and PR workflow
  - `CHANGELOG.md`, `UPSTREAM_CHANGES.md`

### Changed
- Version bumped from 0.3.0 to 0.12.0
- Python 3.13 classifier added
- Package find excludes `pyrite-mcp/` directory
- Fixed FTS5 query sanitization for hyphenated terms
- Fixed deprecation warnings (`datetime.utcnow()` → `datetime.now(timezone.utc)`)
- Fixed sqlite3 date/datetime adapter warnings for Python 3.12+

### Removed
- Legacy `mcp_server.py` and `setup_mcp.py` root scripts
- Legacy test files importing old `zettelkasten_assistant` package
- Stale `zettelkasten_assistant` references from docs and pyproject.toml

## [0.2.0] - 2025-02-21

### Added
- **Web UI** (`ui/`)
  - Streamlit-based interface with search, timeline, actors pages
  - Entry detail view with links and sources
  - Cached data layer for performance

- **REST API** (`server/api.py`)
  - FastAPI server with OpenAPI documentation
  - Full CRUD endpoints for entries
  - Search, timeline, tags, actors endpoints
  - CORS support for web frontends

- **Agent-Optimized CLIs**
  - `crk-read`: Read-only CLI for AI agents
  - `crk`: Full-access CLI for researchers
  - JSON output format with structured errors
  - Semantic exit codes

- **Claude Code Integration**
  - `.claude/skills/kb/skill.md` for Claude Code discoverability
  - MCP server for Model Context Protocol

### Changed
- Entry points consolidated: `crk`, `crk-read`, `crk-server`, `crk-ui`

## [0.1.0] - 2025-01-15

### Added
- **Multi-KB Architecture**
  - Support for multiple knowledge bases with different types
  - Events KB for timeline entries
  - Research KB for actors, organizations, themes

- **SQLite FTS5 Storage**
  - Full-text search with BM25 ranking
  - Tag and actor indexing
  - Link/relationship storage

- **Entry Models**
  - `EventEntry` for timeline events
  - `ResearchEntry` for research documents
  - YAML frontmatter parsing

- **GitHub OAuth**
  - Private repository access for collaborative research

- **Typer CLI**
  - Rich command-line interface (`pyrite`)

## [0.0.1] - 2024-12-01

### Added
- Initial fork from joshylchen/zettelkasten
- Basic project structure
