# Pyrite Development Roadmap

## Status: Active Development

Multi-KB research infrastructure for citizen journalists and AI agents. Inspired by joshylchen/zettelkasten, now developed independently at markramm/pyrite.

## Completed ✓

### Phase 1: Core Infrastructure (Commits fe98f26 → 6a850cc)

- [x] **Multi-KB Configuration System** — Support for multiple knowledge bases with different types (Events, Research)
- [x] **Entry Models** — EventEntry, ResearchEntry with full frontmatter parsing
- [x] **GitHub OAuth** — Private repository access for collaborative research
- [x] **SQLite FTS5 Storage** — Full-text search with BM25 ranking

### Phase 2: Interfaces (Commits 9e64a8b → e53d381)

- [x] **Typer CLI** — Rich command-line interface (`pyrite`)
- [x] **MCP Server** — Model Context Protocol server for Claude Code integration
- [x] **Architecture Documentation** — System design and API reference

### Phase 3: Agent Integration (Commits 1d52c8f → 5fa6258)

- [x] **Agent-Optimized CLIs** — Permission-separated `pyrite-read` and `pyrite` commands
  - JSON output by default
  - Structured error messages with doc links
  - Semantic exit codes
  - FTS5 query sanitization for hyphenated terms
- [x] **Claude Skill** — `.claude/skills/kb/skill.md` for Claude Code discoverability
- [x] **CLI Tests** — 15 tests covering read/write operations

### Phase 4: REST API (Current)

- [x] **FastAPI Server** — Full REST API at `/` with OpenAPI docs
  - CORS enabled for web frontends
  - All endpoints return Pydantic models
  - Dependency injection for config/db
- [x] **Endpoints Implemented:**
  - `GET /kbs` — List knowledge bases
  - `GET /search` — Full-text search with filters
  - `GET /entries/{id}` — Get entry by ID
  - `POST /entries` — Create new entry
  - `PUT /entries/{id}` — Update entry
  - `DELETE /entries/{id}` — Delete entry
  - `GET /timeline` — Timeline events with filters
  - `GET /tags` — Tags with counts
  - `GET /actors` — Actors with counts
  - `GET /stats` — Index statistics
  - `POST /index/sync` — Trigger index sync
  - `GET /health` — Health check
- [x] **REST API Tests** — 12 tests covering all endpoints
- [x] **Entry Point** — `pyrite-server` command to run API

## Current Test Status

```
136 tests passing, 3 skipped (fastapi/typer not installed)
├── test_agent_cli.py: 15 tests
├── test_config.py: 15 tests
├── test_integration.py: 17 tests
├── test_migrations.py: 11 tests
├── test_models.py: 15 tests
├── test_services.py: 42 tests (including 12 query expansion tests)
├── test_storage.py: 15 tests
├── test_rest_api.py: 12 tests (skipped without fastapi)
└── test_mcp_server.py: 24 tests (skipped without fastapi)
```

## Planned Work

### Technical Debt (Priority)

**Priority 1 — Critical:** ✓ Complete
- [x] **Schema Versioning & Migrations** — `pyrite/storage/migrations.py`
  - Version tracking via `schema_version` table
  - `MigrationManager` with forward/rollback support
  - Auto-runs on CascadeDB initialization
  - 11 new tests in `tests/test_migrations.py`
- [x] **Service Layer** — `pyrite/services/`
  - `KBService`: KB listing, entry CRUD, index sync
  - `SearchService`: FTS5 query sanitization, search operations
  - 18 new tests in `tests/test_services.py`
- [x] **CONTRIBUTING.md** — Development workflow documentation
  - Setup instructions, code standards, PR process

**Priority 2 — High:** ✓ Complete
- [x] **Pre-commit Hooks** — `.pre-commit-config.yaml`
  - Ruff linting and formatting
  - Trailing whitespace, YAML validation
  - Pytest quick check on commit
  - Install: `pre-commit install`
- [x] **CHANGELOG.md** — Track changes for releases
- [x] **UPSTREAM_CHANGES.md** — Document differences from original joshylchen/zettelkasten inspiration

**Priority 3 — Medium:** ✓ Complete
- [x] **Integration Tests** — `tests/test_integration.py` (16 tests)
  - File → Repository → Index → Database → Search flow
  - Create, update, delete operations
  - Tag and actor indexing
  - Timeline date/importance filtering
  - Index sync for manual file changes
  - FTS5 edge cases (hyphens, special chars)
  - Migration integration
- [x] **Structured Logging** — `pyrite/logging.py`
  - Replaced print() with logging in storage modules
  - Configurable log levels
  - Module-specific loggers
- [x] **Refactor Large Files** — Completed
  - `cli.py` (992 lines) -> `cli/` package (4 files: `__init__.py`, `kb_commands.py`, `index_commands.py`, `search_commands.py`)
  - `server/api.py` (658 lines) -> extracted Pydantic models to `server/schemas.py` (~475 lines remaining)
  - `storage/database.py` (766 lines) -> extracted SQL DDL to `storage/schema.py` (~630 lines remaining)

**Priority 4 — Code Quality & Open Source:** ✓ Complete
- [x] **GitHub Actions CI** — `.github/workflows/ci.yml`
  - Python 3.11/3.12/3.13 matrix testing
  - Ruff lint + format checks
  - mypy type checking
  - Separate job for full test suite with optional deps
