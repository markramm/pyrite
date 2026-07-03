# Pyrite Development Guide

Pyrite is a knowledge infrastructure platform — Knowledge-as-Code for humans and AI agents.

## Using the KB for Project Context

This project has a comprehensive knowledge base in `kb/` indexed by Pyrite's own tools. **Use the CLI to get context before and during work** — it's faster and cheaper than reading files manually.

### Quick Context Lookups

```bash
# Search for anything — architecture, decisions, components, backlog items
.venv/bin/pyrite search "<topic>" -k pyrite

# Semantic search (finds conceptually related content, not just keyword matches)
.venv/bin/pyrite search "<question>" -k pyrite --mode semantic

# Get a specific entry by ID
.venv/bin/pyrite get <entry-id> -k pyrite

# Browse project structure
.venv/bin/pyrite sw components    # Core modules and services
.venv/bin/pyrite sw adrs          # Architecture Decision Records
.venv/bin/pyrite sw backlog       # All backlog items with status
.venv/bin/pyrite sw standards     # Coding standards and conventions

# Find what links to something
.venv/bin/pyrite backlinks <entry-id> -k pyrite

# Browse by tag
.venv/bin/pyrite tags -k pyrite
```

### When to Use KB Tools

- **Starting work on a feature**: Search for the backlog item, related ADRs, and component docs
- **Understanding architecture**: `pyrite sw components` and `pyrite sw adrs`
- **Finding related code**: `pyrite search "<module or pattern>" -k pyrite --mode hybrid`
- **Checking what's been decided**: `pyrite search "<topic>" -k pyrite` — ADRs and design docs will surface
- **Before modifying shared files**: Search for the file path to see what docs reference it

### Updating the KB After Work

When your work changes architecture, adds components, or completes backlog items:

```bash
# Sync index to pick up file changes
.venv/bin/pyrite index sync

# Create new entries using proper types
.venv/bin/pyrite create -k pyrite -t component --title "..." -b "..." --tags core
.venv/bin/pyrite create -k pyrite -t backlog_item --title "..." -b "..." --tags enhancement

# Create new ADRs
.venv/bin/pyrite sw new-adr --title "..." --status accepted

# Verify your changes are findable
.venv/bin/pyrite search "<your feature>" -k pyrite
.venv/bin/pyrite index health
```

Use correct `type` frontmatter so plugin tools can find entries:
- `type: component` (with `kind`, `path`, `owner`, `dependencies`) — `pyrite sw components`
- `type: adr` (with `adr_number`, `status`, `date`) — `pyrite sw adrs`
- `type: backlog_item` (with `kind`, `status`, `priority`, `effort`) — `pyrite sw backlog`
- `type: standard` — `pyrite sw standards`

## Key Architecture

- **Core code**: `pyrite/` — CLI, server, storage, services, plugins, models
- **REST API**: `pyrite/server/api.py` (factory + deps) + `pyrite/server/endpoints/` (per-feature modules)
- **MCP server**: `pyrite/server/mcp_server.py` (3-tier tools)
- **Extensions**: `extensions/` — zettelkasten, social, encyclopedia, software-kb, journalism-investigation, cascade
- **Web frontend**: `web/` — SvelteKit + Svelte 5
- **Knowledge base**: `kb/` — ADRs, backlog, components, designs, standards, runbooks

## Git Workflow (ADR-0025)

- **`dev`** — daily development (default branch). All work happens here.
- **`main`** — stable releases only. Merge from dev requires passing CI.
- Deploy demo.pyrite.wiki from `dev`, capturecascade.org from `main` tags.
- See `.claude/skills/pyrite-dev/SKILL.md` for release and deploy commands.

## Testing

```bash
# Backend tests (~2700 tests)
.venv/bin/pytest tests/ -v

# Frontend
cd web && npm run build && npm run test:unit

# Linting
ruff check pyrite/
```

## Parallel Agents

**Do NOT use `isolation: "worktree"` for parallel agents.** Worktree merges are fragile and expensive — conflict markers, regex group mismatches, and stray artifacts cost more tokens than Edit retries.

Instead, launch agents without isolation. They work directly on the current branch (`dev`). Use **file footprint planning** to minimize collisions. When agents share a file, the Edit tool's exact-match replacement fails gracefully on conflict — the agent retries with the updated content. This is cheaper and self-correcting.

**Read `.claude/skills/pyrite-dev/parallel-agents.md` before launching parallel agents.** It has the full protocol: wave planning, file footprint validation, agent prompt templates, and merge steps.

## Multi-Session Git Hazard

Two or more Claude sessions (a cron job, a manual session, a concurrent worktree agent) can commit to `dev` concurrently — observed 2026-07-02: a backlog regroom session and a 0.25 implementation session interleaving commits on the same branch. There's no lock; the only protection is discipline:

- **Stage explicit paths only.** Never `git add -A` or `git add .` — another session's in-progress edit can be sitting unstaged in the same working tree and get swept into your commit.
- **Check `git status` before staging.** If you see files you didn't touch, another session is active — don't silently include or discard them.
- **Re-read files before editing** if there's any chance the tree moved since you last read them (a concurrent session's commit, or the Edit tool reporting "modified since read"). Don't blind-retry an Edit against stale content.
- **Never assume you're the only writer.** A clean `git status` at the start of your turn doesn't guarantee it stays clean mid-task.

## Pre-commit Hooks

One-time setup on a fresh clone: `.venv/bin/pip install -e ".[dev]"` (installs `pre-commit`), then `.venv/bin/pre-commit install`. If that fails with "Cowardly refusing to install hooks with core.hooksPath set", run `git config --unset-all core.hooksPath` first — some environments set it to a directory of unused `.sample` files, which blocks installation.

Once installed, ruff, ruff-format, trailing-whitespace, end-of-file, check-yaml, check-large-files, check-merge-conflict, debug-statements, KB schema validation, and pytest run automatically on every commit. If ruff-format modifies files, re-stage and commit again.

The pytest hook runs the full suite with `-x` (stop on first failure) and is fast-failing but not currently 100% reliable: a small number of tests are order-dependent and fail only under a full-suite run, never in isolation (tracked in `full-suite-only-flaky-tests-state-leak-across-test-files`). If a hook-blocked commit's failure is a test you didn't touch and it passes standalone, that's very likely one of these — verify with `pytest tests/ -q` (no `-x`) before concluding it's safe to bypass, and only use `--no-verify` with a clear justification in the commit message plus a linked ticket if the flake isn't already tracked.
