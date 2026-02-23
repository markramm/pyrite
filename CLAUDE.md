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
- **Extensions**: `extensions/` — zettelkasten, social, encyclopedia, software-kb
- **Web frontend**: `web/` — SvelteKit + Svelte 5
- **Knowledge base**: `kb/` — ADRs, backlog, components, designs, standards, runbooks

## Testing

```bash
# Backend tests (583 tests)
.venv/bin/pytest tests/ -v

# Frontend
cd web && npm run build && npm run test:unit

# Linting
ruff check pyrite/
```

## Pre-commit Hooks

Ruff, ruff-format, trailing-whitespace, end-of-file, check-yaml, check-large-files, check-merge-conflict, debug-statements, and pytest run automatically. If ruff-format modifies files, re-stage and commit again.
