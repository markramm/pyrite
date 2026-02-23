
# User Guide

## What is Pyrite?
A multi-KB research infrastructure for citizen journalists and AI agents. It stores entries as Markdown files (with YAML frontmatter) and provides full-text search, timeline queries, and multiple interfaces.

## Core Concepts
- **Knowledge Base (KB)**: A directory of related entries. Can be of type `events` or `research`.
- **Event Entry**: A dated event with importance rating, actors, and tags.
- **Research Entry**: A research document (actor profile, organization, topic, etc.) with sources and tags.
- **Index**: SQLite FTS5 database for fast full-text search across all KBs.

## CLI Usage

### Main CLI
```bash
# List all knowledge bases
pyrite kbs

# Search across all KBs
pyrite search "immigration policy"

# Get timeline of events
pyrite timeline --from 2025-01-01 --to 2025-12-31
```

### Agent CLIs (for AI integration)
```bash
# Read-only operations (safe for AI agents)
pyrite-read list-kbs
pyrite-read search "Stephen Miller"
pyrite-read get <entry-id>
pyrite-read timeline --from 2025-01-01

# Write operations (create/update entries)
pyrite create-event --kb my-events --title "New Event" --date 2025-01-15
pyrite create-actor --kb my-research --name "Jane Doe" --role "Policy Analyst"
```

## REST API
```bash
# Start the server
pyrite-server

# Or directly:
python -m pyrite.server.api
```
Then visit `http://localhost:8088/docs` for interactive API docs.

## Streamlit Web UI
```bash
pyrite-ui
```

## MCP Server (for Claude Code)
See [MCP_SETUP.md](MCP_SETUP.md) for integration with Claude Code and other MCP-compatible tools.
