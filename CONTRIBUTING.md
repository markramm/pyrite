# Contributing to Pyrite

Thank you for considering contributing to Pyrite! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.11+
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

# Verify installation
pytest
```

### Configuration

Create a config file at `~/.pyrite/config.yaml`:

```yaml
knowledge_bases:
  - name: test-kb
    path: ./test-data/research
    type: research
  - name: test-timeline
    path: ./test-data/timeline
    type: events

settings:
  index_path: ~/.pyrite/index.db
```

## Code Standards

### Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Type Hints

- Use modern Python type hints (3.11+ syntax)
- `list[str]` not `List[str]`
- `str | None` not `Optional[str]`
- `dict[str, Any]` not `Dict[str, Any]`

### Imports

- Use absolute imports within the package
- Group imports: stdlib → third-party → local
- Let ruff sort imports automatically

### Documentation

- Docstrings for all public functions/classes
- Use Google-style docstrings
- Include Args, Returns, Raises sections where applicable

## Architecture

### Layer Structure

```
pyrite/
├── models/          # Data models (Entry, EventEntry, ResearchEntry)
├── storage/         # File and database operations
│   ├── database.py  # SQLite FTS5 operations
│   ├── repository.py # File-based KB operations
│   ├── index.py     # Indexing and sync
│   └── migrations.py # Schema versioning
├── services/        # Business logic (search, kb operations)
├── server/          # REST API (FastAPI)
├── ui/              # Web UI (Streamlit)
├── read_cli.py      # Read-only CLI
├── write_cli.py     # Full access CLI
└── mcp_server.py    # MCP protocol server
```

### Key Principles

1. **Service Layer**: Business logic lives in `services/`, not in CLI/API/UI
2. **Repository Pattern**: File operations go through `KBRepository`
3. **Unified Search**: Use `SearchService.sanitize_fts_query()` for all FTS5 queries

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pyrite

# Run specific test file
pytest tests/test_models.py

# Run tests matching pattern
pytest -k "search"
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use pytest fixtures for common setup
- Test both success and error cases

### Test Categories

- `tests/test_models.py` — Entry model parsing
- `tests/test_database.py` — FTS5 operations
- `tests/test_repository.py` — File operations
- `tests/test_agent_cli.py` — CLI commands
- `tests/test_rest_api.py` — API endpoints

## Pull Request Process

### Before Submitting

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Write tests** for new functionality
3. **Run the test suite**: `pytest`
4. **Run linting**: `ruff check --fix . && ruff format .`
5. **Update documentation** if needed

### PR Guidelines

- Keep PRs focused on a single change
- Write clear commit messages
- Reference any related issues
- Update CHANGELOG.md for user-facing changes

### Commit Messages

Use conventional commits:

```
feat: add vector search support
fix: handle hyphens in FTS5 queries
docs: update API reference
test: add timeline endpoint tests
refactor: extract search service
```

## Project Structure

### Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `pyrite` | `cli:main` | Full CLI (Typer) |
| `crk` | `write_cli:main` | Agent CLI (full access) |
| `crk-read` | `read_cli:main` | Agent CLI (read-only) |
| `crk-server` | `server.api:main` | REST API server |
| `crk-ui` | `ui.app:main` | Web UI |

### Configuration

- User config: `~/.pyrite/config.yaml`
- Index database: `~/.pyrite/index.db` (default)
- Claude skill: `.claude/skills/kb/skill.md`

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Include reproduction steps for bugs

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