- [x] **Open Source Governance Files**
  - `CODE_OF_CONDUCT.md` (Contributor Covenant)
  - `SECURITY.md` (vulnerability reporting)
  - `.github/ISSUE_TEMPLATE/` (bug report, feature request)
  - `.github/PULL_REQUEST_TEMPLATE.md`
- [x] **Legacy Cleanup**
  - Removed legacy `mcp_server.py`, `setup_mcp.py` root scripts
  - Removed legacy test files importing old `zettelkasten_assistant`
  - Fixed Dockerfile module reference
  - Cleaned all stale legacy references from docs/config
- [x] **Deprecation Warning Fixes**
  - sqlite3 date/datetime adapter warnings (1218 per test run → 0)
  - Lazy imports in `server/__init__.py` for optional fastapi dependency
  - `pytest.importorskip` for graceful test skipping without fastapi

---

### Phase 5: Web UI (Current)

- [x] **Streamlit app structure** — Multi-page app with navigation
- [x] **Search page** — Full-text search with faceted filtering (tags, type, date)
- [x] **Timeline page** — Browse events by date with importance filter
- [x] **Actors page** — Browse actors by mention count
- [x] **Entry detail page** — Full content view with links and sources
- [x] **Data layer** — Cached access to DB via `ui/data.py`
- [x] **Entry point** — `pyrite-ui` command to launch

- [x] **Relationship graph viewer** — Interactive graph visualization using streamlit-agraph
  - Shows outgoing links, backlinks, and related entries as nodes/edges
  - Color-coded by entry type, sized by importance
  - Clickable nodes navigate to entry detail
- [x] **Entry editor with live preview** — In-browser editing on entry detail page
  - Edit title, body (markdown), tags, importance, status
  - Side-by-side live markdown preview
  - Saves via KBService with automatic re-indexing

### Phase 6: Semantic Search ✓ Complete

- [x] Vector embeddings for entries — `services/embedding_service.py`
- [x] sqlite-vec integration (local-first) — via `storage/database.py` vec_entry table
- [x] Hybrid search (FTS5 + vector similarity) — Reciprocal Rank Fusion in `services/search_service.py`
- [x] AI-powered query expansion — `services/query_expansion_service.py`
  - Supports Anthropic and OpenAI providers
  - `--expand` / `-x` flag on all search interfaces (CLI, API, MCP, UI)
  - Graceful fallback for stub/none providers or missing SDKs

### Phase 7: Collaboration

- [ ] Multi-user attribution tracking
- [ ] Conflict resolution for concurrent edits
- [ ] Review workflow for entry quality
- [ ] Change notifications

### Phase 8: FollowTheMoney Export (Deferred)

*Waiting on Aleph Pro subscription for API access*

- [ ] FtM entity mapping for actors, organizations, events
- [ ] Export command for Aleph/OpenAleph compatibility
- [ ] Relationship export as edges

## Branch Strategy

- **Main branch:** `main` on markramm/pyrite
- **Feature branches:** created from `main` for new work, merged via PR

## Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `pyrite` | `pyrite.cli:main` | Full CLI (Typer) |
| `pyrite` | `pyrite.write_cli:main` | Agent CLI (full access) |
| `pyrite-read` | `pyrite.read_cli:main` | Agent CLI (read-only) |
| `pyrite-server` | `pyrite.server.api:main` | REST API server |

## Configuration

```yaml
# ~/.pyrite/config.yaml
knowledge_bases:
  - name: timeline
    path: /path/to/timeline
    type: events
  - name: research-kb
    path: /path/to/research-kb
    type: research

settings:
  index_path: ~/.pyrite/index.db
```

## Key Files

```
pyrite/
├── config.py           # Configuration loading and validation
├── models.py           # EventEntry, ResearchEntry models
├── cli/                # Typer CLI (pyrite)
│   ├── __init__.py     # App setup, repo/auth/get/config/serve/mcp commands
│   ├── kb_commands.py  # KB management (list, add, remove, discover, validate)
│   ├── index_commands.py # Index management (build, sync, stats, embed, health)
│   └── search_commands.py # Search command with file fallback
├── read_cli.py         # Read-only agent CLI (pyrite-read)
├── write_cli.py        # Full access agent CLI (pyrite)
├── server/
│   ├── api.py          # FastAPI REST server
│   ├── schemas.py      # Pydantic models for API
│   └── mcp_server.py   # MCP protocol server
├── services/
│   ├── kb_service.py   # KB operations (CRUD, index)
│   ├── search_service.py # Search with FTS5 sanitization + hybrid/expansion
│   ├── embedding_service.py # Vector embeddings via sentence-transformers
│   └── query_expansion_service.py # AI-powered query expansion
└── storage/
    ├── database.py     # SQLite FTS5 operations
    ├── schema.py       # SQL DDL for core schema
    ├── repository.py   # File-based KB operations
    ├── index.py        # Indexing and sync
    └── migrations.py   # Schema versioning

.claude/skills/kb/
└── skill.md            # Claude Code skill documentation

docs/
├── ARCHITECTURE.md     # System design
└── ROADMAP.md          # This file
```
