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
git clone https://github.com/pyrite-wiki/pyrite.git
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
```

Pytest prints the current collected and passed test counts in its summary;
they change as the project and extensions grow.

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
# Everything, in parallel. This is what the pre-push hook and CI run.
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

The full suite can take several minutes; runtime varies with available CPU
cores and system load.

**The runner itself is pinned.** `pytest`, `pytest-cov` and `pytest-xdist`
are exact `==` pins in the `dev` extra (#128) — not a floor like the rest of
the project's dependencies — so every worktree venv and every CI leg run the
identical version. An unbounded `pytest>=8.0.0` once resolved 9.1.1 on one
interpreter and 9.0.2 on another; a change that passed the PR gate under one
version broke `dev` under the other. `tests/test_dev_process_config.py`
asserts the pins stay exact, so loosening one is a visible diff, not a silent
drift on the next `uv pip install`. After changing a pin, refresh your
worktree's venv and confirm it took:

```bash
uv pip install --python .venv/bin/python -e ".[all,dev]"
.venv/bin/python -m pytest --version
```

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
| pre-push | `pytest tests/ extensions/ -n auto`, only when the push touches code or config | Several minutes; varies by machine and load |

CI runs the same checks plus the full Python matrix, Postgres, the frontend
build and Playwright. `--no-verify` is for a documented emergency, not for a
red test you did not write; if a test you did not touch fails, say so in the PR
and we will look at it together.

**Claiming an issue:** before you spend more than an hour on an issue, say so
on the issue: two or three lines on how you'll fix it and what test proves
it. A draft PR with that in the body is even better — we'll steer you there
before you write much, and the draft is visible to everyone else looking at
the issue. The plan scales with the change: for a `good first issue` one
sentence is enough ("I'll add `id`/`kb_name` to the three projections and a
test per command").

A claim with no PR after 5 days lapses. Two people on one issue is fine — the
first PR that meets the acceptance criteria merges, and we credit the other
in the changelog entry for the change.

A placeholder commit or file is not a claim, and we don't merge placeholders.

Push as you go. A fix that exists only on your machine cannot be reviewed,
and "it's in a local commit" has cost a round trip more than once.

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

- **Bugs and requests → [GitHub Issues](https://github.com/pyrite-wiki/pyrite/issues).**
  Anyone can file one; use the templates. Issues labelled
  [`good first issue`](https://github.com/pyrite-wiki/pyrite/labels/good%20first%20issue)
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

**Contributing a fix.** The PRs that merge fastest here look like this — and
the ones that arrived on 2026-09-18 from four first-time contributors all did:

- One issue per PR, and the diff stays inside it. A stray hunk from another
  project (an editor's `.gitignore` additions, say) is the most common thing a
  review asks to remove.
- A test that fails without the fix. Reviews run `scripts/verify-red.sh
  <test> <impl files>` to check exactly that; you can run it too.
- The full suite green locally: `pytest tests/ extensions/ -n auto`, plus
  `ruff check` and `ruff format --check`.
- A changelog fragment: a **new file** `changelog.d/<slug>.<section>.md`
  containing the bullet as it should read in the release notes. Do **not** edit
  `CHANGELOG.md` — it is the one file every pull request used to conflict on,
  and a fragment has a name nobody else picks, so two branches in flight cannot
  collide. `changelog.d/README.md` lists the sections and shows an example; the
  release script assembles the fragments when the release is cut.

  If your change touches `pyrite/` or `extensions/` and adds no fragment, CI
  leaves a **warning** on the pull request. It is a reminder, not a gate —
  nothing is blocked, and no one has to argue with a script about whether a
  change is user-visible. When it genuinely isn't one (a refactor with no
  behaviour change), say so in the pull-request description and the warning
  goes away:

  ```
  Changelog: none
  ```
- AI-assisted contributions are welcome here. If an AI coding agent wrote or
  co-wrote your change, declare it with a `Co-authored-by:` trailer on the
  commit (most agent tools add this automatically) — it is machine-readable,
  it survives a squash-merge, and it is the form we'll look for first. A
  mention in the PR body is welcome too, and helps the reviewer know what to
  look at first, but it's optional on top of the trailer, not instead of it.

What happens next: every outside PR gets a review within about an hour,
posted as a comment with a plain recommendation (merge as is, merge after
listed changes, or which of two competing PRs and what to credit from the
other). First-time contributors' CI runs wait for a maintainer to approve
them; that is a GitHub safety default, not a judgement. A maintainer may
rebase your branch or push one small, credited fixup commit to it with a
comment saying what changed — your commits and authorship stay yours. The
merge itself is the maintainer's click.

**Security issues:** never in a public issue — see [SECURITY.md](SECURITY.md).

**Private material:** this repository and its KB are public. Placeholders, not
names, for anything that is not yours to publish; no absolute home paths.

## Project Configuration

- KB config: `kb.yaml` in each KB directory
- Claude Code skill: `.claude/skills/pyrite-dev/SKILL.md`
- Plugin developer guide: `kb/notes/plugin-developer-guide.md`
- Architecture docs: `kb/components/` and `kb/adrs/`

## Getting Help

- A bug or a feature request: open an issue
- A question about how something works: open an issue with the `question` label
- Something you found by deploying it: that is the most valuable report there
  is — see the v0.24.1 notes for the three that shaped that release

## Contributors

Maintainer: Mark Ramm (BDFL; see ADR-0032). Contributors are credited by
name in the release notes of the release their work ships in (the runbook
lists every outside author of a merged PR), in the changelog entry for the
change, and in the README.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
