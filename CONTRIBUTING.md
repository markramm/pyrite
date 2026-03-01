# Contributing to Pyrite

Thank you for considering contributing to Pyrite! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+ (3.13 recommended)
- Git
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/markramm/pyrite.git
cd pyrite

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e ".[dev]"

# Install all extensions (required for full test suite)
.venv/bin/pip install -e extensions/zettelkasten
.venv/bin/pip install -e extensions/social
.venv/bin/pip install -e extensions/encyclopedia
.venv/bin/pip install -e extensions/software-kb
.venv/bin/pip install -e extensions/task

# Install pre-commit hooks
pre-commit install

# Verify installation
.venv/bin/pytest tests/ extensions/*/tests/ -q
# Expected: 1654+ tests passing
```

See [Setting Up the Development Environment](kb/runbooks/setting-up-dev-environment.md) for troubleshooting.

## Code Standards

### Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check pyrite/

# Auto-fix issues
ruff check --fix pyrite/

# Format code
ruff format pyrite/
```

### Type Hints

- Use modern Python type hints (3.11+ syntax)
- `list[str]` not `List[str]`
- `str | None` not `Optional[str]`
- `dict[str, Any]` not `Dict[str, Any]`

### Imports

- Use absolute imports within the package
- Group imports: stdlib, third-party, local
- Let ruff sort imports automatically

## Architecture

### Layer Structure

```
pyrite/
├── models/          # Data models (Entry, core types, factory)
├── storage/         # File and database operations
│   ├── database.py  # PyriteDB: SQLAlchemy ORM + mixin-based modules
│   ├── repository.py # KBRepository: markdown files with YAML frontmatter
│   ├── index.py     # IndexManager: builds/syncs index from markdown
│   ├── migrations.py # MigrationManager: custom schema versioning
│   └── backends/    # SearchBackend protocol + implementations
│       ├── protocol.py        # SearchBackend structural protocol
│       ├── sqlite_backend.py  # SQLiteBackend (default: FTS5 + sqlite-vec)
│       └── postgres_backend.py # PostgresBackend (server: tsvector + pgvector)
├── services/        # Business logic (search, KB ops, QA, schema, etc.)
├── plugins/         # Plugin protocol, registry, context (DI)
├── cli/             # CLI commands (Typer sub-apps)
├── server/
│   ├── api.py       # FastAPI app factory
│   ├── endpoints/   # Per-feature REST endpoint modules
│   └── mcp_server.py # Three-tier MCP server
├── formats/         # Content negotiation (JSON, Markdown, CSV, YAML)
└── utils/           # Shared utilities (yaml, markdown)
```

### Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `pyrite` | `pyrite.cli:main` | Full CLI (Typer) — primary interface for humans and agents |
| `pyrite-read` | `pyrite.read_cli:main` | Read-only CLI (safe for untrusted agents) |
| `pyrite-admin` | `pyrite.admin_cli:main` | Admin CLI (DB management, config) |
| `pyrite-server` | `pyrite.server.api:main` | REST API + web UI server |

### Key Principles

1. **Service Layer**: Business logic lives in `services/`, not in CLI/API/MCP handlers
2. **Repository Pattern**: File operations go through `KBRepository`
3. **Two-Tier Durability**: Markdown files (git) = source of truth, SQLite/Postgres = derived index
4. **Plugin Protocol**: Extensions use structural typing (Protocol) — no base class inheritance required
5. **SearchBackend Abstraction**: All search operations go through `SearchBackend` protocol (SQLite or Postgres)

## Testing

### Running Tests

```bash
# Run all backend tests
.venv/bin/pytest tests/ -v

# Run extension tests too
.venv/bin/pytest tests/ extensions/*/tests/ -v

# Run specific test file
.venv/bin/pytest tests/test_models.py

# Run tests matching pattern
.venv/bin/pytest -k "search"

# Frontend tests
cd web && npm run test:unit
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use pytest fixtures for common setup (`tmp_kb`, isolated plugin registry)
- Test both success and error cases
- Use `in` not `len` for registry assertions (see [testing standards](kb/standards/testing-standards.md))

## Pull Request Process

### Before Submitting

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Write tests** for new functionality
3. **Run the test suite**: `.venv/bin/pytest tests/ -v`
4. **Run linting**: `ruff check --fix pyrite/ && ruff format pyrite/`
5. **Update documentation** if needed

### PR Guidelines

- Keep PRs focused on a single change
- Write clear commit messages
- Reference any related issues

### Commit Messages

Use conventional commits:

```
feat: add vector search support
fix: handle hyphens in FTS5 queries
docs: update API reference
test: add timeline endpoint tests
refactor: extract search service
```

## Project Configuration

- KB config: `kb.yaml` in each KB directory
- Claude Code skill: `.claude/skills/pyrite-dev/SKILL.md`
- Plugin developer guide: `kb/standards/plugin-developer-guide.md`
- Architecture docs: `kb/components/` and `kb/adrs/`

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Include reproduction steps for bugs

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
