# Changelog

All notable changes to Pyrite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
