# Pyrite

Multi-KB research infrastructure for citizen journalists and AI agents. Git-native markdown storage with SQLite full-text search indexing.

## Architecture

- **Core**: Python package (`pyrite/`) with FastAPI REST API and MCP server
- **Web**: SvelteKit + CodeMirror 6 frontend (`web/`)
- **Extensions**: Plugin system via entry points (`extensions/`)
- **Knowledge Base**: ADRs, designs, standards, backlog (`kb/`)

## Key Commands

- `pyrite serve` -- Start web server (API + SPA)
- `pyrite mcp` -- Start MCP server (stdio, write tier)
- `pyrite search "query"` -- Full-text search across KBs
- `pyrite get <id>` -- Retrieve entry by ID
- `pyrite kb list` -- List configured knowledge bases
- `pyrite index build` -- Rebuild search index
- `.venv/bin/pytest tests/ -v` -- Run backend tests
- `cd web && npm run test:unit` -- Run frontend tests

## Skills Available

- **kb** (`.claude/skills/kb/`) -- Search, read, create, and update KB entries
- **pyrite-dev** (`.claude/skills/pyrite-dev/`) -- Development workflow for Pyrite core, extensions, web frontend, and API

## Project Knowledge

See `kb/` for architectural decisions (ADRs), design docs, standards, and the prioritized backlog.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite + FTS5, Typer CLI |
| Frontend | SvelteKit, Svelte 5, CodeMirror 6, Tailwind CSS 4 |
| MCP | MCP 2024-11-05 protocol, 3-tier tools (read/write/admin) |
| Plugins | Entry-point based plugin system with protocol class |
| Testing | pytest, Vitest, Playwright |
| Storage | Git-native markdown + YAML frontmatter |
