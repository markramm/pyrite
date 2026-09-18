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
# `.[all]` is the whole optional surface (CLI, server, MCP, AI) plus the test
# tooling. `.[dev]` alone is tooling only and cannot even collect the suite.
uv pip install -e ".[all]"

# Install all extensions (required for full test suite)
for ext in extensions/*/; do uv pip install -e "$ext"; done

# Install the git hooks (commit, commit-msg and pre-push in one go)
pre-commit install

# Verify installation
.venv/bin/pytest tests/ extensions/*/tests/ -q
# Expected: ~4000 tests passing
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

```bash
# Everything, in parallel (~1 min). This is what the pre-push hook and CI run.
.venv/bin/pytest tests/ extensions/ -n auto

# One file, or tests matching a pattern
.venv/bin/pytest tests/test_models.py
.venv/bin/pytest -k "search"

# Frontend
cd web && npm run check && npm run test:unit
```

The suite does not load the embedding model unless a test is marked
`@pytest.mark.embeddings`; everything else runs with `auto_embed` off. A test
that passes alone but fails under `-n auto` is a bug in that test (shared
state, a fixed wall-clock timeout, an unclosed database), not a reason to run
serially — `tests/test_task_claim_concurrency.py` shows the pattern for
process-spawning tests.

### Writing Tests

- Tests live in `tests/`; extension tests in `extensions/<name>/tests/`
- Name test files `test_*.py`
- A `fix:` commit must include a test that fails without the fix (a hook checks
  that it touches `tests/`)
- Use pytest fixtures for common setup (`tmp_kb`, isolated plugin registry);
  close any `PyriteDB` you open
- Use `in` not `len` for registry assertions (see [testing standards](kb/standards/testing-standards.md))

## Branches, hooks and pull requests

**Branches** (ADR-0025 and ADR-0032):

- `dev` is the default branch and where work integrates. `main` is releases
  only and moves by fast-forward to a commit that already passed CI.
- Branch from `dev`, open the PR against `dev`. Rebase is the default merge
  method (it keeps your commits and their messages); squash is fine for a
  branch whose history is noise.
- A PR merges when its checks are green **on top of current `dev`** — one
  required check, `gate`, summarizes the Python suite, the frontend build and
  KB validation (whichever the change needs), and the branch must be up to
  date. If `dev` is broken, nothing merges until it is fixed.

**Git hooks** — `pre-commit install` installs all three:

| Stage | Runs | Takes |
|---|---|---|
| commit | ruff, formatting, file hygiene, import-cycle check, KB schema validation | seconds |
| commit-msg | a `fix:` commit must touch `tests/` | — |
| pre-push | `pytest tests/ extensions/ -n auto`, only when the push touches code or config | ~1 min |

CI runs the same checks plus the full Python matrix, Postgres, the frontend
build and Playwright. `--no-verify` is for a documented emergency, not for a
red test you did not write; if a test you did not touch fails, say so in the PR
and we will look at it together.

**Pull requests:**

1. `git checkout -b fix/what-it-fixes dev` (or `feature/...`)
2. Write the failing test, then the fix
3. Push; the pre-push hook runs the suite
4. Open the PR against `dev` and fill in the template (`Fixes #N` for bugs)
5. Expect a first response **within a week**. If you have heard nothing after
   that, comment on the PR — it is a lapse, not a verdict.

Commit messages use conventional commits (`feat:`, `fix:`, `docs:`, `test:`,
`refactor:`, `ci:`, `kb:`).

## Where work is tracked

Two places, one rule — an item lives in exactly one of them (ADR-0033):

- **Bugs and requests → [GitHub Issues](https://github.com/markramm/pyrite/issues).**
  Anyone can file one; use the templates. Issues labelled
  [`good first issue`](https://github.com/markramm/pyrite/labels/good%20first%20issue)
  are small, well-specified and a fine place to start.
- **The roadmap → `kb/`** in this repo: epics, planned work and architecture
  decisions, browsable with the tool itself:

  ```bash
  pyrite sw backlog        # planned work, by priority
  pyrite sw adrs           # architecture decision records
  pyrite sw components     # module documentation
  ```

  `kb/roadmap.md` is the plan for the next releases. A request we accept gets a
  roadmap item that links back to the issue.

**Security issues:** never in a public issue — see [SECURITY.md](SECURITY.md).

**Private material:** this repository and its KB are public. Placeholders, not
names, for anything that is not yours to publish; no absolute home paths.

## Project Configuration

- KB config: `kb.yaml` in each KB directory
- Claude Code skill: `.claude/skills/pyrite-dev/SKILL.md`
- Plugin developer guide: `kb/standards/plugin-developer-guide.md`
- Architecture docs: `kb/components/` and `kb/adrs/`

## Getting Help

- A bug or a feature request: open an issue
- A question about how something works: open an issue with the `question` label
- Something you found by deploying it: that is the most valuable report there
  is — see the v0.24.1 notes for the three that shaped that release

## Contributors

Maintainer: Mark Ramm (BDFL; see ADR-0032). Contributors are credited in the
CHANGELOG for the release their work ships in, and in the README.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
